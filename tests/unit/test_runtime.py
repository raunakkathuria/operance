from pathlib import Path

import pytest

from operance.config import AppConfig
from operance.daemon import OperanceDaemon
from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction
from operance.models.events import (
    ActionPlanEvent,
    ActionResultEvent,
    PlanValidationEvent,
    ResponseEvent,
    RuntimeState,
    StateTransition,
    TranscriptEvent,
    WakeEvent,
)
from operance.runtime.event_bus import InMemoryEventBus
from operance.runtime.state_machine import InvalidStateTransition, RuntimeStateMachine
from operance.validator import ValidationResult


def test_in_memory_event_bus_dispatches_typed_events() -> None:
    bus = InMemoryEventBus()
    seen: list[str] = []

    bus.subscribe(WakeEvent, lambda event: seen.append(event.kind))
    bus.publish(WakeEvent())

    assert seen == ["wake.detected"]


def test_state_machine_rejects_invalid_transition() -> None:
    state_machine = RuntimeStateMachine()

    with pytest.raises(InvalidStateTransition):
        state_machine.transition_to(RuntimeState.EXECUTING, "cannot skip ahead from idle")


def test_state_machine_emits_transitions_to_event_bus() -> None:
    bus = InMemoryEventBus()
    transitions: list[StateTransition] = []
    bus.subscribe(StateTransition, transitions.append)

    state_machine = RuntimeStateMachine(event_bus=bus)
    state_machine.transition_to(RuntimeState.WAKE_DETECTED, "wake word detected")
    state_machine.transition_to(RuntimeState.LISTENING, "capturing audio")

    assert [transition.current_state for transition in transitions] == [
        RuntimeState.WAKE_DETECTED,
        RuntimeState.LISTENING,
    ]


def test_daemon_bootstrap_and_demo_events(tmp_path: Path) -> None:
    config = AppConfig.from_env({"OPERANCE_DATA_DIR": str(tmp_path / "data")})
    daemon = OperanceDaemon(config=config)
    seen: list[object] = []
    daemon.event_bus.subscribe_all(seen.append)

    daemon.start()
    wake_event = daemon.emit_wake_detected("operance")
    transcript_event = daemon.emit_transcript("open firefox", confidence=0.93)
    daemon.stop()

    assert daemon.running is False
    assert wake_event.phrase == "operance"
    assert transcript_event.text == "open firefox"
    assert transcript_event.confidence == 0.93
    assert config.paths.data_dir.exists()
    assert any(isinstance(event, WakeEvent) for event in seen)
    assert any(isinstance(event, TranscriptEvent) for event in seen)
    assert any(isinstance(event, ActionPlanEvent) for event in seen)
    assert any(isinstance(event, ActionResultEvent) for event in seen)
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_emits_action_plan_event_for_final_known_transcript(tmp_path: Path) -> None:
    config = AppConfig.from_env({"OPERANCE_DATA_DIR": str(tmp_path / "data")})
    daemon = OperanceDaemon(config=config)
    planned_events: list[ActionPlanEvent] = []
    daemon.event_bus.subscribe(ActionPlanEvent, planned_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert len(planned_events) == 1
    assert planned_events[0].plan.original_text == "open firefox"
    assert planned_events[0].plan.actions[0].tool == ToolName.APPS_LAUNCH
    assert planned_events[0].plan.actions[0].args == {"app": "firefox"}
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_emits_action_result_event_for_final_known_transcript(tmp_path: Path) -> None:
    config = AppConfig.from_env({"OPERANCE_DATA_DIR": str(tmp_path / "data")})
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert len(result_events) == 1
    assert result_events[0].result.status == "success"
    assert result_events[0].result.results[0].tool == ToolName.APPS_LAUNCH
    assert result_events[0].result.results[0].message == "Launched firefox"
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_emits_response_event_for_final_known_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Launched firefox"
    assert responses[0].status == "success"
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_emits_fallback_response_for_unknown_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("install updates", confidence=0.42, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "I did not understand that command."
    assert responses[0].status == "unmatched"
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_routes_high_confidence_unknown_transcript_to_planner_when_enabled(tmp_path: Path) -> None:
    class StubPlannerClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            self.calls.append(transcript)
            return {
                "actions": [
                    {
                        "tool": "notifications.show",
                        "args": {"title": "Planner", "message": "Fallback executed"},
                    }
                ]
            }

    planner_client = StubPlannerClient()
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
        }
    )
    daemon.planner_client = planner_client
    responses: list[ResponseEvent] = []
    planned_events: list[ActionPlanEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionPlanEvent, planned_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)

    assert planner_client.calls == ["let me know when this is done"]
    assert len(planned_events) == 1
    assert planned_events[0].plan.source == PlanSource.PLANNER
    assert planned_events[0].plan.actions[0].tool == ToolName.NOTIFICATIONS_SHOW
    assert responses[-1].status == "success"
    assert responses[-1].text == "Notification shown"
    snapshot = daemon.status_snapshot()
    assert snapshot.last_plan_source == "planner"
    assert snapshot.last_routing_reason == "fallback_to_planner"
    assert snapshot.last_planner_error is None
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_keeps_unmatched_response_when_planner_is_disabled(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "0",
        }
    )
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "I did not understand that command."
    assert responses[0].status == "unmatched"
    snapshot = daemon.status_snapshot()
    assert snapshot.last_plan_source is None
    assert snapshot.last_routing_reason == "planner_unavailable"
    assert snapshot.last_planner_error == "planner runtime unavailable"


