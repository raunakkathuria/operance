"""Supported-command catalog and user-facing help text."""

from __future__ import annotations

from .doctor import build_environment_report
from .models.actions import ToolName
from .platforms import get_platform_provider
from .registry import build_default_action_registry


def build_supported_command_catalog(
    report: dict[str, object] | None = None,
    *,
    available_only: bool = False,
) -> dict[str, object]:
    environment_report = build_environment_report() if report is None else report
    provider = get_platform_provider(
        system_name=str(environment_report.get("platform") or ""),
        provider_id=(
            str(environment_report["platform_provider"])
            if isinstance(environment_report.get("platform_provider"), str)
            else None
        ),
    )
    snapshot = _build_setup_snapshot(environment_report)
    steps_by_name = {step.name: step for step in snapshot.steps}
    registry = build_default_action_registry()

    commands_by_domain: dict[str, list[dict[str, object]]] = {}

    for spec in registry.list_specs():
        blockers = provider.tool_live_runtime_blockers(spec.name, steps_by_name)
        release_verification_status = _tool_release_verification_status(
            spec.name,
            provider.release_verified_tools,
        )
        live_runtime_status = _tool_live_runtime_status(blockers, release_verification_status)
        if available_only and live_runtime_status != "available":
            continue

        domain = spec.name.value.split(".", 1)[0]
        commands_by_domain.setdefault(domain, []).append(
            {
                "tool": spec.name.value,
                "description": spec.description,
                "example_transcripts": list(spec.example_transcripts),
                "usage_pattern": _tool_usage_pattern(spec.name),
                "risk_tier": spec.risk_tier.name.lower(),
                "requires_confirmation": spec.requires_confirmation,
                "undoable": spec.undoable,
                "live_runtime_status": live_runtime_status,
                "live_runtime_blockers": blockers,
                "release_verification_status": release_verification_status,
                "release_verification_target": provider.release_verification_target,
                "live_runtime_suggested_command": provider.tool_live_runtime_suggested_command(
                    spec.name,
                    steps_by_name,
                ),
            }
        )

    domains = [
        {
            "domain": domain,
            "label": _domain_label(domain),
            "description": _domain_description(domain),
            "commands": commands_by_domain[domain],
        }
        for domain in sorted(commands_by_domain)
    ]
    all_commands = [
        command
        for domain in domains
        for command in domain["commands"]
    ]
    total_commands = len(all_commands)
    available_count = sum(1 for command in all_commands if command["live_runtime_status"] == "available")
    unverified_count = sum(1 for command in all_commands if command["live_runtime_status"] == "unverified")
    blocked_count = sum(1 for command in all_commands if command["live_runtime_status"] == "blocked")
    confirmation_count = sum(1 for command in all_commands if bool(command["requires_confirmation"]))
    return {
        "catalog_filter": "available_only" if available_only else "all",
        "summary": {
            "total_commands": total_commands,
            "available_commands": available_count,
            "unverified_commands": unverified_count,
            "confirmation_gated_commands": confirmation_count,
            "blocked_commands": blocked_count,
        },
        "domains": domains,
    }


def build_supported_command_help_text(catalog: dict[str, object]) -> dict[str, object]:
    summary = catalog.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    domains = catalog.get("domains")
    if not isinstance(domains, list):
        domains = []

    available_count = _int_value(summary.get("available_commands"))
    unverified_count = _int_value(summary.get("unverified_commands"))
    blocked_count = _int_value(summary.get("blocked_commands"))
    confirmation_count = _int_value(summary.get("confirmation_gated_commands"))

    details_lines: list[str] = []

    for domain in domains:
        if not isinstance(domain, dict):
            continue
        label = str(domain.get("label") or domain.get("domain") or "Commands")
        commands = domain.get("commands")
        if not isinstance(commands, list):
            continue

        available_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "available"
        ]
        unverified_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "unverified"
        ]
        blocked_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "blocked"
        ]

        if available_commands:
            details_lines.append(f"{label}:")
            for command in sorted(available_commands, key=_help_command_priority):
                line = _command_example_text(command, prefer_usage_pattern=True)
                details_lines.append(f"- {line}")

        if unverified_commands:
            details_lines.append(f"{label} not yet release-verified:")
            for command in sorted(unverified_commands, key=_help_command_priority):
                target = command.get("release_verification_target")
                target_text = (
                    f" -> {target}"
                    if isinstance(target, str) and target
                    else ""
                )
                details_lines.append(f"- {_command_example_text(command, prefer_usage_pattern=True)}{target_text}")

        if blocked_commands:
            details_lines.append(f"{label} blocked:")
            for command in sorted(blocked_commands, key=_help_command_priority):
                blockers = command.get("live_runtime_blockers")
                blockers_text = ", ".join(str(blocker) for blocker in blockers) if isinstance(blockers, list) else "Unavailable"
                details_lines.append(
                    f"- {_command_example_text(command, prefer_usage_pattern=True)} -> {blockers_text}"
                )

    if not details_lines:
        details_lines.append("No supported command metadata is available.")

    return {
        "title": "Supported commands",
        "summary": (
            f"{available_count} commands are ready on this machine. "
            f"{confirmation_count} ask for confirmation before running. "
            f"{blocked_count} need setup."
        ),
        "examples": _help_examples(domains),
        "details": "\n".join(details_lines),
    }


