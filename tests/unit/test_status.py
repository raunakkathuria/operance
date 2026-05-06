from pathlib import Path

from operance.daemon import OperanceDaemon
from operance.models.events import RuntimeState


def test_daemon_status_snapshot_reports_last_command_context(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", is_final=True)

    snapshot = daemon.status_snapshot()

    assert snapshot.current_state == RuntimeState.RESPONDING
    assert snapshot.last_transcript == "open firefox"
    assert snapshot.last_response == "Launched firefox"
    assert snapshot.last_command_status == "success"
    assert snapshot.last_plan_source == "deterministic"
    assert snapshot.last_routing_reason == "deterministic_match"
    assert snapshot.last_planner_error is None
    assert snapshot.planner_context_entry_count == 2
    assert snapshot.planner_context_messages == [
        {"role": "user", "content": "open firefox"},
        {"role": "assistant", "content": "Launched firefox"},
    ]
    assert snapshot.undo_available is False
    assert snapshot.last_undo_tool is None
    assert snapshot.completed_commands == 1
    assert snapshot.p95_latency_ms is not None


def test_daemon_status_snapshot_returns_idle_after_cycle_completion(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", is_final=True)
    daemon.complete_response_cycle()

    snapshot = daemon.status_snapshot()

    assert snapshot.current_state == RuntimeState.IDLE
    assert snapshot.undo_available is False
    assert snapshot.last_undo_tool is None


def test_daemon_status_snapshot_reports_pending_confirmation(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", is_final=True)

    snapshot = daemon.status_snapshot()

    assert snapshot.current_state == RuntimeState.AWAITING_CONFIRMATION
    assert snapshot.last_command_status == "awaiting_confirmation"
    assert snapshot.pending_confirmation is True
    assert snapshot.pending_plan_id is not None
    assert snapshot.pending_plan_preview == "Planned action: close window 'firefox'."
    assert snapshot.pending_original_text == "close window firefox"
    assert snapshot.pending_source == "deterministic"
    assert snapshot.pending_risk_tier == 2
    assert snapshot.pending_action is not None
    assert snapshot.pending_action["tool"] == "windows.close"
    assert snapshot.pending_action["args"] == {"window": "firefox"}
    assert snapshot.pending_action["risk_tier"] == 2
    assert snapshot.pending_action["requires_confirmation"] is True
    assert snapshot.pending_action["undoable"] is False
    assert snapshot.pending_affected_resources == ["window: firefox"]
    assert snapshot.pending_rollback_hint == "No automatic undo is available after execution."
    assert snapshot.pending_timeout_seconds == 30.0
    assert snapshot.pending_timeout_behavior == "Pending command expires after 30 seconds without confirmation."
    assert snapshot.undo_available is False
    assert snapshot.last_undo_tool is None


def test_daemon_status_snapshot_reports_planner_cooldown_state(tmp_path: Path) -> None:
    class FailingPlannerClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            self.calls.append(transcript)
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

    snapshot = daemon.status_snapshot()

    assert snapshot.planner_consecutive_failures == 2
    assert snapshot.planner_cooldown_remaining_seconds is not None
    assert snapshot.planner_cooldown_remaining_seconds > 0
    assert snapshot.last_routing_reason == "planner_failed"
    assert snapshot.last_planner_error == "planner failed for tell me when this finishes"


def test_daemon_status_snapshot_reports_undo_available_after_reversible_action(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 50 percent", is_final=True)

    snapshot = daemon.status_snapshot()

    assert snapshot.undo_available is True
    assert snapshot.last_undo_tool == "audio.set_volume"
