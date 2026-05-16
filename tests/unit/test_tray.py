from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from operance.models.events import RuntimeState
from operance.status import StatusSnapshot
from operance.voice.runtime import VoiceLoopRuntimeStatusSnapshot


def _status_snapshot(**overrides: object) -> StatusSnapshot:
    payload: dict[str, object] = {
        "current_state": RuntimeState.IDLE,
        "last_transcript": None,
        "last_response": None,
        "last_command_status": None,
        "last_plan_source": None,
        "last_routing_reason": None,
        "last_planner_error": None,
        "planner_consecutive_failures": 0,
        "planner_cooldown_remaining_seconds": None,
        "planner_context_entry_count": 0,
        "planner_context_messages": [],
        "pending_confirmation": False,
        "pending_plan_id": None,
        "pending_plan_preview": None,
        "pending_original_text": None,
        "pending_source": None,
        "pending_risk_tier": None,
        "pending_action": None,
        "pending_affected_resources": [],
        "pending_rollback_hint": None,
        "pending_timeout_seconds": None,
        "pending_timeout_behavior": None,
        "undo_available": False,
        "last_undo_tool": None,
        "completed_commands": 0,
        "p95_latency_ms": None,
    }
    payload.update(overrides)
    return StatusSnapshot(**payload)


def _voice_loop_status_snapshot(**overrides: object) -> VoiceLoopRuntimeStatusSnapshot:
    payload: dict[str, object] = {
        "status_file_path": "/repo/.operance/voice-loop-status.json",
        "status_file_exists": True,
        "status": "ok",
        "message": "Voice-loop runtime heartbeat is fresh.",
        "loop_state": "waiting_for_wake",
        "daemon_state": "IDLE",
        "started_at": datetime(2026, 4, 30, 1, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 30, 1, 0, 1, tzinfo=timezone.utc),
        "stopped_at": None,
        "heartbeat_age_seconds": 1.0,
        "heartbeat_timeout_seconds": 30.0,
        "heartbeat_fresh": True,
        "processed_frames": 42,
        "wake_detections": 2,
        "completed_commands": 1,
        "awaiting_confirmation": False,
        "last_wake_phrase": "operance",
        "last_wake_confidence": 0.91,
        "last_transcript_text": "what is the volume",
        "last_transcript_final": True,
        "last_response_text": "Volume is 30%",
        "last_response_status": "success",
        "stopped_reason": None,
    }
    payload.update(overrides)
    return VoiceLoopRuntimeStatusSnapshot(**payload)


def test_build_tray_snapshot_reports_idle_state() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(_status_snapshot())

    payload = snapshot.to_dict()

    assert payload["current_state"] == "IDLE"
    assert payload["tray_state"] == "idle"
    assert payload["mic_state"] == "inactive"
    assert payload["state_label"] == "Idle"
    assert payload["voice_loop_status"] is None
    assert payload["voice_loop_state"] is None
    assert payload["voice_loop_heartbeat_fresh"] is None
    assert payload["voice_loop_message"] is None
    assert payload["voice_loop_activity"] is None
    assert payload["voice_loop_last_transcript"] is None
    assert payload["voice_loop_last_response"] is None
    assert payload["last_command_transcript"] is None
    assert payload["last_command_preview"] is None
    assert payload["last_interaction"] is None
    assert payload["pending_confirmation_prompt"] is None
    assert payload["click_to_talk_label"] == "Click to talk"
    assert payload["can_start_click_to_talk"] is True
    assert payload["can_confirm"] is False
    assert payload["can_cancel"] is False
    assert payload["can_undo"] is False
    assert payload["can_reset_planner"] is False
    assert payload["can_restart_voice_loop_service"] is False
    assert payload["tooltip"] == "Operance: Idle | Left-click to talk"


def test_build_tray_snapshot_marks_developer_mode_as_simulated() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(_status_snapshot(), developer_mode=True)

    payload = snapshot.to_dict()

    assert payload["developer_mode"] is True
    assert payload["state_label"] == "Idle (simulated)"
    assert payload["tooltip"] == (
        "Operance: Idle (simulated) | Developer mode uses simulated adapters | Left-click to talk"
    )


