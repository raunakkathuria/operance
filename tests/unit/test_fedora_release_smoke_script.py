import subprocess
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_fedora_release_smoke.sh"


def _run_fedora_release_smoke_script(
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


def test_fedora_release_smoke_script_dry_run_prints_default_steps() -> None:
    result = _run_fedora_release_smoke_script(
        "--dry-run",
        "--root-dir",
        "/tmp/operance-release",
        "--version",
        "1.2.3",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir /tmp/operance-release --version 1.2.3 --bundle-profile mvp --dry-run",
        "+ ./scripts/run_installed_beta_smoke.sh --package /tmp/operance-release/rpm/operance-1.2.3-1.noarch.rpm --installer dnf --require-mvp-runtime --uninstall-after --dry-run",
    ]
    assert result.stderr == ""


def test_fedora_release_smoke_script_can_forward_smoke_options_and_keep_install() -> None:
    result = _run_fedora_release_smoke_script(
        "--dry-run",
        "--root-dir",
        "/tmp/operance-release",
        "--version",
        "2.0.0",
        "--support-bundle-out",
        "/tmp/operance-release-support.tar.gz",
        "--no-sudo",
        "--keep-installed",
        "--",
        "--command",
        "/tmp/fake-operance",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir /tmp/operance-release --version 2.0.0 --bundle-profile mvp --dry-run",
        (
            "+ ./scripts/run_installed_beta_smoke.sh --package /tmp/operance-release/rpm/operance-2.0.0-1.noarch.rpm "
            "--installer dnf --support-bundle-out /tmp/operance-release-support.tar.gz --no-sudo "
            "--require-mvp-runtime --dry-run "
            "--command /tmp/fake-operance"
        ),
    ]
    assert result.stderr == ""


def test_fedora_release_smoke_script_forwards_bundle_profile_options() -> None:
    result = _run_fedora_release_smoke_script(
        "--dry-run",
        "--root-dir",
        "/tmp/operance-release",
        "--bundle-profile",
        "mvp",
        "--bundle-python",
        "/tmp/operance-python",
        "--bundle-source-site-packages",
        "/tmp/operance-site-packages",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir /tmp/operance-release --version 0.1.0 --bundle-profile mvp --bundle-python /tmp/operance-python --bundle-source-site-packages /tmp/operance-site-packages --dry-run",
        "+ ./scripts/run_installed_beta_smoke.sh --package /tmp/operance-release/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --require-mvp-runtime --uninstall-after --dry-run",
    ]
    assert result.stderr == ""


def test_fedora_release_smoke_script_fails_fast_when_rpm_build_tools_are_missing(tmp_path) -> None:
    empty_path = tmp_path / "bin"
    empty_path.mkdir()
    dirname_bin = shutil.which("dirname")
    assert dirname_bin is not None
    (empty_path / "dirname").symlink_to(dirname_bin)

    result = _run_fedora_release_smoke_script(
        "--version",
        "1.2.3",
        check=False,
        env={"PATH": str(empty_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        "rpmbuild not found; install RPM packaging tools with "
        "./scripts/install_packaging_tools.sh --rpm"
    )
