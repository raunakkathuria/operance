import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_voice_loop.sh"


def _run_voice_loop_script(*args: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        return subprocess.run(
            ["bash", str(SCRIPT_PATH), *args],
            capture_output=True,
            check=True,
            cwd=REPO_ROOT,
            env={
                "HOME": str(temp_root / "home"),
                "PATH": os.environ["PATH"],
                "XDG_CONFIG_HOME": str(temp_root / "config-home"),
            },
            text=True,
        )


def test_voice_loop_script_dry_run_prints_default_command() -> None:
    result = _run_voice_loop_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --voice-loop",
    ]
    assert result.stderr == ""


def test_voice_loop_script_forwards_extra_cli_args_after_separator() -> None:
    result = _run_voice_loop_script(
        "--dry-run",
        "--python",
        ".envs/operance/bin/python",
        "--",
        "--wakeword-model",
        "/tmp/operance.onnx",
        "--voice-loop-max-commands",
        "2",
    )

    assert result.stdout.splitlines() == [
        "+ .envs/operance/bin/python -m operance.cli --voice-loop --wakeword-model /tmp/operance.onnx --voice-loop-max-commands 2",
    ]
    assert result.stderr == ""


def test_voice_loop_script_loads_optional_args_file(tmp_path: Path) -> None:
    args_file = tmp_path / "voice-loop.args"
    args_file.write_text(
        "\n".join(
            [
                "# comment",
                "--wakeword-model",
                "/tmp/operance.onnx",
                "",
                "--voice-loop-max-commands",
                "2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_voice_loop_script("--dry-run", "--args-file", str(args_file))

    assert result.stdout.splitlines() == [
        f"+ .venv/bin/python -m operance.cli --voice-loop --wakeword-model /tmp/operance.onnx --voice-loop-max-commands 2",
    ]
    assert result.stderr == ""


def test_voice_loop_script_uses_user_config_when_repo_args_are_missing(tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"
    args_path = config_home / "operance" / "voice-loop.args"
    args_path.parent.mkdir(parents=True)
    args_path.write_text(
        "--voice-loop-max-commands\n3\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--dry-run"],
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": os.environ["PATH"],
            "XDG_CONFIG_HOME": str(config_home),
        },
        text=True,
    )

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --voice-loop --voice-loop-max-commands 3",
    ]
    assert result.stderr == ""