def test_build_tray_snapshot_reports_pending_confirmation() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.AWAITING_CONFIRMATION,
            last_transcript="close window firefox",
            last_response="Command requires confirmation.",
            last_command_status="awaiting_confirmation",
            pending_confirmation=True,
            pending_plan_id="plan-1",
            pending_plan_preview="Planned action: close window 'firefox'.",
            pending_original_text="close window firefox",
            pending_source="deterministic",
            pending_risk_tier=2,
            pending_action={"tool": "windows.close"},
            pending_affected_resources=["window: firefox"],
            pending_rollback_hint="No automatic undo is available after execution.",
            pending_timeout_seconds=30.0,
            pending_timeout_behavior="Pending command expires after 30 seconds without confirmation.",
            completed_commands=1,
            p95_latency_ms=123.0,
        )
    )

    payload = snapshot.to_dict()

    assert payload["tray_state"] == "attention"
    assert payload["mic_state"] == "inactive"
    assert payload["state_label"] == "Confirmation needed"
    assert payload["last_command_transcript"] == "close window firefox"
    assert payload["last_command_preview"] == "Command requires confirmation."
    assert payload["pending_confirmation_prompt"] == "Planned action: close window 'firefox'."
    assert payload["click_to_talk_label"] == "Reply to pending command"
    assert payload["can_start_click_to_talk"] is True
    assert payload["can_confirm"] is True
    assert payload["can_cancel"] is True
    assert payload["can_undo"] is False
    assert payload["can_reset_planner"] is False
    assert payload["confirmation_dialog"] == {
        "cancel_label": "Cancel",
        "confirm_label": "Confirm",
        "details": [
            "Original command: close window firefox",
            "Source: deterministic",
            "Risk tier: 2",
            "Affected: window: firefox",
            "Rollback: No automatic undo is available after execution.",
            "Timeout: Pending command expires after 30 seconds without confirmation.",
        ],
        "message": "Planned action: close window 'firefox'.",
        "title": "Confirm pending command",
    }
    assert payload["notification"] is None


def test_build_tray_snapshot_includes_voice_loop_runtime_projection() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(),
        voice_loop_status=_voice_loop_status_snapshot(),
    )

    payload = snapshot.to_dict()

    assert payload["voice_loop_status"] == "ok"
    assert payload["voice_loop_state"] == "waiting_for_wake"
    assert payload["voice_loop_heartbeat_fresh"] is True
    assert payload["voice_loop_message"] == "Voice-loop runtime heartbeat is fresh."
    assert payload["voice_loop_activity"] == "Waiting for wake word"
    assert payload["voice_loop_last_transcript"] == "what is the volume"
    assert payload["voice_loop_last_response"] == "Volume is 30%"
    assert payload["last_command_transcript"] is None
    assert payload["last_command_preview"] is None
    assert payload["can_restart_voice_loop_service"] is False
    assert payload["tooltip"] == "Operance: Idle | Left-click to talk"


def test_build_tray_snapshot_reports_voice_loop_warning_notification() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(),
        voice_loop_status=_voice_loop_status_snapshot(
            status="warn",
            message="Voice-loop runtime heartbeat is stale.",
            loop_state="waiting_for_wake",
            heartbeat_fresh=False,
            heartbeat_age_seconds=42.0,
        ),
    )

    payload = snapshot.to_dict()

    assert payload["notification"] == {
        "event_id": "voice_loop:waiting_for_wake:Voice-loop runtime heartbeat is stale.",
        "level": "warning",
        "message": "Voice-loop runtime heartbeat is stale.",
        "title": "Voice loop needs attention",
    }
    assert payload["voice_loop_heartbeat_fresh"] is False
    assert payload["can_restart_voice_loop_service"] is True


def test_build_tray_snapshot_treats_missing_voice_loop_status_as_click_to_talk_optional() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(),
        voice_loop_status=_voice_loop_status_snapshot(
            status_file_exists=False,
            status="warn",
            message="No voice-loop runtime status file found.",
            loop_state="missing",
            heartbeat_fresh=False,
            heartbeat_age_seconds=None,
        ),
    )

    payload = snapshot.to_dict()

    assert payload["notification"] is None
    assert payload["can_restart_voice_loop_service"] is False
    assert payload["can_start_click_to_talk"] is True
    assert payload["tooltip"] == "Operance: Idle | Left-click to talk"


