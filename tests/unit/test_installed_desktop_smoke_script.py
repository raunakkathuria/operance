import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_installed_desktop_smoke.sh"


def _run_installed_desktop_smoke_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_installed_desktop_smoke_dry_run_prints_default_steps() -> None:
    result = _run_installed_desktop_smoke_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ python3 scripts/check_installed_mvp_runtime.py --command operance --check-tray-service",
        "+ systemctl --user enable --now operance-tray.service",
        "+ systemctl --user status operance-tray.service --no-pager",
        "+ operance --installed-smoke",
        "+ operance --print-config",
        "+ operance --getting-started",
        "+ operance --planner-setup-template",
        "+ operance --planner-status",
        "+ operance --supported-commands --supported-commands-available-only",
        "+ operance --issue-report",
        "Manual tray click-to-talk checks:",
        "- open firefox",
        "- open localhost:3000",
        "- open firefox and load localhost:3000",
        "- show recent files",
        "- list windows",
        "- switch to window <visible window title>",
        "- what time is it",
        "- wifi status",
        "- what is the volume",
        "- is audio muted",
        "- set volume to 50 percent",
        "- mute audio",
        "- unmute audio",
        "- quit firefox, then confirm",
    ]
    assert result.stderr == ""


def test_installed_desktop_smoke_can_override_command_and_systemctl() -> None:
    result = _run_installed_desktop_smoke_script(
        "--command",
        "/tmp/operance",
        "--systemctl-command",
        "/tmp/systemctl",
        "--dry-run",
    )

    assert result.stdout.splitlines()[:5] == [
        "+ python3 scripts/check_installed_mvp_runtime.py --command /tmp/operance --check-tray-service --systemctl-command /tmp/systemctl",
        "+ /tmp/systemctl --user enable --now operance-tray.service",
        "+ /tmp/systemctl --user status operance-tray.service --no-pager",
        "+ /tmp/operance --installed-smoke",
        "+ /tmp/operance --print-config",
    ]
    assert result.stderr == ""
