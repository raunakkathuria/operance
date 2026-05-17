import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_installed_build_identity.py"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_installed_build_identity_check_passes_for_packaged_identity(tmp_path: Path) -> None:
    command = tmp_path / "operance"
    _write_executable(
        command,
        (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' '{\"install_mode\":\"packaged\",\"build_git_commit\":\"abcdef123456\",\"build_git_commit_short\":\"abcdef1\",\"build_time\":\"2026-05-17T00:00:00Z\",\"install_root\":\"/usr/lib/operance\",\"package_profile\":\"mvp\"}'\n"
        ),
    )

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--command", str(command), "--package-profile", "mvp"],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.stdout == '{"identity_checked": true, "status": "ok"}\n'
    assert result.stderr == ""


def test_installed_build_identity_check_fails_for_source_identity(tmp_path: Path) -> None:
    command = tmp_path / "operance"
    _write_executable(
        command,
        "#!/usr/bin/env bash\nprintf '%s\\n' '{\"install_mode\":\"source_checkout\"}'\n",
    )

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--command", str(command)],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.returncode == 1
    assert "install_mode='source_checkout'" in result.stderr
    assert "build_git_commit missing" in result.stderr
