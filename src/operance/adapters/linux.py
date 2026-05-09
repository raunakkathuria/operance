"""Linux-backed desktop adapters for KDE/Wayland developer machines."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Callable
from uuid import uuid4

from .base import AdapterSet
from ..key_presses import normalize_supported_key, supported_key_display_name
from ..launch_targets import is_url_like_target, normalize_launch_target


RunCommand = Callable[[list[str]], subprocess.CompletedProcess[str]]
SpawnCommand = Callable[[list[str]], None]
ResolveExecutable = Callable[[str], str | None]
GDBUS_TIMEOUT_SECONDS = "3"
APP_LAUNCH_VERIFICATION_TIMEOUT_SECONDS = 5.0
APP_LAUNCH_VERIFICATION_INTERVAL_SECONDS = 0.25
APP_LAUNCH_VERIFICATION_SETTLE_SECONDS = 2.0
_WTYPE_ARGS_BY_SUPPORTED_KEY = {
    "backspace": ["-k", "BackSpace"],
    "enter": ["-k", "Return"],
    "escape": ["-k", "Escape"],
    "tab": ["-k", "Tab"],
    "ctrl+c": ["-M", "ctrl", "c", "-m", "ctrl"],
    "ctrl+v": ["-M", "ctrl", "v", "-m", "ctrl"],
    "ctrl+l": ["-M", "ctrl", "l", "-m", "ctrl"],
    "ctrl+r": ["-M", "ctrl", "r", "-m", "ctrl"],
    "ctrl+t": ["-M", "ctrl", "t", "-m", "ctrl"],
    "ctrl+w": ["-M", "ctrl", "w", "-m", "ctrl"],
    "ctrl+shift+p": ["-M", "ctrl", "-M", "shift", "p", "-m", "shift", "-m", "ctrl"],
}


def _default_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _default_spawn_command(command: list[str]) -> None:
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _default_resolve_executable(name: str) -> str | None:
    return shutil.which(name)


def _wtype_args_for_supported_key(key: str) -> list[str] | None:
    normalized = normalize_supported_key(key)
    if normalized is None:
        return None
    args = _WTYPE_ARGS_BY_SUPPORTED_KEY.get(normalized)
    if args is None:
        return None
    return list(args)


def _require_success(
    result: subprocess.CompletedProcess[str],
    *,
    command_label: str,
) -> subprocess.CompletedProcess[str]:
    if result.returncode == 0:
        return result

    detail = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
    raise ValueError(f"{command_label} failed: {detail}")


def _require_text_input_success(result: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    if result.returncode == 0:
        return result

    detail = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
    if "virtual keyboard protocol" in detail.casefold():
        raise ValueError(
            "wtype is installed but the compositor does not support the virtual keyboard protocol"
        )
    raise ValueError(f"wtype failed: {detail}")


def _strip_desktop_suffix(app: str) -> str:
    return app[:-8] if app.endswith(".desktop") else app


def _process_name_candidates_for_launch(app: str, command: list[str]) -> list[str]:
    candidates: list[str] = []
    launcher_names = {"gtk-launch", "xdg-open"}
    for raw_candidate in (
        Path(command[0]).name if command else "",
        _strip_desktop_suffix(app),
        _strip_desktop_suffix(app).split(".")[-1],
    ):
        candidate = raw_candidate.strip()
        if not candidate or "/" in candidate or candidate in launcher_names:
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


@dataclass(slots=True)
class LinuxAppsAdapter:
    run_command: RunCommand = _default_run_command
    spawn_command: SpawnCommand = _default_spawn_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def launch(self, app: str) -> str:
        self._run_launch_command(app)
        if is_url_like_target(app):
            return f"Opened {normalize_launch_target(app)}"
        return f"Launched {app}"

    def focus(self, app: str) -> str:
        if self.resolve_executable("gdbus") is not None and self._focus_via_kwin(app):
            return f"Focused {app}"

        self._run_launch_command(app)
        return f"Focused {app}"

    def quit(self, app: str) -> str:
        LinuxWindowsAdapter(run_command=self.run_command).close(app)
        return f"Quit {app}"

    def _focus_via_kwin(self, app: str) -> bool:
        try:
            before = self._query_active_window_info()
        except ValueError:
            before = None
        if _window_info_matches_app(before, app):
            return True

        plugin_name = f"operance_focus_{uuid4().hex}"
        script_path = self._write_focus_script(app)
        script_id: int | None = None
        try:
            script_id = self._load_kwin_script(script_path, plugin_name)
            _require_success(
                self.run_command(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--timeout",
                        GDBUS_TIMEOUT_SECONDS,
                        "--dest",
                        "org.kde.KWin",
                        "--object-path",
                        f"/Scripting/Script{script_id}",
                        "--method",
                        "org.kde.kwin.Script.run",
                    ]
                ),
                command_label="gdbus kwin script run",
            )
        except ValueError:
            return False
        finally:
            if script_id is not None:
                try:
                    _require_success(
                        self.run_command(
                            [
                                "gdbus",
                                "call",
                                "--session",
                                "--timeout",
                                GDBUS_TIMEOUT_SECONDS,
                                "--dest",
                                "org.kde.KWin",
                                "--object-path",
                                "/Scripting",
                                "--method",
                                "org.kde.kwin.Scripting.unloadScript",
                                plugin_name,
                            ]
                        ),
                        command_label="gdbus kwin unloadScript",
                    )
                except ValueError:
                    pass
            script_path.unlink(missing_ok=True)

        try:
            after = self._query_active_window_info()
        except ValueError:
            after = None
        return _window_info_matches_app(after, app)

    def _run_launch_command(self, app: str) -> None:
        command, command_label = self._resolve_launch_command(app)
        if command_label == "spawn":
            self.spawn_command(command)
            if not is_url_like_target(app):
                self._require_launched_app_observable(app, command)
            return
        _require_success(self.run_command(command), command_label=command_label)
        if not is_url_like_target(app):
            self._require_launched_app_observable(app, command)

    def _resolve_launch_command(self, app: str) -> tuple[list[str], str]:
        resolved = self.resolve_executable(app)
        if resolved is not None:
            return [resolved], "spawn"

        if app == "terminal":
            for candidate in ("konsole", "kgx", "gnome-terminal", "ptyxis", "xterm"):
                resolved_terminal = self.resolve_executable(candidate)
                if resolved_terminal is not None:
                    return [resolved_terminal], "spawn"

        if is_url_like_target(app):
            xdg_open = self.resolve_executable("xdg-open")
            if xdg_open is not None:
                return [xdg_open, normalize_launch_target(app)], "xdg-open"

        gtk_launch = self.resolve_executable("gtk-launch")
        if gtk_launch is not None:
            return [gtk_launch, f"{_strip_desktop_suffix(app)}.desktop"], "gtk-launch"

        xdg_open = self.resolve_executable("xdg-open")
        if xdg_open is not None:
            return [xdg_open, normalize_launch_target(app)], "xdg-open"

        raise ValueError(f"unable to resolve application launcher for {app}")

    def _require_launched_app_observable(self, app: str, command: list[str]) -> None:
        pgrep = self.resolve_executable("pgrep")
        if pgrep is None:
            return

        candidates = _process_name_candidates_for_launch(app, command)
        if not candidates:
            return

        started_at = time.monotonic()
        deadline = started_at + APP_LAUNCH_VERIFICATION_TIMEOUT_SECONDS
        settle_deadline = started_at + APP_LAUNCH_VERIFICATION_SETTLE_SECONDS
        if APP_LAUNCH_VERIFICATION_SETTLE_SECONDS > 0:
            time.sleep(APP_LAUNCH_VERIFICATION_SETTLE_SECONDS)
        while True:
            for candidate in candidates:
                result = self.run_command([pgrep, "-x", candidate])
                if result.returncode == 0 and time.monotonic() >= settle_deadline:
                    return
            if time.monotonic() >= deadline:
                break
            time.sleep(APP_LAUNCH_VERIFICATION_INTERVAL_SECONDS)

        candidate_text = ", ".join(candidates)
        raise ValueError(
            f"launch command completed but no matching process appeared for {app} "
            f"(checked: {candidate_text})"
        )

    def _query_active_window_info(self) -> dict[str, str] | None:
        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.kde.KWin",
                    "--object-path",
                    "/KWin",
                    "--method",
                    "org.kde.KWin.queryWindowInfo",
                ]
            ),
            command_label="gdbus kwin queryWindowInfo",
        )
        return _parse_window_info_map(result.stdout)

    def _load_kwin_script(self, script_path: Path, plugin_name: str) -> int:
        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.kde.KWin",
                    "--object-path",
                    "/Scripting",
                    "--method",
                    "org.kde.kwin.Scripting.loadScript",
                    str(script_path),
                    plugin_name,
                ]
            ),
            command_label="gdbus kwin loadScript",
        )
        return _parse_first_int(result.stdout)

    def _write_focus_script(self, app: str) -> Path:
        script = f"""
