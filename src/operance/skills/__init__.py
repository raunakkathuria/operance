"""Declarative desktop skill packs for typed command expansion."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable, Mapping

from ..launch_targets import normalize_explicit_url_target
from ..models.actions import ActionPlan, PlanSource, ToolName, TypedAction
from ..platforms import get_platform_provider
from ..registry import build_default_action_registry
from ..validator import PlanValidator


class SkillValidationError(ValueError):
    """Raised when a skill pack cannot be loaded safely."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass(slots=True, frozen=True)
class SkillCommand:
    command_id: str
    phrases: tuple[str, ...]
    actions: tuple[TypedAction, ...]
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.command_id,
            "description": self.description,
            "phrases": list(self.phrases),
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass(slots=True, frozen=True)
class SkillPack:
    skill_id: str
    name: str
    description: str
    commands: tuple[SkillCommand, ...]
    platforms: tuple[str, ...] = ()
    source: str = "builtin"

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "platforms": list(self.platforms),
            "source": self.source,
            "commands": [command.to_dict() for command in self.commands],
        }


@dataclass(slots=True, frozen=True)
class SkillLibrary:
    packs: tuple[SkillPack, ...]
    platform_family: str | None = None
    warnings: tuple[str, ...] = ()

    def match(self, text: str) -> SkillCommand | None:
        normalized = normalize_skill_phrase(text)
        for pack in self.packs:
            if not self.pack_applies(pack):
                continue
            for command in pack.commands:
                if normalized in command.phrases:
                    return command
        return None

    def pack_applies(self, pack: SkillPack) -> bool:
        """A pack applies when it declares no platforms or names the current one."""

        if not pack.platforms or self.platform_family is None:
            return True
        return self.platform_family in pack.platforms

    def to_dict(self) -> dict[str, object]:
        active_packs = [pack for pack in self.packs if self.pack_applies(pack)]
        command_count = sum(len(pack.commands) for pack in active_packs)
        phrase_count = sum(len(command.phrases) for pack in active_packs for command in pack.commands)
        return {
            "status": "warn" if self.warnings else "ok",
            "summary": {
                "pack_count": len(active_packs),
                "command_count": command_count,
                "phrase_count": phrase_count,
                "inactive_pack_count": len(self.packs) - len(active_packs),
                "platform_family": self.platform_family,
            },
            "safety_contract": _safety_contract(),
            "warnings": list(self.warnings),
            "packs": [
                {**pack.to_dict(), "active": self.pack_applies(pack)} for pack in self.packs
            ],
        }


def normalize_skill_phrase(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"[?!,]+", "", normalized)
    normalized = normalized.rstrip(".")
    return re.sub(r"\s+", " ", normalized)


def build_default_skill_library() -> SkillLibrary:
    return SkillLibrary(())


def build_skill_library_from_paths(
    paths: Iterable[Path],
    *,
    include_builtins: bool = True,
    strict: bool = False,
    system_name: str | None = None,
) -> SkillLibrary:
    """Load skill packs, skipping unreadable packs unless strict is requested.

    A malformed pack must not stop the daemon, tray, or MCP server from starting,
    so by default each failure becomes a warning and the remaining packs load.
    """

    packs: list[SkillPack] = list(build_default_skill_library().packs) if include_builtins else []
    warnings: list[str] = []
    for path in paths:
        for pack_path in _expand_skill_pack_paths(path):
            try:
                packs.append(load_skill_pack_from_path(pack_path))
            except (SkillValidationError, OSError) as exc:
                if strict:
                    raise
                warnings.append(f"{pack_path}: skipped: {exc}")
    warnings.extend(_phrase_collision_warnings(packs))
    return SkillLibrary(
        packs=tuple(packs),
        platform_family=get_platform_provider(system_name=system_name).platform_family,
        warnings=tuple(warnings),
    )


def load_skill_library_from_mappings(mappings: Iterable[Mapping[str, object]]) -> SkillLibrary:
    return SkillLibrary(tuple(load_skill_pack_from_mapping(mapping) for mapping in mappings))


def load_skill_pack_from_path(path: Path) -> SkillPack:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillValidationError([f"{path}: invalid JSON: {exc.msg}"]) from exc
    if not isinstance(payload, Mapping):
        raise SkillValidationError([f"{path}: skill pack must be a JSON object"])
    return load_skill_pack_from_mapping(payload, source=str(path))


