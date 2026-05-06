import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "render_packaged_assets.sh"


def _run_render_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_packaged_assets_script_dry_run_prints_expected_steps() -> None:
    result = _run_render_script("--dry-run", "--output-dir", "/tmp/operance-packaged-assets")

    assert result.stdout.splitlines() == [
        "+ mkdir -p /tmp/operance-packaged-assets/applications",
        "+ mkdir -p /tmp/operance-packaged-assets/bin",
        "+ mkdir -p /tmp/operance-packaged-assets/etc/operance",
        "+ mkdir -p /tmp/operance-packaged-assets/lib/operance",
        "+ mkdir -p /tmp/operance-packaged-assets/lib/operance/site-packages/operance",
        "+ mkdir -p /tmp/operance-packaged-assets/systemd",
        "+ render packaging/operance.desktop.in -> /tmp/operance-packaged-assets/applications/operance.desktop",
        "+ render packaging/bin/operance-entrypoint.in -> /tmp/operance-packaged-assets/bin/operance",
        "+ render packaging/etc/voice-loop.args.example.in -> /tmp/operance-packaged-assets/etc/operance/voice-loop.args.example",
        "+ render packaging/bin/operance-voice-loop-launcher.in -> /tmp/operance-packaged-assets/lib/operance/voice-loop-launcher",
        "+ cp pyproject.toml /tmp/operance-packaged-assets/lib/operance/pyproject.toml",
        "+ cp -R src/operance/. /tmp/operance-packaged-assets/lib/operance/site-packages/operance",
        "+ render packaging/systemd/operance-tray-packaged.service.in -> /tmp/operance-packaged-assets/systemd/operance-tray.service",
        "+ render packaging/systemd/operance-voice-loop-packaged.service.in -> /tmp/operance-packaged-assets/systemd/operance-voice-loop.service",
    ]
    assert result.stderr == ""


def test_packaged_assets_script_renders_desktop_entry_and_service(tmp_path: Path) -> None:
    output_dir = tmp_path / "packaged-assets"

    result = _run_render_script(
        "--output-dir",
        str(output_dir),
        "--entrypoint",
        "/opt/operance/bin/operance",
    )

    desktop_entry = output_dir / "applications" / "operance.desktop"
    packaged_entrypoint = output_dir / "bin" / "operance"
    voice_loop_args_example = output_dir / "etc" / "operance" / "voice-loop.args.example"
    packaged_pyproject = output_dir / "lib" / "operance" / "pyproject.toml"
    packaged_runtime_dir = output_dir / "lib" / "operance" / "site-packages" / "operance"
    voice_loop_launcher = output_dir / "lib" / "operance" / "voice-loop-launcher"
    tray_service_unit = output_dir / "systemd" / "operance-tray.service"
    voice_loop_service_unit = output_dir / "systemd" / "operance-voice-loop.service"

    assert result.stdout.splitlines() == [
        f"+ mkdir -p {output_dir / 'applications'}",
        f"+ mkdir -p {output_dir / 'bin'}",
        f"+ mkdir -p {output_dir / 'etc' / 'operance'}",
        f"+ mkdir -p {output_dir / 'lib' / 'operance'}",
        f"+ mkdir -p {output_dir / 'lib' / 'operance' / 'site-packages' / 'operance'}",
        f"+ mkdir -p {output_dir / 'systemd'}",
        f"+ render packaging/operance.desktop.in -> {desktop_entry}",
        f"+ render packaging/bin/operance-entrypoint.in -> {packaged_entrypoint}",
        f"+ render packaging/etc/voice-loop.args.example.in -> {voice_loop_args_example}",
        f"+ render packaging/bin/operance-voice-loop-launcher.in -> {voice_loop_launcher}",
        f"+ cp pyproject.toml {packaged_pyproject}",
        f"+ cp -R src/operance/. {packaged_runtime_dir}",
        f"+ render packaging/systemd/operance-tray-packaged.service.in -> {tray_service_unit}",
        f"+ render packaging/systemd/operance-voice-loop-packaged.service.in -> {voice_loop_service_unit}",
    ]
    assert result.stderr == ""
    assert desktop_entry.exists()
    assert packaged_entrypoint.exists()
    assert voice_loop_args_example.exists()
    assert packaged_pyproject.exists()
    assert packaged_runtime_dir.exists()
    assert voice_loop_launcher.exists()
    assert tray_service_unit.exists()
    assert voice_loop_service_unit.exists()

    desktop_text = desktop_entry.read_text(encoding="utf-8")
    packaged_entrypoint_text = packaged_entrypoint.read_text(encoding="utf-8")
    voice_loop_args_example_text = voice_loop_args_example.read_text(encoding="utf-8")
    packaged_pyproject_text = packaged_pyproject.read_text(encoding="utf-8")
    packaged_runtime_init_text = (packaged_runtime_dir / "__init__.py").read_text(encoding="utf-8")
    voice_loop_launcher_text = voice_loop_launcher.read_text(encoding="utf-8")
    tray_service_text = tray_service_unit.read_text(encoding="utf-8")
    voice_loop_service_text = voice_loop_service_unit.read_text(encoding="utf-8")

    assert "Exec=/opt/operance/bin/operance --tray-run" in desktop_text
    assert "Name=Operance" in desktop_text
    assert 'python_bin="/usr/bin/python3"' in packaged_entrypoint_text
    assert 'install_root="/usr/lib/operance"' in packaged_entrypoint_text
    assert 'site_packages="${install_root}/site-packages"' in packaged_entrypoint_text
    assert 'exec "${python_bin}" -m operance.cli "$@"' in packaged_entrypoint_text
    assert "--wakeword-model" in voice_loop_args_example_text
    assert "--voice-loop-max-commands" in voice_loop_args_example_text
    assert 'version = "0.1.0"' in packaged_pyproject_text
    assert '"""Operance package bootstrap."""' in packaged_runtime_init_text
    assert 'entrypoint="/opt/operance/bin/operance"' in voice_loop_launcher_text
    assert 'default_user_args_file="${XDG_CONFIG_HOME:-${HOME}/.config}/operance/voice-loop.args"' in voice_loop_launcher_text
    assert 'default_system_args_file="/etc/operance/voice-loop.args"' in voice_loop_launcher_text
    assert 'command=("${entrypoint}" "-m" "operance.cli" "--voice-loop")' not in voice_loop_launcher_text
    assert 'command=("${entrypoint}" "--voice-loop")' in voice_loop_launcher_text
    assert "ExecStart=/opt/operance/bin/operance --tray-run" in tray_service_text
    assert "Description=Operance tray app" in tray_service_text
    assert "ExecStart=/usr/lib/operance/voice-loop-launcher" in voice_loop_service_text
    assert "Description=Operance continuous voice loop" in voice_loop_service_text


