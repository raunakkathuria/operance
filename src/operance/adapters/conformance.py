"""Adapter capability contracts and conformance checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .base import AdapterSet
from ..models.actions import ToolName


@dataclass(slots=True, frozen=True)
class AdapterToolContract:
    tool: ToolName
    adapter: str
    required_methods: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "tool": self.tool.value,
            "adapter": self.adapter,
            "required_methods": list(self.required_methods),
        }


@dataclass(slots=True, frozen=True)
class AdapterConformanceCheck:
    tool: ToolName
    adapter: str
    required_methods: tuple[str, ...]
    status: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tool": self.tool.value,
            "adapter": self.adapter,
            "required_methods": list(self.required_methods),
            "status": self.status,
            "message": self.message,
        }


@dataclass(slots=True, frozen=True)
class AdapterConformanceReport:
    status: str
    checks: tuple[AdapterConformanceCheck, ...]

    def to_dict(self) -> dict[str, object]:
        failed_count = sum(1 for check in self.checks if check.status != "ok")
        return {
            "status": self.status,
            "summary": {
                "checked_tools": len(self.checks),
                "failed_tools": failed_count,
            },
            "checks": [check.to_dict() for check in self.checks],
        }


ADAPTER_TOOL_CONTRACTS: dict[ToolName, AdapterToolContract] = {
    ToolName.APPS_LAUNCH: AdapterToolContract(ToolName.APPS_LAUNCH, "apps", ("launch",)),
    ToolName.APPS_FOCUS: AdapterToolContract(ToolName.APPS_FOCUS, "apps", ("focus",)),
    ToolName.APPS_QUIT: AdapterToolContract(ToolName.APPS_QUIT, "apps", ("quit",)),
    ToolName.WINDOWS_LIST: AdapterToolContract(ToolName.WINDOWS_LIST, "windows", ("list_windows",)),
    ToolName.WINDOWS_SWITCH: AdapterToolContract(ToolName.WINDOWS_SWITCH, "windows", ("switch",)),
    ToolName.WINDOWS_MINIMIZE: AdapterToolContract(ToolName.WINDOWS_MINIMIZE, "windows", ("minimize",)),
    ToolName.WINDOWS_MAXIMIZE: AdapterToolContract(ToolName.WINDOWS_MAXIMIZE, "windows", ("maximize",)),
    ToolName.WINDOWS_SET_FULLSCREEN: AdapterToolContract(
        ToolName.WINDOWS_SET_FULLSCREEN,
        "windows",
        ("set_fullscreen",),
    ),
    ToolName.WINDOWS_SET_KEEP_ABOVE: AdapterToolContract(
        ToolName.WINDOWS_SET_KEEP_ABOVE,
        "windows",
        ("set_keep_above",),
    ),
    ToolName.WINDOWS_SET_SHADED: AdapterToolContract(ToolName.WINDOWS_SET_SHADED, "windows", ("set_shaded",)),
    ToolName.WINDOWS_SET_KEEP_BELOW: AdapterToolContract(
        ToolName.WINDOWS_SET_KEEP_BELOW,
        "windows",
        ("set_keep_below",),
    ),
    ToolName.WINDOWS_SET_ON_ALL_DESKTOPS: AdapterToolContract(
        ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
        "windows",
        ("set_on_all_desktops",),
    ),
    ToolName.WINDOWS_RESTORE: AdapterToolContract(ToolName.WINDOWS_RESTORE, "windows", ("restore",)),
    ToolName.WINDOWS_CLOSE: AdapterToolContract(ToolName.WINDOWS_CLOSE, "windows", ("close",)),
    ToolName.TIME_NOW: AdapterToolContract(ToolName.TIME_NOW, "time", ("now",)),
    ToolName.POWER_BATTERY_STATUS: AdapterToolContract(
        ToolName.POWER_BATTERY_STATUS,
        "power",
        ("battery_status",),
    ),
    ToolName.AUDIO_GET_VOLUME: AdapterToolContract(ToolName.AUDIO_GET_VOLUME, "audio", ("get_volume",)),
    ToolName.AUDIO_MUTE_STATUS: AdapterToolContract(ToolName.AUDIO_MUTE_STATUS, "audio", ("is_muted",)),
    ToolName.AUDIO_SET_VOLUME: AdapterToolContract(ToolName.AUDIO_SET_VOLUME, "audio", ("set_volume",)),
    ToolName.AUDIO_SET_MUTED: AdapterToolContract(ToolName.AUDIO_SET_MUTED, "audio", ("set_muted",)),
    ToolName.CLIPBOARD_GET_TEXT: AdapterToolContract(ToolName.CLIPBOARD_GET_TEXT, "clipboard", ("get_text",)),
    ToolName.CLIPBOARD_SET_TEXT: AdapterToolContract(ToolName.CLIPBOARD_SET_TEXT, "clipboard", ("set_text",)),
    ToolName.CLIPBOARD_CLEAR: AdapterToolContract(ToolName.CLIPBOARD_CLEAR, "clipboard", ("clear",)),
    ToolName.CLIPBOARD_COPY_SELECTION: AdapterToolContract(
        ToolName.CLIPBOARD_COPY_SELECTION,
        "text_input",
        ("copy_selection",),
    ),
    ToolName.CLIPBOARD_PASTE: AdapterToolContract(ToolName.CLIPBOARD_PASTE, "text_input", ("paste",)),
    ToolName.TEXT_TYPE: AdapterToolContract(ToolName.TEXT_TYPE, "text_input", ("type_text",)),
    ToolName.KEYS_PRESS: AdapterToolContract(ToolName.KEYS_PRESS, "text_input", ("press_key",)),
    ToolName.NETWORK_WIFI_STATUS: AdapterToolContract(ToolName.NETWORK_WIFI_STATUS, "network", ("wifi_status",)),
    ToolName.NETWORK_DISCONNECT_CURRENT: AdapterToolContract(
        ToolName.NETWORK_DISCONNECT_CURRENT,
        "network",
        ("disconnect_current",),
    ),
    ToolName.NETWORK_SET_WIFI_ENABLED: AdapterToolContract(
        ToolName.NETWORK_SET_WIFI_ENABLED,
        "network",
        ("set_wifi_enabled",),
    ),
    ToolName.NETWORK_CONNECT_KNOWN_SSID: AdapterToolContract(
        ToolName.NETWORK_CONNECT_KNOWN_SSID,
        "network",
        ("connect_known_ssid",),
    ),
    ToolName.NOTIFICATIONS_SHOW: AdapterToolContract(ToolName.NOTIFICATIONS_SHOW, "notifications", ("show",)),
    ToolName.FILES_LIST_RECENT: AdapterToolContract(ToolName.FILES_LIST_RECENT, "files", ("list_recent",)),
    ToolName.FILES_OPEN: AdapterToolContract(ToolName.FILES_OPEN, "files", ("open_path",)),
    ToolName.FILES_CREATE_FOLDER: AdapterToolContract(ToolName.FILES_CREATE_FOLDER, "files", ("create_folder",)),
    ToolName.FILES_DELETE_FOLDER: AdapterToolContract(ToolName.FILES_DELETE_FOLDER, "files", ("remove_folder",)),
    ToolName.FILES_DELETE_FILE: AdapterToolContract(ToolName.FILES_DELETE_FILE, "files", ("remove_file",)),
    ToolName.FILES_RENAME: AdapterToolContract(ToolName.FILES_RENAME, "files", ("rename_path",)),
    ToolName.FILES_MOVE: AdapterToolContract(ToolName.FILES_MOVE, "files", ("move_path",)),
}


def validate_adapter_set(
    adapters: AdapterSet,
    *,
    tools: Iterable[ToolName] | None = None,
) -> AdapterConformanceReport:
    selected_tools = tuple(sorted(tools or ADAPTER_TOOL_CONTRACTS, key=lambda tool: tool.value))
    checks = tuple(_validate_tool_contract(adapters, ADAPTER_TOOL_CONTRACTS[tool]) for tool in selected_tools)
    status = "ok" if all(check.status == "ok" for check in checks) else "failed"
    return AdapterConformanceReport(status=status, checks=checks)


def adapter_capability_matrix() -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {}
    for contract in ADAPTER_TOOL_CONTRACTS.values():
        matrix.setdefault(contract.adapter, []).append(contract.tool.value)
    return {adapter: sorted(tools) for adapter, tools in sorted(matrix.items())}


def _validate_tool_contract(
    adapters: AdapterSet,
    contract: AdapterToolContract,
) -> AdapterConformanceCheck:
    adapter = getattr(adapters, contract.adapter)
    if adapter is None:
        return AdapterConformanceCheck(
            tool=contract.tool,
            adapter=contract.adapter,
            required_methods=contract.required_methods,
            status="failed",
            message=f"missing adapter: {contract.adapter}",
        )

    missing_methods = [
        method_name
        for method_name in contract.required_methods
        if not callable(getattr(adapter, method_name, None))
    ]
    if missing_methods:
        return AdapterConformanceCheck(
            tool=contract.tool,
            adapter=contract.adapter,
            required_methods=contract.required_methods,
            status="failed",
            message="missing methods: " + ", ".join(missing_methods),
        )

    return AdapterConformanceCheck(
        tool=contract.tool,
        adapter=contract.adapter,
        required_methods=contract.required_methods,
        status="ok",
        message="adapter contract satisfied",
    )
