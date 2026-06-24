"""Prompt-template helpers for local planner requests."""

from __future__ import annotations

from ..models.actions import ToolName
from ..registry import ToolSpec, build_default_action_registry

_PROMPT_EXAMPLE_TOOLS = {
    ToolName.APPS_LAUNCH,
    ToolName.APPS_QUIT,
    ToolName.WINDOWS_SWITCH,
}


def build_planner_messages(transcript: str) -> list[dict[str, str]]:
    registry = build_default_action_registry()
    tool_lines = [_format_tool_prompt_line(spec) for spec in registry.list_specs()]
    system_message = "\n".join(
        [
            "Use only the approved tools listed below.",
            "Return JSON only.",
            "Do not invent tools or arguments outside the provided schema.",
            "Plan at most two actions.",
            'Return shape: {"actions":[{"tool":"tool.name","args":{}}]}.',
            "The request carries a machine-enforced JSON schema; follow the tool and arg hints exactly.",
            "Intent hints: open/launch/start apps or websites MUST use apps.launch, never windows.switch.",
            "Use windows.switch only when the user explicitly asks to switch to an existing window.",
            'Example: open firefox and notify me -> {"actions":[{"tool":"apps.launch","args":{"app":"firefox"}},{"tool":"notifications.show","args":{"title":"Opened","message":"Firefox opened"}}]}',
            'Example: switch to firefox -> {"actions":[{"tool":"windows.switch","args":{"window":"firefox"}}]}',
            "confirmation=required means the runtime will stop for user confirmation before execution.",
            "Approved tools:",
            *tool_lines,
        ]
    )
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": transcript},
    ]


def _format_tool_prompt_line(spec: ToolSpec) -> str:
    example_transcript = ""
    if spec.name in _PROMPT_EXAMPLE_TOOLS and spec.example_transcripts:
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
