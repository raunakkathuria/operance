import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_wakeword_model_asset.sh"


def _run_install_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        text=True,
    )


def test_wakeword_model_install_script_dry_run_prints_expected_steps(tmp_path: Path) -> None:
    source_path = tmp_path / "operance.onnx"
    source_path.write_bytes(b"model")
    config_home = tmp_path / "config-home"

    result = _run_install_script(
        "--dry-run",
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
    )

    target_dir = config_home / "operance" / "wakeword"
    target_path = target_dir / "operance.onnx"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {target_dir}",
        f"+ cp {source_path} {target_path}",
    ]
    assert result.stderr == ""


def test_wakeword_model_install_script_copies_model(tmp_path: Path) -> None:
    source_path = tmp_path / "operance.onnx"
    source_path.write_bytes(b"model")
    config_home = tmp_path / "config-home"

    result = _run_install_script(
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
    )

    target_path = config_home / "operance" / "wakeword" / "operance.onnx"

    assert result.stderr == ""
    assert target_path.exists()
    assert target_path.read_bytes() == b"model"


def test_wakeword_model_install_script_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    source_path = tmp_path / "operance.onnx"
    source_path.write_bytes(b"new-model")
    config_home = tmp_path / "config-home"
    target_path = config_home / "operance" / "wakeword" / "operance.onnx"
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(b"existing-model")

    result = _run_install_script(
        "--source",
        str(source_path),
        "--config-home",
        str(config_home),
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == f"target wake-word model already exists: {target_path}"
