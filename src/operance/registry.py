"""Typed tool registry for the current desktop action surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .key_presses import normalize_supported_key, supported_key_error
from .models.actions import RiskTier, ToolName


ValidatorFn = Callable[[dict[str, object]], list[str]]


@dataclass(slots=True, frozen=True)
class ToolSpec:
    name: ToolName
    description: str
    required_args: tuple[str, ...] = ()
    input_schema: dict[str, object] = field(default_factory=lambda: _object_schema({}))
    result_schema: dict[str, object] = field(default_factory=dict)
    example_transcripts: tuple[str, ...] = ()
    risk_tier: RiskTier = RiskTier.TIER_0
    requires_confirmation: bool = False
    undoable: bool = False
    allowed_side_effects: tuple[str, ...] = ()
    undo_summary: str | None = None
    validate_args: ValidatorFn | None = None

    def __post_init__(self) -> None:
        if not self.result_schema:
            object.__setattr__(self, "result_schema", _tool_result_schema(self.name.value))
        if self.undo_summary is None and (
            self.undoable or self.risk_tier != RiskTier.TIER_0 or self.requires_confirmation
        ):
            object.__setattr__(
                self,
                "undo_summary",
                describe_undo_behavior(self.name, self.undoable),
            )


@dataclass(slots=True)
class ActionRegistry:
    _specs: dict[ToolName, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, tool: ToolName) -> ToolSpec | None:
        return self._specs.get(tool)

    def list_specs(self) -> list[ToolSpec]:
        return sorted(self._specs.values(), key=lambda spec: spec.name.value)


def build_default_action_registry() -> ActionRegistry:
    registry = ActionRegistry()

    registry.register(
        ToolSpec(
            ToolName.APPS_LAUNCH,
            "Launch an application or open a URL",
            ("app",),
            input_schema=_object_schema({"app": {"type": "string"}}, required=("app",)),
            example_transcripts=(
                "open firefox",
                "open http://localhost:3000",
                "browse to localhost 3000",
                "browse to docs.python.org/3",
            ),
            allowed_side_effects=("launch_app", "open_url"),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.APPS_FOCUS,
            "Focus an application window",
            ("app",),
            input_schema=_object_schema({"app": {"type": "string"}}, required=("app",)),
            example_transcripts=("focus firefox",),
            allowed_side_effects=("focus_app_window",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.APPS_QUIT,
            "Quit an application",
            ("app",),
            input_schema=_object_schema({"app": {"type": "string"}}, required=("app",)),
            example_transcripts=("quit firefox",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("quit_app", "close_app_windows"),
        )
    )
    registry.register(ToolSpec(ToolName.WINDOWS_LIST, "List open windows"))
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SWITCH,
            "Switch to an open window",
            ("window",),
            input_schema=_object_schema({"window": {"type": "string"}}, required=("window",)),
            example_transcripts=("switch to window firefox",),
            allowed_side_effects=("focus_window",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_MINIMIZE,
            "Minimize an open window",
            ("window",),
            input_schema=_object_schema({"window": {"type": "string"}}, required=("window",)),
            example_transcripts=("minimize window firefox",),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("minimize_window",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_MAXIMIZE,
            "Maximize an open window",
            ("window",),
            input_schema=_object_schema({"window": {"type": "string"}}, required=("window",)),
            example_transcripts=("maximize window firefox",),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("maximize_window",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SET_FULLSCREEN,
            "Enable or disable fullscreen for an open window",
            ("window", "enabled"),
            input_schema=_object_schema(
                {
                    "window": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                required=("window", "enabled"),
            ),
            example_transcripts=("fullscreen window firefox", "exit fullscreen for window firefox"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("set_window_fullscreen",),
            validate_args=_validate_window_boolean_state_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SET_KEEP_ABOVE,
            "Enable or disable keep-above for an open window",
            ("window", "enabled"),
            input_schema=_object_schema(
                {
                    "window": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                required=("window", "enabled"),
            ),
            example_transcripts=("keep window firefox above", "stop keeping window firefox above"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("set_window_keep_above",),
            validate_args=_validate_window_boolean_state_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SET_SHADED,
            "Enable or disable shade for an open window",
            ("window", "enabled"),
            input_schema=_object_schema(
                {
                    "window": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                required=("window", "enabled"),
            ),
            example_transcripts=("shade window firefox", "unshade window firefox"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("set_window_shaded",),
            validate_args=_validate_window_boolean_state_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SET_KEEP_BELOW,
            "Enable or disable keep-below for an open window",
            ("window", "enabled"),
            input_schema=_object_schema(
                {
                    "window": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                required=("window", "enabled"),
            ),
            example_transcripts=("keep window firefox below", "stop keeping window firefox below"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("set_window_keep_below",),
            validate_args=_validate_window_boolean_state_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
            "Show or hide an open window on all desktops",
            ("window", "enabled"),
            input_schema=_object_schema(
                {
                    "window": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                required=("window", "enabled"),
            ),
            example_transcripts=("show window firefox on all desktops", "show window firefox only on this desktop"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("set_window_on_all_desktops",),
            validate_args=_validate_window_boolean_state_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_RESTORE,
            "Restore an open window",
            ("window",),
            input_schema=_object_schema({"window": {"type": "string"}}, required=("window",)),
            example_transcripts=("restore window firefox",),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("restore_window",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.WINDOWS_CLOSE,
            "Close an open window",
            ("window",),
            input_schema=_object_schema({"window": {"type": "string"}}, required=("window",)),
            example_transcripts=("close window firefox",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("close_window",),
        )
    )
    registry.register(ToolSpec(ToolName.TIME_NOW, "Get the current time", example_transcripts=("what time is it",)))
    registry.register(
        ToolSpec(
            ToolName.POWER_BATTERY_STATUS,
            "Get battery status",
            example_transcripts=("what is my battery level",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.AUDIO_GET_VOLUME,
            "Get the current audio volume",
            example_transcripts=("what is the volume",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.AUDIO_MUTE_STATUS,
            "Get the current audio mute status",
            example_transcripts=("is audio muted",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.CLIPBOARD_GET_TEXT,
            "Read the current clipboard text",
            example_transcripts=("what is on the clipboard",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.CLIPBOARD_SET_TEXT,
            "Copy text to the clipboard",
            ("text",),
            input_schema=_object_schema({"text": {"type": "string"}}, required=("text",)),
            example_transcripts=("copy build complete to clipboard",),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("set_clipboard_text",),
            validate_args=_validate_clipboard_text,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.CLIPBOARD_COPY_SELECTION,
            "Copy the current selection to the clipboard",
            example_transcripts=("copy selection",),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("copy_selection_to_clipboard",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.CLIPBOARD_CLEAR,
            "Clear the current clipboard text",
            example_transcripts=("clear clipboard",),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("clear_clipboard",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.CLIPBOARD_PASTE,
            "Paste the current clipboard text into the active window",
            example_transcripts=("paste clipboard",),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("paste_clipboard_text",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.TEXT_TYPE,
            "Type text into the active window",
            ("text",),
            input_schema=_object_schema({"text": {"type": "string"}}, required=("text",)),
            example_transcripts=("type build complete",),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("type_text",),
            validate_args=_validate_clipboard_text,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.KEYS_PRESS,
            "Press a supported key in the active window",
            ("key",),
            input_schema=_object_schema({"key": {"type": "string"}}, required=("key",)),
            example_transcripts=("press enter", "press control c", "press control shift p"),
            risk_tier=RiskTier.TIER_1,
            allowed_side_effects=("press_key",),
            validate_args=_validate_supported_key_press,
        )
    )
    registry.register(ToolSpec(ToolName.NETWORK_WIFI_STATUS, "Get Wi-Fi status", example_transcripts=("wifi status",)))
    registry.register(
        ToolSpec(
            ToolName.NETWORK_DISCONNECT_CURRENT,
            "Disconnect the current Wi-Fi connection",
            example_transcripts=("disconnect wifi",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("disconnect_wifi",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.AUDIO_SET_VOLUME,
            "Set the audio volume",
            ("percent",),
            input_schema=_object_schema(
                {"percent": {"type": "integer", "minimum": 0, "maximum": 100}},
                required=("percent",),
            ),
            example_transcripts=("set volume to 50 percent",),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("set_audio_volume",),
            validate_args=_validate_percent,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.AUDIO_SET_MUTED,
            "Mute or unmute audio",
            ("muted",),
            input_schema=_object_schema({"muted": {"type": "boolean"}}, required=("muted",)),
            example_transcripts=("mute audio", "unmute audio"),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("set_audio_muted",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.NETWORK_SET_WIFI_ENABLED,
            "Toggle Wi-Fi",
            ("enabled",),
            input_schema=_object_schema({"enabled": {"type": "boolean"}}, required=("enabled",)),
            example_transcripts=("turn wifi on", "turn wi fi off"),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("toggle_wifi",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.NETWORK_CONNECT_KNOWN_SSID,
            "Connect to a saved Wi-Fi network",
            ("ssid",),
            input_schema=_object_schema({"ssid": {"type": "string"}}, required=("ssid",)),
            example_transcripts=("connect to wifi home",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("connect_saved_wifi",),
            validate_args=_validate_known_ssid,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.NOTIFICATIONS_SHOW,
            "Show a notification",
            ("title", "message"),
            input_schema=_object_schema(
                {
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                },
                required=("title", "message"),
            ),
            example_transcripts=("show a notification saying build complete",),
            allowed_side_effects=("show_notification",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_LIST_RECENT,
            "List recent files",
            ("modified_since",),
            input_schema=_object_schema(
                {"modified_since": {"type": "string"}},
                required=("modified_since",),
            ),
            example_transcripts=("show recent files",),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_OPEN,
            "Open a desktop entry or recent file",
            ("location", "name"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop", "recent"]},
                    "name": {"type": "string"},
                },
                required=("location", "name"),
            ),
            example_transcripts=("open file on desktop called notes.txt", "open recent file called notes.txt"),
            allowed_side_effects=("open_desktop_entry",),
            validate_args=_validate_file_open_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_CREATE_FOLDER,
            "Create a folder on the desktop",
            ("location", "name"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop"]},
                    "name": {"type": "string"},
                },
                required=("location", "name"),
            ),
            example_transcripts=("create folder on desktop called projects",),
            risk_tier=RiskTier.TIER_1,
            undoable=True,
            allowed_side_effects=("create_desktop_folder",),
            validate_args=lambda args: _validate_desktop_entry_args(args, name_fields=("name",)),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_DELETE_FOLDER,
            "Delete a folder on the desktop",
            ("location", "name"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop"]},
                    "name": {"type": "string"},
                },
                required=("location", "name"),
            ),
            example_transcripts=("delete folder on desktop called projects",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("delete_desktop_folder",),
            validate_args=lambda args: _validate_desktop_entry_args(args, name_fields=("name",)),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_DELETE_FILE,
            "Delete a file on the desktop",
            ("location", "name"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop"]},
                    "name": {"type": "string"},
                },
                required=("location", "name"),
            ),
            example_transcripts=("delete file on desktop called notes.txt",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            allowed_side_effects=("delete_desktop_file",),
            validate_args=lambda args: _validate_desktop_entry_args(args, name_fields=("name",)),
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_RENAME,
            "Rename a desktop entry",
            ("location", "source_name", "target_name"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop"]},
                    "source_name": {"type": "string"},
                    "target_name": {"type": "string"},
                },
                required=("location", "source_name", "target_name"),
            ),
            example_transcripts=("rename folder on desktop from projects to archive",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            undoable=True,
            allowed_side_effects=("rename_desktop_entry",),
            validate_args=_validate_file_rename_args,
        )
    )
    registry.register(
        ToolSpec(
            ToolName.FILES_MOVE,
            "Move a desktop entry into another desktop folder",
            ("location", "name", "destination_folder"),
            input_schema=_object_schema(
                {
                    "location": {"type": "string", "enum": ["desktop"]},
                    "name": {"type": "string"},
                    "destination_folder": {"type": "string"},
                },
                required=("location", "name", "destination_folder"),
            ),
            example_transcripts=("move folder on desktop called projects to archive",),
            risk_tier=RiskTier.TIER_2,
            requires_confirmation=True,
            undoable=True,
            allowed_side_effects=("move_desktop_entry",),
            validate_args=_validate_file_move_args,
        )
    )

    return registry


def derive_action_safety_metadata(
    tool: ToolName,
    args: dict[str, object],
    *,
    base_risk_tier: RiskTier,
    requires_confirmation: bool,
) -> tuple[RiskTier, bool]:
    risk_tier = base_risk_tier
    confirmation_required = requires_confirmation

    if tool == ToolName.AUDIO_SET_VOLUME:
        percent = args.get("percent")
        if isinstance(percent, int) and percent >= 90:
            risk_tier = max(risk_tier, RiskTier.TIER_2)
            confirmation_required = True

    if tool == ToolName.NETWORK_SET_WIFI_ENABLED and args.get("enabled") is False:
        risk_tier = max(risk_tier, RiskTier.TIER_2)
        confirmation_required = True

    return (risk_tier, confirmation_required)


def describe_undo_behavior(tool: ToolName, undoable: bool) -> str:
    if undoable:
        if tool == ToolName.AUDIO_SET_VOLUME:
            return "Undo will restore the previous volume."
        if tool == ToolName.CLIPBOARD_SET_TEXT:
            return "Undo will restore the previous clipboard text."
        if tool == ToolName.CLIPBOARD_COPY_SELECTION:
            return "Undo will restore the previous clipboard text."
        if tool == ToolName.CLIPBOARD_CLEAR:
            return "Undo will restore the previous clipboard text."
        if tool == ToolName.NETWORK_SET_WIFI_ENABLED:
            return "Undo will restore the previous Wi-Fi state."
        return "Undo will restore the previous state."

    if tool in {
        ToolName.WINDOWS_MINIMIZE,
        ToolName.WINDOWS_MAXIMIZE,
        ToolName.WINDOWS_SET_FULLSCREEN,
        ToolName.WINDOWS_SET_KEEP_ABOVE,
        ToolName.WINDOWS_SET_SHADED,
        ToolName.WINDOWS_SET_KEEP_BELOW,
        ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
        ToolName.WINDOWS_RESTORE,
    }:
        return "No automatic undo is available because the previous window state is not tracked safely."

    if tool in {ToolName.CLIPBOARD_PASTE, ToolName.TEXT_TYPE, ToolName.KEYS_PRESS}:
        return "No automatic undo is available because the target application state is not tracked safely."

    return "No automatic undo is available after execution."


def _validate_percent(args: dict[str, object]) -> list[str]:
    value = args.get("percent")
    if not isinstance(value, int):
        return ["percent must be an integer"]
    if not 0 <= value <= 100:
        return ["percent must be between 0 and 100"]
    return []


def _validate_clipboard_text(args: dict[str, object]) -> list[str]:
    value = args.get("text")
    if not isinstance(value, str) or not value.strip():
        return ["text must be a non-empty string"]
    return []


def _validate_supported_key_press(args: dict[str, object]) -> list[str]:
    value = args.get("key")
    if not isinstance(value, str):
        return [supported_key_error()]
    normalized = normalize_supported_key(value)
    if normalized is None:
        return [supported_key_error()]
    args["key"] = normalized
    return []


def _validate_window_boolean_state_args(args: dict[str, object]) -> list[str]:
    errors: list[str] = []
    window = args.get("window")
    enabled = args.get("enabled")

    if not isinstance(window, str) or not window.strip():
        errors.append("window must be a non-empty string")
    if not isinstance(enabled, bool):
        errors.append("enabled must be a boolean")
    return errors


def _validate_known_ssid(args: dict[str, object]) -> list[str]:
    value = args.get("ssid")
    if not isinstance(value, str) or not value.strip():
        return ["ssid must be a non-empty string"]
    if value != value.strip():
        return ["ssid must not include leading or trailing whitespace"]
    if any(character in value for character in ("\n", "\r", "\t")):
        return ["ssid must not include control whitespace"]
    return []


def _validate_desktop_entry_args(
    args: dict[str, object],
    *,
    name_fields: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []

    if args.get("location") != "desktop":
        errors.append("location must be 'desktop'")

    for field_name in name_fields:
        value = args.get(field_name)
        if not isinstance(value, str) or not _is_simple_desktop_entry_name(value):
            errors.append(f"{field_name} must be a simple desktop entry name")

    return errors


def _validate_file_open_args(args: dict[str, object]) -> list[str]:
    errors: list[str] = []

    if args.get("location") not in {"desktop", "recent"}:
        errors.append("location must be 'desktop' or 'recent'")

    value = args.get("name")
    if not isinstance(value, str) or not _is_simple_desktop_entry_name(value):
        errors.append("name must be a simple desktop entry name")

    return errors


def _validate_file_rename_args(args: dict[str, object]) -> list[str]:
    errors = _validate_desktop_entry_args(
        args,
        name_fields=("source_name", "target_name"),
    )
    if not errors and args["source_name"] == args["target_name"]:
        errors.append("target_name must differ from source_name")
    return errors


def _validate_file_move_args(args: dict[str, object]) -> list[str]:
    errors = _validate_desktop_entry_args(
        args,
        name_fields=("name", "destination_folder"),
    )
    if not errors and args["name"] == args["destination_folder"]:
        errors.append("destination_folder must differ from name")
    return errors


def _is_simple_desktop_entry_name(value: str) -> bool:
    stripped = value.strip()
    if not stripped or stripped != value:
        return False
    if stripped in {".", ".."}:
        return False
    return "/" not in stripped and "\\" not in stripped


def _object_schema(
    properties: dict[str, object],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _tool_result_schema(tool_name: str, *, const_tool: bool = True) -> dict[str, object]:
    tool_property: dict[str, object] = {"type": "string"}
    if const_tool:
        tool_property["const"] = tool_name
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
            "tool": tool_property,
        },
        "required": ["status", "message", "tool"],
        "additionalProperties": True,
    }
