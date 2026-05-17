"""Shared developer support snapshot surfaces."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .audit import AuditStore
from .config import AppConfig
from .doctor import build_environment_report
from .project_info import build_project_identity
from .supported_commands import build_supported_command_catalog
from .voice import build_voice_loop_config_snapshot
from .voice.service import build_voice_loop_service_snapshot


def build_support_snapshot(
    *,
    env: dict[str, str] | None = None,
    report: dict[str, object] | None = None,
    redact: bool = False,
    home_dir: str | None = None,
) -> dict[str, object]:
    doctor_report = build_environment_report() if report is None else report
    snapshot = {
        "build": build_project_identity(),
        "doctor": doctor_report,
        "setup": _build_setup_snapshot(doctor_report).to_dict(),
        "supported_commands": build_supported_command_catalog(doctor_report),
        "runnable_supported_commands": build_supported_command_catalog(doctor_report, available_only=True),
        "voice_loop_config": build_voice_loop_config_snapshot(env=env).to_dict(),
        "voice_loop_service": build_voice_loop_service_snapshot(env=env, report=doctor_report).to_dict(),
        "audit": _build_recent_audit_payload(env=env),
    }
    if redact:
        return redact_support_snapshot(snapshot, home_dir=home_dir)
    return snapshot


def build_support_snapshot_help_text(snapshot: dict[str, object]) -> dict[str, object]:
    doctor = snapshot.get("doctor")
    if not isinstance(doctor, dict):
        doctor = {}
    setup = snapshot.get("setup")
    if not isinstance(setup, dict):
        setup = {}
    build = snapshot.get("build")
    if not isinstance(build, dict):
        build = {}
    supported_commands = snapshot.get("supported_commands")
    if not isinstance(supported_commands, dict):
        supported_commands = {}
    supported_summary = supported_commands.get("summary")
    if not isinstance(supported_summary, dict):
        supported_summary = {}
    voice_loop_service = snapshot.get("voice_loop_service")
    if not isinstance(voice_loop_service, dict):
        voice_loop_service = {}
    audit = snapshot.get("audit")
    if not isinstance(audit, dict):
        audit = {}

    doctor_checks = doctor.get("checks")
    warning_names = []
    if isinstance(doctor_checks, list):
        warning_names = [
            str(check.get("name"))
            for check in doctor_checks
            if isinstance(check, dict) and check.get("status") == "warn" and check.get("name") is not None
        ]

    ready_for_mvp = bool(setup.get("ready_for_mvp"))
    available_commands = _int_value(supported_summary.get("available_commands"))
    unverified_commands = _int_value(supported_summary.get("unverified_commands"))
    blocked_commands = _int_value(supported_summary.get("blocked_commands"))
    audit_count = _int_value(audit.get("count"))

    highlights = [
        _format_build_highlight(build),
        f"Setup summary: {setup.get('summary_status') or 'unknown'}",
        f"Voice-loop service: {voice_loop_service.get('status') or 'unknown'}",
    ]
    if audit_count:
        highlights.append(f"Recent audit entries: {audit_count}")
    recommended_command = voice_loop_service.get("recommended_command")
    if isinstance(recommended_command, str) and recommended_command:
        highlights.append(f"Next voice-loop action: {recommended_command}")
    if warning_names:
        highlights.append("Doctor warnings: " + ", ".join(warning_names[:6]))

    return {
        "title": "Support snapshot",
        "summary": (
            f"MVP ready: {'yes' if ready_for_mvp else 'no'} | "
            f"{available_commands} release-verified and available | "
            f"{unverified_commands} unverified | {blocked_commands} blocked."
        ),
        "highlights": highlights,
        "details": json.dumps(snapshot, indent=2, sort_keys=True),
    }


def _format_build_highlight(build: dict[str, object]) -> str:
    name = build.get("name")
    version = build.get("version")
    git_commit = build.get("build_git_commit_short") or build.get("git_commit")
    if isinstance(name, str) and name and isinstance(version, str) and version:
        if isinstance(git_commit, str) and git_commit:
            return f"Build: {name} {version} ({git_commit})"
        return f"Build: {name} {version}"
    return "Build: unknown"


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


def redact_support_snapshot(snapshot: object, *, home_dir: str | None = None) -> object:
    normalized_home = str(home_dir or os.path.expanduser("~")).rstrip("/")
    if not normalized_home:
        return snapshot
    return _redact_value(snapshot, home_dir=normalized_home)


def _redact_value(value: object, *, home_dir: str) -> object:
    if isinstance(value, dict):
        return {key: _redact_value(item, home_dir=home_dir) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, home_dir=home_dir) for item in value]
    if isinstance(value, str):
        return value.replace(home_dir, "~")
    return value


def _build_setup_snapshot(report: dict[str, object]):
    from .ui.setup import build_setup_snapshot

    return build_setup_snapshot(report)


def _build_recent_audit_payload(
    *,
    env: dict[str, str] | None = None,
    limit: int = 20,
) -> dict[str, object]:
    config = AppConfig.from_env(env)
    audit_path = config.paths.data_dir / "audit.sqlite3"
    if not audit_path.exists():
        return {"count": 0, "entries": []}

    entries = AuditStore(Path(audit_path)).list_recent(limit=limit)
    return {
        "count": len(entries),
        "entries": [entry.to_dict() for entry in entries],
    }