def test_daemon_falls_back_to_unmatched_when_planner_errors(tmp_path: Path) -> None:
    class FailingPlannerClient:
        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            raise ValueError(f"planner failed for {transcript}")

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
        }
    )
    daemon.planner_client = FailingPlannerClient()
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "I did not understand that command."
    assert responses[0].status == "unmatched"
    snapshot = daemon.status_snapshot()
    assert snapshot.last_plan_source is None
    assert snapshot.last_routing_reason == "planner_failed"
    assert snapshot.last_planner_error == "planner failed for let me know when this is done"


def test_daemon_enters_planner_cooldown_after_repeated_failures(tmp_path: Path) -> None:
    class FailingPlannerClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            self.calls.append(transcript)
            raise ValueError(f"planner failed for {transcript}")

    planner_client = FailingPlannerClient()
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES": "2",
            "OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS": "30",
        }
    )
    daemon.planner_client = planner_client

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)
    daemon.complete_response_cycle()
    daemon.emit_transcript("tell me when this finishes", confidence=0.93, is_final=True)
    second_snapshot = daemon.status_snapshot()
    daemon.complete_response_cycle()
    daemon.emit_transcript("let me know again", confidence=0.93, is_final=True)

    third_snapshot = daemon.status_snapshot()

    assert planner_client.calls == [
        "let me know when this is done",
        "tell me when this finishes",
    ]
    assert second_snapshot.planner_consecutive_failures == 2
    assert second_snapshot.planner_cooldown_remaining_seconds is not None
    assert second_snapshot.planner_cooldown_remaining_seconds > 0
    assert second_snapshot.last_routing_reason == "planner_failed"
    assert third_snapshot.planner_consecutive_failures == 2
    assert third_snapshot.planner_cooldown_remaining_seconds is not None
    assert third_snapshot.planner_cooldown_remaining_seconds > 0
    assert third_snapshot.last_routing_reason == "planner_cooldown_active"
    assert third_snapshot.last_planner_error == "planner failed for tell me when this finishes"


