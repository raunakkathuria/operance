import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_linux_dev.sh"


def _run_install_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_install_script_dry_run_prints_default_steps() -> None:
    result = _run_install_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ python3 -m venv .venv",
        "+ .venv/bin/python -m pip install --upgrade pip",
        '+ .venv/bin/python -m pip install -e ".[dev]"',
        "+ .venv/bin/python -m operance.cli --doctor",
    ]
    assert result.stderr == ""


def test_install_script_dry_run_supports_optional_extras_and_custom_venv() -> None:
    result = _run_install_script(
        "--dry-run",
        "--ui",
        "--voice",
        "--skip-doctor",
        "--venv",
        ".envs/operance",
    )

    assert result.stdout.splitlines() == [
        "+ python3 -m venv .envs/operance",
        "+ .envs/operance/bin/python -m pip install --upgrade pip",
        '+ .envs/operance/bin/python -m pip install -e ".[dev,ui,voice]"',
    ]
    assert result.stderr == ""
