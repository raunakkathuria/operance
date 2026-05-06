"""Continuous voice-loop runtime status helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from ..config import AppConfig
from ..models.base import SerializableModel, utc_now

_VOICE_LOOP_STATUS_FILENAME = "voice-loop-status.json"
_DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30.0
_STATUS_WRITE_INTERVAL_FRAMES = 10


def voice_loop_status_path(*, env: Mapping[str, str] | None = None) -> Path:
    return AppConfig.from_env(env).paths.data_dir / _VOICE_LOOP_STATUS_FILENAME


@dataclass(slots=True, frozen=True)
class VoiceLoopRuntimeStatusSnapshot(SerializableModel):
    status_file_path: str
    status_file_exists: bool
    status: str
    message: str
    loop_state: str
    daemon_state: str | None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    stopped_at: datetime | None = None
    heartbeat_age_seconds: float | None = None
    heartbeat_timeout_seconds: float = _DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
    heartbeat_fresh: bool = False
    processed_frames: int = 0
    wake_detections: int = 0
    completed_commands: int = 0
    awaiting_confirmation: bool = False
    last_wake_phrase: str | None = None
    last_wake_confidence: float | None = None
    last_transcript_text: str | None = None
    last_transcript_final: bool | None = None
    last_response_text: str | None = None
    last_response_status: str | None = None
    stopped_reason: str | None = None


class VoiceLoopRuntimeStatusWriter:
    """Write coarse runtime heartbeat information for the continuous voice loop."""

    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.path = voice_loop_status_path(env=env)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started_at = utc_now().isoformat()
        self._payload: dict[str, object] = {
            "awaiting_confirmation": False,
            "completed_commands": 0,
            "daemon_state": None,
            "last_response_status": None,
            "last_response_text": None,
            "last_transcript_final": None,
            "last_transcript_text": None,
            "last_wake_confidence": None,
            "last_wake_phrase": None,
            "loop_state": "starting",
            "processed_frames": 0,
            "started_at": started_at,
            "stopped_at": None,
            "stopped_reason": None,
            "updated_at": started_at,
            "wake_detections": 0,
        }
        self._last_heartbeat_frame = 0
        self._write()

    def update(self, **fields: object) -> None:
        self._payload.update(fields)
        self._payload["updated_at"] = utc_now().isoformat()
        self._write()

    def heartbeat(
        self,
        *,
        processed_frames: int,
        loop_state: str,
        daemon_state: str,
        awaiting_confirmation: bool,
        completed_commands: int,
    ) -> None:
        if processed_frames > 0 and processed_frames - self._last_heartbeat_frame < _STATUS_WRITE_INTERVAL_FRAMES:
            return
        self._last_heartbeat_frame = processed_frames
        self.update(
            processed_frames=processed_frames,
            loop_state=loop_state,
            daemon_state=daemon_state,
            awaiting_confirmation=awaiting_confirmation,
            completed_commands=completed_commands,
        )

    def stop(
        self,
        *,
        processed_frames: int,
        loop_state: str,
        daemon_state: str,
        awaiting_confirmation: bool,
        completed_commands: int,
        stopped_reason: str,
    ) -> None:
        stopped_at = utc_now().isoformat()
        self._payload.update(
            {
                "processed_frames": processed_frames,
                "loop_state": loop_state,
                "daemon_state": daemon_state,
                "awaiting_confirmation": awaiting_confirmation,
                "completed_commands": completed_commands,
                "stopped_at": stopped_at,
                "stopped_reason": stopped_reason,
                "updated_at": stopped_at,
            }
        )
        self._write()

    def _write(self) -> None:
        self.path.write_text(json.dumps(self._payload, sort_keys=True), encoding="utf-8")


def build_voice_loop_runtime_status_snapshot(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    heartbeat_timeout_seconds: float = _DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
) -> VoiceLoopRuntimeStatusSnapshot:
    status_path = voice_loop_status_path(env=env)
    if not status_path.exists():
        return VoiceLoopRuntimeStatusSnapshot(
            status_file_path=str(status_path),
            status_file_exists=False,
            status="warn",
            message="No voice-loop runtime status file found.",
            loop_state="missing",
            daemon_state=None,
            heartbeat_timeout_seconds=heartbeat_timeout_seconds,
        )

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return VoiceLoopRuntimeStatusSnapshot(
            status_file_path=str(status_path),
            status_file_exists=True,
            status="warn",
            message="Voice-loop runtime status file could not be parsed.",
            loop_state="invalid",
            daemon_state=None,
            heartbeat_timeout_seconds=heartbeat_timeout_seconds,
        )

    if not isinstance(payload, dict):
        return VoiceLoopRuntimeStatusSnapshot(
            status_file_path=str(status_path),
            status_file_exists=True,
            status="warn",
            message="Voice-loop runtime status file has an invalid payload shape.",
            loop_state="invalid",
            daemon_state=None,
            heartbeat_timeout_seconds=heartbeat_timeout_seconds,
        )

    current_time = utc_now() if now is None else now
    started_at = _parse_datetime(payload.get("started_at"))
    updated_at = _parse_datetime(payload.get("updated_at"))
    stopped_at = _parse_datetime(payload.get("stopped_at"))
    heartbeat_age_seconds = (
        max((current_time - updated_at).total_seconds(), 0.0) if updated_at is not None else None
    )
    heartbeat_fresh = (
        heartbeat_age_seconds is not None and heartbeat_age_seconds <= heartbeat_timeout_seconds
    )
    loop_state = _string_value(payload.get("loop_state")) or "unknown"
    daemon_state = _string_value(payload.get("daemon_state"))

    if updated_at is None:
        status = "warn"
        message = "Voice-loop runtime status file is missing heartbeat timestamps."
    elif loop_state == "stopped":
        status = "ok"
        message = "Voice-loop is not running; showing the last recorded status."
    elif heartbeat_fresh:
        status = "ok"
        message = "Voice-loop runtime heartbeat is fresh."
    else:
        status = "warn"
        message = "Voice-loop runtime heartbeat is stale."

    return VoiceLoopRuntimeStatusSnapshot(
        status_file_path=str(status_path),
        status_file_exists=True,
        status=status,
        message=message,
        loop_state=loop_state,
        daemon_state=daemon_state,
        started_at=started_at,
        updated_at=updated_at,
        stopped_at=stopped_at,
        heartbeat_age_seconds=heartbeat_age_seconds,
        heartbeat_timeout_seconds=heartbeat_timeout_seconds,
        heartbeat_fresh=heartbeat_fresh,
        processed_frames=_int_value(payload.get("processed_frames")),
        wake_detections=_int_value(payload.get("wake_detections")),
        completed_commands=_int_value(payload.get("completed_commands")),
        awaiting_confirmation=bool(payload.get("awaiting_confirmation", False)),
        last_wake_phrase=_string_value(payload.get("last_wake_phrase")),
        last_wake_confidence=_float_value(payload.get("last_wake_confidence")),
        last_transcript_text=_string_value(payload.get("last_transcript_text")),
        last_transcript_final=_bool_value(payload.get("last_transcript_final")),
        last_response_text=_string_value(payload.get("last_response_text")),
        last_response_status=_string_value(payload.get("last_response_status")),
        stopped_reason=_string_value(payload.get("stopped_reason")),
    )


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


def _float_value(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _bool_value(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
