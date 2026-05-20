"""Release-channel diagnostics for installed Operance runtimes."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Mapping

from .project_info import build_project_identity

DEFAULT_RELEASE_REPOSITORY = "raunakkathuria/operance"
DEFAULT_RELEASE_CHANNEL = "prerelease"
SUPPORTED_RELEASE_CHANNELS = frozenset({"prerelease", "stable"})

ReleaseFetcher = Callable[[str, str, float], Mapping[str, object]]


def build_release_update_status(
    identity: Mapping[str, object] | None = None,
    *,
    channel: str | None = None,
    check_remote: bool = True,
    fetch_latest_release: ReleaseFetcher | None = None,
    timeout_seconds: float = 5.0,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build a release-channel status payload without mutating the host."""

    source = os.environ if env is None else env
    resolved_channel = _release_channel(channel or source.get("OPERANCE_RELEASE_CHANNEL"))
    repository = str(source.get("OPERANCE_RELEASE_REPOSITORY") or DEFAULT_RELEASE_REPOSITORY)
    runtime_identity = dict(build_project_identity() if identity is None else identity)
    installed_tag = _string_value(runtime_identity.get("build_git_tag"))
    installed_commit = _string_value(
        runtime_identity.get("build_git_commit_short") or runtime_identity.get("git_commit")
    )
    install_mode = _string_value(runtime_identity.get("install_mode")) or "unknown"

    base_payload: dict[str, object] = {
        "status": "unknown",
        "repository": repository,
        "channel": resolved_channel,
        "check_remote": check_remote,
        "install_mode": install_mode,
        "installed_tag": installed_tag,
        "installed_commit": installed_commit,
        "latest_tag": None,
        "update_available": None,
        "release_url": None,
        "message": "Remote release check was not requested.",
        "suggested_command": "operance --check-updates",
    }
    if not check_remote:
        return base_payload

    fetcher = fetch_latest_release or fetch_latest_github_release
    try:
        release = dict(fetcher(repository, resolved_channel, timeout_seconds))
    except Exception as exc:
        base_payload.update(
            {
                "status": "failed",
                "message": f"Could not check GitHub releases: {exc}",
                "suggested_command": "Retry operance --check-updates when network access is available.",
            }
        )
        return base_payload

    latest_tag = _string_value(release.get("tag_name"))
    release_url = _string_value(release.get("html_url"))
    base_payload.update(
        {
            "status": "ok",
            "latest_tag": latest_tag,
            "release_url": release_url,
        }
    )

    if install_mode != "packaged":
        base_payload.update(
            {
                "update_available": None,
                "message": (
                    f"Latest {resolved_channel} release is {latest_tag}; source checkouts should update through git."
                    if latest_tag
                    else f"No {resolved_channel} release was found; source checkouts should update through git."
                ),
                "suggested_command": "git pull --ff-only",
            }
        )
        return base_payload

    if not latest_tag:
        base_payload.update(
            {
                "status": "failed",
                "message": f"No {resolved_channel} release tag was found.",
                "suggested_command": "Retry operance --check-updates later.",
            }
        )
        return base_payload

    if latest_tag == installed_tag:
        base_payload.update(
            {
                "update_available": False,
                "message": f"Installed release is current for the {resolved_channel} channel.",
                "suggested_command": None,
            }
        )
        return base_payload

    base_payload.update(
        {
            "update_available": True,
            "message": f"Update available: {latest_tag}.",
            "suggested_command": (
                f"Download and install the latest RPM from {release_url}"
                if release_url
                else "Download and install the latest RPM from the Operance GitHub releases page."
            ),
        }
    )
    return base_payload


def fetch_latest_github_release(
    repository: str,
    channel: str,
    timeout_seconds: float,
) -> Mapping[str, object]:
    url = _github_release_api_url(repository, channel)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "operance-release-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(str(reason)) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub returned invalid JSON") from exc

    if channel == "stable":
        if not isinstance(payload, dict):
            raise RuntimeError("GitHub stable release payload was not an object")
        return payload

    if not isinstance(payload, list):
        raise RuntimeError("GitHub prerelease payload was not a list")
    for item in payload:
        if isinstance(item, dict) and bool(item.get("prerelease")):
            return item
    raise RuntimeError("no prerelease was found")


def _github_release_api_url(repository: str, channel: str) -> str:
    if channel == "stable":
        return f"https://api.github.com/repos/{repository}/releases/latest"
    return f"https://api.github.com/repos/{repository}/releases"


def _release_channel(raw_channel: str | None) -> str:
    channel = (raw_channel or DEFAULT_RELEASE_CHANNEL).strip().lower()
    if channel not in SUPPORTED_RELEASE_CHANNELS:
        raise ValueError(
            "release channel must be one of: "
            + ", ".join(sorted(SUPPORTED_RELEASE_CHANNELS))
        )
    return channel


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
