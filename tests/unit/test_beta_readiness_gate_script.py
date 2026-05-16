import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_beta_readiness_gate.sh"


def _run_beta_readiness_gate_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_beta_readiness_gate_dry_run_prints_default_steps() -> None:
    result = _run_beta_readiness_gate_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m pytest",
        "+ git grep -n -i <old-brand> -- .",
        "+ ./scripts/run_beta_smoke.sh --python .venv/bin/python",
        "+ ./scripts/run_fedora_gate.sh --reset-user-services --dry-run",
        "+ ./scripts/run_installed_desktop_smoke.sh --dry-run",
    ]
    assert result.stderr == ""


def test_beta_readiness_gate_can_forward_options() -> None:
    result = _run_beta_readiness_gate_script(
        "--python",
        "/tmp/operance-python",
        "--support-bundle-out",
        "/tmp/operance-beta-support.tar.gz",
        "--run-package-gate",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ /tmp/operance-python -m pytest",
        "+ git grep -n -i <old-brand> -- .",
        (
            "+ ./scripts/run_beta_smoke.sh --python /tmp/operance-python "
            "--support-bundle-out /tmp/operance-beta-support.tar.gz"
        ),
        "+ ./scripts/run_fedora_gate.sh --reset-user-services --keep-installed",
        "+ ./scripts/run_installed_desktop_smoke.sh",
    ]
    assert result.stderr == ""
