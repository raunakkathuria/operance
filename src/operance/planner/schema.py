"""JSON-schema helpers for planner payload contracts."""

from __future__ import annotations

from ..registry import ToolSpec, build_default_action_registry


def build_planner_payload_schema() -> dict[str, object]:
    registry = build_default_action_registry()
    return {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {"oneOf": [_tool_action_schema(spec) for spec in registry.list_specs()]},
            }
        },
        "required": ["actions"],
        "additionalProperties": False,
    }


def _tool_action_schema(spec: ToolSpec) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "const": spec.name.value,
            },
            "args": spec.input_schema,
        },
        "required": ["tool", "args"],
        "additionalProperties": False,
    }
