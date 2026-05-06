import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_tts_assets.sh"


def _run_install_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        text=True,
    )


def test_tts_asset_install_script_dry_run_prints_expected_steps(tmp_path: Path) -> None:
    model_path = tmp_path / "kokoro.onnx"
    voices_path = tmp_path / "voices.bin"
    model_path.write_bytes(b"model")
    voices_path.write_bytes(b"voices")
    config_home = tmp_path / "config-home"

    result = _run_install_script(
        "--dry-run",
        "--model",
        str(model_path),
        "--voices",
        str(voices_path),
        "--config-home",
        str(config_home),
    )

    target_dir = config_home / "operance" / "tts"
    target_model_path = target_dir / "kokoro.onnx"
    target_voices_path = target_dir / "voices.bin"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {target_dir}",
        f"+ cp {model_path} {target_model_path}",
        f"+ cp {voices_path} {target_voices_path}",
    ]
    assert result.stderr == ""


def test_tts_asset_install_script_copies_selected_assets(tmp_path: Path) -> None:
    model_path = tmp_path / "kokoro.onnx"
    model_path.write_bytes(b"model")
    config_home = tmp_path / "config-home"

    result = _run_install_script(
        "--model",
        str(model_path),
        "--config-home",
        str(config_home),
    )

    target_model_path = config_home / "operance" / "tts" / "kokoro.onnx"
    target_voices_path = config_home / "operance" / "tts" / "voices.bin"

    assert result.stderr == ""
    assert target_model_path.exists()
    assert target_model_path.read_bytes() == b"model"
    assert not target_voices_path.exists()


def test_tts_asset_install_script_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    model_path = tmp_path / "kokoro.onnx"
    model_path.write_bytes(b"new-model")
    config_home = tmp_path / "config-home"
    target_model_path = config_home / "operance" / "tts" / "kokoro.onnx"
    target_model_path.parent.mkdir(parents=True)
    target_model_path.write_bytes(b"existing-model")

    result = _run_install_script(
        "--model",
        str(model_path),
        "--config-home",
        str(config_home),
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == f"target TTS model already exists: {target_model_path}"