def test_build_tray_startup_notification_prefers_click_to_talk_hint() -> None:
    from operance.ui import build_tray_snapshot
    from operance.ui.tray import build_startup_notification

    snapshot = build_tray_snapshot(
        _status_snapshot(),
        voice_loop_status=_voice_loop_status_snapshot(),
    )

    notification = build_startup_notification(snapshot)

    assert notification is not None
    assert notification.to_dict() == {
        "event_id": "startup:click_to_talk",
        "level": "info",
        "message": "Left-click the tray icon to talk. Right-click for supported commands.",
        "title": "Operance is ready",
    }


def test_build_tray_startup_notification_skips_attention_states() -> None:
    from operance.ui import build_tray_snapshot
    from operance.ui.tray import build_startup_notification

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.AWAITING_CONFIRMATION,
            pending_confirmation=True,
            pending_plan_preview="Planned action: close window 'firefox'.",
        )
    )

    assert build_startup_notification(snapshot) is None


def test_build_installed_readiness_report_summarizes_ok_result() -> None:
    from operance.installed_smoke import InstalledSmokeCheck, InstalledSmokeResult
    from operance.ui.tray import (
        build_installed_readiness_notification,
        build_installed_readiness_report,
    )

    report = build_installed_readiness_report(
        InstalledSmokeResult(
            status="ok",
            checks=[
                InstalledSmokeCheck(
                    name="installed_live_mode",
                    status="ok",
                    detail={"developer_mode": False},
                )
            ],
            next_steps=["systemctl --user status operance-tray.service --no-pager"],
            manual_checks=["Click the tray icon and say: open firefox"],
        )
    )

    assert report.to_dict() == {
        "details": [
            "All installed package checks passed.",
            "Next steps:",
            "- systemctl --user status operance-tray.service --no-pager",
            "Manual click-to-talk checks:",
            "- Click the tray icon and say: open firefox",
        ],
        "status": "ok",
        "summary": "Installed package is ready for tray click-to-talk.",
        "title": "Installed package readiness",
    }
    assert build_installed_readiness_notification(report) is None


def test_build_installed_readiness_report_surfaces_next_steps_for_failures() -> None:
    from operance.installed_smoke import InstalledSmokeCheck, InstalledSmokeResult
    from operance.ui.tray import (
        build_installed_readiness_notification,
        build_installed_readiness_report,
    )

    report = build_installed_readiness_report(
        InstalledSmokeResult(
            status="failed",
            checks=[
                InstalledSmokeCheck(
                    name="tray_user_service_not_shadowed",
                    status="failed",
                    detail={"fragment_path": "/home/test/.config/systemd/user/operance-tray.service"},
                    suggested_command="Remove stale user units or reinstall with --reset-user-services.",
                )
            ],
            next_steps=["Remove stale user units or reinstall with --reset-user-services."],
            manual_checks=["Click the tray icon and say: open firefox"],
        )
    )

    notification = build_installed_readiness_notification(report)

    assert report.status == "failed"
    assert report.summary == "Installed package is not ready for the supported tray path."
    assert report.details == [
        "Checks needing attention:",
        "- failed: tray_user_service_not_shadowed: fragment_path=/home/test/.config/systemd/user/operance-tray.service; next: Remove stale user units or reinstall with --reset-user-services.",
        "Next steps:",
        "- Remove stale user units or reinstall with --reset-user-services.",
        "Manual click-to-talk checks:",
        "- Click the tray icon and say: open firefox",
    ]
    assert notification is not None
    assert notification.to_dict() == {
        "event_id": (
            "installed_readiness:failed:"
            "Installed package is not ready for the supported tray path."
        ),
        "level": "error",
        "message": "Installed package is not ready for the supported tray path.",
        "title": "Installed package needs attention",
    }


