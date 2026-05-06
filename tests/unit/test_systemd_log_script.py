import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "tail_systemd_user_service_logs.sh"


def _run_log_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_systemd_log_script_dry_run_prints_expected_command() -> None:
    result = _run_log_script("--dry-run", "--lines", "25")

    assert result.stdout.splitlines() == [
        "+ journalctl --user --unit operance-tray.service -n 25 --no-pager",
    ]
    assert result.stderr == ""


def test_systemd_log_script_dry_run_supports_follow_mode() -> None:
    result = _run_log_script("--dry-run", "--follow")

    assert result.stdout.splitlines() == [
        "+ journalctl --user --unit operance-tray.service -n 50 --no-pager --follow",
    ]
    assert result.stderr == ""


def test_systemd_log_script_can_target_voice_loop_service() -> None:
    result = _run_log_script("--dry-run", "--voice-loop", "--lines", "10")

    assert result.stdout.splitlines() == [
        "+ journalctl --user --unit operance-voice-loop.service -n 10 --no-pager",
    ]
    assert result.stderr == ""
