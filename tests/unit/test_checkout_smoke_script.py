import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_checkout_smoke.sh"


def _run_checkout_smoke_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_checkout_smoke_script_dry_run_prints_default_steps() -> None:
    result = _run_checkout_smoke_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --version",
        "+ .venv/bin/python -m operance.cli --doctor",
        "+ .venv/bin/python -m operance.cli --setup-actions",
        "+ .venv/bin/python -m operance.cli --supported-commands --supported-commands-available-only",
        "+ .venv/bin/python -m operance.cli --support-bundle",
    ]
    assert result.stderr == ""


def test_checkout_smoke_script_can_forward_bundle_output_path() -> None:
    result = _run_checkout_smoke_script(
        "--dry-run",
        "--support-bundle-out",
        "/tmp/operance-support.tar.gz",
    )

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m operance.cli --version",
        "+ .venv/bin/python -m operance.cli --doctor",
        "+ .venv/bin/python -m operance.cli --setup-actions",
        "+ .venv/bin/python -m operance.cli --supported-commands --supported-commands-available-only",
        "+ .venv/bin/python -m operance.cli --support-bundle --support-bundle-out /tmp/operance-support.tar.gz",
    ]
    assert result.stderr == ""
