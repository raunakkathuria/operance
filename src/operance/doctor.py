"""Environment readiness checks for development and Linux handoff."""

from __future__ import annotations

import importlib.util
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from typing import Callable

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


def build_voice_loop_config_snapshot():
    from .voice.config import build_voice_loop_config_snapshot as _build_voice_loop_config_snapshot

    return _build_voice_loop_config_snapshot()


def build_voice_loop_runtime_status_snapshot():
    from .voice.runtime import (
        build_voice_loop_runtime_status_snapshot as _build_voice_loop_runtime_status_snapshot,
    )

    return _build_voice_loop_runtime_status_snapshot()


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
    power_supply_root = "/sys/class/power_supply"
    if not os.path.isdir(power_supply_root):
        return False
    return any(entry.startswith("BAT") for entry in os.listdir(power_supply_root))


def _planner_config() -> PlannerSettings:
    return AppConfig.from_env().planner


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
        return ("warn", detail)
    if not runtime_dir or not display:
        detail["message"] = "WAYLAND_DISPLAY or XDG_RUNTIME_DIR is not set."
        return ("warn", detail)

    socket_path = Path(runtime_dir) / display
    detail["socket_path"] = str(socket_path)
    if not socket_path.exists():
        detail["message"] = "Wayland socket path does not exist."
        return ("warn", detail)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(0.5)
        client.connect(str(socket_path))
    except OSError as exc:
        detail["message"] = str(exc)
        return ("warn", detail)
    finally:
        client.close()

    detail["message"] = "Wayland session socket is accessible."
    return ("ok", detail)


def _probe_text_input_backend(
    *,
    wayland_session_accessible: bool,
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    resolve_executable: Callable[[str], str | None] | None = None,
) -> tuple[str, dict[str, object]]:
    resolver = shutil.which if resolve_executable is None else resolve_executable
    wtype_path = resolver("wtype")
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
        return ("ok", detail)

    runner = run_command or (lambda command: subprocess.run(command, capture_output=True, text=True, check=False))
    result = runner(["wtype", "-M", "shift", "-m", "shift"])
    if result.returncode == 0:
        detail["backend_status"] = "ok"
        detail["message"] = "wtype backend is usable."
        return ("ok", detail)

    probe_error = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
    if "virtual keyboard protocol" in probe_error.casefold():
        detail["backend_status"] = "unsupported_protocol"
        detail["message"] = "wtype is installed but the compositor does not support the virtual keyboard protocol."
    else:
        detail["backend_status"] = "probe_failed"
        detail["message"] = "wtype is installed but the runtime probe failed."
    detail["probe_error"] = probe_error
    return ("warn", detail)


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


def _voice_asset_source_path(env_name: str) -> Path | None:
    raw_value = os.environ.get(env_name)
    if not raw_value:
        return None

    candidate = Path(raw_value).expanduser()
    if candidate.exists():
        return candidate
    return None


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
        Path("/etc/operance/voice-loop.args"),
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
    executable = systemctl_path or shutil.which("systemctl")
    if executable is None:
        return ("warn", "systemctl not found")

    try:
        completed = subprocess.run(
            [executable, "--user", subcommand, unit_name],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        return ("warn", str(exc))

    detail = completed.stdout.strip() or completed.stderr.strip()
    if not detail:
        detail = "ok" if completed.returncode == 0 else "unknown"

    return ("ok" if completed.returncode == 0 else "warn", detail)
