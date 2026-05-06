import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_package_scaffolds.sh"


def _run_bundle_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_package_scaffold_bundle_script_dry_run_prints_expected_steps() -> None:
    result = _run_bundle_script(
        "--dry-run",
        "--version",
        "1.2.3",
        "--root-dir",
        "/tmp/operance-package-scaffolds",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_deb_package.sh --skip-build --staging-dir /tmp/operance-package-scaffolds/deb/operance --output-dir /tmp/operance-package-scaffolds/deb --version 1.2.3 --dry-run",
        "+ ./scripts/build_rpm_package.sh --skip-build --spec-dir /tmp/operance-package-scaffolds/rpm --version 1.2.3 --dry-run",
    ]
    assert result.stderr == ""


def test_package_scaffold_bundle_script_can_render_both_staging_trees(tmp_path: Path) -> None:
    root_dir = tmp_path / "package-scaffolds"

    result = _run_bundle_script(
        "--root-dir",
        str(root_dir),
        "--version",
        "9.9.9",
        "--entrypoint",
        "/opt/operance/bin/operance",
    )

    deb_control = root_dir / "deb" / "operance" / "DEBIAN" / "control"
    rpm_spec = root_dir / "rpm" / "operance.spec"

    assert result.stderr == ""
    assert deb_control.exists()
    assert rpm_spec.exists()

    assert "Version: 9.9.9" in deb_control.read_text(encoding="utf-8")
    assert "Version:        9.9.9" in rpm_spec.read_text(encoding="utf-8")
