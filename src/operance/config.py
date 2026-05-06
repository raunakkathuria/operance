"""Application configuration for the Phase 0A scaffold."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def _parse_int(value: str | None, default: int) -> int:
    return default if value is None else int(value)


def _parse_float(value: str | None, default: float) -> float:
    return default if value is None else float(value)


@dataclass(slots=True, frozen=True)
class LoggingSettings:
    level: str = "INFO"
    json: bool = True


@dataclass(slots=True, frozen=True)
class RuntimeSettings:
    command_timeout_seconds: int = 5
    cooldown_seconds: float = 1.5
    confirmation_timeout_seconds: float = 30.0
    developer_mode: bool = True


@dataclass(slots=True, frozen=True)
class AudioSettings:
    wake_word_enabled: bool = False
    push_to_talk_enabled: bool = False


@dataclass(slots=True, frozen=True)
class PlannerSettings:
    enabled: bool = False
    min_confidence: float = 0.7
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "qwen2.5-7b-instruct"
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_consecutive_failures: int = 2
    failure_cooldown_seconds: float = 30.0


@dataclass(slots=True, frozen=True)
class PathsSettings:
    data_dir: Path
    log_dir: Path
    desktop_dir: Path

    @classmethod
    def default(cls) -> "PathsSettings":
        data_dir = Path.cwd() / ".operance"
        return cls(data_dir=data_dir, log_dir=data_dir / "logs", desktop_dir=data_dir / "Desktop")


@dataclass(slots=True, frozen=True)
class AppConfig:
    app_name: str
    environment: str
    paths: PathsSettings
    logging: LoggingSettings
    runtime: RuntimeSettings
    audio: AudioSettings
    planner: PlannerSettings

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AppConfig":
        source = dict(os.environ)
        source.update(env or {})

        default_paths = PathsSettings.default()
        data_dir = Path(source.get("OPERANCE_DATA_DIR", str(default_paths.data_dir))).expanduser()
        log_dir = Path(source.get("OPERANCE_LOG_DIR", str(data_dir / "logs"))).expanduser()
        desktop_dir = Path(
            source.get("OPERANCE_DESKTOP_DIR", str(default_paths.desktop_dir))
        ).expanduser()

        logging = LoggingSettings(
            level=source.get("OPERANCE_LOG_LEVEL", "INFO").upper(),
            json=_parse_bool(source.get("OPERANCE_LOG_JSON"), True),
        )
        runtime = RuntimeSettings(
            command_timeout_seconds=_parse_int(source.get("OPERANCE_COMMAND_TIMEOUT_SECONDS"), 5),
            cooldown_seconds=_parse_float(source.get("OPERANCE_COOLDOWN_SECONDS"), 1.5),
            confirmation_timeout_seconds=_parse_float(
                source.get("OPERANCE_CONFIRMATION_TIMEOUT_SECONDS"),
                30.0,
            ),
            developer_mode=_parse_bool(source.get("OPERANCE_DEVELOPER_MODE"), True),
        )
        audio = AudioSettings(
            wake_word_enabled=_parse_bool(source.get("OPERANCE_WAKE_WORD_ENABLED"), False),
            push_to_talk_enabled=_parse_bool(source.get("OPERANCE_PUSH_TO_TALK_ENABLED"), False),
        )
        planner = PlannerSettings(
            enabled=_parse_bool(source.get("OPERANCE_PLANNER_ENABLED"), False),
            min_confidence=_parse_float(source.get("OPERANCE_PLANNER_MIN_CONFIDENCE"), 0.7),
            endpoint=source.get(
                "OPERANCE_PLANNER_ENDPOINT",
                "http://127.0.0.1:8080/v1/chat/completions",
            ),
            model=source.get("OPERANCE_PLANNER_MODEL", "qwen2.5-7b-instruct"),
            timeout_seconds=_parse_float(source.get("OPERANCE_PLANNER_TIMEOUT_SECONDS"), 30.0),
            max_retries=_parse_int(source.get("OPERANCE_PLANNER_MAX_RETRIES"), 1),
            max_consecutive_failures=_parse_int(
                source.get("OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES"),
                2,
            ),
            failure_cooldown_seconds=_parse_float(
                source.get("OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS"),
                30.0,
            ),
        )

        return cls(
            app_name=source.get("OPERANCE_APP_NAME", "operance"),
            environment=source.get("OPERANCE_ENVIRONMENT", "development"),
            paths=PathsSettings(data_dir=data_dir, log_dir=log_dir, desktop_dir=desktop_dir),
            logging=logging,
            runtime=runtime,
            audio=audio,
            planner=planner,
        )

    def ensure_directories(self) -> None:
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.log_dir.mkdir(parents=True, exist_ok=True)
        self.paths.desktop_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "paths": {
                "data_dir": str(self.paths.data_dir),
                "log_dir": str(self.paths.log_dir),
                "desktop_dir": str(self.paths.desktop_dir),
            },
            "logging": {
                "level": self.logging.level,
                "json": self.logging.json,
            },
            "runtime": {
                "command_timeout_seconds": self.runtime.command_timeout_seconds,
                "cooldown_seconds": self.runtime.cooldown_seconds,
                "confirmation_timeout_seconds": self.runtime.confirmation_timeout_seconds,
                "developer_mode": self.runtime.developer_mode,
            },
            "audio": {
                "wake_word_enabled": self.audio.wake_word_enabled,
                "push_to_talk_enabled": self.audio.push_to_talk_enabled,
            },
            "planner": {
                "enabled": self.planner.enabled,
                "min_confidence": self.planner.min_confidence,
                "endpoint": self.planner.endpoint,
                "model": self.planner.model,
                "timeout_seconds": self.planner.timeout_seconds,
                "max_retries": self.planner.max_retries,
                "max_consecutive_failures": self.planner.max_consecutive_failures,
                "failure_cooldown_seconds": self.planner.failure_cooldown_seconds,
            },
        }
