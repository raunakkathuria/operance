"""Parsing helpers for schema-constrained planner output."""

from __future__ import annotations

from dataclasses import dataclass
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

        actions.append(TypedAction(tool=tool, args=dict(args_value)))

    return ActionPlan(
        source=PlanSource.PLANNER,
        original_text=original_text,
        actions=actions,
    )
