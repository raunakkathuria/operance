"""Short spoken response text for voice and tray surfaces."""

from __future__ import annotations

from collections.abc import Mapping

from .command_guidance import unmatched_spoken_response


def build_spoken_response_text(response: Mapping[str, object] | None) -> str | None:
    if response is None:
        return None
    status = response.get("status")
    text = response.get("text")
    if status == "no_transcript":
        return "Sorry, I did not hear that."
    if status == "unmatched":
        return unmatched_spoken_response()
    if status == "awaiting_confirmation":
        return "Please confirm before I continue."
    if status in {"failed", "denied"}:
        if isinstance(text, str) and text.strip():
            return f"Sorry, {text.strip()}"
        return "Sorry, that did not work."
    if isinstance(text, str) and text.strip():
        return _shorten_spoken_response(text)
    return None


def _shorten_spoken_response(text: str) -> str:
    first_line = text.strip().splitlines()[0].strip()
    if not first_line:
        return ""
    if len(first_line) <= 120:
        return first_line
    return first_line[:117].rstrip() + "..."
