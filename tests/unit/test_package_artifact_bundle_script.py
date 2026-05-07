import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_package_artifacts.sh"


def _run_bundle_script(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_package_artifact_bundle_script_dry_run_prints_expected_steps() -> None:
    result = _run_bundle_script(
        "--dry-run",
        "--version",
        "1.2.3",
        "--root-dir",
        "/tmp/operance-package-builds",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_deb_package.sh --staging-dir /tmp/operance-package-builds/deb/operance --output-dir /tmp/operance-package-builds/deb --bundle-profile base --version 1.2.3 --dry-run",
        "+ ./scripts/build_rpm_package.sh --spec-dir /tmp/operance-package-builds/rpm --output-dir /tmp/operance-package-builds/rpm --bundle-profile base --version 1.2.3 --dry-run",
    ]
    assert result.stderr == ""


def test_package_artifact_bundle_script_forwards_bundle_profile_options() -> None:
    result = _run_bundle_script(
        "--dry-run",
        "--rpm",
        "--root-dir",
        "/tmp/operance-package-builds",
        "--bundle-profile",
        "mvp",
        "--bundle-python",
        "/tmp/operance-python",
        "--bundle-source-site-packages",
        "/tmp/operance-site-packages",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_rpm_package.sh --spec-dir /tmp/operance-package-builds/rpm --output-dir /tmp/operance-package-builds/rpm --bundle-profile mvp --bundle-python /tmp/operance-python --bundle-source-site-packages /tmp/operance-site-packages --dry-run",
    ]
    assert result.stderr == ""


def test_package_artifact_bundle_script_can_build_both_formats_with_fake_tooling(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "package-builds"
    fake_bin = tmp_path / "bin"
    rpm_log = tmp_path / "rpmbuild.log"

    fake_bin.mkdir()
    _write_executable(
        fake_bin / "dpkg-deb",
        "#!/usr/bin/env bash\nset -euo pipefail\ntouch \"$3\"\n",
    )
    _write_executable(
        fake_bin / "rpmbuild",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" > \"$FAKE_RPMBUILD_LOG\"\n"
            "topdir=\"${2#_topdir }\"\n"
            "mkdir -p \"${topdir}/RPMS/noarch\"\n"
            "touch \"${topdir}/RPMS/noarch/operance-9.9.9-1.noarch.rpm\"\n"
        ),
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_RPMBUILD_LOG"] = str(rpm_log)

    result = _run_bundle_script(
        "--root-dir",
        str(root_dir),
        "--version",
        "9.9.9",
        "--entrypoint",
        "/opt/operance/bin/operance",
        env=env,
    )

    deb_artifact = root_dir / "deb" / "operance_9.9.9_all.deb"
    rpm_artifact = root_dir / "rpm" / "operance-9.9.9-1.noarch.rpm"
    rpm_spec = root_dir / "rpm" / "operance.spec"
    rpm_tarball = root_dir / "rpm" / "SOURCES" / "operance-packaged-assets-9.9.9.tar.gz"
    desktop_entry = root_dir / "deb" / "operance" / "usr" / "share" / "applications" / "operance.desktop"

    assert result.stderr == ""
    assert deb_artifact.exists()
    assert rpm_artifact.exists()
    assert rpm_spec.exists()
    assert rpm_tarball.exists()
    assert rpm_log.exists()
    assert "Exec=/opt/operance/bin/operance --tray-run" in desktop_entry.read_text(encoding="utf-8")


def test_package_artifact_bundle_script_can_select_rpm_only(tmp_path: Path) -> None:
    root_dir = tmp_path / "package-builds"

    result = _run_bundle_script(
        "--dry-run",
        "--rpm",
        "--root-dir",
        str(root_dir),
        "--version",
        "2.0.0",
    )

    assert result.stdout.splitlines() == [
        f"+ ./scripts/build_rpm_package.sh --spec-dir {root_dir / 'rpm'} --output-dir {root_dir / 'rpm'} --bundle-profile base --version 2.0.0 --dry-run",
    ]
    assert result.stderr == ""
