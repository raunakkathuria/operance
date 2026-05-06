from pathlib import Path
import os
import subprocess

import pytest

from operance.config import AppConfig


def test_build_default_adapter_set_uses_linux_backends_when_developer_mode_disabled(tmp_path: Path) -> None:
    from operance.adapters import build_default_adapter_set
    from operance.adapters.linux import (
        LinuxAppsAdapter,
        LinuxAudioAdapter,
        LinuxClipboardAdapter,
        LinuxFilesAdapter,
        LinuxNetworkAdapter,
        LinuxNotificationsAdapter,
        LinuxPowerAdapter,
        LinuxTextInputAdapter,
        SystemTimeAdapter,
    )

    config = AppConfig.from_env(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_DEVELOPER_MODE": "0",
        }
    )

    adapters = build_default_adapter_set(config, system_name="Linux")

    assert isinstance(adapters.apps, LinuxAppsAdapter)
    assert isinstance(adapters.time, SystemTimeAdapter)
    assert isinstance(adapters.power, LinuxPowerAdapter)
    assert isinstance(adapters.audio, LinuxAudioAdapter)
    assert isinstance(adapters.clipboard, LinuxClipboardAdapter)
    assert isinstance(adapters.text_input, LinuxTextInputAdapter)
    assert isinstance(adapters.network, LinuxNetworkAdapter)
    assert isinstance(adapters.notifications, LinuxNotificationsAdapter)
    assert isinstance(adapters.files, LinuxFilesAdapter)


def test_build_default_adapter_set_keeps_mock_backends_in_developer_mode(tmp_path: Path) -> None:
    from operance.adapters import build_default_adapter_set
    from operance.adapters.mock import MockAppsAdapter

    config = AppConfig.from_env(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    adapters = build_default_adapter_set(config, system_name="Linux")

    assert isinstance(adapters.apps, MockAppsAdapter)


def test_linux_apps_adapter_launches_resolved_application() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    spawned: list[list[str]] = []

    adapter = LinuxAppsAdapter(
        spawn_command=spawned.append,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "firefox" else None,
    )

    message = adapter.launch("firefox")

    assert message == "Launched firefox"
    assert spawned == [["/usr/bin/firefox"]]


def test_linux_apps_adapter_uses_terminal_fallback_candidates() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    spawned: list[list[str]] = []

    def resolve(name: str) -> str | None:
        return "/usr/bin/konsole" if name == "konsole" else None

    adapter = LinuxAppsAdapter(
        spawn_command=spawned.append,
        resolve_executable=resolve,
    )

    message = adapter.launch("terminal")

    assert message == "Launched terminal"
    assert spawned == [["/usr/bin/konsole"]]


def test_linux_apps_adapter_opens_explicit_url_targets() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    adapter = LinuxAppsAdapter(
        run_command=lambda command: commands.append(command) or subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        ),
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "xdg-open" else None,
    )

    message = adapter.launch("https://example.com/docs")

    assert message == "Opened https://example.com/docs"
    assert commands == [["/usr/bin/xdg-open", "https://example.com/docs"]]


def test_linux_apps_adapter_normalizes_localhost_targets_for_xdg_open() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    adapter = LinuxAppsAdapter(
        run_command=lambda command: commands.append(command) or subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        ),
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "xdg-open" else None,
    )

    message = adapter.launch("localhost:3000")

    assert message == "Opened http://localhost:3000"
    assert commands == [["/usr/bin/xdg-open", "http://localhost:3000"]]


def test_linux_apps_adapter_prefers_xdg_open_over_gtk_launch_for_url_like_targets() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    def resolve_executable(name: str) -> str | None:
        if name in {"gtk-launch", "xdg-open"}:
            return f"/usr/bin/{name}"
        return None

    adapter = LinuxAppsAdapter(
        run_command=lambda command: commands.append(command) or subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        ),
        resolve_executable=resolve_executable,
    )

    message = adapter.launch("localhost:3000")

    assert message == "Opened http://localhost:3000"
    assert commands == [["/usr/bin/xdg-open", "http://localhost:3000"]]


