import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_fedora_container_smoke.sh"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )


def test_fedora_container_smoke_script_dry_run_prints_the_container_command() -> None:
    result = _run_script("--dry-run")

    assert result.returncode == 0
    assert result.stdout.startswith("+ docker run --rm -v ")
    assert ":/src:ro fedora:41 bash -lc" in result.stdout


def test_fedora_container_smoke_script_dry_run_honours_runtime_and_image() -> None:
    result = _run_script("--dry-run", "--runtime", "podman", "--image", "fedora:42")

    assert result.returncode == 0
    assert "podman run" in result.stdout
    assert "fedora:42" in result.stdout


def test_fedora_container_smoke_script_keep_flag_drops_the_remove_flag() -> None:
    result = _run_script("--dry-run", "--keep")

    assert result.returncode == 0
    assert "--rm" not in result.stdout


def test_fedora_container_smoke_script_rejects_unknown_arguments() -> None:
    result = _run_script("--nope")

    assert result.returncode != 0
    assert "Unknown argument: --nope" in result.stderr


def test_fedora_container_smoke_script_help_documents_the_session_limitation() -> None:
    result = _run_script("--help")

    assert result.returncode == 0
    assert "Plasma Wayland" in result.stdout
    assert "development-environments.md" in result.stdout


def test_fedora_container_smoke_script_does_not_install_the_ui_extra() -> None:
    """PySide6 without a display makes tray tests fail, so the container skips it."""

    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[dev,ui]" not in source
    assert ".[ui]" not in source


def test_fedora_container_smoke_script_does_not_require_privileged_mode() -> None:
    """The RPM has no install scriptlets, so systemd is not needed in the container."""

    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "--privileged" not in source
    assert "--systemd" not in source


def test_ci_builds_and_installs_the_rpm_in_a_fedora_container() -> None:
    """CI ran packaging dry-runs only, so a real build-and-install was untested."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "fedora-package-smoke:" in workflow
    assert "image: fedora:41" in workflow
    assert "build_rpm_package.sh" in workflow
    assert "operance --version" in workflow
