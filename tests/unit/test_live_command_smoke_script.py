import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_live_command_smoke.sh"


def _run_live_command_smoke_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_live_command_smoke_dry_run_prints_controlled_fixture_steps() -> None:
    result = _run_live_command_smoke_script("--dry-run")

    assert result.stdout.splitlines() == [
        '+ tmp_dir="$(mktemp -d)"',
        '+ mkdir -p "${tmp_dir}/Desktop"',
        '+ touch "${tmp_dir}/Desktop/operance-recent-smoke.txt"',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript "show recent files"',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript "create folder on desktop called projects"',
        '+ test -d "${tmp_dir}/Desktop/projects"',
        '+ write ${tmp_dir}/delete-folder.txt',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript-file ${tmp_dir}/delete-folder.txt',
        '+ test ! -e "${tmp_dir}/Desktop/projects"',
        '+ touch "${tmp_dir}/Desktop/notes.txt"',
        '+ write ${tmp_dir}/delete-file.txt',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript-file ${tmp_dir}/delete-file.txt',
        '+ test ! -e "${tmp_dir}/Desktop/notes.txt"',
        '+ mkdir -p "${tmp_dir}/Desktop/projects"',
        '+ write ${tmp_dir}/rename-folder.txt',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript-file ${tmp_dir}/rename-folder.txt',
        '+ test -d "${tmp_dir}/Desktop/archive"',
        '+ test ! -e "${tmp_dir}/Desktop/projects"',
        '+ rm -rf "${tmp_dir}/Desktop/archive"',
        '+ mkdir -p "${tmp_dir}/Desktop/projects" "${tmp_dir}/Desktop/archive"',
        '+ write ${tmp_dir}/move-folder.txt',
        '+ OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript-file ${tmp_dir}/move-folder.txt',
        '+ test -d "${tmp_dir}/Desktop/archive/projects"',
        '+ test ! -e "${tmp_dir}/Desktop/projects"',
        '+ rm -rf "${tmp_dir}"',
    ]
    assert result.stderr == ""


def test_live_command_smoke_can_override_python() -> None:
    result = _run_live_command_smoke_script("--python", "/tmp/operance-python", "--dry-run")

    assert (
        '+ OPERANCE_DEVELOPER_MODE=0 /tmp/operance-python -m operance.cli --desktop-dir ${tmp_dir}/Desktop --transcript "show recent files"'
        in result.stdout.splitlines()
    )
    assert result.stderr == ""