def test_linux_apps_adapter_uses_gtk_launch_for_desktop_entries_and_requires_success() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    adapter = LinuxAppsAdapter(
        run_command=lambda command: commands.append(command) or subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        ),
        resolve_executable=lambda name: "/usr/bin/gtk-launch" if name == "gtk-launch" else None,
    )

    message = adapter.launch("firefox")

    assert message == "Launched firefox"
    assert commands == [["/usr/bin/gtk-launch", "firefox.desktop"]]


def test_linux_apps_adapter_surfaces_xdg_open_failures() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    adapter = LinuxAppsAdapter(
        run_command=lambda command: subprocess.CompletedProcess(
            command,
            3,
            stdout="",
            stderr="no browser available",
        ),
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "xdg-open" else None,
    )

    with pytest.raises(ValueError, match="xdg-open failed: no browser available"):
        adapter.launch("https://example.com/docs")


def test_linux_apps_adapter_focuses_app_through_kwin_script() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-1] == "org.kde.KWin.queryWindowInfo":
            if len([item for item in commands if item[-1] == "org.kde.KWin.queryWindowInfo"]) == 1:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="({'caption': <'Other app'>, 'desktopFile': <'org.kde.konsole'>, 'resourceClass': <'org.kde.konsole'>, 'resourceName': <'konsole'>},)\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="({'caption': <'Mozilla Firefox'>, 'desktopFile': <'firefox'>, 'resourceClass': <'firefox'>, 'resourceName': <'firefox'>},)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxAppsAdapter(
        run_command=run_command,
        spawn_command=lambda _: (_ for _ in ()).throw(AssertionError("spawn should not be used")),
        resolve_executable=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None,
    )

    assert adapter.focus("firefox") == "Focused firefox"
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_apps_adapter_focus_falls_back_to_launch_when_kwin_focus_does_not_match() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []
    spawned: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-1] == "org.kde.KWin.queryWindowInfo":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="({'caption': <'Konsole'>, 'desktopFile': <'org.kde.konsole'>, 'resourceClass': <'org.kde.konsole'>, 'resourceName': <'konsole'>},)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxAppsAdapter(
        run_command=run_command,
        spawn_command=spawned.append,
        resolve_executable=lambda name: (
            "/usr/bin/gdbus"
            if name == "gdbus"
            else "/usr/bin/firefox"
            if name == "firefox"
            else None
        ),
    )

    assert adapter.focus("firefox") == "Focused firefox"
    assert spawned == [["/usr/bin/firefox"]]


def test_linux_apps_adapter_quits_matching_app_via_kwin_window_close() -> None:
    from operance.adapters.linux import LinuxAppsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxAppsAdapter(run_command=run_command)

    assert adapter.quit("firefox") == "Quit firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_lists_deduplicated_window_titles() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>}), ('0_{def}', 'Terminal', 'utilities-terminal', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>}), ('0_{abc}', 'Firefox', 'firefox', 30, 0.5, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
            stderr="",
        )

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.list_windows() == ["Firefox", "Terminal"]
    assert commands == [[
        "gdbus",
        "call",
        "--session",
        "--timeout",
        "3",
        "--dest",
        "org.kde.KWin",
        "--object-path",
        "/WindowsRunner",
        "--method",
        "org.kde.krunner1.Match",
        "",
    ]]


