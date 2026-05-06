import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_local_linux_app.sh"


def _run_install_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_local_install_orchestrator_dry_run_prints_expected_steps() -> None:
    result = _run_install_script(
        "--dry-run",
        "--voice",
        "--voice-loop",
        "--venv",
        ".envs/operance",
        "--unit-dir",
        "/tmp/operance-systemd",
        "--skip-systemctl",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/install_linux_dev.sh --ui --voice --venv .envs/operance",
        "+ ./scripts/install_systemd_user_service.sh --python .envs/operance/bin/python --unit-dir /tmp/operance-systemd --skip-systemctl",
        "+ ./scripts/install_voice_loop_user_service.sh --unit-dir /tmp/operance-systemd --skip-systemctl",
    ]
    assert result.stderr == ""


def test_local_install_orchestrator_can_render_service_without_bootstrap(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"

    result = _run_install_script(
        "--skip-bootstrap",
        "--skip-systemctl",
        "--venv",
        ".venv",
        "--unit-dir",
        str(unit_dir),
    )

    unit_path = unit_dir / "operance-tray.service"

    assert result.stdout.splitlines() == [
        f"+ ./scripts/install_systemd_user_service.sh --python .venv/bin/python --unit-dir {unit_dir} --skip-systemctl",
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-tray.service.in -> {unit_path}",
    ]
    assert result.stderr == ""
    assert unit_path.exists()

    unit_text = unit_path.read_text(encoding="utf-8")
    assert f"ExecStart={REPO_ROOT / '.venv/bin/python'} -m operance.cli --tray-run" in unit_text


def test_local_install_orchestrator_can_render_voice_loop_service_without_bootstrap(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"

    result = _run_install_script(
        "--skip-bootstrap",
        "--skip-systemctl",
        "--voice-loop",
        "--venv",
        ".venv",
        "--unit-dir",
        str(unit_dir),
    )

    tray_unit_path = unit_dir / "operance-tray.service"
    voice_unit_path = unit_dir / "operance-voice-loop.service"

    assert result.stdout.splitlines() == [
        f"+ ./scripts/install_systemd_user_service.sh --python .venv/bin/python --unit-dir {unit_dir} --skip-systemctl",
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-tray.service.in -> {tray_unit_path}",
        f"+ ./scripts/install_voice_loop_user_service.sh --unit-dir {unit_dir} --skip-systemctl",
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-voice-loop.service.in -> {voice_unit_path}",
    ]
    assert result.stderr == ""
    assert tray_unit_path.exists()
    assert voice_unit_path.exists()

    voice_unit_text = voice_unit_path.read_text(encoding="utf-8")
    assert f"ExecStart=/bin/bash {REPO_ROOT / 'scripts/run_voice_loop.sh'}" in voice_unit_text


def test_local_install_orchestrator_ignores_unrelated_units(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"
    unrelated_tray_unit = unit_dir / "archived-tray.service"
    unrelated_voice_unit = unit_dir / "archived-voice-loop.service"
    unrelated_tray_unit.parent.mkdir(parents=True)
    unrelated_tray_unit.write_text("[Unit]\nDescription=Archived tray app\n", encoding="utf-8")
    unrelated_voice_unit.write_text("[Unit]\nDescription=Archived voice loop\n", encoding="utf-8")

    result = _run_install_script(
        "--skip-bootstrap",
        "--skip-systemctl",
        "--voice-loop",
        "--venv",
        ".venv",
        "--unit-dir",
        str(unit_dir),
    )

    tray_unit_path = unit_dir / "operance-tray.service"
    voice_unit_path = unit_dir / "operance-voice-loop.service"
    assert result.stdout.splitlines() == [
        f"+ ./scripts/install_systemd_user_service.sh --python .venv/bin/python --unit-dir {unit_dir} --skip-systemctl",
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-tray.service.in -> {tray_unit_path}",
        f"+ ./scripts/install_voice_loop_user_service.sh --unit-dir {unit_dir} --skip-systemctl",
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-voice-loop.service.in -> {voice_unit_path}",
    ]
    assert result.stderr == ""
