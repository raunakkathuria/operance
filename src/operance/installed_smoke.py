"""Installed-package smoke diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any, Mapping

from .config import AppConfig
from .doctor import build_environment_report
from .project_info import build_project_identity


DEFAULT_REQUIRED_CHECKS = ("tray_ui_available", "stt_backend_available")
DEFAULT_DESKTOP_ENTRY_PATH = Path("/usr/share/applications/operance.desktop")
DEFAULT_TRAY_UNIT_PATH = Path("/usr/lib/systemd/user/operance-tray.service")
DEFAULT_VOICE_LOOP_UNIT_PATH = Path("/usr/lib/systemd/user/operance-voice-loop.service")


@dataclass(slots=True, frozen=True)
class InstalledSmokeCheck:
    name: str
    status: str
    detail: Any
    suggested_command: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.suggested_command is not None:
            payload["suggested_command"] = self.suggested_command
        return payload


@dataclass(slots=True, frozen=True)
class InstalledSmokeResult:
    status: str
    checks: list[InstalledSmokeCheck]
    next_steps: list[str]
    manual_checks: list[str]
    build: dict[str, object]
    evidence: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "build": dict(self.build),
            "checks": [check.to_dict() for check in self.checks],
            "evidence": dict(self.evidence),
            "manual_checks": list(self.manual_checks),
            "next_steps": list(self.next_steps),
            "status": self.status,
        }


def build_installed_smoke_result(
    *,
    command: str = "operance",
    systemctl_command: str = "systemctl",
    desktop_entry_path: Path = DEFAULT_DESKTOP_ENTRY_PATH,
    tray_unit_path: Path = DEFAULT_TRAY_UNIT_PATH,
    voice_loop_unit_path: Path = DEFAULT_VOICE_LOOP_UNIT_PATH,
    env: Mapping[str, str] | None = None,
    report: dict[str, object] | None = None,
    config: AppConfig | None = None,
) -> InstalledSmokeResult:
    config = AppConfig.from_env(env) if config is None else config
    report = build_environment_report() if report is None else report
    build_identity = build_project_identity()
    checks_by_name = _checks_by_name(report)
    tray_service = _tray_service_properties(command=command, systemctl_command=systemctl_command)

    checks: list[InstalledSmokeCheck] = [
        _build_identity_check(build_identity),
        _runtime_mode_check(config),
        _path_check("desktop_entry_installed", desktop_entry_path),
        _path_check("tray_user_service_unit_installed", tray_unit_path),
        _path_check("voice_loop_user_service_unit_installed", voice_loop_unit_path),
    ]
    checks.extend(_required_doctor_checks(checks_by_name))
    checks.extend(_tray_service_checks(tray_service))

    status = _summary_status(checks)
    return InstalledSmokeResult(
        status=status,
        checks=checks,
        next_steps=_next_steps(checks),
        manual_checks=[
            "Click the tray icon and say: open firefox",
            "Click the tray icon and say: open localhost:3000",
            "Click the tray icon and say: show recent files",
            "Click the tray icon and say: list windows",
            "Click the tray icon and say: switch to window <visible window title>",
            "Click the tray icon and say: what time is it",
        ],
        build=build_identity,
        evidence=_build_evidence(
            command=command,
            config=config,
            build_identity=build_identity,
            tray_service=tray_service,
            checks=checks,
        ),
    )


def _checks_by_name(payload: dict[str, object]) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        return checks
    for item in raw_checks:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            checks[str(item["name"])] = item
    return checks


def _runtime_mode_check(config: AppConfig) -> InstalledSmokeCheck:
    if config.runtime.developer_mode is False:
        return InstalledSmokeCheck(
            name="installed_live_mode",
            status="ok",
            detail={"developer_mode": False},
        )
    return InstalledSmokeCheck(
        name="installed_live_mode",
        status="failed",
        detail={"developer_mode": config.runtime.developer_mode},
        suggested_command="Use the packaged operance command or set OPERANCE_DEVELOPER_MODE=0.",
    )


def _build_identity_check(identity: dict[str, object]) -> InstalledSmokeCheck:
    missing = []
    if identity.get("install_mode") != "packaged":
        missing.append(f"install_mode={identity.get('install_mode')!r}")
    if not identity.get("build_git_commit"):
        missing.append("build_git_commit")
    if not identity.get("package_profile"):
        missing.append("package_profile")
    if not identity.get("install_root"):
        missing.append("install_root")
    if not missing:
        return InstalledSmokeCheck(
            name="packaged_build_identity_available",
            status="ok",
            detail={
                "build_git_commit_short": identity.get("build_git_commit_short"),
                "build_git_tag": identity.get("build_git_tag"),
                "package_profile": identity.get("package_profile"),
            },
        )
    return InstalledSmokeCheck(
        name="packaged_build_identity_available",
        status="failed",
        detail={"missing": missing},
        suggested_command="Rebuild and reinstall the package from the current release tag.",
    )


def _path_check(name: str, path: Path) -> InstalledSmokeCheck:
    if path.exists():
        return InstalledSmokeCheck(name=name, status="ok", detail=str(path))
    return InstalledSmokeCheck(
        name=name,
        status="failed",
        detail=f"missing: {path}",
        suggested_command="Reinstall the package, then rerun operance --installed-smoke.",
    )


def _required_doctor_checks(checks_by_name: dict[str, dict[str, Any]]) -> list[InstalledSmokeCheck]:
    checks: list[InstalledSmokeCheck] = []
    for check_name in DEFAULT_REQUIRED_CHECKS:
        check = checks_by_name.get(check_name)
        if check is None:
            checks.append(
                InstalledSmokeCheck(
                    name=check_name,
                    status="failed",
                    detail="missing doctor check",
                    suggested_command="Run operance --doctor.",
                )
            )
            continue
        status = str(check.get("status"))
        checks.append(
            InstalledSmokeCheck(
                name=check_name,
                status="ok" if status == "ok" else "failed",
                detail=check.get("detail"),
                suggested_command=None if status == "ok" else "Install the packaged MVP runtime and rerun the smoke.",
            )
        )
    return checks


def _tray_service_properties(*, command: str, systemctl_command: str) -> dict[str, object]:
    try:
        completed = subprocess.run(
            [
                systemctl_command,
                "--user",
                "show",
                "operance-tray.service",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "FragmentPath",
                "-p",
                "ExecStart",
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return {
            "inspectable": False,
            "command": systemctl_command,
            "error": f"{systemctl_command} not found",
        }
    if completed.returncode != 0:
        return {
            "inspectable": False,
            "command": systemctl_command,
            "error": _command_detail(completed),
        }

    properties: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value

    return {
        "inspectable": True,
        "command": systemctl_command,
        "expected_command": command,
        "load_state": properties.get("LoadState") or "unknown",
        "active_state": properties.get("ActiveState") or "unknown",
        "fragment_path": properties.get("FragmentPath") or "",
        "exec_start": properties.get("ExecStart") or "",
    }


def _tray_service_checks(properties: dict[str, object]) -> list[InstalledSmokeCheck]:
    if not properties.get("inspectable"):
        return [
            InstalledSmokeCheck(
                name="tray_user_service_inspectable",
                status="warn",
                detail=properties.get("error") or "not inspectable",
                suggested_command="systemctl --user status operance-tray.service --no-pager",
            )
        ]

    command = str(properties.get("expected_command") or "")
    load_state = str(properties.get("load_state") or "unknown")
    active_state = str(properties.get("active_state") or "unknown")
    fragment_path = str(properties.get("fragment_path") or "")
    exec_start = str(properties.get("exec_start") or "")

    checks: list[InstalledSmokeCheck] = [
        InstalledSmokeCheck(
            name="tray_user_service_load_state",
            status="ok" if load_state == "loaded" else "failed",
            detail=load_state,
            suggested_command=None if load_state == "loaded" else "Reinstall the package and rerun operance --installed-smoke.",
        ),
        InstalledSmokeCheck(
            name="tray_user_service_active_state",
            status="ok" if active_state == "active" else "warn",
            detail=active_state,
            suggested_command=None if active_state == "active" else "systemctl --user enable --now operance-tray.service",
        ),
    ]

    if fragment_path.startswith("/home/") and "/.config/systemd/user/" in fragment_path:
        checks.append(
            InstalledSmokeCheck(
                name="tray_user_service_not_shadowed",
                status="failed",
                detail={"fragment_path": fragment_path},
                suggested_command="Remove stale user units or reinstall with --reset-user-services.",
            )
        )
    else:
        checks.append(
            InstalledSmokeCheck(
                name="tray_user_service_not_shadowed",
                status="ok",
                detail={"fragment_path": fragment_path},
            )
        )

    if command in exec_start:
        checks.append(
            InstalledSmokeCheck(
                name="tray_user_service_exec_start",
                status="ok",
                detail=exec_start,
            )
        )
    else:
        checks.append(
            InstalledSmokeCheck(
                name="tray_user_service_exec_start",
                status="failed",
                detail=exec_start,
                suggested_command="Reinstall the package or inspect systemctl --user cat operance-tray.service.",
            )
        )

    return checks


def _build_evidence(
    *,
    command: str,
    config: AppConfig,
    build_identity: dict[str, object],
    tray_service: dict[str, object],
    checks: list[InstalledSmokeCheck],
) -> dict[str, object]:
    return {
        "command": command,
        "developer_mode": config.runtime.developer_mode,
        "environment": config.environment,
        "data_dir": str(config.paths.data_dir),
        "install_mode": build_identity.get("install_mode"),
        "package_profile": build_identity.get("package_profile"),
        "version": build_identity.get("version"),
        "build_git_tag": build_identity.get("build_git_tag"),
        "build_git_commit_short": build_identity.get("build_git_commit_short"),
        "install_root": build_identity.get("install_root"),
        "tray_service": dict(tray_service),
        "failed_checks": [check.name for check in checks if check.status == "failed"],
        "warning_checks": [check.name for check in checks if check.status == "warn"],
    }


def _command_detail(completed: subprocess.CompletedProcess[str]) -> str:
    return (completed.stderr or completed.stdout or "").strip() or f"exit code {completed.returncode}"


def _summary_status(checks: list[InstalledSmokeCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "ok"


def _next_steps(checks: list[InstalledSmokeCheck]) -> list[str]:
    commands: list[str] = []
    for check in checks:
        if check.suggested_command and check.suggested_command not in commands:
            commands.append(check.suggested_command)
    if any(check.status == "failed" for check in checks):
        commands.append("operance --support-bundle")
    else:
        commands.append("systemctl --user status operance-tray.service --no-pager")
    return commands
