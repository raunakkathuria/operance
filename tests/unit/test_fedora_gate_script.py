import subprocess
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_fedora_gate.sh"


def _run_fedora_gate_script(
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


def test_fedora_gate_script_dry_run_prints_default_steps() -> None:
    result = _run_fedora_gate_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ .venv/bin/python -m pytest",
        "+ ./scripts/run_checkout_smoke.sh --python .venv/bin/python --dry-run",
        "+ ./scripts/run_fedora_release_smoke.sh --bundle-profile mvp --dry-run",
    ]
    assert result.stderr == ""


def test_fedora_gate_script_forwards_release_smoke_options() -> None:
    result = _run_fedora_gate_script(
        "--python",
        "/tmp/operance-python",
        "--support-bundle-out",
        "/tmp/operance-support.tar.gz",
        "--no-sudo",
        "--reset-user-services",
        "--keep-installed",
        "--bundle-profile",
        "mvp",
        "--bundle-python",
        "/tmp/operance-build-python",
        "--bundle-source-site-packages",
        "/tmp/operance-site-packages",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ /tmp/operance-python -m pytest",
        "+ ./scripts/run_checkout_smoke.sh --python /tmp/operance-python --dry-run",
        (
            "+ ./scripts/run_fedora_release_smoke.sh --bundle-profile mvp --support-bundle-out "
            "/tmp/operance-support.tar.gz --bundle-python /tmp/operance-build-python "
            "--bundle-source-site-packages /tmp/operance-site-packages --no-sudo "
            "--reset-user-services --keep-installed --dry-run"
        ),
    ]
    assert result.stderr == ""


def test_fedora_gate_script_fails_fast_when_rpm_build_tools_are_missing(tmp_path) -> None:
    empty_path = tmp_path / "bin"
    empty_path.mkdir()
    dirname_bin = shutil.which("dirname")
    assert dirname_bin is not None
    (empty_path / "dirname").symlink_to(dirname_bin)

    result = _run_fedora_gate_script(
        "--python",
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        check=False,
        env={"PATH": str(empty_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        "rpmbuild not found; install RPM packaging tools with "
        "./scripts/install_packaging_tools.sh --rpm"
    )