const target = {json.dumps(app.casefold())};

function matchesWindow(window) {{
    const fields = [
        String(window.caption || ""),
        String(window.resourceName || ""),
        String(window.resourceClass || ""),
        String(window.desktopFile || ""),
    ];
    for (let i = 0; i < fields.length; ++i) {{
        if (fields[i].toLowerCase().includes(target)) {{
            return true;
        }}
    }}
    return false;
}}

const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (matchesWindow(window)) {{
        workspace.activeWindow = window;
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-focus-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)


@dataclass(slots=True, frozen=True)
class WindowsRunnerMatch:
    match_id: str
    title: str
    icon: str
    category_relevance: int
    score: float
    subtext: str


@dataclass(slots=True)
class SystemTimeAdapter:
    def now(self) -> str:
        return f"It is {datetime.now().strftime('%H:%M')}"


@dataclass(slots=True)
class LinuxPowerAdapter:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable
    power_supply_root: Path = Path("/sys/class/power_supply")

    def battery_status(self) -> str:
        dbus_percent = self._read_upower_percentage()
        if dbus_percent is not None:
            return f"Battery is {dbus_percent}%"

        sysfs_percent = self._read_sysfs_capacity()
        if sysfs_percent is not None:
            return f"Battery is {sysfs_percent}%"

        battery_path = self._upower_battery_path()
        if battery_path is None:
            return "Battery status unavailable"

        result = _require_success(
            self.run_command(["upower", "--show-info", battery_path]),
            command_label="upower --show-info",
        )
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("percentage:"):
                return f"Battery is {stripped.removeprefix('percentage:').strip()}"

        return "Battery status unavailable"

    def _read_upower_percentage(self) -> int | None:
        if self.resolve_executable("gdbus") is None:
            return None

        battery_path = self._upower_battery_path_dbus()
        if battery_path is None:
            return None

        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--system",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.freedesktop.UPower",
                    "--object-path",
                    battery_path,
                    "--method",
                    "org.freedesktop.DBus.Properties.Get",
                    "org.freedesktop.UPower.Device",
                    "Percentage",
                ]
            ),
            command_label="gdbus upower percentage",
        )
        return _parse_dbus_float(result.stdout)

    def _read_sysfs_capacity(self) -> int | None:
        if not self.power_supply_root.exists():
            return None

        for battery_dir in sorted(self.power_supply_root.glob("BAT*")):
            capacity_file = battery_dir / "capacity"
            if capacity_file.exists():
                try:
                    return int(capacity_file.read_text(encoding="utf-8").strip())
                except ValueError:
                    continue
        return None

    def _upower_battery_path(self) -> str | None:
        result = _require_success(
            self.run_command(["upower", "--enumerate"]),
            command_label="upower --enumerate",
        )
        for line in result.stdout.splitlines():
            if "battery" in line.lower():
                return line.strip()
        return None

    def _upower_battery_path_dbus(self) -> str | None:
        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--system",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.freedesktop.UPower",
                    "--object-path",
                    "/org/freedesktop/UPower",
                    "--method",
                    "org.freedesktop.UPower.EnumerateDevices",
                ]
            ),
            command_label="gdbus upower enumerate",
        )
        return _parse_first_object_path(result.stdout)