def test_linux_windows_adapter_sets_fullscreen_state_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.set_fullscreen("firefox", True) == "Enabled fullscreen for window Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_sets_keep_above_state_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.set_keep_above("firefox", True) == "Enabled keep-above for window Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_sets_shaded_state_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.set_shaded("firefox", True) == "Shaded window Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_sets_keep_below_state_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.set_keep_below("firefox", True) == "Enabled keep-below for window Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_sets_on_all_desktops_state_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.set_on_all_desktops("firefox", True) == "Enabled all-desktops for window Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_switches_best_matching_window() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>}), ('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 30, 0.5, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.krunner1.Run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.switch("firefox") == "Switched to window GitHub — Mozilla Firefox"
    assert commands == [
        [
            "gdbus",
            "call",
            "--session",
            "--timeout",
            "3",
            "--dest",
            "org.kde.KWin",
            "--object-path",
            "/WindowsRunner",
            "--method",
            "org.kde.krunner1.Match",
            "firefox",
        ],
        [
            "gdbus",
            "call",
            "--session",
            "--timeout",
            "3",
            "--dest",
            "org.kde.KWin",
            "--object-path",
            "/WindowsRunner",
            "--method",
            "org.kde.krunner1.Run",
            "0_{abc}",
            "",
        ],
    ]


def test_linux_windows_adapter_minimizes_matching_window_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.minimize("firefox") == "Minimized window GitHub — Mozilla Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_maximizes_matching_window_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.maximize("firefox") == "Maximized window GitHub — Mozilla Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_restores_matching_window_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.restore("firefox") == "Restored window GitHub — Mozilla Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_windows_adapter_closes_matching_window_via_kwin_script() -> None:
    from operance.adapters.linux import LinuxWindowsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-2:] == ["org.kde.krunner1.Match", "firefox"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="([('0_{abc}', 'GitHub — Mozilla Firefox', 'firefox', 100, 0.8, {'subtext': <'Activate running window on Desktop 1'>})],)\n",
                stderr="",
            )
        if "org.kde.kwin.Scripting.loadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(0,)\n", stderr="")
        if "org.kde.kwin.Script.run" in command:
            return subprocess.CompletedProcess(command, 0, stdout="()\n", stderr="")
        if "org.kde.kwin.Scripting.unloadScript" in command:
            return subprocess.CompletedProcess(command, 0, stdout="(true,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxWindowsAdapter(run_command=run_command)

    assert adapter.close("firefox") == "Closed window GitHub — Mozilla Firefox"
    assert any("org.kde.krunner1.Match" in command for command in commands)
    assert any("org.kde.kwin.Scripting.loadScript" in command for command in commands)
    assert any("org.kde.kwin.Script.run" in command for command in commands)
    assert any("org.kde.kwin.Scripting.unloadScript" in command for command in commands)


def test_linux_power_adapter_reads_battery_from_sysfs(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxPowerAdapter

    battery_dir = tmp_path / "BAT0"
    battery_dir.mkdir()
    (battery_dir / "capacity").write_text("87\n", encoding="utf-8")

    adapter = LinuxPowerAdapter(
        power_supply_root=tmp_path,
        resolve_executable=lambda _: None,
    )

    assert adapter.battery_status() == "Battery is 87%"


def test_linux_power_adapter_prefers_upower_dbus_when_available() -> None:
    from operance.adapters.linux import LinuxPowerAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:7] == ["gdbus", "call", "--system", "--timeout", "3", "--dest", "org.freedesktop.UPower"]:
            if command[-1] == "org.freedesktop.UPower.EnumerateDevices":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="([objectpath '/org/freedesktop/UPower/devices/battery_BAT0'],)\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(command, 0, stdout="(<96.0>,)\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    adapter = LinuxPowerAdapter(
        run_command=run_command,
        resolve_executable=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None,
    )

    assert adapter.battery_status() == "Battery is 96%"
    assert commands == [
        [
            "gdbus",
            "call",
            "--system",
            "--timeout",
            "3",
            "--dest",
            "org.freedesktop.UPower",
            "--object-path",
            "/org/freedesktop/UPower",
            "--method",
            "org.freedesktop.UPower.EnumerateDevices",
        ],
        [
            "gdbus",
            "call",
            "--system",
            "--timeout",
            "3",
            "--dest",
            "org.freedesktop.UPower",
            "--object-path",
            "/org/freedesktop/UPower/devices/battery_BAT0",
            "--method",
            "org.freedesktop.DBus.Properties.Get",
            "org.freedesktop.UPower.Device",
            "Percentage",
        ],
    ]


def test_linux_audio_adapter_uses_wpctl_when_available() -> None:
    from operance.adapters.linux import LinuxAudioAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:2] == ["wpctl", "get-volume"]:
            return subprocess.CompletedProcess(command, 0, stdout="Volume: 0.42 [MUTED]\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxAudioAdapter(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "wpctl" else None,
    )

    assert adapter.get_volume() == 42
    assert adapter.is_muted() is True
    assert adapter.set_volume(50) == "Volume set to 50%"
    assert adapter.set_muted(False) == "Audio unmuted"
    assert commands == [
        ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
        ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "50%"],
        ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"],
    ]


