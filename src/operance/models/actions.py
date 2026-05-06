"""Typed action contracts for deterministic Phase 0A commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any

from .base import SerializableModel, new_id


class PlanSource(StrEnum):
    DETERMINISTIC = "deterministic"
    PLANNER = "planner"


class RiskTier(IntEnum):
    TIER_0 = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4


class ToolName(StrEnum):
    APPS_LAUNCH = "apps.launch"
    APPS_FOCUS = "apps.focus"
    APPS_QUIT = "apps.quit"
    WINDOWS_LIST = "windows.list"
    WINDOWS_SWITCH = "windows.switch"
    WINDOWS_MINIMIZE = "windows.minimize"
    WINDOWS_MAXIMIZE = "windows.maximize"
    WINDOWS_SET_FULLSCREEN = "windows.set_fullscreen"
    WINDOWS_SET_KEEP_ABOVE = "windows.set_keep_above"
    WINDOWS_SET_SHADED = "windows.set_shaded"
    WINDOWS_SET_KEEP_BELOW = "windows.set_keep_below"
    WINDOWS_SET_ON_ALL_DESKTOPS = "windows.set_on_all_desktops"
    WINDOWS_RESTORE = "windows.restore"
    WINDOWS_CLOSE = "windows.close"
    TIME_NOW = "time.now"
    POWER_BATTERY_STATUS = "power.battery_status"
    AUDIO_GET_VOLUME = "audio.get_volume"
    AUDIO_MUTE_STATUS = "audio.mute_status"
    AUDIO_SET_VOLUME = "audio.set_volume"
    AUDIO_SET_MUTED = "audio.set_muted"
    CLIPBOARD_GET_TEXT = "clipboard.get_text"
    CLIPBOARD_SET_TEXT = "clipboard.set_text"
    CLIPBOARD_COPY_SELECTION = "clipboard.copy_selection"
    CLIPBOARD_CLEAR = "clipboard.clear"
    CLIPBOARD_PASTE = "clipboard.paste"
    TEXT_TYPE = "text.type"
    KEYS_PRESS = "keys.press"
    NETWORK_WIFI_STATUS = "network.wifi_status"
    NETWORK_DISCONNECT_CURRENT = "network.disconnect_current"
    NETWORK_SET_WIFI_ENABLED = "network.set_wifi_enabled"
    NETWORK_CONNECT_KNOWN_SSID = "network.connect_known_ssid"
    NOTIFICATIONS_SHOW = "notifications.show"
    FILES_LIST_RECENT = "files.list_recent"
    FILES_OPEN = "files.open"
    FILES_CREATE_FOLDER = "files.create_folder"
    FILES_DELETE_FOLDER = "files.delete_folder"
    FILES_DELETE_FILE = "files.delete_file"
    FILES_RENAME = "files.rename"
    FILES_MOVE = "files.move"


@dataclass(slots=True, frozen=True)
class TypedAction(SerializableModel):
    tool: ToolName
    args: dict[str, Any] = field(default_factory=dict)
    risk_tier: RiskTier = RiskTier.TIER_0
    requires_confirmation: bool = False
    undoable: bool = False


@dataclass(slots=True, frozen=True)
class ActionPlan(SerializableModel):
    source: PlanSource
    original_text: str
    actions: list[TypedAction]
    plan_id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if not self.actions:
            raise ValueError("action plan must contain at least one action")
        if self.source == PlanSource.PLANNER and len(self.actions) > 2:
            raise ValueError("planner action plans may contain at most 2 actions")


@dataclass(slots=True, frozen=True)
class ActionResultItem(SerializableModel):
    tool: ToolName
    status: str
    message: str
    undo_token: str | None = None


@dataclass(slots=True, frozen=True)
class ActionResult(SerializableModel):
    plan_id: str
    status: str
    results: list[ActionResultItem]
