"""Helpers for classifying and normalizing launch targets."""

from __future__ import annotations

import re

_URL_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_LOCALHOST_TARGET_RE = re.compile(r"^(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/.*)?$", re.IGNORECASE)
_BARE_HOST_TARGET_RE = re.compile(r"^(?:[a-z0-9-]+\.)+[a-z0-9-]+(?::\d+)?(?:/.*)?$", re.IGNORECASE)


def is_url_like_target(value: str) -> bool:
    candidate = value.strip()
    if not candidate or " " in candidate:
        return False
    return bool(_URL_SCHEME_RE.match(candidate) or _LOCALHOST_TARGET_RE.fullmatch(candidate))


def normalize_launch_target(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return candidate
    if _URL_SCHEME_RE.match(candidate):
        return candidate
    if _LOCALHOST_TARGET_RE.fullmatch(candidate):
        return f"http://{candidate}"
    return candidate


def normalize_explicit_url_target(value: str) -> str:
    candidate = normalize_launch_target(value)
    if _URL_SCHEME_RE.match(candidate):
        return candidate
    if _BARE_HOST_TARGET_RE.fullmatch(candidate):
        return f"https://{candidate}"
    return candidate