def test_daemon_resets_planner_failure_state_after_planner_success(tmp_path: Path) -> None:
    class FlakyPlannerClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            self.calls.append(transcript)
            if len(self.calls) == 1:
                raise ValueError(f"planner failed for {transcript}")
            return {
                "actions": [
                    {
                        "tool": "notifications.show",
                        "args": {"title": "Planner", "message": "Fallback executed"},
                    }
                ]
            }

    planner_client = FlakyPlannerClient()
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
        }
    )
    daemon.planner_client = planner_client

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)
    daemon.complete_response_cycle()
    daemon.emit_transcript("tell me when this finishes", confidence=0.93, is_final=True)

    snapshot = daemon.status_snapshot()

    assert planner_client.calls == [
        "let me know when this is done",
        "tell me when this finishes",
    ]
    assert snapshot.last_plan_source == "planner"
    assert snapshot.last_routing_reason == "fallback_to_planner"
    assert snapshot.last_planner_error is None
    assert snapshot.planner_consecutive_failures == 0
    assert snapshot.planner_cooldown_remaining_seconds is None


def test_daemon_can_reset_planner_runtime_after_cooldown(tmp_path: Path) -> None:
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

    message = daemon.reset_planner_runtime()
    snapshot = daemon.status_snapshot()

    assert message == "Planner runtime state reset."
    assert snapshot.last_routing_reason == "planner_runtime_reset"
    assert snapshot.last_planner_error is None
    assert snapshot.planner_consecutive_failures == 0
    assert snapshot.planner_cooldown_remaining_seconds is None