@dataclass(slots=True)
class LinuxAudioAdapter:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def get_volume(self) -> int:
        backend = self._backend()
        if backend == "wpctl":
            result = _require_success(
                self.run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]),
                command_label="wpctl get-volume",
            )
            return _parse_wpctl_volume(result.stdout)

        result = _require_success(
            self.run_command(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]),
            command_label="pactl get-sink-volume",
        )
        return _parse_percent_token(result.stdout)

    def set_volume(self, percent: int) -> str:
        backend = self._backend()
        if backend == "wpctl":
            _require_success(
                self.run_command(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"]),
                command_label="wpctl set-volume",
            )
        else:
            _require_success(
                self.run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"]),
                command_label="pactl set-sink-volume",
            )
        return f"Volume set to {percent}%"

    def set_muted(self, muted: bool) -> str:
        backend = self._backend()
        if backend == "wpctl":
            _require_success(
                self.run_command(
                    ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"]
                ),
                command_label="wpctl set-mute",
            )
        else:
            _require_success(
                self.run_command(
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"]
                ),
                command_label="pactl set-sink-mute",
            )
        return "Audio muted" if muted else "Audio unmuted"

    def is_muted(self) -> bool:
        backend = self._backend()
        if backend == "wpctl":
            result = _require_success(
                self.run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]),
                command_label="wpctl get-volume",
            )
            return "[MUTED]" in result.stdout

        result = _require_success(
            self.run_command(["pactl", "get-sink-mute", "@DEFAULT_SINK@"]),
            command_label="pactl get-sink-mute",
        )
        return result.stdout.strip().lower().endswith("yes")

    def _backend(self) -> str:
        if self.resolve_executable("wpctl") is not None:
            return "wpctl"
        if self.resolve_executable("pactl") is not None:
            return "pactl"
        raise ValueError("unable to find a supported Linux audio backend")


