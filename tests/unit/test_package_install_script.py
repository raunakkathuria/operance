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