def test_daemon_requires_confirmation_for_close_window_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_quit_app_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("quit firefox", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_delete_folder_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("delete folder on desktop called projects", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_delete_file_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("delete file on desktop called notes.txt", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_rename_entry_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("rename folder on desktop from projects to archive", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_move_entry_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("move folder on desktop called projects to archive", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_wifi_disable_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("turn wifi off", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_wifi_disconnect_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("disconnect wifi", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_known_wifi_connection_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("connect to wifi home", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_requires_confirmation_for_high_volume_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 90 percent", confidence=0.93, is_final=True)

    assert len(responses) == 1
    assert responses[0].text == "Command requires confirmation."
    assert responses[0].status == "awaiting_confirmation"
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_executes_pending_plan_when_user_confirms(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)
    daemon.emit_transcript("confirm", confidence=0.93, is_final=True)

    assert [response.status for response in responses] == ["awaiting_confirmation", "success"]
    assert responses[-1].text == "Closed window Firefox"
    assert len(result_events) == 1
    assert result_events[0].result is not None
    assert result_events[0].result.results[0].tool == ToolName.WINDOWS_CLOSE
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_expires_pending_plan_before_late_confirmation(tmp_path: Path, monkeypatch) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)
    daemon.pending_confirmation_started_at = 0.0
    monkeypatch.setattr("operance.daemon.monotonic", lambda: 1000.0)
    daemon.emit_transcript("confirm", confidence=0.93, is_final=True)

    assert [response.status for response in responses] == ["awaiting_confirmation", "expired"]
    assert responses[-1].text == "Pending command expired."
    assert result_events == []
    assert daemon.pending_confirmation_plan is None
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_clears_expired_pending_plan_and_processes_new_command(tmp_path: Path, monkeypatch) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)
    daemon.pending_confirmation_started_at = 0.0
    monkeypatch.setattr("operance.daemon.monotonic", lambda: 1000.0)
    daemon.emit_transcript("what time is it", confidence=0.93, is_final=True)

    assert [response.status for response in responses] == ["awaiting_confirmation", "success"]
    assert responses[-1].text == "It is 09:41"
    assert daemon.pending_confirmation_plan is None
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_cancels_pending_plan_when_user_declines(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)
    daemon.emit_transcript("cancel", confidence=0.93, is_final=True)

    assert [response.status for response in responses] == ["awaiting_confirmation", "cancelled"]
    assert responses[-1].text == "Cancelled pending command."
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_keeps_waiting_when_confirmation_reply_is_unrecognized(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", confidence=0.93, is_final=True)
    daemon.emit_transcript("maybe later", confidence=0.93, is_final=True)

    assert [response.status for response in responses] == ["awaiting_confirmation", "awaiting_confirmation"]
    assert responses[-1].text == "Please confirm or cancel the pending command."
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_does_not_plan_for_partial_transcript(tmp_path: Path) -> None:
    config = AppConfig.from_env({"OPERANCE_DATA_DIR": str(tmp_path / "data")})
    daemon = OperanceDaemon(config=config)
    planned_events: list[ActionPlanEvent] = []
    daemon.event_bus.subscribe(ActionPlanEvent, planned_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open fire", confidence=0.4, is_final=False)

    assert planned_events == []
    assert daemon.state_machine.current_state == RuntimeState.TRANSCRIBING


def test_daemon_tracks_latency_for_final_transcript(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert len(daemon.metrics.completed_commands) == 1
    metric = daemon.metrics.completed_commands[0]
    assert metric.transcript == "open firefox"
    assert metric.matched is True
    assert metric.total_duration_ms >= 0.0
    assert metric.planning_duration_ms >= 0.0
    assert metric.execution_duration_ms is not None
    assert metric.response_duration_ms >= 0.0


def test_daemon_rejects_invalid_plan_from_matcher(tmp_path: Path) -> None:
    class InvalidMatcher:
        def match(self, text: str) -> ActionPlan | None:
            return ActionPlan(
                source=PlanSource.DETERMINISTIC,
                original_text=text,
                actions=[
                    TypedAction(
                        tool=ToolName.APPS_LAUNCH,
                        args={},
                        risk_tier=RiskTier.TIER_0,
                    )
                ],
            )

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.intent_matcher = InvalidMatcher()
    validation_events: list[PlanValidationEvent] = []
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(PlanValidationEvent, validation_events.append)
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert len(validation_events) == 1
    assert validation_events[0].result.valid is False
    assert responses[-1].status == "denied"
    assert responses[-1].text == "Command validation failed."
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.RESPONDING


def test_daemon_stops_before_execution_when_confirmation_is_required(tmp_path: Path) -> None:
    from operance.policy import ExecutionPolicy

    class TierTwoValidator:
        def validate(self, plan: ActionPlan) -> ValidationResult:
            normalized_plan = ActionPlan(
                source=plan.source,
                original_text=plan.original_text,
                plan_id=plan.plan_id,
                actions=[
                    TypedAction(
                        tool=ToolName.FILES_CREATE_FOLDER,
                        args={"location": "desktop", "name": "clients"},
                        risk_tier=RiskTier.TIER_2,
                        requires_confirmation=True,
                    )
                ],
            )
            return ValidationResult(valid=True, errors=[], normalized_plan=normalized_plan)

    class TierTwoMatcher:
        def match(self, text: str) -> ActionPlan | None:
            return ActionPlan(
                source=PlanSource.DETERMINISTIC,
                original_text=text,
                actions=[
                    TypedAction(
                        tool=ToolName.FILES_CREATE_FOLDER,
                        args={"location": "desktop", "name": "clients"},
                        risk_tier=RiskTier.TIER_1,
                    )
                ],
            )

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.intent_matcher = TierTwoMatcher()
    daemon.validator = TierTwoValidator()
    responses: list[ResponseEvent] = []
    result_events: list[ActionResultEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)
    daemon.event_bus.subscribe(ActionResultEvent, result_events.append)

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("create clients folder", is_final=True)

    assert responses[-1].status == "awaiting_confirmation"
    assert responses[-1].text == "Command requires confirmation."
    assert result_events == []
    assert daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION


def test_daemon_can_complete_response_cycle_back_to_idle(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", confidence=0.93, is_final=True)

    assert daemon.state_machine.current_state == RuntimeState.RESPONDING

    daemon.complete_response_cycle()

    assert daemon.state_machine.current_state == RuntimeState.IDLE
    assert daemon.state_machine.history[-2].current_state == RuntimeState.COOLDOWN
    assert daemon.state_machine.history[-1].current_state == RuntimeState.IDLE


def test_daemon_can_undo_last_reversible_action(tmp_path: Path) -> None:
    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 50 percent", is_final=True)

    assert daemon.last_undo_token is not None
    assert daemon.adapters.audio is not None
    assert daemon.adapters.audio.volume == 50

    message = daemon.undo_last_action()

    assert message == "Volume restored to 30%"
    assert daemon.adapters.audio.volume == 30
