"""Package support diagnostics into one local archive."""

from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import tarfile
from typing import Mapping

from .config import AppConfig
from .project_info import build_project_identity, project_version
from .support_snapshot import (
    build_support_snapshot,
    build_support_snapshot_help_text,
    redact_support_snapshot,
)
from .voice.runtime import build_voice_loop_runtime_status_snapshot

_DEFAULT_SERVICE_LOG_LINES = 100
_SUPPORT_BUNDLE_UNITS = (
    "operance-tray.service",
    "operance-voice-loop.service",
)


def write_support_bundle_artifact(
    *,
    output_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    redact: bool = True,
    home_dir: str | None = None,
    now: datetime | None = None,
    service_log_lines: int = _DEFAULT_SERVICE_LOG_LINES,
) -> dict[str, object]:
    config = AppConfig.from_env(env)
    timestamp = now if now is not None else datetime.now(timezone.utc)
    bundle_path = output_path if output_path is not None else _default_bundle_path(config.paths.data_dir, timestamp)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_home = str(Path(home_dir).expanduser()) if home_dir else str(Path.home())
    bundle_env = dict(env or {})

    snapshot = build_support_snapshot(
        env=bundle_env,
        redact=redact,
        home_dir=normalized_home if redact else None,
    )
    help_text = build_support_snapshot_help_text(snapshot)
    runtime_snapshot: object = build_voice_loop_runtime_status_snapshot(env=bundle_env).to_dict()
    if redact:
        runtime_snapshot = redact_support_snapshot(runtime_snapshot, home_dir=normalized_home)

    members: dict[str, bytes] = {
        "support-snapshot.json": _json_bytes(snapshot),
        "support-help.json": _json_bytes(help_text),
        "voice-loop-runtime.json": _json_bytes(runtime_snapshot),
    }
    warnings: list[str] = []

    for unit_name in _SUPPORT_BUNDLE_UNITS:
        log_text, warning = _read_user_service_log(unit_name, lines=service_log_lines)
        if log_text is not None:
            if redact:
                log_text = str(redact_support_snapshot(log_text, home_dir=normalized_home))
            members[f"logs/{unit_name}.log"] = _text_bytes(log_text)
        if warning is not None:
            warnings.append(f"{unit_name}: {warning}")

    manifest = {
        "bundle_version": 1,
        "generated_at": timestamp.isoformat(),
        "project": build_project_identity(),
        "redacted": redact,
        "data_dir": (
            redact_support_snapshot(str(config.paths.data_dir), home_dir=normalized_home)
            if redact
            else str(config.paths.data_dir)
        ),
        "included_files": sorted(["manifest.json", *members.keys()]),
        "service_log_lines": service_log_lines,
        "warning_count": len(warnings),
        "warnings": warnings,
    }
    members["manifest.json"] = _json_bytes(manifest)

    with tarfile.open(bundle_path, "w:gz") as archive:
        for name in sorted(members):
            payload = members[name]
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mtime = timestamp.timestamp()
            archive.addfile(info, io.BytesIO(payload))

    return {
        "bundle_path": str(bundle_path),
        "included_files": manifest["included_files"],
        "warning_count": len(warnings),
        "warnings": warnings,
        "redacted": redact,
    }


def _default_bundle_path(data_dir: Path, timestamp: datetime) -> Path:
    output_dir = data_dir / "support-bundles"
    return output_dir / f"support-bundle-{project_version()}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.tar.gz"


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _text_bytes(payload: str) -> bytes:
    text = payload if payload.endswith("\n") else payload + "\n"
    return text.encode("utf-8")


def _read_user_service_log(unit_name: str, *, lines: int = _DEFAULT_SERVICE_LOG_LINES) -> tuple[str | None, str | None]:
    command = [
        "journalctl",
        "--user",
        "--unit",
        unit_name,
        "-n",
        str(lines),
        "--no-pager",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        message = stderr or stdout or f"journalctl exited with status {completed.returncode}"
        return None, message
    if not stdout:
        return None, "no journal output"
    return stdout, None
