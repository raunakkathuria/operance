"""Runtime status snapshot models."""

from __future__ import annotations

from dataclasses import dataclass

from .models.events import RuntimeState


@dataclass(slots=True, frozen=True)
class StatusSnapshot:
    current_state: RuntimeState
    last_transcript: str | None
    last_response: str | None
    last_command_status: str | None
    last_plan_source: str | None
    last_routing_reason: str | None
    last_planner_error: str | None
    planner_consecutive_failures: int
    planner_cooldown_remaining_seconds: float | None
    planner_context_entry_count: int
    planner_context_messages: list[dict[str, str]]
    pending_confirmation: bool
    pending_plan_id: str | None
    pending_plan_preview: str | None
    pending_original_text: str | None
    pending_source: str | None
    pending_risk_tier: int | None
    pending_action: dict[str, object] | None
    pending_affected_resources: list[str]
    pending_rollback_hint: str | None
    pending_timeout_seconds: float | None
    pending_timeout_behavior: str | None
    undo_available: bool
    last_undo_tool: str | None
    completed_commands: int
    p95_latency_ms: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "current_state": self.current_state.value,
            "last_transcript": self.last_transcript,
            "last_response": self.last_response,
            "last_command_status": self.last_command_status,
            "last_plan_source": self.last_plan_source,
            "last_routing_reason": self.last_routing_reason,
            "last_planner_error": self.last_planner_error,
            "planner_consecutive_failures": self.planner_consecutive_failures,
            "planner_cooldown_remaining_seconds": self.planner_cooldown_remaining_seconds,
            "planner_context_entry_count": self.planner_context_entry_count,
            "planner_context_messages": self.planner_context_messages,
            "pending_confirmation": self.pending_confirmation,
            "pending_plan_id": self.pending_plan_id,
            "pending_plan_preview": self.pending_plan_preview,
            "pending_original_text": self.pending_original_text,
            "pending_source": self.pending_source,
            "pending_risk_tier": self.pending_risk_tier,
            "pending_action": self.pending_action,
            "pending_affected_resources": self.pending_affected_resources,
            "pending_rollback_hint": self.pending_rollback_hint,
            "pending_timeout_seconds": self.pending_timeout_seconds,
            "pending_timeout_behavior": self.pending_timeout_behavior,
            "undo_available": self.undo_available,
            "last_undo_tool": self.last_undo_tool,
            "completed_commands": self.completed_commands,
            "p95_latency_ms": self.p95_latency_ms,
        }