def test_tray_controller_can_build_installed_readiness_report(monkeypatch, tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.installed_smoke import InstalledSmokeResult
    from operance.ui import TrayController

    seen_env: list[object] = []

    def fake_smoke_result(*, env=None):
        seen_env.append(env)
        return InstalledSmokeResult(
            status="warn",
            checks=[],
            next_steps=["systemctl --user enable --now operance-tray.service"],
            manual_checks=[],
        )

    monkeypatch.setattr("operance.ui.tray.build_installed_smoke_result", fake_smoke_result)
    env = {
        "OPERANCE_DATA_DIR": str(tmp_path / "data"),
        "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        "OPERANCE_DEVELOPER_MODE": "0",
    }
    daemon = OperanceDaemon.build_default(env)

    controller = TrayController(daemon, env=env)
    report = controller.installed_readiness_report()

    assert seen_env == [env]
    assert report.status == "warn"
    assert report.summary == "Installed package is usable, but one or more checks need attention."
    assert report.details == [
        "No individual check failures were reported.",
        "Next steps:",
        "- systemctl --user enable --now operance-tray.service",
    ]


def test_build_click_to_talk_started_notification() -> None:
    from operance.ui.tray import build_click_to_talk_started_notification

    notification = build_click_to_talk_started_notification()

    assert notification.to_dict() == {
        "event_id": "click_to_talk:started",
        "level": "info",
        "message": "Speak a command now. Operance will stop listening automatically.",
        "title": "Listening",
    }


def test_acquire_tray_instance_lock_rejects_duplicate_process(tmp_path: Path) -> None:
    from operance.ui.tray import _acquire_tray_instance_lock, _release_tray_instance_lock

    lock_path = tmp_path / "operance-tray.lock"
    lock_handle = _acquire_tray_instance_lock(lock_path)

    try:
        with pytest.raises(ValueError, match="Operance tray is already running"):
            _acquire_tray_instance_lock(lock_path)
    finally:
        _release_tray_instance_lock(lock_handle)


def test_build_tray_icon_prefers_operance_theme_icon() -> None:
    from operance.ui.tray import _build_tray_icon

    class FakeIcon:
        theme_names: list[str] = []

        def __init__(self, source: str, *, null: bool = False) -> None:
            self.source = source
            self._null = null

        def isNull(self) -> bool:
            return self._null

        @classmethod
        def fromTheme(cls, name: str):
            cls.theme_names.append(name)
            return cls(f"theme:{name}")

    class FakeStyle:
        def standardIcon(self, icon: str) -> str:
            return f"standard:{icon}"

    class FakeApp:
        def style(self) -> FakeStyle:
            return FakeStyle()

    class FakeQStyle:
        class StandardPixmap:
            SP_ComputerIcon = "computer"
            SP_MessageBoxWarning = "warning"
            SP_MessageBoxCritical = "critical"
            SP_BrowserReload = "reload"

    icon = _build_tray_icon(FakeApp(), FakeQStyle, "idle", qicon=FakeIcon)

    assert icon.source == "theme:operance"
    assert FakeIcon.theme_names == ["operance"]


def test_build_tray_icon_falls_back_to_stock_icon_when_operance_icon_is_missing() -> None:
    from operance.ui.tray import _build_tray_icon

    class FakeIcon:
        def __init__(self, source: str = "", *, null: bool = True) -> None:
            self.source = source
            self._null = null

        def isNull(self) -> bool:
            return self._null

        @classmethod
        def fromTheme(cls, name: str):
            return cls(f"theme:{name}", null=True)

    class FakeStyle:
        def standardIcon(self, icon: str) -> str:
            return f"standard:{icon}"

    class FakeApp:
        def style(self) -> FakeStyle:
            return FakeStyle()

    class FakeQStyle:
        class StandardPixmap:
            SP_ComputerIcon = "computer"
            SP_MessageBoxWarning = "warning"
            SP_MessageBoxCritical = "critical"
            SP_BrowserReload = "reload"

    assert _build_tray_icon(FakeApp(), FakeQStyle, "error", qicon=FakeIcon) == "standard:critical"


def test_build_tray_snapshot_disables_click_to_talk_while_capture_is_active() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(current_state=RuntimeState.LISTENING),
        click_to_talk_active=True,
    )

    payload = snapshot.to_dict()

    assert payload["click_to_talk_label"] == "Listening..."
    assert payload["can_start_click_to_talk"] is False


def test_build_tray_snapshot_shows_listening_state_as_soon_as_click_to_talk_starts() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(current_state=RuntimeState.IDLE),
        click_to_talk_active=True,
    )

    payload = snapshot.to_dict()

    assert payload["tray_state"] == "listening"
    assert payload["mic_state"] == "listening"
    assert payload["state_label"] == "Listening"
    assert payload["click_to_talk_label"] == "Listening..."
    assert payload["can_start_click_to_talk"] is False
    assert payload["tooltip"] == "Operance: Listening"


