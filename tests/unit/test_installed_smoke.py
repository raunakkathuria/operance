import subprocess
from pathlib import Path

import pytest

from operance.config import AppConfig
from operance.installed_smoke import build_installed_smoke_result


@pytest.fixture(autouse=True)
def _packaged_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        "operance.installed_smoke.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "install_mode": "packaged",
            "build_git_commit": "abcdef123456",
            "build_git_commit_short": "abcdef1",
            "package_profile": "mvp",
            "install_root": "/usr/lib/operance",
        },
    )


def _live_config() -> AppConfig:
    return AppConfig.from_env({"OPERANCE_DEVELOPER_MODE": "0"})


def _report(*, stt_status: str = "ok") -> dict[str, object]:
    return {
        "checks": [
            {"name": "tray_ui_available", "status": "ok", "detail": "PySide6"},
            {"name": "stt_backend_available", "status": stt_status, "detail": "moonshine_voice"},
        ]
    }


def test_installed_smoke_passes_for_packaged_active_tray_service(monkeypatch, tmp_path: Path) -> None:
    desktop_entry = tmp_path / "operance.desktop"
    tray_unit = tmp_path / "operance-tray.service"
    voice_loop_unit = tmp_path / "operance-voice-loop.service"
    for path in (desktop_entry, tray_unit, voice_loop_unit):
        path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "LoadState=loaded\n"
                "ActiveState=active\n"
                "FragmentPath=/usr/lib/systemd/user/operance-tray.service\n"
                "ExecStart={ path=/usr/bin/operance ; argv[]=/usr/bin/operance --tray-run ; }\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("operance.installed_smoke.subprocess.run", fake_run)

    result = build_installed_smoke_result(
        desktop_entry_path=desktop_entry,
        tray_unit_path=tray_unit,
        voice_loop_unit_path=voice_loop_unit,
        config=_live_config(),
        report=_report(),
    )

    assert result.status == "ok"
    assert result.to_dict()["next_steps"] == ["systemctl --user status operance-tray.service --no-pager"]


def test_installed_smoke_fails_for_developer_mode_and_missing_runtime(tmp_path: Path) -> None:
    desktop_entry = tmp_path / "operance.desktop"
    tray_unit = tmp_path / "operance-tray.service"
    voice_loop_unit = tmp_path / "operance-voice-loop.service"
    for path in (desktop_entry, tray_unit, voice_loop_unit):
        path.write_text("", encoding="utf-8")

    result = build_installed_smoke_result(
        desktop_entry_path=desktop_entry,
        tray_unit_path=tray_unit,
        voice_loop_unit_path=voice_loop_unit,
        config=AppConfig.from_env({"OPERANCE_DEVELOPER_MODE": "1"}),
        report=_report(stt_status="warn"),
        systemctl_command="/missing/systemctl",
    )

    payload = result.to_dict()

    assert result.status == "failed"
    assert {check["name"]: check["status"] for check in payload["checks"]}["installed_live_mode"] == "failed"
    assert {check["name"]: check["status"] for check in payload["checks"]}["stt_backend_available"] == "failed"
    assert "operance --support-bundle" in payload["next_steps"]


def test_installed_smoke_warns_when_tray_service_is_inactive(monkeypatch, tmp_path: Path) -> None:
    desktop_entry = tmp_path / "operance.desktop"
    tray_unit = tmp_path / "operance-tray.service"
    voice_loop_unit = tmp_path / "operance-voice-loop.service"
    for path in (desktop_entry, tray_unit, voice_loop_unit):
        path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "LoadState=loaded\n"
                "ActiveState=inactive\n"
                "FragmentPath=/usr/lib/systemd/user/operance-tray.service\n"
                "ExecStart={ path=/usr/bin/operance ; argv[]=/usr/bin/operance --tray-run ; }\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("operance.installed_smoke.subprocess.run", fake_run)

    result = build_installed_smoke_result(
        desktop_entry_path=desktop_entry,
        tray_unit_path=tray_unit,
        voice_loop_unit_path=voice_loop_unit,
        config=_live_config(),
        report=_report(),
    )

    assert result.status == "warn"
    assert "systemctl --user enable --now operance-tray.service" in result.to_dict()["next_steps"]


def test_installed_smoke_fails_when_user_unit_shadows_packaged_service(monkeypatch, tmp_path: Path) -> None:
    desktop_entry = tmp_path / "operance.desktop"
    tray_unit = tmp_path / "operance-tray.service"
    voice_loop_unit = tmp_path / "operance-voice-loop.service"
    for path in (desktop_entry, tray_unit, voice_loop_unit):
        path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "LoadState=loaded\n"
                "ActiveState=active\n"
                "FragmentPath=/home/test/.config/systemd/user/operance-tray.service\n"
                "ExecStart={ path=/home/test/checkout/.venv/bin/python ; argv[]=/home/test/checkout/.venv/bin/python -m operance.cli --tray-run ; }\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("operance.installed_smoke.subprocess.run", fake_run)

    result = build_installed_smoke_result(
        desktop_entry_path=desktop_entry,
        tray_unit_path=tray_unit,
        voice_loop_unit_path=voice_loop_unit,
        config=_live_config(),
        report=_report(),
    )

    payload = result.to_dict()

    assert result.status == "failed"
    assert {check["name"]: check["status"] for check in payload["checks"]}["tray_user_service_not_shadowed"] == "failed"
