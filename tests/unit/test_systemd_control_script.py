import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "control_systemd_user_services.sh"


def _run_control_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


def test_systemd_control_script_dry_run_defaults_to_tray_status() -> None:
    result = _run_control_script("status", "--dry-run")

    assert result.stdout.splitlines() == [
        "+ systemctl --user status operance-tray.service --no-pager",
    ]
    assert result.stderr == ""


def test_systemd_control_script_dry_run_can_restart_both_services() -> None:
    result = _run_control_script("restart", "--all", "--dry-run")

    assert result.stdout.splitlines() == [
        "+ systemctl --user restart operance-tray.service operance-voice-loop.service",
    ]
    assert result.stderr == ""


def test_systemd_control_script_dry_run_can_enable_voice_loop_service() -> None:
    result = _run_control_script("enable", "--voice-loop", "--dry-run")

    assert result.stdout.splitlines() == [
        "+ systemctl --user enable --now operance-voice-loop.service",
    ]
    assert result.stderr == ""


def test_systemd_control_script_runs_voice_loop_command_through_systemctl(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_systemctl = fake_bin / "systemctl"
    fake_systemctl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    fake_systemctl.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_control_script("start", "--voice-loop", env=env)

    assert result.stdout.splitlines() == [
        "+ systemctl --user start operance-voice-loop.service",
        "--user start operance-voice-loop.service",
    ]
    assert result.stderr == ""