def test_linux_clipboard_adapter_reads_and_writes_text() -> None:
    from operance.adapters.linux import LinuxClipboardAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:2] == ["wl-paste", "--no-newline"]:
            return subprocess.CompletedProcess(command, 0, stdout="hello from clipboard", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxClipboardAdapter(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name in {"wl-copy", "wl-paste"} else None,
    )

    assert adapter.get_text() == "hello from clipboard"
    assert adapter.set_text("build complete") == "Copied text to clipboard"
    assert adapter.clear() == "Cleared clipboard"
    assert commands == [
        ["wl-paste", "--no-newline"],
        ["wl-copy", "--trim-newline", "build complete"],
        ["wl-copy", "--clear"],
    ]


def test_linux_text_input_adapter_pastes_and_types_text() -> None:
    from operance.adapters.linux import LinuxTextInputAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxTextInputAdapter(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
    )

    assert adapter.copy_selection() == "Copied selection to clipboard"
    assert adapter.paste() == "Pasted clipboard into active window"
    assert adapter.type_text("build complete") == "Typed text into active window"
    assert adapter.press_key("enter") == "Pressed Enter key"
    assert adapter.press_key("ctrl+shift+p") == "Pressed Ctrl+Shift+P shortcut"
    assert commands == [
        ["wtype", "-M", "ctrl", "c", "-m", "ctrl"],
        ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
        ["wtype", "build complete"],
        ["wtype", "-k", "Return"],
        ["wtype", "-M", "ctrl", "-M", "shift", "p", "-m", "shift", "-m", "ctrl"],
    ]


def test_linux_text_input_adapter_reports_unsupported_virtual_keyboard_protocol() -> None:
    from operance.adapters.linux import LinuxTextInputAdapter

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="Compositor does not support the virtual keyboard protocol",
        )

    adapter = LinuxTextInputAdapter(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
    )

    with pytest.raises(
        ValueError,
        match="wtype is installed but the compositor does not support the virtual keyboard protocol",
    ):
        adapter.type_text("build complete")


def test_linux_network_adapter_toggles_and_reads_wifi_state() -> None:
    from operance.adapters.linux import LinuxNetworkAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command == ["nmcli", "radio", "wifi"]:
            return subprocess.CompletedProcess(command, 0, stdout="enabled\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxNetworkAdapter(run_command=run_command)

    assert adapter.is_wifi_enabled() is True
    assert adapter.wifi_status() == "Wi-Fi is on"
    assert adapter.set_wifi_enabled(False) == "Wi-Fi turned off"
    assert commands == [
        ["nmcli", "radio", "wifi"],
        ["nmcli", "radio", "wifi"],
        ["nmcli", "radio", "wifi", "off"],
    ]


def test_linux_network_adapter_connects_known_ssid() -> None:
    from operance.adapters.linux import LinuxNetworkAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="successfully activated\n", stderr="")

    adapter = LinuxNetworkAdapter(run_command=run_command)

    assert adapter.connect_known_ssid("home") == "Connected to Wi-Fi home"
    assert commands == [["nmcli", "connection", "up", "id", "home"]]


