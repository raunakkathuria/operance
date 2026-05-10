import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_package_artifact.sh"


def _run_install_script(
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


def test_package_install_script_dry_run_prints_expected_apt_command(tmp_path: Path) -> None:
    package_path = tmp_path / "operance_1.2.3_all.deb"
    package_path.write_text("deb", encoding="utf-8")

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "apt",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        f"+ sudo apt install -y {package_path}",
    ]
    assert result.stderr == ""


def test_package_install_script_dry_run_prints_expected_dnf_command_without_sudo(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-1.2.3-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--no-sudo",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        f"+ dnf install -y {package_path}",
    ]
    assert result.stderr == ""


def test_package_install_script_dry_run_can_replace_existing_dnf_package(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-1.2.3-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--replace-existing",
        "--no-sudo",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ dnf remove -y operance",
        f"+ dnf install -y {package_path}",
    ]
    assert result.stderr == ""


def test_package_install_script_dry_run_can_reset_user_services_before_install(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-1.2.3-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--reset-user-services",
        "--no-sudo",
        "--dry-run",
    )

    unit_dir = Path.home() / ".config" / "systemd" / "user"
    assert result.stdout.splitlines() == [
        "+ systemctl --user disable --now operance-tray.service",
        f"+ rm -f {unit_dir / 'operance-tray.service'}",
        "+ systemctl --user disable --now operance-voice-loop.service",
        f"+ rm -f {unit_dir / 'operance-voice-loop.service'}",
        "+ systemctl --user daemon-reload",
        f"+ dnf install -y {package_path}",
    ]
    assert result.stderr == ""


def test_package_install_script_resets_user_services_before_install(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    config_home = tmp_path / "config"
    unit_dir = config_home / "systemd" / "user"
    systemctl_log = tmp_path / "systemctl.log"
    dnf_log = tmp_path / "dnf.log"

    fake_bin.mkdir()
    unit_dir.mkdir(parents=True)
    tray_unit = unit_dir / "operance-tray.service"
    voice_unit = unit_dir / "operance-voice-loop.service"
    tray_unit.write_text("stale tray", encoding="utf-8")
    voice_unit.write_text("stale voice loop", encoding="utf-8")
    _write_executable(
        fake_bin / "systemctl",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" >> \"$FAKE_SYSTEMCTL_LOG\"\n",
    )
    _write_executable(
        fake_bin / "dnf",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" > \"$FAKE_DNF_LOG\"\n",
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["XDG_CONFIG_HOME"] = str(config_home)
    env["FAKE_SYSTEMCTL_LOG"] = str(systemctl_log)
    env["FAKE_DNF_LOG"] = str(dnf_log)

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--reset-user-services",
        "--no-sudo",
        env=env,
    )

    assert result.stderr == ""
    assert not tray_unit.exists()
    assert not voice_unit.exists()
    assert systemctl_log.read_text(encoding="utf-8").splitlines() == [
        "--user disable --now operance-tray.service",
        "--user disable --now operance-voice-loop.service",
        "--user daemon-reload",
    ]
    assert dnf_log.read_text(encoding="utf-8").strip() == f"install -y {package_path}"


def test_package_install_script_can_execute_with_fake_dnf(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    log_path = tmp_path / "dnf.log"

    fake_bin.mkdir()
    _write_executable(
        fake_bin / "dnf",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" > \"$FAKE_DNF_LOG\"\n",
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DNF_LOG"] = str(log_path)

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--no-sudo",
        env=env,
    )

    assert result.stderr == ""
    assert log_path.read_text(encoding="utf-8").strip() == f"install -y {package_path}"


def test_package_install_script_removes_existing_dnf_package_before_install(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    log_path = tmp_path / "dnf.log"

    fake_bin.mkdir()
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
        fake_bin / "dnf",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" >> \"$FAKE_DNF_LOG\"\n",
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DNF_LOG"] = str(log_path)

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--replace-existing",
        "--no-sudo",
        env=env,
    )

    assert result.stderr == ""
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "remove -y operance",
        f"install -y {package_path}",
    ]


def test_package_install_script_installs_when_replacement_package_is_absent(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-9.9.9-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    log_path = tmp_path / "dnf.log"

    fake_bin.mkdir()
    _write_executable(
        fake_bin / "rpm",
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"-qp\" ]]; then printf '%s' operance; exit 0; fi\n"
            "if [[ \"$1\" == \"-q\" ]]; then exit 1; fi\n"
            "exit 1\n"
        ),
    )
    _write_executable(
        fake_bin / "dnf",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" > \"$FAKE_DNF_LOG\"\n",
    )

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DNF_LOG"] = str(log_path)

    result = _run_install_script(
        "--package",
        str(package_path),
        "--installer",
        "dnf",
        "--replace-existing",
        "--no-sudo",
        env=env,
    )

    assert result.stderr == ""
    assert log_path.read_text(encoding="utf-8").strip() == f"install -y {package_path}"
