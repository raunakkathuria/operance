"""JSON-schema helpers for planner payload contracts."""

from __future__ import annotations

from ..models.actions import ToolName


def build_planner_payload_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {
                            "type": "string",
                            "enum": [tool.value for tool in ToolName],
                        },
                        "args": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["tool", "args"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["actions"],
        "additionalProperties": False,
    }
