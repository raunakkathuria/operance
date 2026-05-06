"""Mock adapters for deterministic developer-mode execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil

from .base import AdapterSet
from ..key_presses import normalize_supported_key, supported_key_display_name
from ..launch_targets import is_url_like_target, normalize_launch_target


@dataclass(slots=True)
class MockAppsAdapter:
    launched_apps: list[str] = field(default_factory=list)

    def launch(self, app: str) -> str:
        self.launched_apps.append(app)
        if is_url_like_target(app):
            return f"Opened {normalize_launch_target(app)}"
        return f"Launched {app}"

    def focus(self, app: str) -> str:
        return f"Focused {app}"

    def quit(self, app: str) -> str:
        return f"Quit {app}"


@dataclass(slots=True)
class MockWindowsAdapter:
    windows: list[str] = field(default_factory=lambda: ["Firefox", "Terminal"])

    def list_windows(self) -> list[str]:
        return list(self.windows)

    def switch(self, window: str) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Switched to window {title}"
        raise ValueError(f"no window matched {window!r}")

    def minimize(self, window: str) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Minimized window {title}"
        raise ValueError(f"no window matched {window!r}")

    def maximize(self, window: str) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Maximized window {title}"
        raise ValueError(f"no window matched {window!r}")

    def set_fullscreen(self, window: str, enabled: bool) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return (
                    f"Enabled fullscreen for window {title}"
                    if enabled
                    else f"Disabled fullscreen for window {title}"
                )
        raise ValueError(f"no window matched {window!r}")

    def set_keep_above(self, window: str, enabled: bool) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return (
                    f"Enabled keep-above for window {title}"
                    if enabled
                    else f"Disabled keep-above for window {title}"
                )
        raise ValueError(f"no window matched {window!r}")

    def set_shaded(self, window: str, enabled: bool) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Shaded window {title}" if enabled else f"Unshaded window {title}"
        raise ValueError(f"no window matched {window!r}")

    def set_keep_below(self, window: str, enabled: bool) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return (
                    f"Enabled keep-below for window {title}"
                    if enabled
                    else f"Disabled keep-below for window {title}"
                )
        raise ValueError(f"no window matched {window!r}")

    def set_on_all_desktops(self, window: str, enabled: bool) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return (
                    f"Enabled all-desktops for window {title}"
                    if enabled
                    else f"Disabled all-desktops for window {title}"
                )
        raise ValueError(f"no window matched {window!r}")

    def restore(self, window: str) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Restored window {title}"
        raise ValueError(f"no window matched {window!r}")

    def close(self, window: str) -> str:
        target = window.casefold()
        for title in self.windows:
            if target in title.casefold():
                return f"Closed window {title}"
        raise ValueError(f"no window matched {window!r}")


@dataclass(slots=True)
class MockTimeAdapter:
    current_time: str = "09:41"

    def now(self) -> str:
        return f"It is {self.current_time}"


@dataclass(slots=True)
class MockPowerAdapter:
    battery_percent: int = 87

    def battery_status(self) -> str:
        return f"Battery is {self.battery_percent}%"


@dataclass(slots=True)
class MockAudioAdapter:
    volume: int = 30
    muted: bool = False

    def get_volume(self) -> int:
        return self.volume

    def set_volume(self, percent: int) -> str:
        self.volume = percent
        return f"Volume set to {percent}%"

    def set_muted(self, muted: bool) -> str:
        self.muted = muted
        return "Audio muted" if muted else "Audio unmuted"

    def is_muted(self) -> bool:
        return self.muted


@dataclass(slots=True)
class MockClipboardAdapter:
    text: str = "Initial clipboard text"

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> str:
        self.text = text
        return "Copied text to clipboard"

    def clear(self) -> str:
        self.text = ""
        return "Cleared clipboard"


@dataclass(slots=True)
class MockTextInputAdapter:
    clipboard: MockClipboardAdapter | None = None
    selected_text: str = "Selected mock text"
    copy_selection_count: int = 0
    paste_count: int = 0
    typed_texts: list[str] = field(default_factory=list)
    pressed_keys: list[str] = field(default_factory=list)

    def copy_selection(self) -> str:
        self.copy_selection_count += 1
        if self.clipboard is not None:
            self.clipboard.text = self.selected_text
        return "Copied selection to clipboard"

    def paste(self) -> str:
        self.paste_count += 1
        return "Pasted clipboard into active window"

    def type_text(self, text: str) -> str:
        self.typed_texts.append(text)
        return "Typed text into active window"

    def press_key(self, key: str) -> str:
        normalized = normalize_supported_key(key)
        display_name = supported_key_display_name(key)
        if normalized is None or display_name is None:
            raise ValueError(f"unsupported key for mock text input: {key}")
        self.pressed_keys.append(normalized)
        if "+" in normalized:
            return f"Pressed {display_name} shortcut"
        return f"Pressed {display_name} key"


@dataclass(slots=True)
class MockNetworkAdapter:
    wifi_enabled: bool = True
    known_ssids: list[str] = field(default_factory=lambda: ["home", "office"])
    connected_ssid: str | None = None

    def set_wifi_enabled(self, enabled: bool) -> str:
        self.wifi_enabled = enabled
        if not enabled:
            self.connected_ssid = None
        return "Wi-Fi turned on" if enabled else "Wi-Fi turned off"

    def wifi_status(self) -> str:
        return "Wi-Fi is on" if self.wifi_enabled else "Wi-Fi is off"

    def is_wifi_enabled(self) -> bool:
        return self.wifi_enabled

    def disconnect_current(self) -> str:
        if self.connected_ssid is None:
            raise ValueError("no active Wi-Fi connection")
        ssid = self.connected_ssid
        self.connected_ssid = None
        return f"Disconnected Wi-Fi {ssid}"

    def connect_known_ssid(self, ssid: str) -> str:
        for known_ssid in self.known_ssids:
            if known_ssid.casefold() == ssid.casefold():
                self.wifi_enabled = True
                self.connected_ssid = known_ssid
                return f"Connected to Wi-Fi {known_ssid}"
        raise ValueError(f"known Wi-Fi network not found: {ssid}")


@dataclass(slots=True)
class MockNotificationsAdapter:
    shown_notifications: list[tuple[str, str]] = field(default_factory=list)

    def show(self, title: str, message: str) -> str:
        self.shown_notifications.append((title, message))
        return "Notification shown"


@dataclass(slots=True)
class MockFilesAdapter:
    desktop_dir: Path
    recent_files: list[Path] = field(default_factory=list)

    def list_recent(self, root: Path | None = None) -> list[Path]:
        return list(self.recent_files)

    def open_path(self, path: Path) -> str:
        if not path.exists():
            raise ValueError(f"desktop entry not found: {path.name}")
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


def build_mock_adapter_set(
    *,
    desktop_dir: Path,
    recent_files: list[str] | None = None,
) -> AdapterSet:
    desktop_dir.mkdir(parents=True, exist_ok=True)
    mock_recent_files = [desktop_dir / name for name in (recent_files or ["notes.txt", "todo.md"])]
    for path in mock_recent_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    clipboard = MockClipboardAdapter()

    return AdapterSet(
        apps=MockAppsAdapter(),
        windows=MockWindowsAdapter(),
        time=MockTimeAdapter(),
        power=MockPowerAdapter(),
        audio=MockAudioAdapter(),
        clipboard=clipboard,
        text_input=MockTextInputAdapter(clipboard=clipboard),
        network=MockNetworkAdapter(),
        notifications=MockNotificationsAdapter(),
        files=MockFilesAdapter(desktop_dir=desktop_dir, recent_files=mock_recent_files),
    )
