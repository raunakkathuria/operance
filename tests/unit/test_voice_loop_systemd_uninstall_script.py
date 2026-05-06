import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "uninstall_voice_loop_user_service.sh"


def _run_uninstall_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_voice_loop_systemd_uninstall_script_removes_rendered_unit_when_systemctl_is_skipped(tmp_path: Path) -> None:
    unit_dir = tmp_path / "systemd-user"
    unit_dir.mkdir()
    unit_path = unit_dir / "operance-voice-loop.service"
    unit_path.write_text("[Unit]\nDescription=Operance continuous voice loop\n", encoding="utf-8")

    result = _run_uninstall_script(
        "--unit-dir",
        str(unit_dir),
        "--skip-systemctl",
    )

    assert result.stdout.splitlines() == [
        f"+ rm -f {unit_path}",
    ]
    assert result.stderr == ""
    assert not unit_path.exists()


def test_voice_loop_systemd_uninstall_script_dry_run_prints_expected_commands() -> None:
    result = _run_uninstall_script(
        "--dry-run",
        "--unit-dir",
        "/tmp/operance-systemd",
    )

    assert result.stdout.splitlines() == [
        "+ systemctl --user disable --now operance-voice-loop.service || true",
        "+ rm -f /tmp/operance-systemd/operance-voice-loop.service",
        "+ systemctl --user daemon-reload",
    ]
    assert result.stderr == ""
