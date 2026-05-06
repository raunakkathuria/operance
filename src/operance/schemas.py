"""JSON-schema helpers for exported runtime contracts."""

from __future__ import annotations

from .models.actions import PlanSource, RiskTier, ToolName


def build_action_plan_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "source": {"type": "string", "enum": [source.value for source in PlanSource]},
            "original_text": {"type": "string"},
            "actions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "enum": [tool.value for tool in ToolName]},
                        "args": {"type": "object", "additionalProperties": True},
                        "risk_tier": {"type": "integer", "enum": [int(tier) for tier in RiskTier]},
                        "requires_confirmation": {"type": "boolean"},
                        "undoable": {"type": "boolean"},
                    },
                    "required": [
                        "tool",
                        "args",
                        "risk_tier",
                        "requires_confirmation",
                        "undoable",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["plan_id", "source", "original_text", "actions"],
        "additionalProperties": False,
    }


def build_action_result_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["success", "partial", "failed", "denied", "cancelled"],
            },
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "enum": [tool.value for tool in ToolName]},
                        "status": {"type": "string"},
                        "message": {"type": "string"},
                        "undo_token": {"type": ["string", "null"]},
                    },
                    "required": ["tool", "status", "message", "undo_token"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["plan_id", "status", "results"],
        "additionalProperties": False,
    }
