"""Conservative recovery for common speech-to-text command variants."""

from __future__ import annotations


SPOKEN_APP_ALIASES = {
    "firefall": "firefox",
    "fire fall": "firefox",
    "fire force": "firefox",
    "fire fox": "firefox",
    "fireforth": "firefox",
}


def recover_spoken_app_target(value: str) -> str:
    """Map known STT variants to verified app targets."""

    return SPOKEN_APP_ALIASES.get(value, value)
