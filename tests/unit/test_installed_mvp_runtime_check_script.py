import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_installed_mvp_runtime.py"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_installed_mvp_runtime_check_passes_when_required_doctor_checks_are_ok(tmp_path: Path) -> None:
    fake_operance = tmp_path / "operance"
    _write_executable(
        fake_operance,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"--print-config\" ]]; then\n"
            "  printf '%s\\n' '{\"runtime\":{\"developer_mode\":false}}'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' '{\"checks\":["
            "{\"name\":\"tray_ui_available\",\"status\":\"ok\",\"detail\":\"PySide6\"},"
            "{\"name\":\"stt_backend_available\",\"status\":\"ok\",\"detail\":\"moonshine_voice\"}"
            "]}'\n"
        ),
    )

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--command", str(fake_operance)],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.stderr == ""
    assert result.stdout == (
        '{"required_checks": ["tray_ui_available", "stt_backend_available"], '
        '"status": "ok", "tray_service_checked": false}\n'
    )


def test_installed_mvp_runtime_check_fails_when_required_backend_is_missing(tmp_path: Path) -> None:
    fake_operance = tmp_path / "operance"
    _write_executable(
        fake_operance,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"--print-config\" ]]; then\n"
            "  printf '%s\\n' '{\"runtime\":{\"developer_mode\":false}}'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' '{\"checks\":["
            "{\"name\":\"tray_ui_available\",\"status\":\"ok\",\"detail\":\"PySide6\"},"
            "{\"name\":\"stt_backend_available\",\"status\":\"warn\",\"detail\":\"moonshine-voice not installed\"}"
            "]}'\n"
        ),
    )

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--command", str(fake_operance)],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "installed MVP runtime check failed:\n"
        "- stt_backend_available: status=warn detail=moonshine-voice not installed\n"
    )


def test_installed_mvp_runtime_check_fails_when_command_is_in_developer_mode(tmp_path: Path) -> None:
    fake_operance = tmp_path / "operance"
    _write_executable(
        fake_operance,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"--print-config\" ]]; then\n"
            "  printf '%s\\n' '{\"runtime\":{\"developer_mode\":true}}'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' '{\"checks\":["
            "{\"name\":\"tray_ui_available\",\"status\":\"ok\",\"detail\":\"PySide6\"},"
            "{\"name\":\"stt_backend_available\",\"status\":\"ok\",\"detail\":\"moonshine_voice\"}"
            "]}'\n"
        ),
    )

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--command", str(fake_operance)],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "installed MVP runtime check failed:\n"
        "- runtime.developer_mode: expected false, got True\n"
    )


def test_installed_mvp_runtime_check_fails_for_stale_tray_service_unit(tmp_path: Path) -> None:
    fake_operance = tmp_path / "operance"
    fake_systemctl = tmp_path / "systemctl"
    _write_executable(
        fake_operance,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"--print-config\" ]]; then\n"
            "  printf '%s\\n' '{\"runtime\":{\"developer_mode\":false}}'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' '{\"checks\":["
            "{\"name\":\"tray_ui_available\",\"status\":\"ok\",\"detail\":\"PySide6\"},"
            "{\"name\":\"stt_backend_available\",\"status\":\"ok\",\"detail\":\"moonshine_voice\"}"
            "]}'\n"
        ),
    )
    _write_executable(
        fake_systemctl,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' 'LoadState=loaded'\n"
            "printf '%s\\n' 'ActiveState=active'\n"
            "printf '%s\\n' 'FragmentPath=/home/raunak/.config/systemd/user/operance-tray.service'\n"
            "printf '%s\\n' 'ExecStart={ path=/home/raunak/Documents/personal/stale-checkout/.venv/bin/python ; argv[]=/home/raunak/Documents/personal/stale-checkout/.venv/bin/python -m operance.cli --tray-run ; }'\n"
        ),
    )

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--command",
            str(fake_operance),
            "--check-tray-service",
            "--systemctl-command",
            str(fake_systemctl),
        ],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "expected installed command in ExecStart" in result.stderr
    assert "user unit shadows the packaged unit" in result.stderr


def test_installed_mvp_runtime_check_passes_for_packaged_tray_service_unit(tmp_path: Path) -> None:
    fake_operance = tmp_path / "operance"
    fake_systemctl = tmp_path / "systemctl"
    _write_executable(
        fake_operance,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$1\" == \"--print-config\" ]]; then\n"
            "  printf '%s\\n' '{\"runtime\":{\"developer_mode\":false}}'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' '{\"checks\":["
            "{\"name\":\"tray_ui_available\",\"status\":\"ok\",\"detail\":\"PySide6\"},"
            "{\"name\":\"stt_backend_available\",\"status\":\"ok\",\"detail\":\"moonshine_voice\"}"
            "]}'\n"
        ),
    )
    _write_executable(
        fake_systemctl,
        (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' 'LoadState=loaded'\n"
            "printf '%s\\n' 'ActiveState=active'\n"
            "printf '%s\\n' 'FragmentPath=/usr/lib/systemd/user/operance-tray.service'\n"
            f"printf '%s\\n' 'ExecStart={{ path={fake_operance} ; argv[]={fake_operance} --tray-run ; }}'\n"
        ),
    )

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--command",
            str(fake_operance),
            "--check-tray-service",
            "--systemctl-command",
            str(fake_systemctl),
        ],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.stderr == ""
    assert result.stdout == (
        '{"required_checks": ["tray_ui_available", "stt_backend_available"], '
        '"status": "ok", "tray_service_checked": true}\n'
    )