def load_skill_pack_from_mapping(
    mapping: Mapping[str, object],
    *,
    source: str = "builtin",
) -> SkillPack:
    errors: list[str] = []
    skill_id = _required_string(mapping, "skill_id", errors)
    name = _required_string(mapping, "name", errors)
    description = _required_string(mapping, "description", errors)
    platforms = _optional_string_list(mapping, "platforms", errors)
    command_payloads = mapping.get("commands")
    if not isinstance(command_payloads, list) or not command_payloads:
        errors.append("commands must be a non-empty list")
        command_payloads = []

    commands: list[SkillCommand] = []
    phrase_index: set[str] = set()
    for index, command_payload in enumerate(command_payloads):
        if not isinstance(command_payload, Mapping):
            errors.append(f"commands[{index}] must be an object")
            continue
        command = _load_skill_command(command_payload, index, errors)
        if command is None:
            continue
        duplicate_phrases = sorted(phrase for phrase in command.phrases if phrase in phrase_index)
        if duplicate_phrases:
            errors.append(f"{command.command_id}: duplicate phrases: {', '.join(duplicate_phrases)}")
            continue
        phrase_index.update(command.phrases)
        commands.append(command)

    if skill_id and not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", skill_id):
        errors.append("skill_id must use lowercase letters, digits, dots, underscores, or hyphens")

    if errors:
        raise SkillValidationError(errors)

    return SkillPack(
        skill_id=skill_id,
        name=name,
        description=description,
        platforms=tuple(platforms),
        commands=tuple(commands),
        source=source,
    )


def action_plan_from_skill_command(command: SkillCommand, original_text: str) -> ActionPlan:
    return ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text=original_text,
        actions=list(command.actions),
    )


def _load_skill_command(
    mapping: Mapping[str, object],
    index: int,
    errors: list[str],
) -> SkillCommand | None:
    command_id = _required_string(mapping, "id", errors, prefix=f"commands[{index}].")
    description = str(mapping.get("description") or "")
    phrases = _required_phrase_list(mapping, command_id or f"commands[{index}]", errors)
    action_payloads = mapping.get("actions")
    if action_payloads is None and isinstance(mapping.get("action"), Mapping):
        action_payloads = [mapping["action"]]
    if not isinstance(action_payloads, list) or not action_payloads:
        errors.append(f"{command_id or f'commands[{index}]'}: actions must be a non-empty list")
        return None
    if len(action_payloads) > 2:
        errors.append(f"{command_id or f'commands[{index}]'}: actions may contain at most 2 typed actions")
        return None

    actions = _load_typed_actions(action_payloads, command_id or f"commands[{index}]", errors)
    if not command_id or not phrases or not actions:
        return None
    return SkillCommand(
        command_id=command_id,
        description=description,
        phrases=tuple(phrases),
        actions=tuple(actions),
    )


def _load_typed_actions(
    action_payloads: list[object],
    command_id: str,
    errors: list[str],
) -> list[TypedAction]:
    actions: list[TypedAction] = []
    for index, action_payload in enumerate(action_payloads):
        if not isinstance(action_payload, Mapping):
            errors.append(f"{command_id}: actions[{index}] must be an object")
            continue
        tool_value = action_payload.get("tool")
        if not isinstance(tool_value, str) or not tool_value:
            errors.append(f"{command_id}: actions[{index}].tool must be a non-empty string")
            continue
        try:
            tool = ToolName(tool_value)
        except ValueError:
            errors.append(f"unknown tool: {tool_value}")
            continue
        args_value = action_payload.get("args", {})
        if not isinstance(args_value, dict):
            errors.append(f"{command_id}: actions[{index}].args must be an object")
            continue
        target_args = _resolve_target_args(tool, action_payload, command_id, index, errors)
        if target_args is None:
            continue
        args = {**target_args, **dict(args_value)}
        actions.append(TypedAction(tool=tool, args=args))

    if not actions:
        return []

    validation = PlanValidator(build_default_action_registry()).validate(
        ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=f"skill:{command_id}",
            actions=actions,
        )
    )
    if not validation.valid or validation.normalized_plan is None:
        errors.extend(validation.errors)
        return []
    return list(validation.normalized_plan.actions)


