import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_rpm_package.sh"


def _run_rpm_script(
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


def test_rpm_package_script_dry_run_prints_expected_steps() -> None:
    result = _run_rpm_script(
        "--dry-run",
        "--spec-dir",
        "/tmp/operance-rpm",
        "--version",
        "1.2.3",
    )

    assert result.stdout.splitlines() == [
        "+ mkdir -p /tmp/operance-rpm/SOURCES",
        "+ render packaging/rpm/operance.spec.in -> /tmp/operance-rpm/operance.spec",
        "+ ./scripts/render_packaged_assets.sh --output-dir /tmp/operance-rpm/SOURCES/packaged-assets --entrypoint /usr/bin/operance --bundle-profile base --package-version 1.2.3",
        "+ tar -czf /tmp/operance-rpm/SOURCES/operance-packaged-assets-1.2.3.tar.gz -C /tmp/operance-rpm/SOURCES packaged-assets",
        "+ rpmbuild --define _topdir /tmp/operance-rpm -bb /tmp/operance-rpm/operance.spec",
        "+ mkdir -p /tmp/operance-rpm",
        "+ cp /tmp/operance-rpm/RPMS/noarch/operance-1.2.3-*.noarch.rpm /tmp/operance-rpm/operance-1.2.3-1.noarch.rpm",
    ]
    assert result.stderr == ""


def test_rpm_package_script_forwards_bundle_profile_options() -> None:
    result = _run_rpm_script(
        "--dry-run",
        "--spec-dir",
        "/tmp/operance-rpm",
        "--bundle-profile",
        "mvp",
        "--bundle-python",
        "/tmp/operance-python",
        "--bundle-source-site-packages",
        "/tmp/operance-site-packages",
    )

    assert "+ ./scripts/render_packaged_assets.sh --output-dir /tmp/operance-rpm/SOURCES/packaged-assets --entrypoint /usr/bin/operance --bundle-profile mvp --package-version 0.1.0 --bundle-python /tmp/operance-python --bundle-source-site-packages /tmp/operance-site-packages" in result.stdout.splitlines()
    assert result.stderr == ""


def test_rpm_package_script_can_render_spec_without_building(tmp_path: Path) -> None:
    spec_dir = tmp_path / "operance-rpm"

    result = _run_rpm_script(
        "--skip-build",
        "--spec-dir",
        str(spec_dir),
        "--version",
        "9.9.9",
        "--entrypoint",
        "/opt/operance/bin/operance",
    )

    spec_path = spec_dir / "operance.spec"
    packaged_entrypoint = spec_dir / "SOURCES" / "packaged-assets" / "bin" / "operance"
    voice_loop_args_example = spec_dir / "SOURCES" / "packaged-assets" / "etc" / "operance" / "voice-loop.args.example"
    desktop_entry = spec_dir / "SOURCES" / "packaged-assets" / "applications" / "operance.desktop"
    packaged_icon = spec_dir / "SOURCES" / "packaged-assets" / "icons" / "hicolor" / "scalable" / "apps" / "operance.svg"
    packaged_pyproject = spec_dir / "SOURCES" / "packaged-assets" / "lib" / "operance" / "pyproject.toml"
    packaged_build_info = spec_dir / "SOURCES" / "packaged-assets" / "lib" / "operance" / "build-info.json"
    packaged_runtime_dir = spec_dir / "SOURCES" / "packaged-assets" / "lib" / "operance" / "site-packages" / "operance"
    voice_loop_launcher = spec_dir / "SOURCES" / "packaged-assets" / "lib" / "operance" / "voice-loop-launcher"
    tray_service_unit = spec_dir / "SOURCES" / "packaged-assets" / "systemd" / "operance-tray.service"
    voice_loop_service_unit = spec_dir / "SOURCES" / "packaged-assets" / "systemd" / "operance-voice-loop.service"
    source_tarball = spec_dir / "SOURCES" / "operance-packaged-assets-9.9.9.tar.gz"

    assert result.stderr == ""
    assert spec_path.exists()
    assert packaged_entrypoint.exists()
    assert voice_loop_args_example.exists()
    assert desktop_entry.exists()
    assert packaged_icon.exists()
    assert packaged_pyproject.exists()
    assert packaged_build_info.exists()
    assert packaged_runtime_dir.exists()
    assert voice_loop_launcher.exists()
    assert tray_service_unit.exists()
    assert voice_loop_service_unit.exists()
    assert source_tarball.exists()

    spec_text = spec_path.read_text(encoding="utf-8")
    packaged_entrypoint_text = packaged_entrypoint.read_text(encoding="utf-8")
    voice_loop_args_example_text = voice_loop_args_example.read_text(encoding="utf-8")
    desktop_text = desktop_entry.read_text(encoding="utf-8")
    packaged_pyproject_text = packaged_pyproject.read_text(encoding="utf-8")
    packaged_build_info_text = packaged_build_info.read_text(encoding="utf-8")
    packaged_runtime_init_text = (packaged_runtime_dir / "__init__.py").read_text(encoding="utf-8")
    voice_loop_launcher_text = voice_loop_launcher.read_text(encoding="utf-8")
    tray_service_text = tray_service_unit.read_text(encoding="utf-8")
    voice_loop_service_text = voice_loop_service_unit.read_text(encoding="utf-8")

    assert "Version:        9.9.9" in spec_text
    assert "Name:           operance" in spec_text
    assert "AutoReqProv:    no" in spec_text
    assert "%changelog" in spec_text
    assert "* Fri May 15 2026 Operance Maintainers <maintainers@operance.local> - 9.9.9-1" in spec_text
    assert "- Initial RPM package scaffold." in spec_text
    assert "install -Dpm0755 packaged-assets/bin/operance %{buildroot}/opt/operance/bin/operance" in spec_text
    assert "install -Dpm0644 packaged-assets/icons/hicolor/scalable/apps/operance.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/operance.svg" in spec_text
    files_section = spec_text.split("%files", maxsplit=1)[1]
    assert "/etc/operance/voice-loop.args.example" in spec_text
    assert "%{_datadir}/icons/hicolor/scalable/apps/operance.svg" in files_section
    assert "cp -a packaged-assets/lib/operance/site-packages/. %{buildroot}%{_prefix}/lib/operance/site-packages/" in spec_text
    assert "%{_prefix}/lib/operance/voice-loop-launcher" in spec_text
    assert "/opt/operance/bin/operance" in spec_text
    assert "%{_userunitdir}/operance-voice-loop.service" in spec_text
    assert 'python_bin="/usr/bin/python3"' in packaged_entrypoint_text
    assert "--wakeword-model" in voice_loop_args_example_text
    assert "Exec=/opt/operance/bin/operance --tray-run" in desktop_text
    assert "Icon=operance" in desktop_text
    assert 'version = "0.1.0"' in packaged_pyproject_text
    assert '"package_version": "9.9.9"' in packaged_build_info_text
    assert '"package_profile": "base"' in packaged_build_info_text
    assert '"""Operance package bootstrap."""' in packaged_runtime_init_text
    assert 'entrypoint="/opt/operance/bin/operance"' in voice_loop_launcher_text
    assert "ExecStart=/opt/operance/bin/operance --tray-run" in tray_service_text
    assert "ExecStart=/usr/lib/operance/voice-loop-launcher" in voice_loop_service_text


def test_rpm_package_script_copies_built_artifact_to_output_dir(tmp_path: Path) -> None:
    spec_dir = tmp_path / "rpm-spec"
    output_dir = tmp_path / "rpm-out"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _write_executable(
        fake_bin / "rpmbuild",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "topdir=\"${2#_topdir }\"\n"
            "mkdir -p \"${topdir}/RPMS/noarch\"\n"
            "touch \"${topdir}/RPMS/noarch/operance-9.9.9-1.noarch.rpm\"\n"
        ),
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_rpm_script(
        "--spec-dir",
        str(spec_dir),
        "--output-dir",
        str(output_dir),
        "--version",
        "9.9.9",
        env=env,
    )

    assert result.stderr == ""
    assert (output_dir / "operance-9.9.9-1.noarch.rpm").exists()


def test_rpm_package_script_copies_disttagged_built_artifact_to_normalized_output_path(tmp_path: Path) -> None:
    spec_dir = tmp_path / "rpm-spec"
    output_dir = tmp_path / "rpm-out"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _write_executable(
        fake_bin / "rpmbuild",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "topdir=\"${2#_topdir }\"\n"
            "mkdir -p \"${topdir}/RPMS/noarch\"\n"
            "touch \"${topdir}/RPMS/noarch/operance-9.9.9-1.fc43.noarch.rpm\"\n"
        ),
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_rpm_script(
        "--spec-dir",
        str(spec_dir),
        "--output-dir",
        str(output_dir),
        "--version",
        "9.9.9",
        env=env,
    )

    assert result.stderr == ""
    assert (output_dir / "operance-9.9.9-1.noarch.rpm").exists()
