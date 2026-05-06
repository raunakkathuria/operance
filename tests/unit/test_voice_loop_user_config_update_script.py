import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "update_voice_loop_user_config.sh"


def _run_update_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        text=True,
    )


def test_voice_loop_user_config_update_script_dry_run_prints_expected_steps(tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"

    result = _run_update_script(
        "--dry-run",
        "--config-home",
        str(config_home),
        "--wakeword-threshold",
        "0.72",
        "--wakeword-model",
        "auto",
    )

    target_path = config_home / "operance" / "voice-loop.args"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {config_home / 'operance'}",
        f"+ write {target_path}",
    ]
    assert result.stderr == ""


def test_voice_loop_user_config_update_script_creates_config_file(tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"

    result = _run_update_script(
        "--config-home",
        str(config_home),
        "--wakeword-threshold",
        "0.72",
        "--wakeword-model",
        "auto",
    )

    target_path = config_home / "operance" / "voice-loop.args"

    assert result.stderr == ""
    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == "--wakeword-model\nauto\n--wakeword-threshold\n0.72\n"


def test_voice_loop_user_config_update_script_replaces_existing_wakeword_settings(tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"
    target_path = config_home / "operance" / "voice-loop.args"
    target_path.parent.mkdir(parents=True)
    target_path.write_text(
        "--voice-loop-max-commands\n2\n--wakeword-model\n/path/to/old.onnx\n--wakeword-threshold\n0.6\n",
        encoding="utf-8",
    )

    result = _run_update_script(
        "--config-home",
        str(config_home),
        "--wakeword-threshold",
        "0.83",
    )

    assert result.stderr == ""
    assert target_path.read_text(encoding="utf-8") == "--voice-loop-max-commands\n2\n--wakeword-model\n/path/to/old.onnx\n--wakeword-threshold\n0.83\n"


def test_voice_loop_user_config_update_script_requires_at_least_one_update(tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"

    result = _run_update_script(
        "--config-home",
        str(config_home),
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "at least one update flag is required"