def test_build_tray_snapshot_reports_failure_notification() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="install updates",
            last_response="Command validation failed.",
            last_command_status="denied",
            completed_commands=1,
            p95_latency_ms=88.0,
        )
    )

    payload = snapshot.to_dict()

    assert payload["notification"] == {
        "event_id": "denied:Command validation failed.",
        "level": "error",
        "message": "Command validation failed.",
        "title": "Command denied",
    }
    assert payload["confirmation_dialog"] is None


def test_build_tray_snapshot_surfaces_last_transcript_and_response_in_tooltip() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="open firefox",
            last_response="Launched firefox",
            last_command_status="success",
            completed_commands=1,
            p95_latency_ms=88.0,
        )
    )

    payload = snapshot.to_dict()

    assert payload["last_command_transcript"] == "open firefox"
    assert payload["last_command_preview"] == "Launched firefox"
    assert payload["last_interaction"] == {
        "details": [
            "Heard: open firefox",
            "Status: success",
        ],
        "summary": "Launched firefox",
        "title": "Last interaction",
    }
    assert payload["tooltip"] == "Operance: Responding | Heard: open firefox | Launched firefox"


def test_build_tray_snapshot_reports_planner_failure_notification() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="let me know when this is done",
            last_response="I did not understand that command.",
            last_command_status="unmatched",
            last_routing_reason="planner_failed",
            last_planner_error="planner failed for let me know when this is done",
            completed_commands=1,
            p95_latency_ms=144.0,
        )
    )

    payload = snapshot.to_dict()

    assert payload["notification"] == {
        "event_id": "planner_failed:planner failed for let me know when this is done",
        "level": "warning",
        "message": "planner failed for let me know when this is done",
        "title": "Planner fallback failed",
    }
    assert payload["can_reset_planner"] is True


def test_build_tray_snapshot_enables_planner_reset_during_cooldown() -> None:
    from operance.ui import build_tray_snapshot

    snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="let me know again",
            last_response="I did not understand that command.",
            last_command_status="unmatched",
            last_routing_reason="planner_cooldown_active",
            last_planner_error="planner failed for tell me when this finishes",
            planner_consecutive_failures=2,
            planner_cooldown_remaining_seconds=22.5,
            completed_commands=2,
            p95_latency_ms=144.0,
        )
    )

    payload = snapshot.to_dict()

    assert payload["can_reset_planner"] is True


def test_select_tray_notification_only_emits_new_events() -> None:
    from operance.ui import build_tray_snapshot, select_tray_notification

    denied_snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="install updates",
            last_response="Command validation failed.",
            last_command_status="denied",
            completed_commands=1,
            p95_latency_ms=88.0,
        )
    )
    repeated_snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="install updates",
            last_response="Command validation failed.",
            last_command_status="denied",
            completed_commands=1,
            p95_latency_ms=88.0,
        )
    )
    unmatched_snapshot = build_tray_snapshot(
        _status_snapshot(
            current_state=RuntimeState.RESPONDING,
            last_transcript="install updates",
            last_response="I did not understand that command.",
            last_command_status="unmatched",
            completed_commands=1,
            p95_latency_ms=88.0,
        )
    )

    assert select_tray_notification(None, denied_snapshot) == denied_snapshot.notification
    assert select_tray_notification(denied_snapshot, repeated_snapshot) is None
    assert select_tray_notification(denied_snapshot, unmatched_snapshot) == unmatched_snapshot.notification


def test_tray_controller_can_confirm_pending_command(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", is_final=True)

    controller = TrayController(daemon)
    snapshot = controller.confirm_pending()

    assert snapshot.current_state == "IDLE"
    assert snapshot.tray_state == "idle"
    assert snapshot.last_command_preview == "Closed window Firefox"
    assert snapshot.pending_confirmation_prompt is None
    assert snapshot.can_confirm is False
    assert snapshot.can_cancel is False


def test_tray_controller_can_cancel_pending_command(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", is_final=True)

    controller = TrayController(daemon)
    snapshot = controller.cancel_pending()

    assert snapshot.current_state == "IDLE"
    assert snapshot.tray_state == "idle"
    assert snapshot.last_command_preview == "Cancelled pending command."
    assert snapshot.pending_confirmation_prompt is None
    assert snapshot.can_confirm is False
    assert snapshot.can_cancel is False


def test_tray_controller_can_reset_planner_runtime(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    class FailingPlannerClient:
        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            raise ValueError(f"planner failed for {transcript}")

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES": "2",
            "OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS": "30",
        }
    )
    daemon.planner_client = FailingPlannerClient()
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)
    daemon.complete_response_cycle()
    daemon.emit_transcript("tell me when this finishes", confidence=0.93, is_final=True)

    controller = TrayController(daemon)
    snapshot = controller.reset_planner_runtime()

    assert snapshot.current_state == "RESPONDING"
    assert snapshot.last_command_preview == "Planner runtime state reset."
    assert snapshot.can_reset_planner is False


