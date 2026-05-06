"""Typed action execution against configured adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from .adapters.base import AdapterSet
from .models.actions import ActionPlan, ActionResult, ActionResultItem, ToolName
from .undo import UndoManager


@dataclass(slots=True)
class ActionExecutor:
    adapters: AdapterSet
    undo_manager: UndoManager = field(default_factory=UndoManager)

    def execute(self, plan: ActionPlan) -> ActionResult:
        results = [self._execute_action(action.tool, action.args) for action in plan.actions]
        overall_status = "success" if all(result.status == "success" for result in results) else "failed"
        return ActionResult(plan_id=plan.plan_id, status=overall_status, results=results)

    def undo(self, token: str) -> str:
        return self.undo_manager.undo(token)

    def _execute_action(self, tool: ToolName, args: dict[str, object]) -> ActionResultItem:
        if tool == ToolName.APPS_LAUNCH:
            adapter = self._require_adapter(self.adapters.apps, tool)
            try:
                message = adapter.launch(str(args["app"]))
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.APPS_FOCUS:
            adapter = self._require_adapter(self.adapters.apps, tool)
            try:
                message = adapter.focus(str(args["app"]))
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.APPS_QUIT:
            adapter = self._require_adapter(self.adapters.apps, tool)
            try:
                message = adapter.quit(str(args["app"]))
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_LIST:
            adapter = self._require_adapter(self.adapters.windows, tool)
            windows = adapter.list_windows()
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Open windows: {'; '.join(windows)}",
            )

        if tool == ToolName.WINDOWS_SWITCH:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.switch(str(args["window"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_MINIMIZE:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.minimize(str(args["window"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_MAXIMIZE:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.maximize(str(args["window"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_SET_FULLSCREEN:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.set_fullscreen(str(args["window"]), bool(args["enabled"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_SET_KEEP_ABOVE:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.set_keep_above(str(args["window"]), bool(args["enabled"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_SET_SHADED:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.set_shaded(str(args["window"]), bool(args["enabled"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_SET_KEEP_BELOW:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.set_keep_below(str(args["window"]), bool(args["enabled"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_SET_ON_ALL_DESKTOPS:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.set_on_all_desktops(str(args["window"]), bool(args["enabled"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_RESTORE:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.restore(str(args["window"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.WINDOWS_CLOSE:
            adapter = self._require_adapter(self.adapters.windows, tool)
            message = adapter.close(str(args["window"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.TIME_NOW:
            adapter = self._require_adapter(self.adapters.time, tool)
            return ActionResultItem(tool=tool, status="success", message=adapter.now())

        if tool == ToolName.POWER_BATTERY_STATUS:
            adapter = self._require_adapter(self.adapters.power, tool)
            return ActionResultItem(tool=tool, status="success", message=adapter.battery_status())

        if tool == ToolName.AUDIO_GET_VOLUME:
            adapter = self._require_adapter(self.adapters.audio, tool)
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Volume is {adapter.get_volume()}%",
            )

        if tool == ToolName.AUDIO_MUTE_STATUS:
            adapter = self._require_adapter(self.adapters.audio, tool)
            return ActionResultItem(
                tool=tool,
                status="success",
                message="Audio is muted" if adapter.is_muted() else "Audio is unmuted",
            )

        if tool == ToolName.CLIPBOARD_GET_TEXT:
            adapter = self._require_adapter(self.adapters.clipboard, tool)
            text = adapter.get_text()
            message = f"Clipboard contains: {text}" if text else "Clipboard is empty"
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.CLIPBOARD_SET_TEXT:
            adapter = self._require_adapter(self.adapters.clipboard, tool)
            previous_text = adapter.get_text()
            message = adapter.set_text(str(args["text"]))
            undo_token = self.undo_manager.register(
                lambda: _undo_clipboard_text(adapter, previous_text)
            )
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.CLIPBOARD_COPY_SELECTION:
            clipboard = self._require_adapter(self.adapters.clipboard, tool)
            text_input = self._require_adapter(self.adapters.text_input, tool)
            try:
                previous_text = clipboard.get_text()
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            try:
                message = text_input.copy_selection()
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            undo_token = self.undo_manager.register(
                lambda: _undo_clipboard_text(clipboard, previous_text)
            )
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.CLIPBOARD_CLEAR:
            adapter = self._require_adapter(self.adapters.clipboard, tool)
            previous_text = adapter.get_text()
            message = adapter.clear()
            undo_token = self.undo_manager.register(
                lambda: _undo_clipboard_text(adapter, previous_text)
            )
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.CLIPBOARD_PASTE:
            clipboard = self._require_adapter(self.adapters.clipboard, tool)
            text_input = self._require_adapter(self.adapters.text_input, tool)
            try:
                clipboard_text = clipboard.get_text()
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            if not clipboard_text:
                return ActionResultItem(tool=tool, status="failed", message="Clipboard is empty")
            try:
                message = text_input.paste()
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.TEXT_TYPE:
            adapter = self._require_adapter(self.adapters.text_input, tool)
            try:
                message = adapter.type_text(str(args["text"]))
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.KEYS_PRESS:
            adapter = self._require_adapter(self.adapters.text_input, tool)
            try:
                message = adapter.press_key(str(args["key"]))
            except ValueError as exc:
                return ActionResultItem(tool=tool, status="failed", message=str(exc))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.AUDIO_SET_VOLUME:
            adapter = self._require_adapter(self.adapters.audio, tool)
            previous_volume = adapter.get_volume()
            message = adapter.set_volume(int(args["percent"]))
            undo_token = self.undo_manager.register(
                lambda: _undo_volume(adapter, previous_volume)
            )
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.AUDIO_SET_MUTED:
            adapter = self._require_adapter(self.adapters.audio, tool)
            previous_muted = adapter.is_muted()
            message = adapter.set_muted(bool(args["muted"]))
            undo_token = self.undo_manager.register(lambda: adapter.set_muted(previous_muted))
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.NETWORK_WIFI_STATUS:
            adapter = self._require_adapter(self.adapters.network, tool)
            return ActionResultItem(tool=tool, status="success", message=adapter.wifi_status())

        if tool == ToolName.NETWORK_DISCONNECT_CURRENT:
            adapter = self._require_adapter(self.adapters.network, tool)
            return ActionResultItem(tool=tool, status="success", message=adapter.disconnect_current())

        if tool == ToolName.NETWORK_SET_WIFI_ENABLED:
            adapter = self._require_adapter(self.adapters.network, tool)
            previous_enabled = adapter.is_wifi_enabled()
            message = adapter.set_wifi_enabled(bool(args["enabled"]))
            undo_token = self.undo_manager.register(lambda: adapter.set_wifi_enabled(previous_enabled))
            return ActionResultItem(tool=tool, status="success", message=message, undo_token=undo_token)

        if tool == ToolName.NETWORK_CONNECT_KNOWN_SSID:
            adapter = self._require_adapter(self.adapters.network, tool)
            message = adapter.connect_known_ssid(str(args["ssid"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.NOTIFICATIONS_SHOW:
            adapter = self._require_adapter(self.adapters.notifications, tool)
            message = adapter.show(str(args["title"]), str(args["message"]))
            return ActionResultItem(tool=tool, status="success", message=message)

        if tool == ToolName.FILES_LIST_RECENT:
            adapter = self._require_adapter(self.adapters.files, tool)
            files = adapter.list_recent()
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Found {len(files)} recent files",
            )

        if tool == ToolName.FILES_OPEN:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location == "desktop":
                entry_path = adapter.desktop_dir / str(args["name"])
                message = adapter.open_path(entry_path)
                return ActionResultItem(tool=tool, status="success", message=message)
            if location == "recent":
                target_name = str(args["name"]).casefold()
                for entry_path in adapter.list_recent():
                    if entry_path.name.casefold() == target_name:
                        adapter.open_path(entry_path)
                        return ActionResultItem(
                            tool=tool,
                            status="success",
                            message=f"Opened recent file {entry_path.name}",
                        )
                raise ValueError(f"recent file not found: {args['name']}")
            raise ValueError(f"unsupported folder location: {location}")

        if tool == ToolName.FILES_CREATE_FOLDER:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location != "desktop":
                raise ValueError(f"unsupported folder location: {location}")
            desktop_dir = adapter.desktop_dir
            folder = adapter.create_folder(desktop_dir, str(args["name"]))
            undo_token = self.undo_manager.register(
                lambda: _undo_created_folder(adapter, folder)
            )
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Created folder {folder.name} on desktop",
                undo_token=undo_token,
            )

        if tool == ToolName.FILES_DELETE_FOLDER:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location != "desktop":
                raise ValueError(f"unsupported folder location: {location}")
            desktop_dir = adapter.desktop_dir
            folder = desktop_dir / str(args["name"])
            if not folder.exists():
                raise ValueError(f"folder not found: {folder.name}")
            adapter.remove_folder(folder)
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Deleted folder {folder.name} from desktop",
            )

        if tool == ToolName.FILES_DELETE_FILE:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location != "desktop":
                raise ValueError(f"unsupported folder location: {location}")
            desktop_dir = adapter.desktop_dir
            file_path = desktop_dir / str(args["name"])
            if not file_path.exists() or not file_path.is_file():
                raise ValueError(f"desktop file not found: {file_path.name}")
            adapter.remove_file(file_path)
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Deleted file {file_path.name} from desktop",
            )

        if tool == ToolName.FILES_RENAME:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location != "desktop":
                raise ValueError(f"unsupported folder location: {location}")
            desktop_dir = adapter.desktop_dir
            source_path = desktop_dir / str(args["source_name"])
            if not source_path.exists():
                raise ValueError(f"desktop entry not found: {source_path.name}")
            renamed_path = adapter.rename_path(source_path, str(args["target_name"]))
            undo_token = self.undo_manager.register(
                lambda: _undo_renamed_entry(adapter, renamed_path, source_path.name)
            )
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Renamed desktop entry {source_path.name} to {renamed_path.name}",
                undo_token=undo_token,
            )

        if tool == ToolName.FILES_MOVE:
            adapter = self._require_adapter(self.adapters.files, tool)
            location = str(args["location"])
            if location != "desktop":
                raise ValueError(f"unsupported folder location: {location}")
            desktop_dir = adapter.desktop_dir
            source_path = desktop_dir / str(args["name"])
            if not source_path.exists():
                raise ValueError(f"desktop entry not found: {source_path.name}")
            destination_dir = desktop_dir / str(args["destination_folder"])
            if not destination_dir.exists() or not destination_dir.is_dir():
                raise ValueError(f"destination folder not found: {destination_dir.name}")
            moved_path = adapter.move_path(source_path, destination_dir)
            undo_token = self.undo_manager.register(
                lambda: _undo_moved_entry(adapter, moved_path, source_path.parent)
            )
            return ActionResultItem(
                tool=tool,
                status="success",
                message=f"Moved desktop entry {source_path.name} to {destination_dir.name}",
                undo_token=undo_token,
            )

        raise ValueError(f"unsupported tool: {tool.value}")

    @staticmethod
    def _require_adapter(adapter: object | None, tool: ToolName) -> object:
        if adapter is None:
            raise ValueError(f"missing adapter for {tool.value}")
        return adapter


def _undo_created_folder(adapter, folder) -> str:
    adapter.remove_folder(folder)
    return f"Removed folder {folder.name} from desktop"


def _undo_volume(adapter, previous_volume: int) -> str:
    adapter.set_volume(previous_volume)
    return f"Volume restored to {previous_volume}%"


def _undo_clipboard_text(adapter, previous_text: str) -> str:
    adapter.set_text(previous_text)
    return "Clipboard restored"


def _undo_renamed_entry(adapter, path, original_name: str) -> str:
    restored_path = adapter.rename_path(path, original_name)
    return f"Renamed desktop entry {path.name} to {restored_path.name}"


def _undo_moved_entry(adapter, path, destination_dir) -> str:
    restored_path = adapter.move_path(path, destination_dir)
    return f"Moved desktop entry {restored_path.name} to {destination_dir.name}"
