import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_mvp.sh"


def _run_mvp_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_mvp_script_dry_run_prints_default_command() -> None:
    result = _run_mvp_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --mvp-launch",
    ]
    assert result.stderr == ""


def test_mvp_script_forwards_extra_cli_args_after_separator() -> None:
    result = _run_mvp_script(
        "--dry-run",
        "--python",
        ".envs/operance/bin/python",
        "--",
        "--audio-device",
        "alsa_input.usb-mic",
    )

    assert result.stdout.splitlines() == [
        "+ .envs/operance/bin/python -m operance.cli --mvp-launch --audio-device alsa_input.usb-mic",
    ]
    assert result.stderr == ""


def test_mvp_script_can_print_supported_commands_command() -> None:
    result = _run_mvp_script("--dry-run", "--supported-commands")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --supported-commands",
    ]
    assert result.stderr == ""


def test_mvp_script_can_print_available_supported_commands_command() -> None:
    result = _run_mvp_script("--dry-run", "--supported-commands", "--supported-commands-available-only")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --supported-commands --supported-commands-available-only",
    ]
    assert result.stderr == ""


def test_mvp_script_can_print_support_snapshot_command() -> None:
    result = _run_mvp_script("--dry-run", "--support-snapshot")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --support-snapshot",
    ]
    assert result.stderr == ""


def test_mvp_script_can_forward_support_snapshot_output_path() -> None:
    result = _run_mvp_script(
        "--dry-run",
        "--support-snapshot",
        "--support-snapshot-out",
        "/tmp/operance-support.json",
    )

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --support-snapshot --support-snapshot-out /tmp/operance-support.json",
    ]
    assert result.stderr == ""


def test_mvp_script_can_print_support_bundle_command() -> None:
    result = _run_mvp_script("--dry-run", "--support-bundle")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --support-bundle",
    ]
    assert result.stderr == ""


def test_mvp_script_can_forward_support_bundle_output_path() -> None:
    result = _run_mvp_script(
        "--dry-run",
        "--support-bundle",
        "--support-bundle-out",
        "/tmp/operance-support.tar.gz",
    )

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --support-bundle --support-bundle-out /tmp/operance-support.tar.gz",
    ]
    assert result.stderr == ""
