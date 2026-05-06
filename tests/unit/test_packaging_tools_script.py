import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_packaging_tools.sh"


def _run_install_script(*args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=check,
        cwd=REPO_ROOT,
        text=True,
        env=env,
    )


def test_packaging_tools_script_dry_run_prints_default_rpm_command() -> None:
    result = _run_install_script("--dry-run", "--installer", "dnf")

    assert result.stdout.splitlines() == [
        "+ sudo dnf install -y rpm-build",
    ]
    assert result.stderr == ""


def test_packaging_tools_script_dry_run_supports_deb_tools() -> None:
    result = _run_install_script("--dry-run", "--installer", "apt", "--deb")

    assert result.stdout.splitlines() == [
        "+ sudo apt install -y dpkg-dev",
    ]
    assert result.stderr == ""


def test_packaging_tools_script_executes_detected_installer_with_fake_path(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_path = tmp_path / "sudo.log"

    (fake_bin / "dnf").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (fake_bin / "sudo").write_text(
        "#!/bin/bash\nprintf '%s\\n' \"$*\" > \"$OPERANCE_TEST_LOG\"\n",
        encoding="utf-8",
    )
    os.chmod(fake_bin / "dnf", 0o755)
    os.chmod(fake_bin / "sudo", 0o755)

    env = {
        **os.environ,
        "PATH": str(fake_bin),
        "OPERANCE_TEST_LOG": str(log_path),
    }

    result = _run_install_script(env=env)

    assert result.stdout.splitlines() == [
        "+ sudo dnf install -y rpm-build",
    ]
    assert result.stderr == ""
    assert log_path.read_text(encoding="utf-8").strip() == "dnf install -y rpm-build"


def test_packaging_tools_script_rejects_unsupported_installer_and_tool_combo() -> None:
    result = _run_install_script("--installer", "dnf", "--deb", check=False)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "dnf installer does not support --deb packaging tools"
