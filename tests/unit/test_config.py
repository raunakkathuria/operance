from pathlib import Path

from operance.config import AppConfig


def test_config_uses_workspace_local_defaults() -> None:
    config = AppConfig.from_env({})

    assert config.app_name == "operance"
    assert config.environment == "development"
    assert config.paths.data_dir == Path.cwd() / ".operance"
    assert config.paths.log_dir == Path.cwd() / ".operance" / "logs"
    assert config.paths.desktop_dir == Path.cwd() / ".operance" / "Desktop"
    assert config.runtime.developer_mode is True


def test_config_applies_environment_overrides(tmp_path: Path) -> None:
    config = AppConfig.from_env(
        {
            "OPERANCE_ENVIRONMENT": "test",
            "OPERANCE_LOG_LEVEL": "debug",
            "OPERANCE_LOG_JSON": "false",
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_LOG_DIR": str(tmp_path / "logs"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "desktop"),
            "OPERANCE_COMMAND_TIMEOUT_SECONDS": "9",
            "OPERANCE_COOLDOWN_SECONDS": "2.5",
            "OPERANCE_CONFIRMATION_TIMEOUT_SECONDS": "45",
            "OPERANCE_DEVELOPER_MODE": "0",
            "OPERANCE_WAKE_WORD_ENABLED": "yes",
            "OPERANCE_PUSH_TO_TALK_ENABLED": "1",
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_MIN_CONFIDENCE": "0.85",
            "OPERANCE_PLANNER_TIMEOUT_SECONDS": "11.5",
            "OPERANCE_PLANNER_MAX_RETRIES": "2",
            "OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES": "3",
            "OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS": "18",
            "OPERANCE_PLANNER_ENDPOINT": "http://127.0.0.1:8081/v1/chat/completions",
            "OPERANCE_PLANNER_MODEL": "qwen-test",
        }
    )

    assert config.environment == "test"
    assert config.logging.level == "DEBUG"
    assert config.logging.json is False
    assert config.paths.data_dir == tmp_path / "data"
    assert config.paths.log_dir == tmp_path / "logs"
    assert config.paths.desktop_dir == tmp_path / "desktop"
    assert config.runtime.command_timeout_seconds == 9
    assert config.runtime.cooldown_seconds == 2.5
    assert config.runtime.confirmation_timeout_seconds == 45.0
    assert config.runtime.developer_mode is False
    assert config.audio.wake_word_enabled is True
    assert config.audio.push_to_talk_enabled is True
    assert config.planner.enabled is True
    assert config.planner.min_confidence == 0.85
    assert config.planner.timeout_seconds == 11.5
    assert config.planner.max_retries == 2
    assert config.planner.max_consecutive_failures == 3
    assert config.planner.failure_cooldown_seconds == 18.0
    assert config.planner.endpoint == "http://127.0.0.1:8081/v1/chat/completions"
    assert config.planner.model == "qwen-test"


def test_config_reads_process_environment_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPERANCE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPERANCE_DEVELOPER_MODE", "0")
    monkeypatch.setenv("OPERANCE_PLANNER_ENABLED", "1")

    config = AppConfig.from_env()

    assert config.paths.data_dir == tmp_path / "data"
    assert config.runtime.developer_mode is False
    assert config.planner.enabled is True
