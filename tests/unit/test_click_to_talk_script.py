import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_click_to_talk.sh"


def _run_click_to_talk_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_click_to_talk_script_dry_run_prints_default_command() -> None:
    result = _run_click_to_talk_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --click-to-talk",
    ]
    assert result.stderr == ""


def test_click_to_talk_script_forwards_extra_cli_args_after_separator() -> None:
    result = _run_click_to_talk_script(
        "--dry-run",
        "--python",
        ".envs/operance/bin/python",
        "--",
        "--audio-device",
        "alsa_input.usb-mic",
    )

    assert result.stdout.splitlines() == [
        "+ .envs/operance/bin/python -m operance.cli --click-to-talk --audio-device alsa_input.usb-mic",
    ]
    assert result.stderr == ""
