import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "uninstall_native_package.sh"


def _run_uninstall_script(
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


def test_package_uninstall_script_dry_run_prints_expected_apt_command() -> None:
    result = _run_uninstall_script(
        "--installer",
        "apt",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ sudo apt remove -y operance",
    ]
    assert result.stderr == ""


def test_package_uninstall_script_dry_run_prints_expected_dnf_command_without_sudo() -> None:
    result = _run_uninstall_script(
        "--installer",
        "dnf",
        "--package-name",
        "operance-preview",
        "--no-sudo",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ dnf remove -y operance-preview",
    ]
    assert result.stderr == ""


def test_package_uninstall_script_can_execute_with_fake_dnf(tmp_path: Path) -> None:
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

    result = _run_uninstall_script(
        "--installer",
        "dnf",
        "--package-name",
        "operance",
        "--no-sudo",
        env=env,
    )

    assert result.stderr == ""
    assert log_path.read_text(encoding="utf-8").strip() == "remove -y operance"
