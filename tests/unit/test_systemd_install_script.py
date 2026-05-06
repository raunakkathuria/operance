import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_systemd_user_service.sh"


def _run_install_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_systemd_install_script_renders_repo_local_tray_unit(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"

    result = _run_install_script(
        "--python",
        ".venv/bin/python",
        "--unit-dir",
        str(unit_dir),
        "--skip-systemctl",
    )

    unit_path = unit_dir / "operance-tray.service"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-tray.service.in -> {unit_path}",
    ]
    assert result.stderr == ""
    assert unit_path.exists()

    unit_text = unit_path.read_text(encoding="utf-8")
    assert "Description=Operance tray app" in unit_text
    assert f"WorkingDirectory={REPO_ROOT}" in unit_text
    assert f"ExecStart={REPO_ROOT / '.venv/bin/python'} -m operance.cli --tray-run" in unit_text
    assert "WantedBy=default.target" in unit_text


def test_systemd_install_script_dry_run_prints_expected_commands() -> None:
    result = _run_install_script(
        "--dry-run",
        "--python",
        ".venv/bin/python",
        "--unit-dir",
        "/tmp/operance-systemd",
    )

    assert result.stdout.splitlines() == [
        "+ mkdir -p /tmp/operance-systemd",
        "+ render packaging/systemd/operance-tray.service.in -> /tmp/operance-systemd/operance-tray.service",
        "+ systemctl --user daemon-reload",
        "+ systemctl --user enable --now operance-tray.service",
    ]
    assert result.stderr == ""


def test_systemd_install_script_ignores_unrelated_unit_file(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"
    unrelated_unit_path = unit_dir / "archived-tray.service"
    unrelated_unit_path.parent.mkdir(parents=True)
    unrelated_unit_path.write_text("[Unit]\nDescription=Archived tray app\n", encoding="utf-8")

    result = _run_install_script(
        "--python",
        ".venv/bin/python",
        "--unit-dir",
        str(unit_dir),
        "--skip-systemctl",
    )

    unit_path = unit_dir / "operance-tray.service"
    assert result.stdout.splitlines() == [
        f"+ mkdir -p {unit_dir}",
        f"+ render packaging/systemd/operance-tray.service.in -> {unit_path}",
    ]
    assert result.stderr == ""
    assert unit_path.exists()
