"""Voice-loop service health inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..doctor import build_environment_report
from ..models.base import SerializableModel
from .config import VoiceLoopConfigSnapshot, build_voice_loop_config_snapshot
from .runtime import VoiceLoopRuntimeStatusSnapshot, build_voice_loop_runtime_status_snapshot


@dataclass(slots=True, frozen=True)
class VoiceLoopServiceSnapshot(SerializableModel):
    status: str
    message: str
    recommended_command: str | None
    service_installed: bool
    service_installed_detail: str | None
    service_enabled: bool
    service_enabled_detail: str | None
    service_active: bool
    service_active_detail: str | None
    config: VoiceLoopConfigSnapshot
    runtime: VoiceLoopRuntimeStatusSnapshot


def build_voice_loop_service_snapshot(
    *,
    env: Mapping[str, str] | None = None,
    report: dict[str, object] | None = None,
) -> VoiceLoopServiceSnapshot:
    checks_by_name = {
        str(check.get("name")): check
        for check in (build_environment_report().get("checks", []) if report is None else report.get("checks", []))
        if isinstance(check, dict) and check.get("name") is not None
    }
    config = build_voice_loop_config_snapshot(env=env)
    runtime = build_voice_loop_runtime_status_snapshot(env=env)
    service_installed = str(checks_by_name.get("voice_loop_user_service_installed", {}).get("status")) == "ok"
    service_enabled = str(checks_by_name.get("voice_loop_user_service_enabled", {}).get("status")) == "ok"
    service_active = str(checks_by_name.get("voice_loop_user_service_active", {}).get("status")) == "ok"

    status = "ok"
    message = "Voice-loop user service is active and healthy."
    recommended_command = None

    if not service_installed:
        status = "warn"
        message = "Voice-loop user service is not installed."
        recommended_command = "./scripts/install_voice_loop_user_service.sh"
    elif not service_enabled:
        status = "warn"
        message = "Voice-loop user service is installed but not enabled."
        recommended_command = "./scripts/control_systemd_user_services.sh enable --voice-loop"
    elif not service_active:
        status = "warn"
        message = "Voice-loop user service is enabled but not active."
        recommended_command = "./scripts/control_systemd_user_services.sh restart --voice-loop"
    elif not runtime.heartbeat_fresh:
        status = "warn"
        message = "Voice-loop user service is active but the runtime heartbeat is stale."
        recommended_command = "./scripts/control_systemd_user_services.sh restart --voice-loop"

    return VoiceLoopServiceSnapshot(
        status=status,
        message=message,
        recommended_command=recommended_command,
        service_installed=service_installed,
        service_installed_detail=_detail_text(checks_by_name, "voice_loop_user_service_installed"),
        service_enabled=service_enabled,
        service_enabled_detail=_detail_text(checks_by_name, "voice_loop_user_service_enabled"),
        service_active=service_active,
        service_active_detail=_detail_text(checks_by_name, "voice_loop_user_service_active"),
        config=config,
        runtime=runtime,
    )


def _detail_text(checks_by_name: dict[str, dict[str, object]], name: str) -> str | None:
    detail = checks_by_name.get(name, {}).get("detail")
    if detail is None:
        return None
    return str(detail)
