import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_voice_loop_user_config.sh"


def _run_config_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        text=True,
    )


def test_voice_loop_user_config_script_dry_run_prints_expected_steps(tmp_path: Path) -> None:
    source_path = tmp_path / "voice-loop.args.example"
    source_path.write_text("--wakeword-threshold\n0.6\n", encoding="utf-8")
    config_home = tmp_path / "config-home"

    result = _run_config_script(
        "--dry-run",
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
    )

    target_path = config_home / "operance" / "voice-loop.args"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {config_home / 'operance'}",
        f"+ cp {source_path} {target_path}",
    ]
    assert result.stderr == ""


def test_voice_loop_user_config_script_copies_example_file(tmp_path: Path) -> None:
    source_path = tmp_path / "voice-loop.args.example"
    source_path.write_text("--voice-loop-max-commands\n2\n", encoding="utf-8")
    config_home = tmp_path / "config-home"

    result = _run_config_script(
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
    )

    target_path = config_home / "operance" / "voice-loop.args"

    assert result.stderr == ""
    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == "--voice-loop-max-commands\n2\n"


def test_voice_loop_user_config_script_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    source_path = tmp_path / "voice-loop.args.example"
    source_path.write_text("--voice-loop-max-commands\n2\n", encoding="utf-8")
    config_home = tmp_path / "config-home"
    target_path = config_home / "operance" / "voice-loop.args"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("existing\n", encoding="utf-8")

    result = _run_config_script(
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == f"target config already exists: {target_path}"