@dataclass(slots=True)
class LinuxClipboardAdapter:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def get_text(self) -> str:
        self._require_backend()
        result = _require_success(
            self.run_command(["wl-paste", "--no-newline"]),
            command_label="wl-paste",
        )
        return result.stdout

    def set_text(self, text: str) -> str:
        self._require_backend()
        command = ["wl-copy", "--clear"] if not text else ["wl-copy", "--trim-newline", text]
        _require_success(
            self.run_command(command),
            command_label="wl-copy",
        )
        return "Copied text to clipboard"

    def clear(self) -> str:
        self._require_backend()
        _require_success(
            self.run_command(["wl-copy", "--clear"]),
            command_label="wl-copy",
        )
        return "Cleared clipboard"

    def _require_backend(self) -> None:
        if self.resolve_executable("wl-copy") is None or self.resolve_executable("wl-paste") is None:
            raise ValueError("unable to find wl-copy and wl-paste for Linux clipboard access")


@dataclass(slots=True)
class LinuxTextInputAdapter:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def copy_selection(self) -> str:
        self._require_backend()
        _require_text_input_success(
            self.run_command(["wtype", "-M", "ctrl", "c", "-m", "ctrl"]),
        )
        return "Copied selection to clipboard"

    def paste(self) -> str:
        self._require_backend()
        _require_text_input_success(
            self.run_command(["wtype", "-M", "ctrl", "v", "-m", "ctrl"]),
        )
        return "Pasted clipboard into active window"

    def type_text(self, text: str) -> str:
        self._require_backend()
        _require_text_input_success(
            self.run_command(["wtype", text]),
        )
        return "Typed text into active window"

    def press_key(self, key: str) -> str:
        self._require_backend()
        normalized = normalize_supported_key(key)
        linux_args = _wtype_args_for_supported_key(key)
        display_name = supported_key_display_name(key)
        if normalized is None or linux_args is None or display_name is None:
            raise ValueError(f"unsupported key for Linux text input: {key}")
        _require_text_input_success(
            self.run_command(["wtype", *linux_args]),
        )
        if "+" in normalized:
            return f"Pressed {display_name} shortcut"
        return f"Pressed {display_name} key"

    def _require_backend(self) -> None:
        if self.resolve_executable("wtype") is None:
            raise ValueError("unable to find wtype for Linux text input")