def _resolve_target_args(
    tool: ToolName,
    action_payload: Mapping[str, object],
    command_id: str,
    index: int,
    errors: list[str],
) -> dict[str, object] | None:
    if "target" not in action_payload:
        return {}
    target = action_payload.get("target")
    if not isinstance(target, Mapping):
        errors.append(f"{command_id}: actions[{index}].target must be an object")
        return None
    kind = target.get("kind")
    if not isinstance(kind, str) or not kind:
        errors.append(f"{command_id}: actions[{index}].target.kind must be a non-empty string")
        return None

    if kind == "app":
        name = target.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{command_id}: actions[{index}].target.name must be a non-empty string")
            return None
        if tool not in {ToolName.APPS_LAUNCH, ToolName.APPS_FOCUS, ToolName.APPS_QUIT}:
            errors.append(f"{command_id}: app target is only valid for app tools")
            return None
        return {"app": name.strip()}

    if kind == "url":
        value = target.get("value")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{command_id}: actions[{index}].target.value must be a non-empty string")
            return None
        if tool != ToolName.APPS_LAUNCH:
            errors.append(f"{command_id}: url target is only valid for apps.launch")
            return None
        return {"app": normalize_explicit_url_target(value.strip())}

    if kind == "desktop_file":
        name = target.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{command_id}: actions[{index}].target.name must be a non-empty string")
            return None
        if tool not in {ToolName.FILES_OPEN, ToolName.FILES_DELETE_FILE}:
            errors.append(f"{command_id}: desktop_file target is only valid for file open/delete tools")
            return None
        return {"location": "desktop", "name": name.strip()}

    if kind == "desktop_folder":
        name = target.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{command_id}: actions[{index}].target.name must be a non-empty string")
            return None
        if tool not in {ToolName.FILES_OPEN, ToolName.FILES_DELETE_FOLDER}:
            errors.append(f"{command_id}: desktop_folder target is only valid for folder open/delete tools")
            return None
        return {"location": "desktop", "name": name.strip()}

    errors.append(f"{command_id}: unsupported target kind: {kind}")
    return None


def _required_string(
    mapping: Mapping[str, object],
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{key} must be a non-empty string")
        return ""
    return value.strip()


def _optional_string_list(mapping: Mapping[str, object], key: str, errors: list[str]) -> list[str]:
    value = mapping.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{key} must be a list of strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{key}[{index}] must be a non-empty string")
            continue
        result.append(item.strip())
    return result


def _required_phrase_list(
    mapping: Mapping[str, object],
    command_id: str,
    errors: list[str],
) -> list[str]:
    value = mapping.get("phrases")
    if not isinstance(value, list) or not value:
        errors.append(f"{command_id}: phrases must be a non-empty list")
        return []
    phrases: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{command_id}: phrases[{index}] must be a non-empty string")
            continue
        phrases.append(normalize_skill_phrase(item))
    return phrases


def _expand_skill_pack_paths(path: Path) -> list[Path]:
    expanded = path.expanduser()
    if expanded.is_dir():
        return sorted(expanded.glob("*.json"))
    return [expanded]


def _phrase_collision_warnings(packs: Iterable[SkillPack]) -> list[str]:
    """Report phrases claimed by more than one pack, where the first load wins."""

    claimed_by: dict[str, str] = {}
    warnings: list[str] = []
    for pack in packs:
        for command in pack.commands:
            for phrase in command.phrases:
                owner = claimed_by.get(phrase)
                if owner is None:
                    claimed_by[phrase] = pack.skill_id
                    continue
                if owner != pack.skill_id:
                    warnings.append(
                        f"phrase {phrase!r} is claimed by skill packs {owner} and "
                        f"{pack.skill_id}; {owner} wins because it loaded first"
                    )
    return warnings


def _safety_contract() -> dict[str, object]:
    return {
        "execution": "typed_actions_only",
        "raw_shell": "not_allowed",
        "validation": "all skill actions pass the Operance registry validator",
        "policy": "confirmation-gated actions remain confirmation-gated",
        "adapter_boundary": "skills describe intent; OS adapters execute native behavior",
    }
