"""Linux KDE Wayland platform provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
from typing import Mapping

from ..adapters.base import AdapterSet
from ..adapters.linux import build_linux_adapter_set
from ..models.actions import ToolName
from ..project_info import project_version
from .base import (
    CheckMetadata,
    PlatformSetupAction,
    PlatformSetupBlockedRecommendation,
    PlatformSetupNextStep,
)


CURRENT_RELEASE_VERIFICATION_TARGET = "fedora_kde_wayland_developer_alpha"
CURRENT_RELEASE_VERIFIED_TOOLS = frozenset(
    {
        ToolName.APPS_FOCUS,
        ToolName.APPS_LAUNCH,
        ToolName.AUDIO_GET_VOLUME,
        ToolName.AUDIO_MUTE_STATUS,
        ToolName.NETWORK_WIFI_STATUS,
        ToolName.POWER_BATTERY_STATUS,
        ToolName.TIME_NOW,
    }
)

LINUX_CHECK_METADATA = (
    CheckMetadata("linux_platform", "Linux platform", required_for_local_runtime=True),
    CheckMetadata("kde_wayland_target", "KDE Wayland session", required_for_local_runtime=True),
    CheckMetadata("wayland_session_accessible", "Wayland session access"),
    CheckMetadata("xdg_open_available", "xdg-open", required_for_local_runtime=True),
    CheckMetadata("notify_send_available", "notify-send"),
    CheckMetadata("gdbus_available", "gdbus", required_for_local_runtime=True),
    CheckMetadata("networkmanager_cli_available", "NetworkManager CLI", required_for_local_runtime=True),
    CheckMetadata("audio_cli_available", "Audio control CLI", required_for_local_runtime=True),
    CheckMetadata("audio_capture_cli_available", "Audio capture CLI", required_for_local_runtime=True),
    CheckMetadata("audio_playback_cli_available", "Audio playback CLI"),
    CheckMetadata("clipboard_cli_available", "Wayland clipboard CLI"),
    CheckMetadata(
        "text_input_cli_available",
        "Wayland text input CLI",
        remediation_command="./scripts/install_wayland_input_tools.sh",
    ),
    CheckMetadata(
        "deb_packaging_cli_available",
        "Debian packaging CLI",
        remediation_command="./scripts/install_packaging_tools.sh --deb",
    ),
    CheckMetadata(
        "rpm_packaging_cli_available",
        "RPM packaging CLI",
        remediation_command="./scripts/install_packaging_tools.sh --rpm",
    ),
    CheckMetadata("archive_packaging_cli_available", "Archive CLI"),
    CheckMetadata("deb_package_installer_available", "Debian package installer"),
    CheckMetadata("rpm_package_installer_available", "RPM package installer"),
    CheckMetadata("systemctl_user_available", "systemctl --user", required_for_local_runtime=True),
    CheckMetadata(
        "tray_user_service_installed",
        "Tray user service installed",
        remediation_command="./scripts/install_local_linux_app.sh",
    ),
    CheckMetadata(
        "tray_user_service_enabled",
        "Tray user service enabled",
        remediation_command="./scripts/control_systemd_user_services.sh enable",
    ),
    CheckMetadata(
        "tray_user_service_active",
        "Tray user service active",
        remediation_command="./scripts/control_systemd_user_services.sh restart",
    ),
    CheckMetadata(
        "voice_loop_user_service_installed",
        "Voice-loop user service installed",
        remediation_command="./scripts/install_voice_loop_user_service.sh",
    ),
    CheckMetadata(
        "voice_loop_user_service_enabled",
        "Voice-loop user service enabled",
        remediation_command="./scripts/control_systemd_user_services.sh enable --voice-loop",
    ),
    CheckMetadata(
        "voice_loop_user_service_active",
        "Voice-loop user service active",
        remediation_command="./scripts/control_systemd_user_services.sh restart --voice-loop",
    ),
    CheckMetadata(
        "voice_loop_user_config_available",
        "Voice-loop user config",
        remediation_command="./scripts/install_voice_loop_user_config.sh",
    ),
    CheckMetadata(
        "voice_loop_runtime_status_available",
        "Voice-loop runtime status",
        remediation_command="python3 -m operance.cli --voice-loop-status",
    ),
    CheckMetadata(
        "voice_loop_runtime_heartbeat_fresh",
        "Voice-loop runtime heartbeat",
        remediation_command="python3 -m operance.cli --voice-loop-status",
    ),
    CheckMetadata(
        "voice_loop_wakeword_customized",
        "Voice-loop wake-word config",
        remediation_command="python3 -m operance.cli --voice-loop-config",
    ),
    CheckMetadata("power_status_available", "Power status surface", required_for_local_runtime=True),
)

_SETUP_CHECK_LABELS = {
    "python_3_12_plus": "Python 3.12+",
    "virtualenv_active": "Virtual environment",
    "tray_ui_available": "Tray UI backend",
    "wakeword_backend_available": "Wake-word backend",
    "wakeword_model_asset_available": "Wake-word model asset",
    "wakeword_model_source_available": "Wake-word model source",
    "stt_backend_available": "Speech-to-text backend",
    "tts_backend_available": "Text-to-speech backend",
    "tts_model_asset_available": "TTS model asset",
    "tts_model_source_available": "TTS model source",
    "tts_voices_asset_available": "TTS voices asset",
    "tts_voices_source_available": "TTS voices source",
    "planner_runtime_enabled": "Planner runtime enabled",
    "planner_endpoint_healthy": "Planner endpoint health",
}


@dataclass(slots=True, frozen=True)
class LinuxKdeWaylandPlatformProvider:
    provider_id: str = "linux_kde_wayland"
    display_name: str = "Linux KDE Wayland"
    check_metadata: tuple[CheckMetadata, ...] = LINUX_CHECK_METADATA
    release_verification_target: str = CURRENT_RELEASE_VERIFICATION_TARGET
    release_verified_tools: frozenset[ToolName] = CURRENT_RELEASE_VERIFIED_TOOLS

    def build_adapters(self, config) -> AdapterSet:
        return build_linux_adapter_set(desktop_dir=config.paths.desktop_dir)

    def build_environment_checks(self) -> list[dict[str, object]]:
        session_type = os.environ.get("XDG_SESSION_TYPE")
        desktop_session = os.environ.get("XDG_CURRENT_DESKTOP")
        systemctl_path = shutil.which("systemctl")
        tray_service_path = _tray_user_service_path()
        voice_loop_service_path = _voice_loop_user_service_path()
        voice_loop_config_path = _voice_loop_config_path()
        sysfs_battery_available = _has_battery_sysfs()
        tray_service_enabled_status, tray_service_enabled_detail = _probe_systemctl_user_service_state(
            "is-enabled",
            "operance-tray.service",
            systemctl_path=systemctl_path,
        )
        tray_service_active_status, tray_service_active_detail = _probe_systemctl_user_service_state(
            "is-active",
            "operance-tray.service",
            systemctl_path=systemctl_path,
        )
        voice_loop_service_enabled_status, voice_loop_service_enabled_detail = _probe_systemctl_user_service_state(
            "is-enabled",
            "operance-voice-loop.service",
            systemctl_path=systemctl_path,
        )
        voice_loop_service_active_status, voice_loop_service_active_detail = _probe_systemctl_user_service_state(
            "is-active",
            "operance-voice-loop.service",
            systemctl_path=systemctl_path,
        )
        wayland_session_access_status, wayland_session_access_detail = _probe_wayland_session_access()
        text_input_cli_status, text_input_cli_detail = _probe_text_input_backend(
            wayland_session_accessible=wayland_session_access_status == "ok"
        )
        voice_loop_config_snapshot = build_voice_loop_config_snapshot()
        voice_loop_runtime_status = build_voice_loop_runtime_status_snapshot()
        voice_loop_runtime_status_available_status, voice_loop_runtime_status_available_detail = (
            _voice_loop_runtime_status_available_check(
                voice_loop_runtime_status=voice_loop_runtime_status,
                voice_loop_service_active_status=voice_loop_service_active_status,
            )
        )
        voice_loop_runtime_heartbeat_status, voice_loop_runtime_heartbeat_detail = (
            _voice_loop_runtime_heartbeat_check(
                voice_loop_runtime_status=voice_loop_runtime_status,
                voice_loop_service_active_status=voice_loop_service_active_status,
            )
        )
        voice_loop_wakeword_customized = (
            voice_loop_config_snapshot.effective.wakeword_mode != "energy_fallback"
            or voice_loop_config_snapshot.effective.wakeword_threshold != 0.6
        )

        return [
            {
                "name": "linux_platform",
                "status": "ok",
                "detail": "Linux",
            },
            {
                "name": "kde_wayland_target",
                "status": (
                    "ok"
                    if session_type == "wayland"
                    and desktop_session is not None
                    and "KDE" in desktop_session.upper()
                    else "warn"
                ),
                "detail": {
                    "session_type": session_type,
                    "desktop_session": desktop_session,
                },
            },
            {
                "name": "wayland_session_accessible",
                "status": wayland_session_access_status,
                "detail": wayland_session_access_detail,
            },
            {
                "name": "xdg_open_available",
                "status": "ok" if shutil.which("xdg-open") else "warn",
                "detail": shutil.which("xdg-open") or "not found",
            },
            {
                "name": "notify_send_available",
                "status": "ok" if shutil.which("notify-send") else "warn",
                "detail": shutil.which("notify-send") or "not found",
            },
            {
                "name": "gdbus_available",
                "status": "ok" if shutil.which("gdbus") else "warn",
                "detail": shutil.which("gdbus") or "not found",
            },
            {
                "name": "networkmanager_cli_available",
                "status": "ok" if shutil.which("nmcli") else "warn",
                "detail": shutil.which("nmcli") or "not found",
            },
            {
                "name": "audio_cli_available",
                "status": "ok" if shutil.which("wpctl") or shutil.which("pactl") else "warn",
                "detail": {
                    "wpctl": shutil.which("wpctl"),
                    "pactl": shutil.which("pactl"),
                },
            },
            {
                "name": "audio_capture_cli_available",
                "status": "ok" if shutil.which("pw-record") or shutil.which("parecord") else "warn",
                "detail": {
                    "pw-record": shutil.which("pw-record"),
                    "parecord": shutil.which("parecord"),
                },
            },
            {
                "name": "audio_playback_cli_available",
                "status": "ok" if shutil.which("pw-play") or shutil.which("paplay") or shutil.which("aplay") else "warn",
                "detail": {
                    "pw-play": shutil.which("pw-play"),
                    "paplay": shutil.which("paplay"),
                    "aplay": shutil.which("aplay"),
                },
            },
            {
                "name": "clipboard_cli_available",
                "status": "ok" if shutil.which("wl-copy") and shutil.which("wl-paste") else "warn",
                "detail": {
                    "wl-copy": shutil.which("wl-copy"),
                    "wl-paste": shutil.which("wl-paste"),
                },
            },
            {
                "name": "text_input_cli_available",
                "status": text_input_cli_status,
                "detail": text_input_cli_detail,
            },
            {
                "name": "deb_packaging_cli_available",
                "status": "ok" if shutil.which("dpkg-deb") else "warn",
                "detail": shutil.which("dpkg-deb") or "not found",
            },
            {
                "name": "rpm_packaging_cli_available",
                "status": "ok" if shutil.which("rpmbuild") else "warn",
                "detail": shutil.which("rpmbuild") or "not found",
            },
            {
                "name": "archive_packaging_cli_available",
                "status": "ok" if shutil.which("tar") else "warn",
                "detail": shutil.which("tar") or "not found",
            },
            {
                "name": "deb_package_installer_available",
                "status": "ok" if shutil.which("apt") else "warn",
                "detail": shutil.which("apt") or "not found",
            },
            {
                "name": "rpm_package_installer_available",
                "status": "ok" if shutil.which("dnf") else "warn",
                "detail": shutil.which("dnf") or "not found",
            },
            {
                "name": "systemctl_user_available",
                "status": "ok" if systemctl_path else "warn",
                "detail": systemctl_path or "not found",
            },
            {
                "name": "tray_user_service_installed",
                "status": "ok" if tray_service_path.exists() else "warn",
                "detail": str(tray_service_path),
            },
            {
                "name": "tray_user_service_enabled",
                "status": tray_service_enabled_status,
                "detail": tray_service_enabled_detail,
            },
            {
                "name": "tray_user_service_active",
                "status": tray_service_active_status,
                "detail": tray_service_active_detail,
            },
            {
                "name": "voice_loop_user_service_installed",
                "status": "ok" if voice_loop_service_path.exists() else "warn",
                "detail": str(voice_loop_service_path),
            },
            {
                "name": "voice_loop_user_service_enabled",
                "status": voice_loop_service_enabled_status,
                "detail": voice_loop_service_enabled_detail,
            },
            {
                "name": "voice_loop_user_service_active",
                "status": voice_loop_service_active_status,
                "detail": voice_loop_service_active_detail,
            },
            {
                "name": "voice_loop_user_config_available",
                "status": "ok" if voice_loop_config_path.exists() else "warn",
                "detail": str(voice_loop_config_path),
            },
            {
                "name": "voice_loop_runtime_status_available",
                "status": voice_loop_runtime_status_available_status,
                "detail": voice_loop_runtime_status_available_detail,
            },
            {
                "name": "voice_loop_runtime_heartbeat_fresh",
                "status": voice_loop_runtime_heartbeat_status,
                "detail": voice_loop_runtime_heartbeat_detail,
            },
            {
                "name": "voice_loop_wakeword_customized",
                "status": "ok" if voice_loop_wakeword_customized else "warn",
                "detail": voice_loop_config_snapshot.to_dict(),
            },
            {
                "name": "power_status_available",
                "status": "ok" if shutil.which("upower") or sysfs_battery_available else "warn",
                "detail": {
                    "upower": shutil.which("upower"),
                    "sysfs_battery": sysfs_battery_available,
                },
            },
        ]

    def recommended_command_for_check(
        self,
        name: str,
        status: str,
        checks_by_name: Mapping[str, dict[str, object]],
        remediation_commands: Mapping[str, str],
    ) -> str | None:
        if status == "ok":
            return None
        if name == "virtualenv_active":
            return "./scripts/install_linux_dev.sh"
        if name in {"voice_loop_runtime_status_available", "voice_loop_runtime_heartbeat_fresh"}:
            voice_loop_service_installed = (
                str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) == "ok"
            )
            voice_loop_service_active = (
                str(checks_by_name.get("voice_loop_user_service_active", {}).get("status")) == "ok"
            )
            if voice_loop_service_installed and voice_loop_service_active:
                return "./scripts/control_systemd_user_services.sh restart --voice-loop"
            return "python3 -m operance.cli --voice-loop-status"
        if name == "voice_loop_wakeword_customized":
            if str(checks_by_name.get("voice_loop_user_config_available", {}).get("status")) == "ok":
                return (
                    "python3 -m operance.cli --wakeword-calibrate-frames 20 "
                    "--use-voice-loop-config --apply-suggested-threshold"
                )
            return "./scripts/install_voice_loop_user_config.sh"
        if name == "clipboard_cli_available":
            return _wayland_input_tools_command(checks_by_name) or remediation_commands.get(name)
        if name == "text_input_cli_available":
            if _text_input_needs_install(checks_by_name):
                return _wayland_input_tools_command(checks_by_name) or remediation_commands.get(name)
            return "python3 -m operance.cli --doctor"
        return remediation_commands.get(name)

    def build_setup_recommended_commands(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[str]:
        return _build_setup_recommended_commands(checks_by_name)

    def build_setup_blocked_recommendations(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[PlatformSetupBlockedRecommendation]:
        return _build_setup_blocked_recommendations(checks_by_name)

    def build_setup_next_steps(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        ready_for_local_runtime: bool,
    ) -> list[PlatformSetupNextStep]:
        return _build_setup_next_steps(
            checks_by_name,
            ready_for_local_runtime=ready_for_local_runtime,
        )

    def build_setup_actions(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        recommended_commands: tuple[str, ...],
    ) -> list[PlatformSetupAction]:
        return _build_setup_actions(
            checks_by_name,
            recommended_commands=recommended_commands,
        )

    def tool_live_runtime_blockers(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> list[str]:
        window_tools = {
            ToolName.WINDOWS_LIST,
            ToolName.WINDOWS_SWITCH,
            ToolName.WINDOWS_MINIMIZE,
            ToolName.WINDOWS_MAXIMIZE,
            ToolName.WINDOWS_SET_FULLSCREEN,
            ToolName.WINDOWS_SET_KEEP_ABOVE,
            ToolName.WINDOWS_SET_SHADED,
            ToolName.WINDOWS_SET_KEEP_BELOW,
            ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
            ToolName.WINDOWS_RESTORE,
            ToolName.WINDOWS_CLOSE,
        }
        audio_tools = {
            ToolName.AUDIO_GET_VOLUME,
            ToolName.AUDIO_MUTE_STATUS,
            ToolName.AUDIO_SET_VOLUME,
            ToolName.AUDIO_SET_MUTED,
        }
        network_tools = {
            ToolName.NETWORK_WIFI_STATUS,
            ToolName.NETWORK_DISCONNECT_CURRENT,
            ToolName.NETWORK_SET_WIFI_ENABLED,
            ToolName.NETWORK_CONNECT_KNOWN_SSID,
        }
        file_tools = {
            ToolName.FILES_LIST_RECENT,
            ToolName.FILES_OPEN,
            ToolName.FILES_CREATE_FOLDER,
            ToolName.FILES_DELETE_FOLDER,
            ToolName.FILES_DELETE_FILE,
            ToolName.FILES_RENAME,
            ToolName.FILES_MOVE,
        }

        if tool == ToolName.TIME_NOW:
            return []
        if tool == ToolName.APPS_LAUNCH:
            return _blockers_for(steps_by_name, "linux_platform", "xdg_open_available")
        if tool == ToolName.APPS_FOCUS or tool in window_tools:
            return _blockers_for(steps_by_name, "linux_platform", "kde_wayland_target", "gdbus_available")
        if tool == ToolName.POWER_BATTERY_STATUS:
            return _blockers_for(steps_by_name, "linux_platform", "power_status_available")
        if tool in audio_tools:
            return _blockers_for(steps_by_name, "linux_platform", "audio_cli_available")
        if tool in {ToolName.CLIPBOARD_GET_TEXT, ToolName.CLIPBOARD_SET_TEXT, ToolName.CLIPBOARD_CLEAR}:
            return _blockers_for(
                steps_by_name,
                "linux_platform",
                "clipboard_cli_available",
                "wayland_session_accessible",
            )
        if tool == ToolName.CLIPBOARD_COPY_SELECTION:
            return _blockers_for(
                steps_by_name,
                "linux_platform",
                "clipboard_cli_available",
                "text_input_cli_available",
                "wayland_session_accessible",
            )
        if tool in {ToolName.CLIPBOARD_PASTE, ToolName.TEXT_TYPE, ToolName.KEYS_PRESS}:
            return _blockers_for(
                steps_by_name,
                "linux_platform",
                "text_input_cli_available",
                "wayland_session_accessible",
            )
        if tool in network_tools:
            return _blockers_for(steps_by_name, "linux_platform", "networkmanager_cli_available")
        if tool == ToolName.NOTIFICATIONS_SHOW:
            linux_blockers = _blockers_for(steps_by_name, "linux_platform")
            if linux_blockers:
                return linux_blockers
            notify_step = steps_by_name.get("notify_send_available")
            gdbus_step = steps_by_name.get("gdbus_available")
            if (
                notify_step is not None
                and getattr(notify_step, "status", None) == "ok"
                or gdbus_step is not None
                and getattr(gdbus_step, "status", None) == "ok"
            ):
                return []
            blockers: list[str] = []
            if notify_step is None or getattr(notify_step, "status", None) != "ok":
                blockers.append("notify-send")
            if gdbus_step is None or getattr(gdbus_step, "status", None) != "ok":
                blockers.append("gdbus")
            return blockers
        if tool in file_tools:
            return _blockers_for(steps_by_name, "linux_platform")
        return _blockers_for(steps_by_name, "linux_platform")

    def tool_live_runtime_suggested_command(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> str | None:
        window_tools = {
            ToolName.WINDOWS_LIST,
            ToolName.WINDOWS_SWITCH,
            ToolName.WINDOWS_MINIMIZE,
            ToolName.WINDOWS_MAXIMIZE,
            ToolName.WINDOWS_SET_FULLSCREEN,
            ToolName.WINDOWS_SET_KEEP_ABOVE,
            ToolName.WINDOWS_SET_SHADED,
            ToolName.WINDOWS_SET_KEEP_BELOW,
            ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
            ToolName.WINDOWS_RESTORE,
            ToolName.WINDOWS_CLOSE,
        }
        audio_tools = {
            ToolName.AUDIO_GET_VOLUME,
            ToolName.AUDIO_MUTE_STATUS,
            ToolName.AUDIO_SET_VOLUME,
            ToolName.AUDIO_SET_MUTED,
        }
        network_tools = {
            ToolName.NETWORK_WIFI_STATUS,
            ToolName.NETWORK_DISCONNECT_CURRENT,
            ToolName.NETWORK_SET_WIFI_ENABLED,
            ToolName.NETWORK_CONNECT_KNOWN_SSID,
        }
        file_tools = {
            ToolName.FILES_LIST_RECENT,
            ToolName.FILES_OPEN,
            ToolName.FILES_CREATE_FOLDER,
            ToolName.FILES_DELETE_FOLDER,
            ToolName.FILES_DELETE_FILE,
            ToolName.FILES_RENAME,
            ToolName.FILES_MOVE,
        }

        if tool == ToolName.TIME_NOW:
            return None
        if tool == ToolName.APPS_LAUNCH:
            return _first_recommended(steps_by_name, "linux_platform", "xdg_open_available")
        if tool == ToolName.APPS_FOCUS or tool in window_tools:
            return _first_recommended(
                steps_by_name,
                "linux_platform",
                "kde_wayland_target",
                "gdbus_available",
            )
        if tool == ToolName.POWER_BATTERY_STATUS:
            return _first_recommended(steps_by_name, "linux_platform", "power_status_available")
        if tool in audio_tools:
            return _first_recommended(steps_by_name, "linux_platform", "audio_cli_available")
        if tool in {ToolName.CLIPBOARD_GET_TEXT, ToolName.CLIPBOARD_SET_TEXT, ToolName.CLIPBOARD_CLEAR}:
            return _first_recommended(
                steps_by_name,
                "linux_platform",
                "clipboard_cli_available",
                "wayland_session_accessible",
            )
        if tool == ToolName.CLIPBOARD_COPY_SELECTION:
            return _first_recommended(
                steps_by_name,
                "linux_platform",
                "clipboard_cli_available",
                "text_input_cli_available",
                "wayland_session_accessible",
            )
        if tool in {ToolName.CLIPBOARD_PASTE, ToolName.TEXT_TYPE, ToolName.KEYS_PRESS}:
            return _first_recommended(
                steps_by_name,
                "linux_platform",
                "text_input_cli_available",
                "wayland_session_accessible",
            )
        if tool in network_tools:
            return _first_recommended(steps_by_name, "linux_platform", "networkmanager_cli_available")
        if tool == ToolName.NOTIFICATIONS_SHOW:
            return _first_recommended(steps_by_name, "linux_platform", "notify_send_available", "gdbus_available")
        if tool in file_tools:
            return _first_recommended(steps_by_name, "linux_platform")
        return _first_recommended(steps_by_name, "linux_platform")


def _blockers_for(
    steps_by_name: Mapping[str, object],
    *check_names: str,
) -> list[str]:
    blockers: list[str] = []
    for check_name in check_names:
        step = steps_by_name.get(check_name)
        if step is None:
            blockers.append(check_name.replace("_", " "))
            continue
        if getattr(step, "status", None) != "ok":
            blockers.append(str(getattr(step, "label", check_name.replace("_", " "))))
    return blockers


def _first_recommended(
    steps_by_name: Mapping[str, object],
    *check_names: str,
) -> str | None:
    for check_name in check_names:
        step = steps_by_name.get(check_name)
        if step is None or getattr(step, "status", None) == "ok":
            continue
        command = getattr(step, "recommended_command", None)
        if isinstance(command, str) and command:
            return command
    return None


def _voice_loop_runtime_status_available_check(
    *,
    voice_loop_runtime_status: object,
    voice_loop_service_active_status: str,
) -> tuple[str, object]:
    status_file_exists = bool(getattr(voice_loop_runtime_status, "status_file_exists", False))
    status_file_path = str(getattr(voice_loop_runtime_status, "status_file_path", ""))
    if status_file_exists:
        return "ok", status_file_path
    if voice_loop_service_active_status != "ok":
        return (
            "ok",
            {
                "message": "Voice-loop user service is not active; runtime status is optional until the service runs.",
                "status_file_path": status_file_path,
            },
        )
    return "warn", status_file_path


def _voice_loop_runtime_heartbeat_check(
    *,
    voice_loop_runtime_status: object,
    voice_loop_service_active_status: str,
) -> tuple[str, dict[str, object]]:
    heartbeat_fresh = bool(getattr(voice_loop_runtime_status, "heartbeat_fresh", False))
    detail = getattr(voice_loop_runtime_status, "to_dict", lambda: {})()
    if not isinstance(detail, dict):
        detail = {}
    if heartbeat_fresh:
        return "ok", detail
    if voice_loop_service_active_status != "ok":
        detail = dict(detail)
        detail["status"] = "ok"
        detail["message"] = (
            "Voice-loop user service is not active; no runtime status file has been written yet."
            if not bool(getattr(voice_loop_runtime_status, "status_file_exists", False))
            else "Voice-loop user service is not active; showing the last recorded runtime status."
        )
        return "ok", detail
    return "warn", detail


def _has_battery_sysfs() -> bool:
    power_supply_dir = Path("/sys/class/power_supply")
    if not power_supply_dir.exists():
        return False
    return any(path.name.startswith("BAT") for path in power_supply_dir.iterdir())


def build_voice_loop_config_snapshot():
    from ..voice.config import build_voice_loop_config_snapshot as _build_voice_loop_config_snapshot

    return _build_voice_loop_config_snapshot()


def build_voice_loop_runtime_status_snapshot():
    from ..voice.runtime import (
        build_voice_loop_runtime_status_snapshot as _build_voice_loop_runtime_status_snapshot,
    )

    return _build_voice_loop_runtime_status_snapshot()


def _probe_wayland_session_access(env: dict[str, str] | None = None) -> tuple[str, object]:
    current_env = os.environ if env is None else env
    session_type = current_env.get("XDG_SESSION_TYPE")
    runtime_dir = current_env.get("XDG_RUNTIME_DIR")
    display = current_env.get("WAYLAND_DISPLAY")

    detail: dict[str, object] = {
        "session_type": session_type,
        "runtime_dir": runtime_dir,
        "display": display,
    }

    if session_type != "wayland":
        detail["message"] = "Wayland session is not active."
        return "warn", detail
    if not runtime_dir or not display:
        detail["message"] = "WAYLAND_DISPLAY or XDG_RUNTIME_DIR is not set."
        return "warn", detail

    socket_path = Path(runtime_dir) / display
    detail["socket_path"] = str(socket_path)
    if not socket_path.exists():
        detail["message"] = "Wayland socket path does not exist."
        return "warn", detail

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(0.5)
        client.connect(str(socket_path))
    except OSError as exc:
        detail["message"] = str(exc)
        return "warn", detail
    finally:
        client.close()

    detail["message"] = "Wayland session socket is accessible."
    return "ok", detail


def _probe_text_input_backend(
    *,
    wayland_session_accessible: bool,
    run_command=None,
    resolve_executable=shutil.which,
) -> tuple[str, object]:
    wtype_path = resolve_executable("wtype")
    if wtype_path is None:
        return (
            "warn",
            {
                "backend_status": "missing_binary",
                "message": "wtype is not installed.",
                "wtype": None,
            },
        )
    detail: dict[str, object] = {
        "backend_status": "probe_skipped",
        "message": "wtype is installed.",
        "wtype": wtype_path,
    }
    if not wayland_session_accessible:
        return "ok", detail

    if run_command is None:
        completed = subprocess.run(
            ["wtype", "-M", "shift", "-m", "shift"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        completed = run_command(["wtype", "-M", "shift", "-m", "shift"])
    if completed.returncode == 0:
        detail["backend_status"] = "ok"
        detail["message"] = "wtype backend is usable."
        return "ok", detail

    probe_error = (completed.stderr or completed.stdout or "").strip() or f"exit code {completed.returncode}"
    if "virtual keyboard protocol" in probe_error.casefold():
        detail["backend_status"] = "unsupported_protocol"
        detail["message"] = "wtype is installed but the compositor does not support the virtual keyboard protocol."
    else:
        detail["backend_status"] = "probe_failed"
        detail["message"] = "wtype is installed but the runtime probe failed."
    detail["probe_error"] = probe_error
    return "warn", detail


def _tray_user_service_path() -> Path:
    return _first_user_service_path("operance-tray.service")


def _voice_loop_user_service_path() -> Path:
    return _first_user_service_path("operance-voice-loop.service")


def _voice_loop_config_path() -> Path:
    candidates = _voice_loop_config_candidate_paths()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _user_service_candidate_paths(unit_name: str) -> list[Path]:
    return [
        Path.home() / ".config" / "systemd" / "user" / unit_name,
        Path("/etc/systemd/user") / unit_name,
        Path("/usr/local/lib/systemd/user") / unit_name,
        Path("/usr/lib/systemd/user") / unit_name,
    ]


def _voice_loop_config_candidate_paths() -> list[Path]:
    return [
        Path.home() / ".config" / "operance" / "voice-loop.args",
        Path("/etc/operance") / "voice-loop.args",
    ]


def _first_user_service_path(unit_name: str) -> Path:
    candidates = _user_service_candidate_paths(unit_name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _probe_systemctl_user_service_state(
    subcommand: str,
    unit_name: str,
    *,
    systemctl_path: str | None = None,
) -> tuple[str, str]:
    systemctl_executable = systemctl_path or shutil.which("systemctl")
    if systemctl_executable is None:
        return "warn", "systemctl not found"

    try:
        completed = subprocess.run(
            [systemctl_executable, "--user", subcommand, unit_name],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        return "warn", str(exc)

    detail = completed.stdout.strip() or completed.stderr.strip()
    if not detail:
        detail = "ok" if completed.returncode == 0 else "unknown"

    return "ok" if completed.returncode == 0 else "warn", detail


def _collect_check_blockers(
    checks_by_name: Mapping[str, dict[str, object]],
    names: tuple[str, ...],
) -> list[str]:
    return [
        _SETUP_CHECK_LABELS.get(
            name,
            next(
                (
                    metadata.label
                    for metadata in LINUX_CHECK_METADATA
                    if metadata.name == name
                ),
                name.replace("_", " "),
            ),
        )
        for name in names
        if str(checks_by_name.get(name, {}).get("status")) != "ok"
    ]


def _build_unavailable_reason(blockers: list[str]) -> str | None:
    if not blockers:
        return None
    return f"Blocked by: {', '.join(blockers)}."


def _text_input_check_detail(
    checks_by_name: Mapping[str, dict[str, object]],
) -> dict[str, object]:
    detail = checks_by_name.get("text_input_cli_available", {}).get("detail")
    return detail if isinstance(detail, dict) else {}


def _text_input_needs_install(
    checks_by_name: Mapping[str, dict[str, object]],
) -> bool:
    if str(checks_by_name.get("text_input_cli_available", {}).get("status")) == "ok":
        return False
    detail = _text_input_check_detail(checks_by_name)
    backend_status = str(detail.get("backend_status", ""))
    return backend_status in {"", "missing_binary"} or detail.get("wtype") is None


def _text_input_backend_blocker(
    checks_by_name: Mapping[str, dict[str, object]],
) -> str | None:
    if _text_input_needs_install(checks_by_name):
        return None
    if str(checks_by_name.get("text_input_cli_available", {}).get("status")) == "ok":
        return None
    backend_status = str(_text_input_check_detail(checks_by_name).get("backend_status", ""))
    if backend_status == "unsupported_protocol":
        return "Wayland text input backend unsupported in this session"
    return "Wayland text input backend unavailable in this session"


def _text_input_backend_reason(
    checks_by_name: Mapping[str, dict[str, object]],
) -> str:
    message = str(_text_input_check_detail(checks_by_name).get("message", "")).strip()
    if not message:
        return (
            "The Wayland text input backend is present but not usable in this session, "
            "so text injection, key press, and selection-copy commands remain disabled."
        )
    if message.endswith("."):
        message = message[:-1]
    return (
        f"{message}, so text injection, key press, and selection-copy commands remain disabled."
    )


def _build_setup_actions(
    checks_by_name: Mapping[str, dict[str, object]],
    *,
    recommended_commands: tuple[str, ...],
) -> list[PlatformSetupAction]:
    linux_ready = str(checks_by_name.get("linux_platform", {}).get("status")) == "ok"
    systemctl_ready = str(checks_by_name.get("systemctl_user_available", {}).get("status")) == "ok"
    python_ready = str(checks_by_name.get("python_3_12_plus", {}).get("status")) == "ok"
    virtualenv_ready = str(checks_by_name.get("virtualenv_active", {}).get("status")) == "ok"
    audio_cli_ready = str(checks_by_name.get("audio_cli_available", {}).get("status")) == "ok"
    audio_capture_ready = str(checks_by_name.get("audio_capture_cli_available", {}).get("status")) == "ok"
    audio_playback_ready = str(checks_by_name.get("audio_playback_cli_available", {}).get("status")) == "ok"
    wakeword_backend_ready = str(checks_by_name.get("wakeword_backend_available", {}).get("status")) == "ok"
    wakeword_model_ready = str(checks_by_name.get("wakeword_model_asset_available", {}).get("status")) == "ok"
    wakeword_model_source_ready = str(checks_by_name.get("wakeword_model_source_available", {}).get("status")) == "ok"
    stt_backend_ready = str(checks_by_name.get("stt_backend_available", {}).get("status")) == "ok"
    tts_backend_ready = str(checks_by_name.get("tts_backend_available", {}).get("status")) == "ok"
    tts_model_ready = str(checks_by_name.get("tts_model_asset_available", {}).get("status")) == "ok"
    tts_model_source_ready = str(checks_by_name.get("tts_model_source_available", {}).get("status")) == "ok"
    tts_voices_ready = str(checks_by_name.get("tts_voices_asset_available", {}).get("status")) == "ok"
    tts_voices_source_ready = str(checks_by_name.get("tts_voices_source_available", {}).get("status")) == "ok"
    clipboard_check_present = "clipboard_cli_available" in checks_by_name
    text_input_check_present = "text_input_cli_available" in checks_by_name
    clipboard_ready = str(checks_by_name.get("clipboard_cli_available", {}).get("status")) == "ok"
    planner_enabled = str(checks_by_name.get("planner_runtime_enabled", {}).get("status")) == "ok"
    voice_loop_ready = _can_install_voice_loop_service(checks_by_name)
    voice_diagnostics_ready = linux_ready and python_ready and virtualenv_ready and audio_cli_ready
    microphone_probe_ready = voice_diagnostics_ready and audio_capture_ready
    tts_probe_ready = (
        voice_diagnostics_ready
        and audio_playback_ready
        and tts_backend_ready
        and tts_model_ready
        and tts_voices_ready
    )
    planner_probe_ready = python_ready and virtualenv_ready and planner_enabled
    voice_loop_runtime_healthy = (
        str(checks_by_name.get("voice_loop_runtime_heartbeat_fresh", {}).get("status", "ok")) == "ok"
    )
    tray_service_enable_ready = (
        linux_ready
        and systemctl_ready
        and str(checks_by_name.get("tray_user_service_installed", {}).get("status")) == "ok"
        and str(checks_by_name.get("tray_user_service_enabled", {}).get("status")) != "ok"
    )
    tray_service_restart_ready = (
        linux_ready
        and systemctl_ready
        and str(checks_by_name.get("tray_user_service_installed", {}).get("status")) == "ok"
        and str(checks_by_name.get("tray_user_service_active", {}).get("status")) != "ok"
    )
    voice_loop_service_enable_ready = (
        linux_ready
        and systemctl_ready
        and str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) == "ok"
        and str(checks_by_name.get("voice_loop_user_service_enabled", {}).get("status")) != "ok"
    )
    voice_loop_service_restart_ready = (
        linux_ready
        and systemctl_ready
        and str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) == "ok"
        and (
            str(checks_by_name.get("voice_loop_user_service_active", {}).get("status")) != "ok"
            or not voice_loop_runtime_healthy
        )
    )
    recommended_set = set(recommended_commands)
    bootstrap_command = _build_bootstrap_command(checks_by_name)
    local_app_command = _build_local_app_command(checks_by_name)
    click_to_talk_command = _click_to_talk_command()
    voice_loop_config_flag = (
        " --use-voice-loop-config"
        if str(checks_by_name.get("voice_loop_user_config_available", {}).get("status")) == "ok"
        else ""
    )
    calibrate_wakeword_command = (
        f"python3 -m operance.cli --wakeword-calibrate-frames 20{voice_loop_config_flag}"
    )
    apply_calibrated_wakeword_command = f"{calibrate_wakeword_command} --apply-suggested-threshold"
    evaluate_wakeword_command = (
        f"python3 -m operance.cli --wakeword-eval-frames 50{voice_loop_config_flag}"
    )
    voice_diagnostic_check_names = (
        "linux_platform",
        "python_3_12_plus",
        "virtualenv_active",
        "audio_cli_available",
    )
    microphone_probe_check_names = voice_diagnostic_check_names + ("audio_capture_cli_available",)
    tts_probe_check_names = voice_diagnostic_check_names + (
        "audio_playback_cli_available",
        "tts_backend_available",
        "tts_model_asset_available",
        "tts_voices_asset_available",
    )
    voice_loop_service_check_names = (
        "python_3_12_plus",
        "virtualenv_active",
        "linux_platform",
        "kde_wayland_target",
        "xdg_open_available",
        "gdbus_available",
        "networkmanager_cli_available",
        "audio_cli_available",
        "audio_capture_cli_available",
        "systemctl_user_available",
        "power_status_available",
        "stt_backend_available",
    )
    install_wakeword_model_asset_command = shlex.join(
        [
            "./scripts/install_wakeword_model_asset.sh",
            "--source",
            str(checks_by_name.get("wakeword_model_source_available", {}).get("detail", "/path/to/operance.onnx")),
        ]
    )
    install_tts_assets_command = shlex.join(
        [
            "./scripts/install_tts_assets.sh",
            "--model",
            str(checks_by_name.get("tts_model_source_available", {}).get("detail", "/path/to/kokoro.onnx")),
            "--voices",
            str(checks_by_name.get("tts_voices_source_available", {}).get("detail", "/path/to/voices.bin")),
        ]
    )
    install_wayland_input_tools_command = _wayland_input_tools_command(checks_by_name)
    wayland_input_backend_blocker = _text_input_backend_blocker(checks_by_name)
    wayland_input_needs_install = (
        (clipboard_check_present and not clipboard_ready)
        or (text_input_check_present and _text_input_needs_install(checks_by_name))
    )
    wayland_input_install_ready = (
        str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok"
        or str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
    )
    install_deb_package_artifact_command = shlex.join(
        [
            "./scripts/install_package_artifact.sh",
            "--package",
            str(_default_deb_package_artifact_path()),
            "--installer",
            "apt",
        ]
    )
    install_rpm_package_artifact_command = shlex.join(
        [
            "./scripts/install_package_artifact.sh",
            "--package",
            str(_default_rpm_package_artifact_path()),
            "--installer",
            "dnf",
            "--replace-existing",
            "--reset-user-services",
        ]
    )
    install_deb_packaging_tools_command = "./scripts/install_packaging_tools.sh --deb"
    install_rpm_packaging_tools_command = "./scripts/install_packaging_tools.sh --rpm"
    run_fedora_alpha_gate_command = "./scripts/run_fedora_alpha_gate.sh --reset-user-services"
    run_installed_rpm_beta_smoke_command = shlex.join(
        [
            "./scripts/run_installed_beta_smoke.sh",
            "--package",
            str(_default_rpm_package_artifact_path()),
            "--installer",
            "dnf",
            "--require-mvp-runtime",
            "--reset-user-services",
            "--uninstall-after",
        ]
    )
    run_fedora_release_smoke_command = "./scripts/run_fedora_release_smoke.sh --reset-user-services"

    def build_action(
        *,
        action_id: str,
        label: str,
        command: str,
        available: bool,
        recommended: bool,
        blocker_checks: tuple[str, ...] = (),
        extra_blockers: list[str] | None = None,
        suggested_command: str | None = None,
    ) -> PlatformSetupAction:
        blockers = _collect_check_blockers(checks_by_name, blocker_checks)
        if extra_blockers:
            blockers.extend(extra_blockers)
        return PlatformSetupAction(
            action_id=action_id,
            label=label,
            command=command,
            available=available,
            recommended=recommended,
            unavailable_reason=None if available else _build_unavailable_reason(blockers),
            suggested_command=None if available else suggested_command,
        )

    return [
        build_action(
            action_id="bootstrap_dev_env",
            label="Bootstrap local dev environment",
            command=bootstrap_command,
            available=linux_ready,
            recommended=bootstrap_command in recommended_set,
            blocker_checks=("linux_platform",),
        ),
        build_action(
            action_id="install_local_app",
            label="Install local Linux app",
            command=local_app_command,
            available=linux_ready,
            recommended=local_app_command in recommended_set,
            blocker_checks=("linux_platform",),
        ),
        build_action(
            action_id="enable_tray_service",
            label="Enable tray user service",
            command="./scripts/control_systemd_user_services.sh enable",
            available=tray_service_enable_ready,
            recommended="./scripts/control_systemd_user_services.sh enable" in recommended_set,
            blocker_checks=("linux_platform", "systemctl_user_available", "tray_user_service_installed"),
            extra_blockers=(
                ["Tray user service already enabled"]
                if not tray_service_enable_ready
                and str(checks_by_name.get("tray_user_service_enabled", {}).get("status")) == "ok"
                else None
            ),
            suggested_command=(
                local_app_command
                if str(checks_by_name.get("tray_user_service_installed", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="restart_tray_service",
            label="Restart tray user service",
            command="./scripts/control_systemd_user_services.sh restart",
            available=tray_service_restart_ready,
            recommended="./scripts/control_systemd_user_services.sh restart" in recommended_set,
            blocker_checks=("linux_platform", "systemctl_user_available", "tray_user_service_installed"),
            extra_blockers=(
                ["Tray user service already active"]
                if not tray_service_restart_ready
                and str(checks_by_name.get("tray_user_service_active", {}).get("status")) == "ok"
                else None
            ),
            suggested_command=(
                local_app_command
                if str(checks_by_name.get("tray_user_service_installed", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="install_ui_backend",
            label="Install tray UI backend",
            command='python3 -m pip install -e ".[dev,ui]"',
            available=python_ready,
            recommended='python3 -m pip install -e ".[dev,ui]"' in recommended_set,
            blocker_checks=("python_3_12_plus",),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="install_voice_backends",
            label="Install voice backends",
            command='python3 -m pip install -e ".[dev,voice]"',
            available=python_ready,
            recommended='python3 -m pip install -e ".[dev,voice]"' in recommended_set,
            blocker_checks=("python_3_12_plus",),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="install_wayland_input_tools",
            label="Install Wayland input tools",
            command=install_wayland_input_tools_command or "./scripts/install_wayland_input_tools.sh",
            available=linux_ready and wayland_input_install_ready and install_wayland_input_tools_command is not None,
            recommended=False,
            blocker_checks=("linux_platform",),
            extra_blockers=(
                _collect_check_blockers(
                    checks_by_name,
                    ("deb_package_installer_available", "rpm_package_installer_available"),
                )
                if not wayland_input_install_ready and wayland_input_needs_install
                else (
                    [wayland_input_backend_blocker]
                    if wayland_input_backend_blocker is not None
                    else (
                        ["Wayland clipboard CLI already installed", "Wayland text input CLI already installed"]
                        if (clipboard_check_present or text_input_check_present)
                        and install_wayland_input_tools_command is None
                        else None
                    )
                )
                if (clipboard_check_present or text_input_check_present)
                else None
            ),
            suggested_command=(
                "python3 -m operance.cli --doctor"
                if wayland_input_backend_blocker is not None
                else ("python3 -m operance.cli --doctor" if not wayland_input_install_ready else None)
            ),
        ),
        build_action(
            action_id="show_voice_asset_paths",
            label="Show voice asset paths",
            command="python3 -m operance.cli --voice-asset-paths",
            available=python_ready and virtualenv_ready,
            recommended=False,
            blocker_checks=("python_3_12_plus", "virtualenv_active"),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="collect_support_bundle",
            label="Collect support bundle",
            command="python3 -m operance.cli --support-bundle",
            available=python_ready and virtualenv_ready,
            recommended=False,
            blocker_checks=("python_3_12_plus", "virtualenv_active"),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="collect_support_snapshot",
            label="Collect support snapshot",
            command="python3 -m operance.cli --support-snapshot",
            available=python_ready and virtualenv_ready,
            recommended=False,
            blocker_checks=("python_3_12_plus", "virtualenv_active"),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="install_wakeword_model_asset",
            label="Install wake-word model asset",
            command=install_wakeword_model_asset_command,
            available=linux_ready and wakeword_model_source_ready and not wakeword_model_ready,
            recommended=install_wakeword_model_asset_command in recommended_set,
            blocker_checks=("linux_platform", "wakeword_model_source_available"),
            extra_blockers=["Wake-word model asset already installed"] if wakeword_model_ready else None,
            suggested_command="python3 -m operance.cli --voice-asset-paths",
        ),
        build_action(
            action_id="install_tts_assets",
            label="Install TTS assets",
            command=install_tts_assets_command,
            available=(
                linux_ready
                and tts_model_source_ready
                and tts_voices_source_ready
                and (not tts_model_ready or not tts_voices_ready)
            ),
            recommended=install_tts_assets_command in recommended_set,
            blocker_checks=("linux_platform", "tts_model_source_available", "tts_voices_source_available"),
            extra_blockers=(
                ["TTS model asset already installed", "TTS voices asset already installed"]
                if tts_model_ready and tts_voices_ready
                else None
            ),
            suggested_command="python3 -m operance.cli --voice-asset-paths",
        ),
        build_action(
            action_id="list_audio_input_devices",
            label="List audio input devices",
            command="python3 -m operance.cli --audio-list-devices",
            available=voice_diagnostics_ready,
            recommended=False,
            blocker_checks=voice_diagnostic_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="probe_microphone_capture",
            label="Probe microphone capture",
            command="python3 -m operance.cli --audio-capture-frames 4",
            available=microphone_probe_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="probe_click_to_talk_path",
            label="Run click-to-talk probe",
            command=click_to_talk_command,
            available=microphone_probe_ready and stt_backend_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names + ("stt_backend_available",),
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not stt_backend_ready
                else bootstrap_command
            ),
        ),
        build_action(
            action_id="probe_wakeword_path",
            label="Probe wake-word path",
            command=f"python3 -m operance.cli --wakeword-probe-frames 8{voice_loop_config_flag}",
            available=microphone_probe_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="calibrate_wakeword_threshold",
            label="Calibrate wake-word threshold",
            command=calibrate_wakeword_command,
            available=microphone_probe_ready,
            recommended=calibrate_wakeword_command in recommended_set,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="apply_calibrated_wakeword_threshold",
            label="Calibrate and apply wake-word threshold",
            command=apply_calibrated_wakeword_command,
            available=microphone_probe_ready,
            recommended=apply_calibrated_wakeword_command in recommended_set,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="evaluate_wakeword_idle_rate",
            label="Measure wake-word idle false activations",
            command=evaluate_wakeword_command,
            available=microphone_probe_ready,
            recommended=evaluate_wakeword_command in recommended_set,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="probe_model_wakeword_path",
            label="Probe model-backed wake-word path",
            command="python3 -m operance.cli --wakeword-probe-frames 8 --wakeword-model auto",
            available=microphone_probe_ready and wakeword_backend_ready and wakeword_model_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names + ("wakeword_backend_available", "wakeword_model_asset_available"),
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not wakeword_backend_ready
                else "python3 -m operance.cli --voice-asset-paths"
                if not wakeword_model_ready
                else bootstrap_command
            ),
        ),
        build_action(
            action_id="probe_stt_path",
            label="Probe speech-to-text path",
            command="python3 -m operance.cli --stt-probe-frames 12",
            available=microphone_probe_ready and stt_backend_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names + ("stt_backend_available",),
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not stt_backend_ready
                else bootstrap_command
            ),
        ),
        build_action(
            action_id="probe_tts_path",
            label="Probe text-to-speech path",
            command='python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-output /tmp/operance-tts-probe.wav --tts-play',
            available=tts_probe_ready,
            recommended=False,
            blocker_checks=tts_probe_check_names,
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not tts_backend_ready
                else "python3 -m operance.cli --voice-asset-paths"
                if not tts_model_ready or not tts_voices_ready
                else bootstrap_command
            ),
        ),
        build_action(
            action_id="run_voice_self_test",
            label="Run voice self-test",
            command=f"python3 -m operance.cli --voice-self-test{voice_loop_config_flag}",
            available=microphone_probe_ready,
            recommended=False,
            blocker_checks=microphone_probe_check_names,
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="probe_planner_health",
            label="Probe planner endpoint",
            command="python3 -m operance.cli --planner-health",
            available=planner_probe_ready,
            recommended="python3 -m operance.cli --planner-health" in recommended_set,
            blocker_checks=("python_3_12_plus", "virtualenv_active", "planner_runtime_enabled"),
            suggested_command=bootstrap_command if not python_ready or not virtualenv_ready else None,
        ),
        build_action(
            action_id="install_voice_loop_service",
            label="Install voice-loop user service",
            command="./scripts/install_voice_loop_user_service.sh",
            available=voice_loop_ready,
            recommended="./scripts/install_voice_loop_user_service.sh" in recommended_set,
            blocker_checks=voice_loop_service_check_names,
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not stt_backend_ready
                else bootstrap_command
            ),
        ),
        build_action(
            action_id="enable_voice_loop_service",
            label="Enable voice-loop user service",
            command="./scripts/control_systemd_user_services.sh enable --voice-loop",
            available=voice_loop_service_enable_ready,
            recommended="./scripts/control_systemd_user_services.sh enable --voice-loop" in recommended_set,
            blocker_checks=("linux_platform", "systemctl_user_available", "voice_loop_user_service_installed"),
            extra_blockers=(
                ["Voice-loop user service already enabled"]
                if not voice_loop_service_enable_ready
                and str(checks_by_name.get("voice_loop_user_service_enabled", {}).get("status")) == "ok"
                else None
            ),
            suggested_command=(
                "./scripts/install_voice_loop_user_service.sh"
                if str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="restart_voice_loop_service",
            label="Restart voice-loop user service",
            command="./scripts/control_systemd_user_services.sh restart --voice-loop",
            available=voice_loop_service_restart_ready,
            recommended="./scripts/control_systemd_user_services.sh restart --voice-loop" in recommended_set,
            blocker_checks=("linux_platform", "systemctl_user_available", "voice_loop_user_service_installed"),
            extra_blockers=(
                ["Voice-loop user service already active and heartbeat looks fresh"]
                if not voice_loop_service_restart_ready
                and str(checks_by_name.get("voice_loop_user_service_active", {}).get("status")) == "ok"
                and voice_loop_runtime_healthy
                else None
            ),
            suggested_command=(
                "./scripts/install_voice_loop_user_service.sh"
                if str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="install_voice_loop_user_config",
            label="Seed voice-loop user config",
            command="./scripts/install_voice_loop_user_config.sh",
            available=linux_ready,
            recommended="./scripts/install_voice_loop_user_config.sh" in recommended_set,
            blocker_checks=("linux_platform",),
        ),
        build_action(
            action_id="inspect_voice_loop_config",
            label="Inspect voice-loop config",
            command="python3 -m operance.cli --voice-loop-config",
            available=python_ready and virtualenv_ready,
            recommended=False,
            blocker_checks=("python_3_12_plus", "virtualenv_active"),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="inspect_voice_loop_runtime_status",
            label="Inspect voice-loop runtime status",
            command="python3 -m operance.cli --voice-loop-status",
            available=python_ready and virtualenv_ready,
            recommended=False,
            blocker_checks=("python_3_12_plus", "virtualenv_active"),
            suggested_command=bootstrap_command,
        ),
        build_action(
            action_id="configure_voice_loop_wakeword_model",
            label="Enable model-backed wake-word in voice-loop config",
            command="./scripts/update_voice_loop_user_config.sh --wakeword-model auto",
            available=linux_ready and wakeword_backend_ready and wakeword_model_ready,
            recommended=False,
            blocker_checks=("linux_platform", "wakeword_backend_available", "wakeword_model_asset_available"),
            suggested_command=(
                'python3 -m pip install -e ".[dev,voice]"'
                if not wakeword_backend_ready
                else "python3 -m operance.cli --voice-asset-paths"
                if not wakeword_model_ready
                else None
            ),
        ),
        build_action(
            action_id="render_package_scaffolds",
            label="Render package scaffolds",
            command="./scripts/build_package_scaffolds.sh",
            available=linux_ready and str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok",
            recommended="./scripts/build_package_scaffolds.sh" in recommended_set,
            blocker_checks=("linux_platform", "archive_packaging_cli_available"),
        ),
        build_action(
            action_id="install_deb_packaging_tools",
            label="Install Debian packaging tools",
            command=install_deb_packaging_tools_command,
            available=(
                linux_ready
                and str(checks_by_name.get("deb_packaging_cli_available", {}).get("status")) != "ok"
                and str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok"
            ),
            recommended=install_deb_packaging_tools_command in recommended_set,
            blocker_checks=("linux_platform", "deb_package_installer_available"),
            extra_blockers=(
                ["Debian packaging CLI already available"]
                if str(checks_by_name.get("deb_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok"
                else None
            ),
            suggested_command=(
                "python3 -m operance.cli --doctor"
                if str(checks_by_name.get("deb_package_installer_available", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="install_rpm_packaging_tools",
            label="Install RPM packaging tools",
            command=install_rpm_packaging_tools_command,
            available=(
                linux_ready
                and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) != "ok"
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
            ),
            recommended=install_rpm_packaging_tools_command in recommended_set,
            blocker_checks=("linux_platform", "rpm_package_installer_available"),
            extra_blockers=(
                ["RPM packaging CLI already available"]
                if str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
                else None
            ),
            suggested_command=(
                "python3 -m operance.cli --doctor"
                if str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) != "ok"
                else None
            ),
        ),
        build_action(
            action_id="build_deb_package_artifact",
            label="Build Debian package artifact",
            command="./scripts/build_package_artifacts.sh --deb",
            available=linux_ready and str(checks_by_name.get("deb_packaging_cli_available", {}).get("status")) == "ok",
            recommended="./scripts/build_package_artifacts.sh --deb" in recommended_set,
            blocker_checks=("linux_platform", "deb_packaging_cli_available"),
        ),
        build_action(
            action_id="build_rpm_package_artifact",
            label="Build RPM package artifact",
            command="./scripts/build_package_artifacts.sh --rpm",
            available=(
                linux_ready
                and str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok"
            ),
            recommended="./scripts/build_package_artifacts.sh --rpm" in recommended_set,
            blocker_checks=("linux_platform", "archive_packaging_cli_available", "rpm_packaging_cli_available"),
        ),
        build_action(
            action_id="run_fedora_alpha_gate",
            label="Run Fedora alpha gate",
            command=run_fedora_alpha_gate_command,
            available=(
                linux_ready
                and str(checks_by_name.get("python_3_12_plus", {}).get("status")) == "ok"
                and str(checks_by_name.get("virtualenv_active", {}).get("status")) == "ok"
                and str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
            ),
            recommended=run_fedora_alpha_gate_command in recommended_set,
            blocker_checks=(
                "linux_platform",
                "python_3_12_plus",
                "virtualenv_active",
                "archive_packaging_cli_available",
                "rpm_packaging_cli_available",
                "rpm_package_installer_available",
            ),
        ),
        build_action(
            action_id="run_fedora_release_smoke",
            label="Run Fedora release smoke",
            command=run_fedora_release_smoke_command,
            available=(
                linux_ready
                and str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok"
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
            ),
            recommended=run_fedora_release_smoke_command in recommended_set,
            blocker_checks=(
                "linux_platform",
                "archive_packaging_cli_available",
                "rpm_packaging_cli_available",
                "rpm_package_installer_available",
            ),
        ),
        build_action(
            action_id="install_deb_package_artifact",
            label="Install Debian package artifact",
            command=install_deb_package_artifact_command,
            available=(
                linux_ready
                and str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok"
                and _default_deb_package_artifact_path().exists()
            ),
            recommended=False,
            blocker_checks=("linux_platform", "deb_package_installer_available"),
            extra_blockers=(
                ["Debian package artifact not built"]
                if not _default_deb_package_artifact_path().exists()
                else None
            ),
            suggested_command=(
                "./scripts/build_package_artifacts.sh --deb"
                if not _default_deb_package_artifact_path().exists()
                else None
            ),
        ),
        build_action(
            action_id="install_rpm_package_artifact",
            label="Install RPM package artifact",
            command=install_rpm_package_artifact_command,
            available=(
                linux_ready
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
                and _default_rpm_package_artifact_path().exists()
            ),
            recommended=False,
            blocker_checks=("linux_platform", "rpm_package_installer_available"),
            extra_blockers=(
                ["RPM package artifact not built"]
                if not _default_rpm_package_artifact_path().exists()
                else None
            ),
            suggested_command=(
                "./scripts/build_package_artifacts.sh --rpm"
                if not _default_rpm_package_artifact_path().exists()
                else None
            ),
        ),
        build_action(
            action_id="run_installed_rpm_beta_smoke",
            label="Run installed RPM beta smoke",
            command=run_installed_rpm_beta_smoke_command,
            available=(
                linux_ready
                and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
                and _default_rpm_package_artifact_path().exists()
            ),
            recommended=False,
            blocker_checks=("linux_platform", "rpm_package_installer_available"),
            extra_blockers=(
                ["RPM package artifact not built"]
                if not _default_rpm_package_artifact_path().exists()
                else None
            ),
            suggested_command=(
                "./scripts/build_package_artifacts.sh --rpm"
                if not _default_rpm_package_artifact_path().exists()
                else None
            ),
        ),
        build_action(
            action_id="uninstall_deb_package",
            label="Uninstall Debian package",
            command="./scripts/uninstall_native_package.sh --installer apt",
            available=linux_ready and str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok",
            recommended=False,
            blocker_checks=("linux_platform", "deb_package_installer_available"),
        ),
        build_action(
            action_id="uninstall_rpm_package",
            label="Uninstall RPM package",
            command="./scripts/uninstall_native_package.sh --installer dnf",
            available=linux_ready and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok",
            recommended=False,
            blocker_checks=("linux_platform", "rpm_package_installer_available"),
        ),
    ]


def _build_setup_recommended_commands(
    checks_by_name: Mapping[str, dict[str, object]],
) -> list[str]:
    needs_service = str(checks_by_name.get("tray_user_service_installed", {}).get("status")) != "ok"
    needs_bootstrap = str(checks_by_name.get("virtualenv_active", {}).get("status")) != "ok"
    systemctl_ready = str(checks_by_name.get("systemctl_user_available", {}).get("status")) == "ok"
    tray_service_installed = str(checks_by_name.get("tray_user_service_installed", {}).get("status")) == "ok"
    tray_service_enabled = str(checks_by_name.get("tray_user_service_enabled", {}).get("status")) == "ok"
    tray_service_active = str(checks_by_name.get("tray_user_service_active", {}).get("status")) == "ok"
    voice_loop_service_installed = (
        str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) == "ok"
    )
    voice_loop_service_enabled = str(checks_by_name.get("voice_loop_user_service_enabled", {}).get("status")) == "ok"
    voice_loop_service_active = str(checks_by_name.get("voice_loop_user_service_active", {}).get("status")) == "ok"
    voice_loop_runtime_healthy = (
        str(checks_by_name.get("voice_loop_runtime_heartbeat_fresh", {}).get("status", "ok")) == "ok"
    )
    voice_loop_config_available = (
        str(checks_by_name.get("voice_loop_user_config_available", {}).get("status")) == "ok"
    )
    voice_loop_wakeword_needs_tuning = (
        str(checks_by_name.get("voice_loop_wakeword_customized", {}).get("status")) == "warn"
    )
    voice_loop_install_ready = _can_install_voice_loop_service(checks_by_name)
    host_blockers = any(
        str(checks_by_name.get(name, {}).get("status")) != "ok"
        for name in (
            "python_3_12_plus",
            "linux_platform",
            "kde_wayland_target",
            "xdg_open_available",
            "gdbus_available",
            "networkmanager_cli_available",
            "audio_cli_available",
            "audio_capture_cli_available",
            "systemctl_user_available",
            "power_status_available",
        )
    )
    needs_ui = str(checks_by_name.get("tray_ui_available", {}).get("status")) != "ok"
    needs_voice = _needs_voice_dependencies(checks_by_name)
    wakeword_model_missing = str(checks_by_name.get("wakeword_model_asset_available", {}).get("status")) != "ok"
    wakeword_model_source_ready = str(checks_by_name.get("wakeword_model_source_available", {}).get("status")) == "ok"
    tts_model_missing = str(checks_by_name.get("tts_model_asset_available", {}).get("status")) != "ok"
    tts_model_source_ready = str(checks_by_name.get("tts_model_source_available", {}).get("status")) == "ok"
    tts_voices_missing = str(checks_by_name.get("tts_voices_asset_available", {}).get("status")) != "ok"
    tts_voices_source_ready = str(checks_by_name.get("tts_voices_source_available", {}).get("status")) == "ok"

    if needs_bootstrap:
        return [_build_bootstrap_command(checks_by_name)]

    use_local_app_command = needs_service and not host_blockers
    voice_loop_config_flag = " --use-voice-loop-config" if voice_loop_config_available else ""
    calibrate_wakeword_command = (
        f"python3 -m operance.cli --wakeword-calibrate-frames 20{voice_loop_config_flag}"
    )
    apply_calibrated_wakeword_command = f"{calibrate_wakeword_command} --apply-suggested-threshold"
    evaluate_wakeword_command = (
        f"python3 -m operance.cli --wakeword-eval-frames 50{voice_loop_config_flag}"
    )
    commands: list[str] = []
    if use_local_app_command:
        commands.append(_build_local_app_command(checks_by_name))
    if not use_local_app_command and not host_blockers and systemctl_ready:
        if tray_service_installed and not tray_service_enabled:
            commands.append("./scripts/control_systemd_user_services.sh enable")
        elif tray_service_installed and not tray_service_active:
            commands.append("./scripts/control_systemd_user_services.sh restart")
        if not voice_loop_service_installed and voice_loop_install_ready:
            commands.append("./scripts/install_voice_loop_user_service.sh")
        elif voice_loop_service_installed and not voice_loop_service_enabled:
            commands.append("./scripts/control_systemd_user_services.sh enable --voice-loop")
        elif voice_loop_service_installed and (not voice_loop_service_active or not voice_loop_runtime_healthy):
            commands.append("./scripts/control_systemd_user_services.sh restart --voice-loop")
    if (
        not use_local_app_command
        and not host_blockers
        and not voice_loop_config_available
        and (voice_loop_service_installed or voice_loop_install_ready)
    ):
        commands.append("./scripts/install_voice_loop_user_config.sh")
    if (
        not use_local_app_command
        and not host_blockers
        and voice_loop_config_available
        and voice_loop_wakeword_needs_tuning
    ):
        commands.append(apply_calibrated_wakeword_command)
        commands.append(evaluate_wakeword_command)
    if needs_ui and not use_local_app_command:
        commands.append('python3 -m pip install -e ".[dev,ui]"')
    if needs_voice and not use_local_app_command:
        commands.append('python3 -m pip install -e ".[dev,voice]"')
    if not host_blockers and wakeword_model_missing and wakeword_model_source_ready:
        commands.append(
            shlex.join(
                [
                    "./scripts/install_wakeword_model_asset.sh",
                    "--source",
                    str(checks_by_name.get("wakeword_model_source_available", {}).get("detail", "/path/to/operance.onnx")),
                ]
            )
        )
    if (
        not host_blockers
        and (tts_model_missing or tts_voices_missing)
        and tts_model_source_ready
        and tts_voices_source_ready
    ):
        commands.append(
            shlex.join(
                [
                    "./scripts/install_tts_assets.sh",
                    "--model",
                    str(checks_by_name.get("tts_model_source_available", {}).get("detail", "/path/to/kokoro.onnx")),
                    "--voices",
                    str(checks_by_name.get("tts_voices_source_available", {}).get("detail", "/path/to/voices.bin")),
                ]
            )
        )
    if (
        str(checks_by_name.get("planner_runtime_enabled", {}).get("status")) == "ok"
        and str(checks_by_name.get("planner_endpoint_healthy", {}).get("status")) != "ok"
    ):
        commands.append("python3 -m operance.cli --planner-health")
    if (
        "rpm_packaging_cli_available" in checks_by_name
        and "rpm_package_installer_available" in checks_by_name
        and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) != "ok"
        and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
    ):
        commands.append("./scripts/install_packaging_tools.sh --rpm")
    if (
        "deb_packaging_cli_available" in checks_by_name
        and "deb_package_installer_available" in checks_by_name
        and str(checks_by_name.get("deb_packaging_cli_available", {}).get("status")) != "ok"
        and str(checks_by_name.get("deb_package_installer_available", {}).get("status")) == "ok"
    ):
        commands.append("./scripts/install_packaging_tools.sh --deb")
    return commands


def _build_setup_blocked_recommendations(
    checks_by_name: Mapping[str, dict[str, object]],
) -> list[PlatformSetupBlockedRecommendation]:
    blocked: list[PlatformSetupBlockedRecommendation] = []
    clipboard_check = checks_by_name.get("clipboard_cli_available")
    if clipboard_check is not None and str(clipboard_check.get("status")) != "ok":
        clipboard_command = _wayland_input_tools_command(checks_by_name)
        blocked.append(
            PlatformSetupBlockedRecommendation(
                label="Install Wayland clipboard CLI",
                reason="Install wl-copy and wl-paste so clipboard read, write, and clear commands can run on Wayland.",
                suggested_command=clipboard_command or "python3 -m operance.cli --doctor",
            )
        )

    text_input_check = checks_by_name.get("text_input_cli_available")
    if text_input_check is not None and str(text_input_check.get("status")) != "ok":
        if _text_input_needs_install(checks_by_name):
            text_input_command = _wayland_input_tools_command(checks_by_name)
            blocked.append(
                PlatformSetupBlockedRecommendation(
                    label="Install Wayland text input CLI",
                    reason="Install wtype so text injection, key press, and selection-copy commands can drive the focused Wayland window.",
                    suggested_command=text_input_command or "python3 -m operance.cli --doctor",
                )
            )
        else:
            blocked.append(
                PlatformSetupBlockedRecommendation(
                    label="Fix Wayland text input backend",
                    reason=_text_input_backend_reason(checks_by_name),
                    suggested_command="python3 -m operance.cli --doctor",
                )
            )

    wayland_session_check = checks_by_name.get("wayland_session_accessible")
    if wayland_session_check is not None and str(wayland_session_check.get("status")) != "ok":
        blocked.append(
            PlatformSetupBlockedRecommendation(
                label="Fix Wayland session access",
                reason="Run Operance from the logged-in KDE Wayland user session so clipboard and text-input commands can reach the Wayland socket.",
                suggested_command="python3 -m operance.cli --doctor",
            )
        )

    wakeword_model_missing = str(checks_by_name.get("wakeword_model_asset_available", {}).get("status")) != "ok"
    wakeword_model_source_ready = str(checks_by_name.get("wakeword_model_source_available", {}).get("status")) == "ok"
    if wakeword_model_missing and not wakeword_model_source_ready:
        blocked.append(
            PlatformSetupBlockedRecommendation(
                label="Install wake-word model asset",
                reason="Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
                suggested_command="python3 -m operance.cli --voice-asset-paths",
            )
        )

    tts_model_missing = str(checks_by_name.get("tts_model_asset_available", {}).get("status")) != "ok"
    tts_model_source_ready = str(checks_by_name.get("tts_model_source_available", {}).get("status")) == "ok"
    tts_voices_missing = str(checks_by_name.get("tts_voices_asset_available", {}).get("status")) != "ok"
    tts_voices_source_ready = str(checks_by_name.get("tts_voices_source_available", {}).get("status")) == "ok"
    if (tts_model_missing or tts_voices_missing) and (not tts_model_source_ready or not tts_voices_source_ready):
        blocked.append(
            PlatformSetupBlockedRecommendation(
                label="Install TTS assets",
                reason="Set OPERANCE_TTS_MODEL_SOURCE and OPERANCE_TTS_VOICES_SOURCE or copy both files to candidate paths before setup can stage them.",
                suggested_command="python3 -m operance.cli --voice-asset-paths",
            )
        )

    if (
        "rpm_packaging_cli_available" in checks_by_name
        and "rpm_package_installer_available" in checks_by_name
        and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) != "ok"
        and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) != "ok"
    ):
        blocked.append(
            PlatformSetupBlockedRecommendation(
                label="Install RPM packaging tools",
                reason="Install rpm-build on the current Fedora-style host before using the RPM artifact or release smoke helpers.",
                suggested_command="python3 -m operance.cli --doctor",
            )
        )

    return blocked


def _wayland_input_tools_command(
    checks_by_name: Mapping[str, dict[str, object]],
) -> str | None:
    clipboard_check = checks_by_name.get("clipboard_cli_available")
    text_input_check = checks_by_name.get("text_input_cli_available")
    if clipboard_check is None and text_input_check is None:
        return None

    clipboard_missing = clipboard_check is not None and str(clipboard_check.get("status")) != "ok"
    text_input_missing = (
        text_input_check is not None
        and str(text_input_check.get("status")) != "ok"
        and _text_input_needs_install(checks_by_name)
    )
    if not clipboard_missing and not text_input_missing:
        return None
    if (
        str(checks_by_name.get("deb_package_installer_available", {}).get("status")) != "ok"
        and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) != "ok"
    ):
        return None

    command = ["./scripts/install_wayland_input_tools.sh"]
    if clipboard_missing and not text_input_missing:
        command.append("--clipboard-only")
    elif text_input_missing and not clipboard_missing:
        command.append("--text-input-only")
    return shlex.join(command)


def _build_setup_next_steps(
    checks_by_name: Mapping[str, dict[str, object]],
    *,
    ready_for_local_runtime: bool,
) -> list[PlatformSetupNextStep]:
    next_steps: list[PlatformSetupNextStep] = []
    if ready_for_local_runtime:
        next_steps.append(
            PlatformSetupNextStep(
                label="Show runnable commands",
                command="python3 -m operance.cli --supported-commands --supported-commands-available-only",
            )
        )
        next_steps.append(
            PlatformSetupNextStep(
                label="Collect support bundle",
                command="python3 -m operance.cli --support-bundle",
            )
        )

    click_to_talk_ready = ready_for_local_runtime and all(
        str(checks_by_name.get(name, {}).get("status")) == "ok"
        for name in ("audio_capture_cli_available", "stt_backend_available")
    )
    if click_to_talk_ready:
        next_steps.insert(
            0,
            PlatformSetupNextStep(
                label="Launch Operance MVP",
                command=_mvp_launch_command(),
            ),
        )
        next_steps.insert(
            1,
            PlatformSetupNextStep(
                label="Run click-to-talk probe",
                command=_click_to_talk_command(),
            ),
        )

    tray_run_ready = ready_for_local_runtime and (
        str(checks_by_name.get("tray_ui_available", {}).get("status")) == "ok"
    )
    if tray_run_ready:
        insert_index = 2 if click_to_talk_ready else 0
        next_steps.insert(
            insert_index,
            PlatformSetupNextStep(
                label="Run tray app",
                command=_tray_run_command(),
            ),
        )

    fedora_release_smoke_ready = (
        "archive_packaging_cli_available" in checks_by_name
        and "rpm_packaging_cli_available" in checks_by_name
        and "rpm_package_installer_available" in checks_by_name
        and str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok"
        and str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok"
        and str(checks_by_name.get("rpm_package_installer_available", {}).get("status")) == "ok"
    )
    fedora_alpha_gate_ready = (
        fedora_release_smoke_ready
        and str(checks_by_name.get("python_3_12_plus", {}).get("status")) == "ok"
        and str(checks_by_name.get("virtualenv_active", {}).get("status")) == "ok"
    )
    if fedora_alpha_gate_ready:
        insert_index = 3 if tray_run_ready else 2 if click_to_talk_ready else 0
        next_steps.insert(
            insert_index,
            PlatformSetupNextStep(
                label="Run Fedora alpha gate",
                command="./scripts/run_fedora_alpha_gate.sh --reset-user-services",
            ),
        )
    elif fedora_release_smoke_ready:
        release_label = "Run Fedora release smoke"
        release_command = "./scripts/run_fedora_release_smoke.sh"
        rpm_artifact_path = _default_rpm_package_artifact_path()
        if rpm_artifact_path.exists():
            release_label = "Run installed RPM beta smoke"
            release_command = shlex.join(
                [
                    "./scripts/run_installed_beta_smoke.sh",
                    "--package",
                    str(rpm_artifact_path),
                    "--installer",
                    "dnf",
                    "--require-mvp-runtime",
                    "--reset-user-services",
                    "--uninstall-after",
                ]
            )
        insert_index = 3 if tray_run_ready else 2 if click_to_talk_ready else 0
        next_steps.insert(
            insert_index,
            PlatformSetupNextStep(
                label=release_label,
                command=release_command,
            ),
        )
    return next_steps


def _click_to_talk_command() -> str:
    return "./scripts/run_click_to_talk.sh"


def _mvp_launch_command() -> str:
    return "./scripts/run_mvp.sh"


def _tray_run_command() -> str:
    return "./scripts/run_tray_app.sh"


def _build_bootstrap_command(
    checks_by_name: Mapping[str, dict[str, object]],
) -> str:
    command = "./scripts/install_linux_dev.sh"
    if str(checks_by_name.get("tray_ui_available", {}).get("status")) != "ok":
        command = f"{command} --ui"
    if _needs_voice_dependencies(checks_by_name):
        command = f"{command} --voice"
    return command


def _build_local_app_command(
    checks_by_name: Mapping[str, dict[str, object]],
) -> str:
    command = "./scripts/install_local_linux_app.sh"
    if _needs_voice_dependencies(checks_by_name):
        command = f"{command} --voice"
    return command


def _needs_voice_dependencies(
    checks_by_name: Mapping[str, dict[str, object]],
) -> bool:
    return any(
        str(checks_by_name.get(name, {}).get("status")) != "ok"
        for name in ("wakeword_backend_available", "stt_backend_available", "tts_backend_available")
    )


def _can_install_voice_loop_service(
    checks_by_name: Mapping[str, dict[str, object]],
) -> bool:
    required_statuses = (
        "python_3_12_plus",
        "virtualenv_active",
        "linux_platform",
        "kde_wayland_target",
        "xdg_open_available",
        "gdbus_available",
        "networkmanager_cli_available",
        "audio_cli_available",
        "audio_capture_cli_available",
        "systemctl_user_available",
        "power_status_available",
        "stt_backend_available",
    )
    return all(str(checks_by_name.get(name, {}).get("status")) == "ok" for name in required_statuses)


def _project_version() -> str:
    return project_version()


def _default_deb_package_artifact_path() -> Path:
    return Path(__file__).resolve().parents[3] / "dist" / "package-artifacts" / "deb" / f"operance_{_project_version()}_all.deb"


def _default_rpm_package_artifact_path() -> Path:
    return Path(__file__).resolve().parents[3] / "dist" / "package-artifacts" / "rpm" / f"operance-{_project_version()}-1.noarch.rpm"
