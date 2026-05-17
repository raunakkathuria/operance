import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_installed_package_smoke.sh"


def _run_installed_package_smoke_script(
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


def test_installed_package_smoke_script_dry_run_prints_expected_steps() -> None:
    result = _run_installed_package_smoke_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ test -f /usr/share/applications/operance.desktop",
        "+ test -f /usr/lib/systemd/user/operance-tray.service",
        "+ test -f /usr/lib/systemd/user/operance-voice-loop.service",
        "+ operance --version",
        "+ operance --about",
        "+ python3 scripts/check_installed_build_identity.py --command operance",
        "+ operance --doctor",
        "+ operance --installed-smoke",
        "+ operance --supported-commands --supported-commands-available-only",
        "+ operance --support-bundle",
    ]
    assert result.stderr == ""


def test_installed_package_smoke_script_can_require_mvp_runtime_in_dry_run() -> None:
    result = _run_installed_package_smoke_script("--require-mvp-runtime", "--dry-run")

    assert result.stdout.splitlines() == [
        "+ test -f /usr/share/applications/operance.desktop",
        "+ test -f /usr/lib/systemd/user/operance-tray.service",
        "+ test -f /usr/lib/systemd/user/operance-voice-loop.service",
        "+ operance --version",
        "+ operance --about",
        "+ python3 scripts/check_installed_build_identity.py --command operance",
        "+ operance --doctor",
        "+ operance --installed-smoke",
        "+ python3 scripts/check_installed_build_identity.py --command operance --package-profile mvp",
        "+ python3 scripts/check_installed_mvp_runtime.py --command operance --check-tray-service",
        "+ operance --supported-commands --supported-commands-available-only",
        "+ operance --support-bundle",
    ]
    assert result.stderr == ""


def test_installed_package_smoke_script_can_reset_user_services_before_package_install(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")

    result = _run_installed_package_smoke_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--reset-user-services",
        "--no-sudo",
        "--dry-run",
    )

    assert result.stdout.splitlines()[0] == (
        f"+ ./scripts/install_package_artifact.sh --package {package_path} "
        "--installer dnf --replace-existing --reset-user-services --no-sudo"
    )
    assert result.stderr == ""


def test_installed_package_smoke_script_can_install_run_and_uninstall_with_fake_tools(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    dnf_log = tmp_path / "dnf.log"
    operance_log = tmp_path / "operance.log"
    support_bundle_path = tmp_path / "operance-support.tar.gz"
    desktop_entry_path = tmp_path / "share" / "applications" / "operance.desktop"
    tray_unit_path = tmp_path / "systemd" / "operance-tray.service"
    voice_loop_unit_path = tmp_path / "systemd" / "operance-voice-loop.service"

    desktop_entry_path.parent.mkdir(parents=True)
    tray_unit_path.parent.mkdir(parents=True)
    desktop_entry_path.write_text("[Desktop Entry]\nName=Operance\n", encoding="utf-8")
    tray_unit_path.write_text("[Unit]\nDescription=Operance tray app\n", encoding="utf-8")
    voice_loop_unit_path.write_text("[Unit]\nDescription=Operance voice loop\n", encoding="utf-8")

    _write_executable(
        fake_bin / "dnf",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" >> \"$FAKE_DNF_LOG\"\n"
        ),
    )
    _write_executable(
        fake_bin / "rpm",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"-qp\" ]]; then printf '%s' operance; exit 0; fi\n"
            "if [[ \"$1\" == \"-q\" ]]; then exit 0; fi\n"
            "exit 1\n"
        ),
    )
    _write_executable(
        fake_bin / "operance",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" >> \"$FAKE_OPERANCE_LOG\"\n"
            "args=(\"$@\")\n"
            "for ((i=0; i<${#args[@]}; i++)); do\n"
            "  if [[ \"${args[$i]}\" == \"--support-bundle-out\" ]]; then\n"
            "    : > \"${args[$((i + 1))]}\"\n"
            "  fi\n"
            "done\n"
            "if [[ \"$*\" == \"--about\" ]]; then\n"
            "  printf '%s\\n' '{\"install_mode\":\"packaged\",\"build_git_commit\":\"abcdef123456\",\"build_git_commit_short\":\"abcdef1\",\"build_time\":\"2026-05-17T00:00:00Z\",\"install_root\":\"/usr/lib/operance\",\"package_profile\":\"mvp\"}'\n"
            "fi\n"
        ),
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DNF_LOG"] = str(dnf_log)
    env["FAKE_OPERANCE_LOG"] = str(operance_log)

    result = _run_installed_package_smoke_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--no-sudo",
        "--uninstall-after",
        "--support-bundle-out",
        str(support_bundle_path),
        "--command",
        str(fake_bin / "operance"),
        "--desktop-entry-path",
        str(desktop_entry_path),
        "--tray-unit-path",
        str(tray_unit_path),
        "--voice-loop-unit-path",
        str(voice_loop_unit_path),
        env=env,
    )

    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        f"+ ./scripts/install_package_artifact.sh --package {package_path} --installer dnf --replace-existing --no-sudo",
        "+ dnf remove -y operance",
        f"+ dnf install -y {package_path}",
        f"+ test -f {desktop_entry_path}",
        f"+ test -f {tray_unit_path}",
        f"+ test -f {voice_loop_unit_path}",
        f"+ {fake_bin / 'operance'} --version",
        f"+ {fake_bin / 'operance'} --about",
        '{"install_mode":"packaged","build_git_commit":"abcdef123456","build_git_commit_short":"abcdef1","build_time":"2026-05-17T00:00:00Z","install_root":"/usr/lib/operance","package_profile":"mvp"}',
        f"+ python3 scripts/check_installed_build_identity.py --command {fake_bin / 'operance'}",
        '{"identity_checked": true, "status": "ok"}',
        f"+ {fake_bin / 'operance'} --doctor",
        f"+ {fake_bin / 'operance'} --installed-smoke",
        f"+ {fake_bin / 'operance'} --supported-commands --supported-commands-available-only",
        f"+ {fake_bin / 'operance'} --support-bundle --support-bundle-out {support_bundle_path}",
        "+ ./scripts/uninstall_native_package.sh --installer dnf --package-name operance --no-sudo",
        "+ dnf remove -y operance",
    ]
    assert dnf_log.read_text(encoding="utf-8").splitlines() == [
        "remove -y operance",
        f"install -y {package_path}",
        "remove -y operance",
    ]
    assert operance_log.read_text(encoding="utf-8").splitlines() == [
        "--version",
        "--about",
        "--about",
        "--doctor",
        "--installed-smoke",
        "--supported-commands --supported-commands-available-only",
        f"--support-bundle --support-bundle-out {support_bundle_path}",
    ]
    assert support_bundle_path.exists()
