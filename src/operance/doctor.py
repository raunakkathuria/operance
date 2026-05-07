"""Environment readiness checks for development and Linux handoff."""

from __future__ import annotations

import importlib.util
import os
import platform
from pathlib import Path
import sys

from .config import AppConfig, PlannerSettings
from .platforms import get_platform_provider
from .planner.client import PlannerServiceClient, PlannerServiceConfig
from .tts.assets import (
    find_existing_tts_model_path,
    find_existing_tts_voices_path,
    preferred_tts_model_path,
    preferred_tts_voices_path,
)
from .wakeword.assets import find_existing_wakeword_model_path, preferred_wakeword_model_path


def build_environment_report(system_name: str | None = None) -> dict[str, object]:
    system_value = system_name or platform.system()
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    tray_spec = importlib.util.find_spec("PySide6")
    wakeword_spec = importlib.util.find_spec("openwakeword")
    stt_spec = importlib.util.find_spec("moonshine_voice")
    tts_spec = importlib.util.find_spec("kokoro_onnx")
    soundfile_spec = importlib.util.find_spec("soundfile")
    provider = get_platform_provider(system_name=system_value)
    planner_config = _planner_config()
    planner_health_status, planner_health_detail = _probe_planner_health(planner_config)
    wakeword_model_path = find_existing_wakeword_model_path()
    wakeword_model_source_path = _voice_asset_source_path("OPERANCE_WAKEWORD_MODEL_SOURCE")
    tts_model_path = find_existing_tts_model_path()
    tts_model_source_path = _voice_asset_source_path("OPERANCE_TTS_MODEL_SOURCE")
    tts_voices_path = find_existing_tts_voices_path()
    tts_voices_source_path = _voice_asset_source_path("OPERANCE_TTS_VOICES_SOURCE")

    checks = [
        {
            "name": "python_3_12_plus",
            "status": "ok" if sys.version_info >= (3, 12) else "fail",
            "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        {
            "name": "virtualenv_active",
            "status": "ok" if in_venv else "warn",
            "detail": "active" if in_venv else "not detected",
        },
        {
            "name": "tray_ui_available",
            "status": "ok" if tray_spec is not None else "warn",
            "detail": tray_spec.origin if tray_spec is not None else "PySide6 not installed",
        },
        {
            "name": "wakeword_backend_available",
            "status": "ok" if wakeword_spec is not None else "warn",
            "detail": wakeword_spec.origin if wakeword_spec is not None else "openwakeword not installed",
        },
        {
            "name": "wakeword_model_asset_available",
            "status": "ok" if wakeword_model_path is not None else "warn",
            "detail": str(wakeword_model_path or preferred_wakeword_model_path()),
        },
        {
            "name": "wakeword_model_source_available",
            "status": "ok" if wakeword_model_source_path is not None else "warn",
            "detail": str(wakeword_model_source_path or "not set"),
        },
        {
            "name": "stt_backend_available",
            "status": "ok" if stt_spec is not None else "warn",
            "detail": stt_spec.origin if stt_spec is not None else "moonshine-voice not installed",
        },
        {
            "name": "tts_backend_available",
            "status": "ok" if tts_spec is not None and soundfile_spec is not None else "warn",
            "detail": {
                "kokoro_onnx": tts_spec.origin if tts_spec is not None else "kokoro-onnx not installed",
                "soundfile": soundfile_spec.origin if soundfile_spec is not None else "soundfile not installed",
            },
        },
        {
            "name": "tts_model_asset_available",
            "status": "ok" if tts_model_path is not None else "warn",
            "detail": str(tts_model_path or preferred_tts_model_path()),
        },
        {
            "name": "tts_model_source_available",
            "status": "ok" if tts_model_source_path is not None else "warn",
            "detail": str(tts_model_source_path or "not set"),
        },
        {
            "name": "tts_voices_asset_available",
            "status": "ok" if tts_voices_path is not None else "warn",
            "detail": str(tts_voices_path or preferred_tts_voices_path()),
        },
        {
            "name": "tts_voices_source_available",
            "status": "ok" if tts_voices_source_path is not None else "warn",
            "detail": str(tts_voices_source_path or "not set"),
        },
        {
            "name": "planner_runtime_enabled",
            "status": "ok" if planner_config.enabled else "warn",
            "detail": {
                "enabled": planner_config.enabled,
                "endpoint": planner_config.endpoint,
                "model": planner_config.model,
            },
        },
        {
            "name": "planner_endpoint_healthy",
            "status": planner_health_status,
            "detail": planner_health_detail,
        },
    ]
    checks.extend(provider.build_environment_checks())

    return {
        "platform": system_value,
        "platform_provider": provider.provider_id,
        "python_version": platform.python_version(),
        "checks": checks,
    }


def _planner_config() -> PlannerSettings:
    return AppConfig.from_env().planner


def _probe_planner_health(planner_config: PlannerSettings) -> tuple[str, object]:
    if not planner_config.enabled:
        return (
            "warn",
            {
                "status": "disabled",
                "endpoint": planner_config.endpoint,
                "model": planner_config.model,
                "message": "planner runtime is disabled",
            },
        )

    client = PlannerServiceClient(
        PlannerServiceConfig(
            endpoint=planner_config.endpoint,
            model=planner_config.model,
            timeout_seconds=min(planner_config.timeout_seconds, 1.0),
            max_retries=0,
        )
    )
    health = client.health()
    return ("ok" if health.get("status") == "ok" else "warn", health)


def _voice_asset_source_path(env_name: str) -> Path | None:
    raw_value = os.environ.get(env_name)
    if not raw_value:
        return None

    candidate = Path(raw_value).expanduser()
    if candidate.exists():
        return candidate
    return None
