"""Runtime self-status responses for user-facing Operance questions."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .models.events import RuntimeState


@dataclass(frozen=True, slots=True)
class SelfStatusCommandSpec:
    tool: str
    description: str
    example_transcripts: tuple[str, ...]
    usage_pattern: str


@dataclass(frozen=True, slots=True)
class SelfStatusContext:
    current_state: RuntimeState
    previous_transcript: str | None
    previous_response: str | None
    previous_command_status: str | None
    planner_enabled: bool
    planner_model: str
    planner_cooldown_remaining_seconds: float | None
    last_planner_error: str | None


SELF_STATUS_COMMAND_SPECS: tuple[SelfStatusCommandSpec, ...] = (
    SelfStatusCommandSpec(
        tool="operance.help",
        description="Show a short list of useful commands to try.",
        example_transcripts=(
            "what can I say",
            "what commands can I use",
            "help",
        ),
        usage_pattern="what can I say | what commands can I use | help",
    ),
    SelfStatusCommandSpec(
        tool="operance.last_heard",
        description="Report the last command Operance heard before this question.",
        example_transcripts=(
            "what did you hear",
            "what was the last command",
        ),
        usage_pattern="what did you hear | what was the last command",
    ),
    SelfStatusCommandSpec(
        tool="operance.listening_status",
        description="Report whether Operance is running and how to speak to it.",
        example_transcripts=(
            "are you listening",
            "are you running",
        ),
        usage_pattern="are you listening | are you running",
    ),
    SelfStatusCommandSpec(
        tool="operance.local_ai_status",
        description="Report optional local AI planner status.",
        example_transcripts=(
            "is local AI ready",
            "is planner ready",
        ),
        usage_pattern="is local AI ready | is planner ready",
    ),
    SelfStatusCommandSpec(
        tool="operance.last_failure",
        description="Explain the most recent failed or unmatched command.",
        example_transcripts=(
            "why did that fail",
            "why did it fail",
            "what went wrong",
        ),
        usage_pattern="why did that fail | why did it fail | what went wrong",
    ),
)


def build_self_status_response(
    transcript: str,
    *,
    context: SelfStatusContext,
) -> tuple[str, str] | None:
    tool = _COMMAND_ALIASES.get(_normalize(transcript))
    if tool is None:
        return None

    if tool == "operance.help":
        return (
            "Try: open browser; open google.com; list files in downloads; "
            "find file named notes.txt; show details for notes.txt; "
            "what apps are open; what time is it.",
            "success",
        )
    if tool == "operance.last_heard":
        if context.previous_transcript:
            return (f"Last command I heard: {context.previous_transcript}.", "success")
        return ("I have not heard a previous command yet.", "success")
    if tool == "operance.listening_status":
        state = context.current_state.value.lower().replace("_", " ")
        return (
            f"Operance is running. Current state: {state}. "
            "Use click-to-talk, or enable always-on listening from the tray.",
            "success",
        )
    if tool == "operance.local_ai_status":
        if context.planner_cooldown_remaining_seconds is not None:
            seconds = int(round(context.planner_cooldown_remaining_seconds))
            reason = (
                f" Last planner error: {context.last_planner_error}."
                if context.last_planner_error
                else ""
            )
            return (
                f"Local AI planner is cooling down for about {seconds} seconds.{reason}",
                "success",
            )
        if context.planner_enabled:
            suffix = (
                f" Last planner error: {context.last_planner_error}."
                if context.last_planner_error
                else ""
            )
            return (
                f"Local AI planner is enabled with {context.planner_model}. "
                f"Verified commands still work without it.{suffix}",
                "success",
            )
        return (
            "Local AI planner is optional and currently disabled. "
            "Verified commands work without it.",
            "success",
        )
    if tool == "operance.last_failure":
        if context.previous_command_status in {"failed", "unmatched", "denied", "expired"}:
            details = context.previous_response or "No response details were recorded."
            return (
                f"Last command status was {context.previous_command_status}: {details}",
                "success",
            )
        return ("No recent failed command is recorded.", "success")

    return None


def _normalize(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(normalized.split())


_COMMAND_ALIASES = {
    _normalize(alias): spec.tool
    for spec in SELF_STATUS_COMMAND_SPECS
    for alias in spec.example_transcripts
}