def test_tray_controller_can_restart_voice_loop_service(monkeypatch, tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController
    from operance.ui.setup import SetupRunResult

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    monkeypatch.setattr(
        "operance.ui.tray.run_setup_action",
        lambda action_id: SetupRunResult(
            action_id=action_id,
            label="Restart voice-loop user service",
            command="./scripts/control_systemd_user_services.sh restart --voice-loop",
            status="success",
            returncode=0,
            stdout="+ systemctl --user restart operance-voice-loop.service",
            stderr="",
            dry_run=False,
        ),
    )

    controller = TrayController(daemon)
    result = controller.restart_voice_loop_service()

    assert result.status == "success"
    assert result.command == "./scripts/control_systemd_user_services.sh restart --voice-loop"


def test_show_confirmation_dialog_returns_cancel_when_cancel_button_clicked() -> None:
    from operance.ui.tray import TrayConfirmationDialog, _show_confirmation_dialog

    class FakeMessageBox:
        class Icon:
            Warning = "warning"

        class ButtonRole:
            AcceptRole = "accept"
            RejectRole = "reject"

        clicked_role = "reject"

        def __init__(self) -> None:
            self._clicked_button = None

        def setWindowTitle(self, title: str) -> None:
            self.title = title

        def setText(self, text: str) -> None:
            self.text = text

        def setInformativeText(self, text: str) -> None:
            self.details = text

        def setIcon(self, icon: str) -> None:
            self.icon = icon

        def addButton(self, label: str, role: str) -> tuple[str, str]:
            return (label, role)

        def exec(self) -> None:
            self._clicked_button = ("Cancel", self.clicked_role)

        def clickedButton(self) -> tuple[str, str] | None:
            return self._clicked_button

    choice = _show_confirmation_dialog(
        FakeMessageBox,
        TrayConfirmationDialog(
            title="Confirm pending command",
            message="Planned action: close window 'firefox'.",
            details=["Affected: window: firefox"],
            confirm_label="Confirm",
            cancel_label="Cancel",
        ),
    )

    assert choice == "cancel"


def test_show_information_dialog_sets_message_box_fields() -> None:
    from operance.ui.tray import _show_information_dialog

    class FakeMessageBox:
        class Icon:
            Information = "information"

        last_instance = None

        def __init__(self) -> None:
            type(self).last_instance = self
            self.title = None
            self.text = None
            self.informative_text = None
            self.detailed_text = None
            self.icon = None
            self.executed = False

        def setWindowTitle(self, title: str) -> None:
            self.title = title

        def setText(self, text: str) -> None:
            self.text = text

        def setInformativeText(self, text: str) -> None:
            self.informative_text = text

        def setDetailedText(self, text: str) -> None:
            self.detailed_text = text

        def setIcon(self, icon: str) -> None:
            self.icon = icon

        def exec(self) -> None:
            self.executed = True

    _show_information_dialog(
        FakeMessageBox,
        title="Last click-to-talk interaction",
        summary="Launched firefox",
        informative_text="Heard: open firefox\nResult: success",
        details="Processed frames: 2",
    )

    dialog = FakeMessageBox.last_instance
    assert dialog is not None
    assert dialog.title == "Last click-to-talk interaction"
    assert dialog.text == "Launched firefox"
    assert dialog.informative_text == "Heard: open firefox\nResult: success"
    assert dialog.detailed_text == "Processed frames: 2"
    assert dialog.icon == "information"
    assert dialog.executed is True


def test_save_support_snapshot_artifact_writes_redacted_json(tmp_path: Path, monkeypatch) -> None:
    from operance.ui.tray import _save_support_snapshot_artifact

    snapshot = {
        "doctor": {"checks": [{"name": "linux_platform", "status": "ok"}]},
        "setup": {"summary_status": "ready"},
    }
    seen_redact: list[bool] = []

    monkeypatch.setattr(
        "operance.ui.tray.build_support_snapshot",
        lambda env=None, redact=False: seen_redact.append(redact) or snapshot,
    )
    monkeypatch.setattr("operance.ui.tray.project_version", lambda: "1.2.3")

    artifact_path = _save_support_snapshot_artifact(
        data_dir=tmp_path,
        env={"OPERANCE_DATA_DIR": str(tmp_path)},
        now=datetime(2026, 5, 1, 1, 2, 3, tzinfo=timezone.utc),
    )

    assert artifact_path == tmp_path / "support-snapshots" / "support-snapshot-1.2.3-20260501T010203Z.json"
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == snapshot
    assert seen_redact == [True]


def test_save_support_bundle_artifact_writes_redacted_archive(tmp_path: Path, monkeypatch) -> None:
    from operance.ui.tray import _save_support_bundle_artifact

    calls: list[dict[str, object]] = []

    def _write_bundle(*, output_path=None, env=None, redact=True, now=None):
        calls.append(
            {
                "output_path": output_path,
                "env": env,
                "redact": redact,
                "now": now,
            }
        )
        return {"bundle_path": str(output_path), "included_files": ["manifest.json"]}

    monkeypatch.setattr(
        "operance.ui.tray.write_support_bundle_artifact",
        _write_bundle,
    )
    monkeypatch.setattr("operance.ui.tray.project_version", lambda: "1.2.3")

    artifact_path = _save_support_bundle_artifact(
        data_dir=tmp_path,
        env={"OPERANCE_DATA_DIR": str(tmp_path)},
        now=datetime(2026, 5, 1, 1, 2, 3, tzinfo=timezone.utc),
    )

    assert artifact_path == tmp_path / "support-bundles" / "support-bundle-1.2.3-20260501T010203Z.tar.gz"
    assert calls == [
        {
            "output_path": artifact_path,
            "env": {"OPERANCE_DATA_DIR": str(tmp_path)},
            "redact": True,
            "now": datetime(2026, 5, 1, 1, 2, 3, tzinfo=timezone.utc),
        }
    ]


def test_format_click_to_talk_notification_message_includes_transcript() -> None:
    from operance.ui.tray import (
        TrayInteractionReport,
        _format_click_to_talk_notification_message,
    )

    report = TrayInteractionReport(
        title="Last click-to-talk interaction",
        summary="Launched firefox",
        details=[
            "Heard: open firefox",
            "Result: success",
        ],
    )

    assert _format_click_to_talk_notification_message(report) == (
        "Heard: open firefox\nLaunched firefox"
    )


def test_format_click_to_talk_notification_message_skips_missing_transcript() -> None:
    from operance.ui.tray import (
        TrayInteractionReport,
        _format_click_to_talk_notification_message,
    )

    report = TrayInteractionReport(
        title="Last click-to-talk interaction",
        summary="I did not catch a command.",
        details=[
            "Heard: No final transcript",
            "Result: no_transcript",
        ],
    )

    assert _format_click_to_talk_notification_message(report) == "I did not catch a command."


def test_tray_activation_helper_starts_click_to_talk_on_primary_click() -> None:
    from operance.ui.tray import _should_start_click_to_talk_from_activation

    class FakeSystemTrayIcon:
        class ActivationReason:
            Trigger = "trigger"
            DoubleClick = "double_click"
            Context = "context"

    assert _should_start_click_to_talk_from_activation(
        FakeSystemTrayIcon.ActivationReason.Trigger,
        FakeSystemTrayIcon,
    ) is True
    assert _should_start_click_to_talk_from_activation(
        FakeSystemTrayIcon.ActivationReason.DoubleClick,
        FakeSystemTrayIcon,
    ) is True
    assert _should_start_click_to_talk_from_activation(
        FakeSystemTrayIcon.ActivationReason.Context,
        FakeSystemTrayIcon,
    ) is False


def test_tray_controller_can_undo_last_action(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 50 percent", is_final=True)
    daemon.complete_response_cycle()

    controller = TrayController(daemon)
    snapshot = controller.undo_last_action()

    assert snapshot.current_state == "IDLE"
    assert snapshot.tray_state == "idle"
    assert snapshot.last_command_preview == "Volume restored to 30%"
    assert snapshot.can_undo is False
    assert snapshot.undo_label is None


def test_tray_controller_can_run_click_to_talk_command(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.stt import TranscriptSegment
    from operance.ui import TrayController

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    controller = TrayController(daemon)

    result = controller.start_click_to_talk(
        capture_source=FakeCaptureSource(),
        build_transcriber=FakeSpeechTranscriber,
        max_frames=4,
    )
    snapshot = controller.snapshot()

    assert result["response"] == {
        "simulated": True,
        "status": "success",
        "text": "Launched firefox",
    }
    assert snapshot.current_state == "IDLE"
    assert snapshot.last_command_transcript == "open firefox"
    assert snapshot.last_command_preview == "Launched firefox"
    assert snapshot.to_dict()["last_interaction"] == {
        "details": [
            "Heard: open firefox",
            "Result: success",
            "Mode: simulated",
            "Processed frames: 2",
            "Stopped: final_transcript",
            "Final state: IDLE",
        ],
        "summary": "Launched firefox",
        "title": "Last click-to-talk interaction",
    }
    assert snapshot.can_start_click_to_talk is True


def test_tray_controller_surfaces_no_transcript_click_to_talk_attempt(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 2
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeSpeechTranscriber:
        def process_frame(self, frame):
            return None

        def finish(self) -> list[object]:
            return []

        def close(self) -> None:
            return None

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    controller = TrayController(daemon)

    result = controller.start_click_to_talk(
        capture_source=FakeCaptureSource(),
        build_transcriber=FakeSpeechTranscriber,
        max_frames=2,
    )
    snapshot = controller.snapshot()

    assert result["response"] == {
        "simulated": True,
        "status": "no_transcript",
        "text": "I did not catch a command.",
    }
    assert snapshot.last_command_transcript is None
    assert snapshot.last_command_preview == "I did not catch a command."
    assert snapshot.to_dict()["last_interaction"] == {
        "details": [
            "Heard: No final transcript",
            "Result: no_transcript",
            "Mode: simulated",
            "Processed frames: 2",
            "Stopped: frame_limit",
            "Final state: IDLE",
        ],
        "summary": "I did not catch a command.",
        "title": "Last click-to-talk interaction",
    }
    assert snapshot.tooltip == (
        "Operance: Idle (simulated) | Developer mode uses simulated adapters | "
        "I did not catch a command."
    )


def test_tray_controller_surfaces_click_to_talk_backend_error(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    controller = TrayController(daemon)

    with pytest.raises(ValueError, match="moonshine-voice is not installed"):
        controller.start_click_to_talk(
            capture_source=object(),
            build_transcriber=lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
            max_frames=2,
        )

    snapshot = controller.snapshot()

    assert snapshot.last_command_transcript is None
    assert snapshot.last_command_preview == "moonshine-voice is not installed"
    assert snapshot.to_dict()["last_interaction"] == {
        "details": ["Source: click-to-talk"],
        "summary": "moonshine-voice is not installed",
        "title": "Last click-to-talk error",
    }
    assert snapshot.tooltip == (
        "Operance: Idle (simulated) | Developer mode uses simulated adapters | "
        "moonshine-voice is not installed"
    )


def test_tray_controller_surfaces_non_value_click_to_talk_backend_error(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.ui import TrayController

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    controller = TrayController(daemon)

    with pytest.raises(RuntimeError, match="audio capture backend failed"):
        controller.start_click_to_talk(
            capture_source=object(),
            build_transcriber=lambda: (_ for _ in ()).throw(RuntimeError("audio capture backend failed")),
            max_frames=2,
        )

    snapshot = controller.snapshot()

    assert snapshot.current_state == "IDLE"
    assert snapshot.last_command_transcript is None
    assert snapshot.last_command_preview == "audio capture backend failed"
    assert snapshot.to_dict()["last_interaction"] == {
        "details": ["Source: click-to-talk"],
        "summary": "audio capture backend failed",
        "title": "Last click-to-talk error",
    }
    assert snapshot.tooltip == (
        "Operance: Idle (simulated) | Developer mode uses simulated adapters | "
        "audio capture backend failed"
    )
