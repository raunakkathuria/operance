"""Shared end-user command recovery guidance."""

from __future__ import annotations


COMMAND_RECOVERY_EXAMPLES = (
    "open browser",
    "open google.com",
    "search google for linux automation",
    "what time is it",
)


def unmatched_command_response() -> str:
    examples = "; ".join(COMMAND_RECOVERY_EXAMPLES)
    return f"I did not understand that command yet. Try: {examples}."


def unmatched_spoken_response() -> str:
    return "Sorry, I did not understand that yet. Try open browser or what time is it."