def test_packaged_voice_loop_launcher_can_load_args_file_and_forward_extra_args(tmp_path: Path) -> None:
    output_dir = tmp_path / "packaged-assets"
    fake_entrypoint = tmp_path / "bin" / "operance"
    fake_entrypoint.parent.mkdir()
    log_path = tmp_path / "invocation.log"
    fake_entrypoint.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" > {log_path}\n",
        encoding="utf-8",
    )
    fake_entrypoint.chmod(0o755)

    _run_render_script(
        "--output-dir",
        str(output_dir),
        "--entrypoint",
        str(fake_entrypoint),
    )

    args_file = tmp_path / "voice-loop.args"
    args_file.write_text(
        "\n".join(
            [
                "# comment",
                "--wakeword-model",
                "/tmp/operance.onnx",
                "--voice-loop-max-commands",
                "2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    launcher_path = output_dir / "lib" / "operance" / "voice-loop-launcher"
    subprocess.run(
        [
            str(launcher_path),
            "--args-file",
            str(args_file),
            "--",
            "--voice-loop-max-frames",
            "10",
        ],
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert log_path.read_text(encoding="utf-8").strip() == (
        "--voice-loop --wakeword-model /tmp/operance.onnx --voice-loop-max-commands 2 --voice-loop-max-frames 10"
    )


def test_packaged_voice_loop_launcher_prefers_user_config_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "packaged-assets"
    fake_entrypoint = tmp_path / "bin" / "operance"
    fake_entrypoint.parent.mkdir()
    log_path = tmp_path / "invocation.log"
    fake_entrypoint.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" > {log_path}\n",
        encoding="utf-8",
    )
    fake_entrypoint.chmod(0o755)

    _run_render_script(
        "--output-dir",
        str(output_dir),
        "--entrypoint",
        str(fake_entrypoint),
    )

    config_home = tmp_path / "config-home"
    args_path = config_home / "operance" / "voice-loop.args"
    args_path.parent.mkdir(parents=True)
    args_path.write_text(
        "--voice-loop-max-commands\n3\n",
        encoding="utf-8",
    )

    launcher_path = output_dir / "lib" / "operance" / "voice-loop-launcher"
    subprocess.run(
        [str(launcher_path)],
        check=True,
        cwd=REPO_ROOT,
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": os.environ["PATH"],
            "XDG_CONFIG_HOME": str(config_home),
        },
        text=True,
    )

    assert log_path.read_text(encoding="utf-8").strip() == "--voice-loop --voice-loop-max-commands 3"