def test_linux_network_adapter_disconnects_current_wifi_connection() -> None:
    from operance.adapters.linux import LinuxNetworkAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command == ["nmcli", "-t", "-f", "ACTIVE,TYPE,NAME", "connection", "show", "--active"]:
            return subprocess.CompletedProcess(command, 0, stdout="yes:wifi:home\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxNetworkAdapter(run_command=run_command)

    assert adapter.disconnect_current() == "Disconnected Wi-Fi home"
    assert commands == [
        ["nmcli", "-t", "-f", "ACTIVE,TYPE,NAME", "connection", "show", "--active"],
        ["nmcli", "connection", "down", "id", "home"],
    ]


def test_linux_notifications_adapter_uses_notify_send() -> None:
    from operance.adapters.linux import LinuxNotificationsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = LinuxNotificationsAdapter(
        run_command=run_command,
        resolve_executable=lambda _: None,
    )

    assert adapter.show("Operance", "Build complete") == "Notification shown"
    assert commands == [["notify-send", "Operance", "Build complete"]]


def test_linux_notifications_adapter_prefers_dbus_when_gdbus_is_available() -> None:
    from operance.adapters.linux import LinuxNotificationsAdapter

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="(uint32 4,)\n", stderr="")

    adapter = LinuxNotificationsAdapter(
        run_command=run_command,
        resolve_executable=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None,
    )

    assert adapter.show("Operance", "Build complete") == "Notification shown"
    assert commands == [
        [
            "gdbus",
            "call",
            "--session",
            "--timeout",
            "3",
            "--dest",
            "org.freedesktop.Notifications",
            "--object-path",
            "/org/freedesktop/Notifications",
            "--method",
            "org.freedesktop.Notifications.Notify",
            "operance",
            "0",
            "",
            "Operance",
            "Build complete",
            "[]",
            "{}",
            "5000",
        ]
    ]


def test_linux_files_adapter_lists_recent_files_in_modified_order(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxFilesAdapter

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    older_file = desktop_dir / "notes.txt"
    newer_file = desktop_dir / "todo.md"
    older_file.write_text("notes", encoding="utf-8")
    newer_file.write_text("todo", encoding="utf-8")
    os.utime(older_file, (1_700_000_000, 1_700_000_000))
    os.utime(newer_file, (1_700_000_100, 1_700_000_100))

    adapter = LinuxFilesAdapter(desktop_dir=desktop_dir)

    assert adapter.list_recent() == [newer_file, older_file]


def test_linux_files_adapter_opens_desktop_entry(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxFilesAdapter

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    file_path = desktop_dir / "notes.txt"
    file_path.write_text("notes", encoding="utf-8")
    commands: list[list[str]] = []
    adapter = LinuxFilesAdapter(
        desktop_dir=desktop_dir,
        run_command=lambda command: commands.append(command)
        or subprocess.CompletedProcess(command, 0, "", ""),
        resolve_executable=lambda name: name,
    )

    message = adapter.open_path(file_path)

    assert message == "Opened desktop entry notes.txt"
    assert commands == [["xdg-open", str(file_path)]]


def test_linux_files_adapter_renames_desktop_entry(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxFilesAdapter

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    source = desktop_dir / "projects"
    source.mkdir()
    adapter = LinuxFilesAdapter(desktop_dir=desktop_dir)

    renamed = adapter.rename_path(source, "archive")

    assert renamed == desktop_dir / "archive"
    assert renamed.exists() is True
    assert source.exists() is False


def test_linux_files_adapter_deletes_desktop_file(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxFilesAdapter

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    file_path = desktop_dir / "notes.txt"
    file_path.write_text("notes", encoding="utf-8")
    adapter = LinuxFilesAdapter(desktop_dir=desktop_dir)

    adapter.remove_file(file_path)

    assert file_path.exists() is False


def test_linux_files_adapter_moves_desktop_entry(tmp_path: Path) -> None:
    from operance.adapters.linux import LinuxFilesAdapter

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    source = desktop_dir / "projects"
    source.mkdir()
    destination_dir = desktop_dir / "archive"
    destination_dir.mkdir()
    adapter = LinuxFilesAdapter(desktop_dir=desktop_dir)

    moved = adapter.move_path(source, destination_dir)

    assert moved == destination_dir / "projects"
    assert moved.exists() is True
    assert source.exists() is False
