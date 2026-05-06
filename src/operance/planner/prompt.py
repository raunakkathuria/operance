"""Prompt-template helpers for local planner requests."""

from __future__ import annotations

import json

from ..registry import ToolSpec, build_default_action_registry
from .schema import build_planner_payload_schema


def build_planner_messages(transcript: str) -> list[dict[str, str]]:
    registry = build_default_action_registry()
    tool_lines = [_format_tool_prompt_line(spec) for spec in registry.list_specs()]
    schema_json = json.dumps(build_planner_payload_schema(), sort_keys=True)
    system_message = "\n".join(
        [
            "Use only the approved tools listed below.",
            "Return JSON only.",
            "Do not invent tools or arguments outside the provided schema.",
            "Plan at most two actions.",
            "confirmation=required means the runtime will stop for user confirmation before execution.",
            "Approved tools:",
            *tool_lines,
            f"Output schema: {schema_json}",
        ]
    )
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": transcript},
    ]


def _format_tool_prompt_line(spec: ToolSpec) -> str:
    example_transcript = ""
    if spec.example_transcripts:
        example_transcript = f' | example="{spec.example_transcripts[0]}"'

    confirmation = "required" if spec.requires_confirmation else "not_required"
    required_args = ",".join(spec.required_args) if spec.required_args else "none"

    return (
        f"- {spec.name.value}: {spec.description}"
        f" | args={required_args}"
        f" | risk=tier_{int(spec.risk_tier)}"
        f" | confirmation={confirmation}"
        f"{example_transcript}"
    )
