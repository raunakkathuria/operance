import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "uninstall_local_linux_app.sh"


def _run_uninstall_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_local_uninstall_orchestrator_dry_run_prints_expected_steps() -> None:
    result = _run_uninstall_script(
        "--dry-run",
        "--voice-loop",
        "--venv",
        ".envs/operance",
        "--unit-dir",
        "/tmp/operance-systemd",
        "--remove-venv",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/uninstall_systemd_user_service.sh --unit-dir /tmp/operance-systemd --dry-run",
        "+ ./scripts/uninstall_voice_loop_user_service.sh --unit-dir /tmp/operance-systemd --dry-run",
        "+ rm -rf .envs/operance",
    ]
    assert result.stderr == ""


def test_local_uninstall_orchestrator_can_remove_service_and_venv_without_systemctl(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"
    unit_dir.mkdir()
    tray_unit_path = unit_dir / "operance-tray.service"
    tray_unit_path.write_text("[Unit]\nDescription=Operance tray app\n", encoding="utf-8")
    voice_unit_path = unit_dir / "operance-voice-loop.service"
    voice_unit_path.write_text("[Unit]\nDescription=Operance continuous voice loop\n", encoding="utf-8")
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    result = _run_uninstall_script(
        "--skip-systemctl",
        "--voice-loop",
        "--remove-venv",
        "--venv",
        str(venv_dir),
        "--unit-dir",
        str(unit_dir),
    )

    assert result.stdout.splitlines() == [
        f"+ ./scripts/uninstall_systemd_user_service.sh --unit-dir {unit_dir} --skip-systemctl",
        f"+ rm -f {tray_unit_path}",
        f"+ ./scripts/uninstall_voice_loop_user_service.sh --unit-dir {unit_dir} --skip-systemctl",
        f"+ rm -f {voice_unit_path}",
        f"+ rm -rf {venv_dir}",
    ]
    assert result.stderr == ""
    assert not tray_unit_path.exists()
    assert not voice_unit_path.exists()
    assert not venv_dir.exists()
