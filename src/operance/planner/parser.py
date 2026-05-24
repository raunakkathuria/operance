"""Parsing helpers for schema-constrained planner output."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from ..models.actions import ActionPlan, PlanSource, ToolName, TypedAction


@dataclass(slots=True)
class PlannerParseError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def parse_planner_payload(payload: Mapping[str, object], *, original_text: str) -> ActionPlan:
    actions_value = payload.get("actions")
    if not isinstance(actions_value, list) or not actions_value:
        raise PlannerParseError("planner payload must include a non-empty actions list")

    actions: list[TypedAction] = []
    for index, action_value in enumerate(actions_value):
        if not isinstance(action_value, Mapping):
            raise PlannerParseError(f"action {index} must be an object")

        tool_value = action_value.get("tool")
        if not isinstance(tool_value, str):
            raise PlannerParseError(f"action {index} tool must be a string")
        try:
            tool = ToolName(tool_value)
        except ValueError as exc:
            raise PlannerParseError(f"unknown tool: {tool_value}") from exc

        args_value = action_value.get("args", {})
        if not isinstance(args_value, dict):
            raise PlannerParseError(f"action {index} args must be an object")

        normalized_tool, normalized_args = _normalize_planner_action(
            original_text,
            tool,
            dict(args_value),
        )
        actions.append(TypedAction(tool=normalized_tool, args=normalized_args))

    return ActionPlan(
        source=PlanSource.PLANNER,
        original_text=original_text,
        actions=actions,
    )


def _normalize_planner_action(
    original_text: str,
    tool: ToolName,
    args: dict[str, object],
) -> tuple[ToolName, dict[str, object]]:
    if not _is_open_launch_intent(original_text):
        return (tool, args)

    if tool == ToolName.WINDOWS_SWITCH:
        window = args.get("window")
        if isinstance(window, str) and window.strip():
            return (ToolName.APPS_LAUNCH, {"app": window.strip()})

    if tool == ToolName.APPS_FOCUS:
        app = args.get("app")
        if isinstance(app, str) and app.strip():
            return (ToolName.APPS_LAUNCH, {"app": app.strip()})

    return (tool, args)


def _is_open_launch_intent(text: str) -> bool:
    normalized = text.strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return bool(re.match(r"^(?:please )?(?:open|launch|start)\b", normalized))
