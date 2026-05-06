"""Shared supported key-press definitions for the current MVP surface."""

from __future__ import annotations

import re

_SUPPORTED_KEY_DISPLAYS = {
    "backspace": "Backspace",
    "enter": "Enter",
    "escape": "Escape",
    "tab": "Tab",
    "ctrl+c": "Ctrl+C",
    "ctrl+v": "Ctrl+V",
    "ctrl+l": "Ctrl+L",
    "ctrl+r": "Ctrl+R",
    "ctrl+t": "Ctrl+T",
    "ctrl+w": "Ctrl+W",
    "ctrl+shift+p": "Ctrl+Shift+P",
}

_KEY_ALIASES = {
    "esc": "escape",
    "ctrl c": "ctrl+c",
    "ctrl v": "ctrl+v",
    "ctrl l": "ctrl+l",
    "ctrl r": "ctrl+r",
    "ctrl t": "ctrl+t",
    "ctrl w": "ctrl+w",
    "ctrl shift p": "ctrl+shift+p",
}


def normalize_supported_key(value: str) -> str | None:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    normalized = normalized.replace("control", "ctrl")
    normalized = re.sub(r"\s*\+\s*", "+", normalized)
    if normalized in _SUPPORTED_KEY_DISPLAYS:
        return normalized
    return _KEY_ALIASES.get(normalized)


def supported_key_names() -> tuple[str, ...]:
    return tuple(_SUPPORTED_KEY_DISPLAYS)


def supported_key_error() -> str:
    return "key must be one of: " + ", ".join(supported_key_names())


def supported_key_display_name(key: str) -> str | None:
    normalized = normalize_supported_key(key)
    if normalized is None:
        return None
    return _SUPPORTED_KEY_DISPLAYS.get(normalized)
