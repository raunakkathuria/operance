from datetime import datetime, timezone


def _voice_loop_config_snapshot():
    from operance.voice.config import EffectiveVoiceLoopConfig, VoiceLoopConfigSnapshot

    return VoiceLoopConfigSnapshot(
        launcher_mode="repo_local",
        explicit_args_file=None,
        search_paths=["/repo/.operance/voice-loop.args"],
        selected_args_file="/repo/.operance/voice-loop.args",
        configured_args=["--wakeword-threshold", "0.844"],
        effective=EffectiveVoiceLoopConfig(
            wakeword_threshold=0.844,
            wakeword_threshold_source="args_file",
            wakeword_model=None,
            wakeword_model_source="default",
            wakeword_mode="energy_fallback",
            wakeword_auto_model_path=None,
            voice_loop_max_frames=None,
            voice_loop_max_frames_source="default",
            voice_loop_max_commands=None,
            voice_loop_max_commands_source="default",
            passthrough_args=[],
        ),
    )


def _voice_loop_runtime_snapshot(*, heartbeat_fresh: bool = True):
    from operance.voice.runtime import VoiceLoopRuntimeStatusSnapshot

    return VoiceLoopRuntimeStatusSnapshot(
        status_file_path="/repo/.operance/voice-loop-status.json",
        status_file_exists=True,
        status="ok" if heartbeat_fresh else "warn",
        message=(
            "Voice-loop runtime heartbeat is fresh."
            if heartbeat_fresh
            else "Voice-loop runtime heartbeat is stale."
        ),
        loop_state="waiting_for_wake",
        daemon_state="IDLE",
        started_at=datetime(2026, 4, 30, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 30, 1, 0, 1, tzinfo=timezone.utc),
        stopped_at=None,
        heartbeat_age_seconds=1.0 if heartbeat_fresh else 45.0,
        heartbeat_timeout_seconds=30.0,
        heartbeat_fresh=heartbeat_fresh,
        processed_frames=24,
        wake_detections=1,
        completed_commands=2,
        awaiting_confirmation=False,
        last_wake_phrase="operance",
        last_wake_confidence=0.88,
        last_transcript_text="open firefox",
        last_transcript_final=True,
        last_response_text="Launched firefox",
        last_response_status="success",
        stopped_reason=None,
    )


def test_build_voice_loop_service_snapshot_reports_install_recommendation(monkeypatch) -> None:
    from operance.voice.service import build_voice_loop_service_snapshot

    monkeypatch.setattr(
        "operance.voice.service.build_environment_report",
        lambda: {
            "checks": [
                {"name": "voice_loop_user_service_installed", "status": "warn", "detail": "/home/test/.config/systemd/user/operance-voice-loop.service"},
                {"name": "voice_loop_user_service_enabled", "status": "warn", "detail": "not-found"},
                {"name": "voice_loop_user_service_active", "status": "warn", "detail": "inactive"},
            ]
        },
    )
    monkeypatch.setattr("operance.voice.service.build_voice_loop_config_snapshot", lambda env=None: _voice_loop_config_snapshot())
    monkeypatch.setattr(
        "operance.voice.service.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _voice_loop_runtime_snapshot(),
    )

    snapshot = build_voice_loop_service_snapshot()

    assert snapshot.status == "warn"
    assert snapshot.message == "Voice-loop user service is not installed."
    assert snapshot.recommended_command == "./scripts/install_voice_loop_user_service.sh"
    assert snapshot.service_installed is False


def test_build_voice_loop_service_snapshot_reports_restart_for_stale_runtime(monkeypatch) -> None:
    from operance.voice.service import build_voice_loop_service_snapshot

    monkeypatch.setattr(
        "operance.voice.service.build_environment_report",
        lambda: {
            "checks": [
                {"name": "voice_loop_user_service_installed", "status": "ok", "detail": "/home/test/.config/systemd/user/operance-voice-loop.service"},
                {"name": "voice_loop_user_service_enabled", "status": "ok", "detail": "enabled"},
                {"name": "voice_loop_user_service_active", "status": "ok", "detail": "active"},
            ]
        },
    )
    monkeypatch.setattr("operance.voice.service.build_voice_loop_config_snapshot", lambda env=None: _voice_loop_config_snapshot())
    monkeypatch.setattr(
        "operance.voice.service.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _voice_loop_runtime_snapshot(heartbeat_fresh=False),
    )

    snapshot = build_voice_loop_service_snapshot()

    assert snapshot.status == "warn"
    assert snapshot.message == "Voice-loop user service is active but the runtime heartbeat is stale."
    assert snapshot.recommended_command == "./scripts/control_systemd_user_services.sh restart --voice-loop"
    assert snapshot.service_active is True


def test_build_voice_loop_service_snapshot_reports_healthy_service(monkeypatch) -> None:
    from operance.voice.service import build_voice_loop_service_snapshot

    monkeypatch.setattr(
        "operance.voice.service.build_environment_report",
        lambda: {
            "checks": [
                {"name": "voice_loop_user_service_installed", "status": "ok", "detail": "/home/test/.config/systemd/user/operance-voice-loop.service"},
                {"name": "voice_loop_user_service_enabled", "status": "ok", "detail": "enabled"},
                {"name": "voice_loop_user_service_active", "status": "ok", "detail": "active"},
            ]
        },
    )
    monkeypatch.setattr("operance.voice.service.build_voice_loop_config_snapshot", lambda env=None: _voice_loop_config_snapshot())
    monkeypatch.setattr(
        "operance.voice.service.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _voice_loop_runtime_snapshot(),
    )

    snapshot = build_voice_loop_service_snapshot()

    assert snapshot.status == "ok"
    assert snapshot.message == "Voice-loop user service is active and healthy."
    assert snapshot.recommended_command is None
    assert snapshot.config.selected_args_file == "/repo/.operance/voice-loop.args"
    assert snapshot.runtime.heartbeat_fresh is True