def _command_example_text(command: dict[str, object], *, prefer_usage_pattern: bool = False) -> str:
    if prefer_usage_pattern:
        usage_pattern = command.get("usage_pattern")
        if isinstance(usage_pattern, str) and usage_pattern:
            return _format_command_confirmation_suffix(
                usage_pattern,
                requires_confirmation=bool(command.get("requires_confirmation")),
            )
    example_transcripts = command.get("example_transcripts")
    if isinstance(example_transcripts, list):
        preferred_example = _preferred_example_transcript(command, example_transcripts)
        if preferred_example is not None:
            return _format_command_confirmation_suffix(
                preferred_example,
                requires_confirmation=bool(command.get("requires_confirmation")),
            )
        for example in example_transcripts:
            if isinstance(example, str) and example:
                return _format_command_confirmation_suffix(
                    example,
                    requires_confirmation=bool(command.get("requires_confirmation")),
                )
    tool = str(command.get("tool") or "unknown")
    return _format_command_confirmation_suffix(
        tool,
        requires_confirmation=bool(command.get("requires_confirmation")),
    )


def _format_command_confirmation_suffix(text: str, *, requires_confirmation: bool) -> str:
    return f"{text} (asks for confirmation)" if requires_confirmation else text


def _preferred_example_transcript(command: dict[str, object], examples: list[object]) -> str | None:
    tool = command.get("tool")
    if tool == ToolName.APPS_LAUNCH.value:
        for candidate in ("open browser", "open google.com"):
            if candidate in examples:
                return candidate
    return None


def _help_command_priority(command: dict[str, object]) -> tuple[int, str]:
    tool = str(command.get("tool") or "")
    priority = {
        ToolName.APPS_LAUNCH.value: 0,
        ToolName.TIME_NOW.value: 1,
        ToolName.NETWORK_WIFI_STATUS.value: 2,
        ToolName.AUDIO_GET_VOLUME.value: 3,
        ToolName.AUDIO_MUTE_STATUS.value: 4,
        ToolName.AUDIO_SET_MUTED.value: 5,
        ToolName.AUDIO_SET_VOLUME.value: 6,
        ToolName.FILES_LIST_RECENT.value: 7,
        ToolName.WINDOWS_LIST.value: 8,
        ToolName.WINDOWS_SWITCH.value: 9,
        ToolName.APPS_FOCUS.value: 10,
        ToolName.APPS_QUIT.value: 11,
    }
    return (priority.get(tool, 100), tool)


def _help_examples(domains: list[object], *, limit: int = 6) -> list[str]:
    commands: list[dict[str, object]] = []
    for domain in domains:
        if not isinstance(domain, dict):
            continue
        domain_commands = domain.get("commands")
        if not isinstance(domain_commands, list):
            continue
        commands.extend(
            command
            for command in domain_commands
            if isinstance(command, dict) and command.get("live_runtime_status") == "available"
        )
    return [
        _command_example_text(command)
        for command in sorted(commands, key=_help_command_priority)[:limit]
    ]


def _tool_usage_pattern(tool: ToolName) -> str | None:
    patterns = {
        ToolName.APPS_LAUNCH: "open browser | open google.com | open <app name> | open <app> and load <website>",
        ToolName.APPS_FOCUS: "focus <app name>",
        ToolName.APPS_QUIT: "quit <app name>",
        ToolName.WINDOWS_LIST: "list windows",
        ToolName.WINDOWS_SWITCH: "switch to window <title>",
        ToolName.NOTIFICATIONS_SHOW: "show a notification saying <message>",
        ToolName.FILES_LIST_RECENT: "show recent files",
        ToolName.FILES_CREATE_FOLDER: "create folder on desktop called <name>",
        ToolName.FILES_DELETE_FOLDER: "delete folder on desktop called <name>",
        ToolName.FILES_DELETE_FILE: "delete file on desktop called <name>",
        ToolName.FILES_RENAME: "rename folder on desktop from <source> to <target>",
        ToolName.FILES_MOVE: "move folder on desktop called <name> to <folder>",
        ToolName.FILES_OPEN: "open file on desktop called <name> | open recent file called <name>",
    }
    return patterns.get(tool)


def _domain_label(domain: str) -> str:
    labels = {
        "apps": "Apps and websites",
        "audio": "Audio",
        "clipboard": "Clipboard",
        "files": "Desktop files",
        "keyboard": "Keyboard",
        "network": "Network",
        "notifications": "Notifications",
        "power": "Power",
        "screen": "Screen",
        "text": "Text input",
        "time": "Time",
        "windows": "Windows",
    }
    return labels.get(domain, domain.replace("_", " ").title())


def _domain_description(domain: str) -> str:
    descriptions = {
        "apps": "Open apps, open URLs, focus apps, or quit apps with confirmation when needed.",
        "audio": "Inspect and control basic desktop audio state.",
        "clipboard": "Clipboard commands that depend on Wayland clipboard tooling.",
        "files": "Work with Desktop files and folders through confirmation-gated actions when needed.",
        "keyboard": "Keyboard input commands that depend on safe text-input backends.",
        "network": "Inspect local network state.",
        "notifications": "Show local desktop notifications.",
        "power": "Inspect battery and power state.",
        "screen": "Inspect or control screen state.",
        "text": "Type semantic text through the active platform adapter.",
        "time": "Answer local time questions.",
        "windows": "List or switch desktop windows.",
    }
    return descriptions.get(domain, "Commands in this action group.")


def _tool_live_runtime_status(
    blockers: list[str],
    release_verification_status: str,
) -> str:
    if blockers:
        return "blocked"
    if release_verification_status != "verified":
        return "unverified"
    return "available"


def _tool_release_verification_status(
    tool: ToolName,
    release_verified_tools: frozenset[ToolName],
) -> str:
    if tool in release_verified_tools:
        return "verified"
    return "unverified"


def _build_setup_snapshot(report: dict[str, object]) -> object:
    from .ui.setup import build_setup_snapshot

    return build_setup_snapshot(report)


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0