@dataclass(slots=True)
class LinuxNetworkAdapter:
    run_command: RunCommand = _default_run_command

    def set_wifi_enabled(self, enabled: bool) -> str:
        _require_success(
            self.run_command(["nmcli", "radio", "wifi", "on" if enabled else "off"]),
            command_label="nmcli radio wifi",
        )
        return "Wi-Fi turned on" if enabled else "Wi-Fi turned off"

    def wifi_status(self) -> str:
        return "Wi-Fi is on" if self.is_wifi_enabled() else "Wi-Fi is off"

    def is_wifi_enabled(self) -> bool:
        result = _require_success(
            self.run_command(["nmcli", "radio", "wifi"]),
            command_label="nmcli radio wifi",
        )
        state = result.stdout.strip().lower()
        return state in {"enabled", "on"}

    def disconnect_current(self) -> str:
        result = _require_success(
            self.run_command(["nmcli", "-t", "-f", "ACTIVE,TYPE,NAME", "connection", "show", "--active"]),
            command_label="nmcli connection show --active",
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split(":", maxsplit=2)
            if len(parts) != 3:
                continue
            active, connection_type, name = parts
            if active != "yes":
                continue
            if connection_type not in {"wifi", "wireless", "802-11-wireless"}:
                continue
            _require_success(
                self.run_command(["nmcli", "connection", "down", "id", name]),
                command_label="nmcli connection down",
            )
            return f"Disconnected Wi-Fi {name}"
        raise ValueError("no active Wi-Fi connection")

    def connect_known_ssid(self, ssid: str) -> str:
        _require_success(
            self.run_command(["nmcli", "connection", "up", "id", ssid]),
            command_label="nmcli connection up",
        )
        return f"Connected to Wi-Fi {ssid}"


@dataclass(slots=True)
class LinuxWindowsAdapter:
    run_command: RunCommand = _default_run_command

    def list_windows(self) -> list[str]:
        matches = self._runner_matches("")
        return [match.title for match in matches]

    def switch(self, window: str) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.kde.KWin",
                    "--object-path",
                    "/WindowsRunner",
                    "--method",
                    "org.kde.krunner1.Run",
                    target.match_id,
                    "",
                ]
            ),
            command_label="gdbus windows runner run",
        )
        return f"Switched to window {target.title}"

    def minimize(self, window: str) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_minimize_{uuid4().hex}"
        script_path = self._write_minimize_script(target.match_id)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin minimize script run",
        )

        return f"Minimized window {target.title}"

    def maximize(self, window: str) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_maximize_{uuid4().hex}"
        script_path = self._write_maximize_script(target.match_id)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin maximize script run",
        )

        return f"Maximized window {target.title}"

    def set_fullscreen(self, window: str, enabled: bool) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_fullscreen_{uuid4().hex}"
        script_path = self._write_set_fullscreen_script(target.match_id, enabled)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin fullscreen script run",
        )

        return (
            f"Enabled fullscreen for window {target.title}"
            if enabled
            else f"Disabled fullscreen for window {target.title}"
        )

    def set_keep_above(self, window: str, enabled: bool) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_keep_above_{uuid4().hex}"
        script_path = self._write_set_keep_above_script(target.match_id, enabled)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin keep-above script run",
        )

        return (
            f"Enabled keep-above for window {target.title}"
            if enabled
            else f"Disabled keep-above for window {target.title}"
        )

    def set_shaded(self, window: str, enabled: bool) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_shade_{uuid4().hex}"
        script_path = self._write_set_shaded_script(target.match_id, enabled)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin shade script run",
        )

        return f"Shaded window {target.title}" if enabled else f"Unshaded window {target.title}"

    def set_keep_below(self, window: str, enabled: bool) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_keep_below_{uuid4().hex}"
        script_path = self._write_set_keep_below_script(target.match_id, enabled)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin keep-below script run",
        )

        return (
            f"Enabled keep-below for window {target.title}"
            if enabled
            else f"Disabled keep-below for window {target.title}"
        )

    def set_on_all_desktops(self, window: str, enabled: bool) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_all_desktops_{uuid4().hex}"
        script_path = self._write_set_on_all_desktops_script(target.match_id, enabled)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin all-desktops script run",
        )

        return (
            f"Enabled all-desktops for window {target.title}"
            if enabled
            else f"Disabled all-desktops for window {target.title}"
        )

    def restore(self, window: str) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_restore_{uuid4().hex}"
        script_path = self._write_restore_script(target.match_id)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin restore script run",
        )

        return f"Restored window {target.title}"

    def close(self, window: str) -> str:
        matches = self._runner_matches(window)
        if not matches:
            raise ValueError(f"no window matched {window!r}")

        target = matches[0]
        plugin_name = f"operance_close_{uuid4().hex}"
        script_path = self._write_close_script(target.match_id)
        self._run_temporary_kwin_script(
            script_path=script_path,
            plugin_name=plugin_name,
            command_label="gdbus kwin close script run",
        )

        return f"Closed window {target.title}"

    def _runner_matches(self, query: str) -> list[WindowsRunnerMatch]:
        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.kde.KWin",
                    "--object-path",
                    "/WindowsRunner",
                    "--method",
                    "org.kde.krunner1.Match",
                    query,
                ]
            ),
            command_label="gdbus windows runner match",
        )
        return _dedupe_window_matches(_parse_windows_runner_matches(result.stdout))

    def _load_kwin_script(self, script_path: Path, plugin_name: str) -> int:
        result = _require_success(
            self.run_command(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--timeout",
                    GDBUS_TIMEOUT_SECONDS,
                    "--dest",
                    "org.kde.KWin",
                    "--object-path",
                    "/Scripting",
                    "--method",
                    "org.kde.kwin.Scripting.loadScript",
                    str(script_path),
                    plugin_name,
                ]
            ),
            command_label="gdbus kwin loadScript",
        )
        return _parse_first_int(result.stdout)

    def _run_temporary_kwin_script(
        self,
        *,
        script_path: Path,
        plugin_name: str,
        command_label: str,
    ) -> None:
        script_id: int | None = None
        try:
            script_id = self._load_kwin_script(script_path, plugin_name)
            _require_success(
                self.run_command(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--timeout",
                        GDBUS_TIMEOUT_SECONDS,
                        "--dest",
                        "org.kde.KWin",
                        "--object-path",
                        f"/Scripting/Script{script_id}",
                        "--method",
                        "org.kde.kwin.Script.run",
                    ]
                ),
                command_label=command_label,
            )
        finally:
            if script_id is not None:
                try:
                    _require_success(
                        self.run_command(
                            [
                                "gdbus",
                                "call",
                                "--session",
                                "--timeout",
                                GDBUS_TIMEOUT_SECONDS,
                                "--dest",
                                "org.kde.KWin",
                                "--object-path",
                                "/Scripting",
                                "--method",
                                "org.kde.kwin.Scripting.unloadScript",
                                plugin_name,
                            ]
                        ),
                        command_label="gdbus kwin unloadScript",
                    )
                except ValueError:
                    pass
            script_path.unlink(missing_ok=True)

    def _write_minimize_script(self, match_id: str) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.minimized = true;
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-minimize-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_maximize_script(self, match_id: str) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        if (typeof window.setMaximize === "function") {{
            window.setMaximize(true, true);
        }} else {{
            window.maximized = true;
        }}
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-maximize-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_set_fullscreen_script(self, match_id: str, enabled: bool) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const enabled = {json.dumps(enabled)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.fullScreen = enabled;
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-fullscreen-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_set_keep_above_script(self, match_id: str, enabled: bool) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const enabled = {json.dumps(enabled)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.keepAbove = enabled;
        if (enabled) {{
            window.keepBelow = false;
        }}
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-keep-above-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_set_shaded_script(self, match_id: str, enabled: bool) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const enabled = {json.dumps(enabled)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.shade = enabled;
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-shade-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_set_keep_below_script(self, match_id: str, enabled: bool) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const enabled = {json.dumps(enabled)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.keepBelow = enabled;
        if (enabled) {{
            window.keepAbove = false;
        }}
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-keep-below-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_set_on_all_desktops_script(self, match_id: str, enabled: bool) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const enabled = {json.dumps(enabled)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.onAllDesktops = enabled;
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-all-desktops-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_restore_script(self, match_id: str) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        window.minimized = false;
        if (typeof window.setMaximize === "function") {{
            window.setMaximize(false, false);
        }} else {{
            window.maximized = false;
        }}
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-restore-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)

    def _write_close_script(self, match_id: str) -> Path:
        window_uuid = _match_id_to_window_uuid(match_id)
        script = f"""
const targetUuid = {json.dumps(window_uuid)};
const windows = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (let i = 0; i < windows.length; ++i) {{
    const window = windows[i];
    if (String(window.internalId || "") === targetUuid) {{
        if (typeof window.closeWindow === "function") {{
            window.closeWindow();
        }}
        break;
    }}
}}
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="operance-kwin-close-",
            suffix=".js",
            delete=False,
        ) as handle:
            handle.write(script)
            return Path(handle.name)


@dataclass(slots=True)
class LinuxNotificationsAdapter:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def show(self, title: str, message: str) -> str:
        if self.resolve_executable("gdbus") is not None:
            _require_success(
                self.run_command(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--timeout",
                        GDBUS_TIMEOUT_SECONDS,
                        "--dest",
                        "org.freedesktop.Notifications",
                        "--object-path",
                        "/org/freedesktop/Notifications",
                        "--method",
                        "org.freedesktop.Notifications.Notify",
                        "operance",
                        "0",
                        "",
                        title,
                        message,
                        "[]",
                        "{}",
                        "5000",
                    ]
                ),
                command_label="gdbus notify",
            )
            return "Notification shown"

        _require_success(
            self.run_command(["notify-send", title, message]),
            command_label="notify-send",
        )
        return "Notification shown"


@dataclass(slots=True)
class LinuxFilesAdapter:
    desktop_dir: Path
    max_recent_files: int = 10
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def list_recent(self, root: Path | None = None) -> list[Path]:
        target_root = root or self.desktop_dir
        if not target_root.exists():
            return []

        recent_files = [path for path in target_root.iterdir() if path.is_file()]
        return sorted(recent_files, key=lambda path: path.stat().st_mtime, reverse=True)[: self.max_recent_files]

    def open_path(self, path: Path) -> str:
        if not path.exists():
            raise ValueError(f"desktop entry not found: {path.name}")
        xdg_open = self.resolve_executable("xdg-open")
        if xdg_open is None:
            raise ValueError("xdg-open is not available")
        _require_success(
            self.run_command([xdg_open, str(path)]),
            command_label="xdg-open",
        )
        return f"Opened desktop entry {path.name}"

    def create_folder(self, root: Path, name: str) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        folder = root / name
        folder.mkdir(exist_ok=True)
        return folder

    def remove_folder(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)

    def remove_file(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def rename_path(self, path: Path, new_name: str) -> Path:
        target = path.with_name(new_name)
        if target.exists():
            raise ValueError(f"desktop entry already exists: {target.name}")
        return path.rename(target)

    def move_path(self, path: Path, destination_dir: Path) -> Path:
        if not destination_dir.exists() or not destination_dir.is_dir():
            raise ValueError(f"destination folder not found: {destination_dir.name}")
        target = destination_dir / path.name
        if target.exists():
            raise ValueError(f"destination entry already exists: {target.name}")
        return path.rename(target)


def build_linux_adapter_set(
    *,
    desktop_dir: Path,
    run_command: RunCommand = _default_run_command,
    spawn_command: SpawnCommand = _default_spawn_command,
    resolve_executable: ResolveExecutable = _default_resolve_executable,
) -> AdapterSet:
    desktop_dir.mkdir(parents=True, exist_ok=True)
    return AdapterSet(
        apps=LinuxAppsAdapter(
            run_command=run_command,
            spawn_command=spawn_command,
            resolve_executable=resolve_executable,
        ),
        windows=LinuxWindowsAdapter(run_command=run_command),
        time=SystemTimeAdapter(),
        power=LinuxPowerAdapter(
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
        audio=LinuxAudioAdapter(
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
        clipboard=LinuxClipboardAdapter(
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
        text_input=LinuxTextInputAdapter(
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
        network=LinuxNetworkAdapter(run_command=run_command),
        notifications=LinuxNotificationsAdapter(
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
        files=LinuxFilesAdapter(
            desktop_dir=desktop_dir,
            run_command=run_command,
            resolve_executable=resolve_executable,
        ),
    )


def _parse_wpctl_volume(raw_output: str) -> int:
    for token in raw_output.split():
        try:
            return round(float(token) * 100)
        except ValueError:
            continue
    raise ValueError("unable to parse wpctl volume output")


def _parse_percent_token(raw_output: str) -> int:
    for token in raw_output.replace("/", " ").split():
        if token.endswith("%"):
            try:
                return int(token.removesuffix("%"))
            except ValueError:
                continue
    raise ValueError("unable to parse percentage output")


def _parse_first_object_path(raw_output: str) -> str | None:
    for token in raw_output.replace("(", " ").replace(")", " ").replace(",", " ").split():
        candidate = token.strip("'[]")
        if candidate.startswith("/"):
            return candidate
    return None


def _parse_dbus_float(raw_output: str) -> int:
    normalized = raw_output.replace("(", " ").replace(")", " ").replace("<", " ").replace(">", " ").replace(",", " ")
    for token in normalized.split():
        try:
            return round(float(token))
        except ValueError:
            continue
    raise ValueError("unable to parse D-Bus numeric output")


def _parse_first_int(raw_output: str) -> int:
    match = re.search(r"-?\d+", raw_output)
    if match is None:
        raise ValueError("unable to parse integer output")
    return int(match.group(0))


def _parse_window_info_map(raw_output: str) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    for key in ("caption", "desktopFile", "resourceClass", "resourceName"):
        match = re.search(rf"'{key}': <'([^']*)'>", raw_output)
        if match is not None:
            fields[key] = match.group(1)
    return fields or None


def _window_info_matches_app(window_info: dict[str, str] | None, app: str) -> bool:
    if window_info is None:
        return False

    targets = _app_match_targets(app)
    for value in window_info.values():
        candidate = value.casefold()
        for target in targets:
            if target in candidate:
                return True
    return False


def _app_match_targets(app: str) -> tuple[str, ...]:
    target = app.casefold()
    if target == "terminal":
        return ("terminal", "konsole", "kgx", "gnome-terminal", "ptyxis", "xterm")
    return (target,)


def _parse_windows_runner_matches(raw_output: str) -> list[WindowsRunnerMatch]:
    normalized = re.sub(r"@a\([^)]+\)\s*", "", raw_output).replace("<", "").replace(">", "")
    parsed = ast.literal_eval(normalized)
    if not isinstance(parsed, tuple) or not parsed:
        raise ValueError("unable to parse windows runner output")

    matches = parsed[0]
    if not isinstance(matches, list):
        raise ValueError("windows runner output did not contain a match list")

    parsed_matches: list[WindowsRunnerMatch] = []
    for match in matches:
        if not isinstance(match, tuple) or len(match) != 6:
            continue
        match_id, title, icon, category_relevance, score, metadata = match
        if not isinstance(match_id, str) or not isinstance(title, str) or not isinstance(icon, str):
            continue
        if not isinstance(category_relevance, int) or not isinstance(score, float):
            continue
        subtext = ""
        if isinstance(metadata, dict):
            raw_subtext = metadata.get("subtext", "")
            if isinstance(raw_subtext, str):
                subtext = raw_subtext
        parsed_matches.append(
            WindowsRunnerMatch(
                match_id=match_id,
                title=title,
                icon=icon,
                category_relevance=category_relevance,
                score=score,
                subtext=subtext,
            )
        )
    return parsed_matches


def _dedupe_window_matches(matches: list[WindowsRunnerMatch]) -> list[WindowsRunnerMatch]:
    seen: set[str] = set()
    deduped: list[WindowsRunnerMatch] = []
    for match in matches:
        if match.match_id in seen:
            continue
        seen.add(match.match_id)
        deduped.append(match)
    return deduped


def _match_id_to_window_uuid(match_id: str) -> str:
    separator = match_id.find("_")
    if separator == -1:
        raise ValueError(f"unexpected windows runner match id: {match_id!r}")
    return match_id[separator + 1 :]
