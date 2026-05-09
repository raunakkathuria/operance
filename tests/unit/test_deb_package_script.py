import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_deb_package.sh"


def _run_deb_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_deb_package_script_dry_run_prints_expected_steps() -> None:
    result = _run_deb_script(
        "--dry-run",
        "--staging-dir",
        "/tmp/operance-deb",
        "--output-dir",
        "/tmp/operance-out",
        "--version",
        "1.2.3",
    )

    assert result.stdout.splitlines() == [
        "+ mkdir -p /tmp/operance-deb/DEBIAN",
        "+ mkdir -p /tmp/operance-deb/etc/operance",
        "+ mkdir -p /tmp/operance-deb/usr/bin",
        "+ mkdir -p /tmp/operance-deb/usr/share/applications",
        "+ mkdir -p /tmp/operance-deb/usr/share/icons/hicolor/scalable/apps",
        "+ mkdir -p /tmp/operance-deb/usr/lib/operance",
        "+ mkdir -p /tmp/operance-deb/usr/lib/operance/site-packages",
        "+ mkdir -p /tmp/operance-deb/usr/lib/systemd/user",
        "+ render packaging/deb/control.in -> /tmp/operance-deb/DEBIAN/control",
        "+ ./scripts/render_packaged_assets.sh --output-dir /tmp/operance-deb/.rendered --entrypoint /usr/bin/operance --bundle-profile base",
        "+ cp /tmp/operance-deb/.rendered/bin/operance /tmp/operance-deb/usr/bin/operance",
        "+ cp /tmp/operance-deb/.rendered/etc/operance/voice-loop.args.example /tmp/operance-deb/etc/operance/voice-loop.args.example",
        "+ cp /tmp/operance-deb/.rendered/applications/operance.desktop /tmp/operance-deb/usr/share/applications/operance.desktop",
        "+ cp /tmp/operance-deb/.rendered/icons/hicolor/scalable/apps/operance.svg /tmp/operance-deb/usr/share/icons/hicolor/scalable/apps/operance.svg",
        "+ cp /tmp/operance-deb/.rendered/lib/operance/pyproject.toml /tmp/operance-deb/usr/lib/operance/pyproject.toml",
        "+ cp -R /tmp/operance-deb/.rendered/lib/operance/site-packages/. /tmp/operance-deb/usr/lib/operance/site-packages",
        "+ cp /tmp/operance-deb/.rendered/lib/operance/voice-loop-launcher /tmp/operance-deb/usr/lib/operance/voice-loop-launcher",
        "+ cp /tmp/operance-deb/.rendered/systemd/operance-tray.service /tmp/operance-deb/usr/lib/systemd/user/operance-tray.service",
        "+ cp /tmp/operance-deb/.rendered/systemd/operance-voice-loop.service /tmp/operance-deb/usr/lib/systemd/user/operance-voice-loop.service",
        "+ dpkg-deb --build /tmp/operance-deb /tmp/operance-out/operance_1.2.3_all.deb",
    ]
    assert result.stderr == ""


def test_deb_package_script_forwards_bundle_profile_options() -> None:
    result = _run_deb_script(
        "--dry-run",
        "--staging-dir",
        "/tmp/operance-deb",
        "--output-dir",
        "/tmp/operance-out",
        "--bundle-profile",
        "mvp",
        "--bundle-python",
        "/tmp/operance-python",
        "--bundle-source-site-packages",
        "/tmp/operance-site-packages",
    )

    assert "+ ./scripts/render_packaged_assets.sh --output-dir /tmp/operance-deb/.rendered --entrypoint /usr/bin/operance --bundle-profile mvp --bundle-python /tmp/operance-python --bundle-source-site-packages /tmp/operance-site-packages" in result.stdout.splitlines()
    assert result.stderr == ""


def test_deb_package_script_can_render_stage_without_building(tmp_path: Path) -> None:
    staging_dir = tmp_path / "operance-deb"
    output_dir = tmp_path / "out"

    result = _run_deb_script(
        "--skip-build",
        "--staging-dir",
        str(staging_dir),
        "--output-dir",
        str(output_dir),
        "--version",
        "9.9.9",
        "--entrypoint",
        "/opt/operance/bin/operance",
    )

    control_path = staging_dir / "DEBIAN" / "control"
    voice_loop_args_example = staging_dir / "etc" / "operance" / "voice-loop.args.example"
    entrypoint_path = staging_dir / "opt" / "operance" / "bin" / "operance"
    desktop_entry = staging_dir / "usr" / "share" / "applications" / "operance.desktop"
    packaged_icon = staging_dir / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "operance.svg"
    packaged_pyproject = staging_dir / "usr" / "lib" / "operance" / "pyproject.toml"
    packaged_runtime_dir = staging_dir / "usr" / "lib" / "operance" / "site-packages" / "operance"
    voice_loop_launcher = staging_dir / "usr" / "lib" / "operance" / "voice-loop-launcher"
    tray_service_unit = staging_dir / "usr" / "lib" / "systemd" / "user" / "operance-tray.service"
    voice_loop_service_unit = staging_dir / "usr" / "lib" / "systemd" / "user" / "operance-voice-loop.service"

    assert result.stderr == ""
    assert control_path.exists()
    assert voice_loop_args_example.exists()
    assert entrypoint_path.exists()
    assert desktop_entry.exists()
    assert packaged_icon.exists()
    assert packaged_pyproject.exists()
    assert packaged_runtime_dir.exists()
    assert voice_loop_launcher.exists()
    assert tray_service_unit.exists()
    assert voice_loop_service_unit.exists()

    control_text = control_path.read_text(encoding="utf-8")
    entrypoint_text = entrypoint_path.read_text(encoding="utf-8")
    voice_loop_args_example_text = voice_loop_args_example.read_text(encoding="utf-8")
    desktop_text = desktop_entry.read_text(encoding="utf-8")
    packaged_pyproject_text = packaged_pyproject.read_text(encoding="utf-8")
    packaged_runtime_init_text = (packaged_runtime_dir / "__init__.py").read_text(encoding="utf-8")
    voice_loop_launcher_text = voice_loop_launcher.read_text(encoding="utf-8")
    tray_service_text = tray_service_unit.read_text(encoding="utf-8")
    voice_loop_service_text = voice_loop_service_unit.read_text(encoding="utf-8")

    assert "Package: operance" in control_text
    assert "Version: 9.9.9" in control_text
    assert 'exec "${python_bin}" -m operance.cli "$@"' in entrypoint_text
    assert "--wakeword-model" in voice_loop_args_example_text
    assert "Exec=/opt/operance/bin/operance --tray-run" in desktop_text
    assert "Icon=operance" in desktop_text
    assert 'version = "0.1.0"' in packaged_pyproject_text
    assert '"""Operance package bootstrap."""' in packaged_runtime_init_text
    assert 'entrypoint="/opt/operance/bin/operance"' in voice_loop_launcher_text
    assert "ExecStart=/opt/operance/bin/operance --tray-run" in tray_service_text
    assert "ExecStart=/usr/lib/operance/voice-loop-launcher" in voice_loop_service_text
    assert not (output_dir / "operance_9.9.9_all.deb").exists()
