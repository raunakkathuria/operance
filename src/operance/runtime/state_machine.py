"""Visible and validated runtime state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models.events import RuntimeState, StateTransition
from .event_bus import EventBusProtocol

_ALLOWED_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
    RuntimeState.IDLE: {RuntimeState.WAKE_DETECTED, RuntimeState.LISTENING, RuntimeState.ERROR},
    RuntimeState.WAKE_DETECTED: {RuntimeState.LISTENING, RuntimeState.COOLDOWN, RuntimeState.ERROR},
    RuntimeState.LISTENING: {RuntimeState.TRANSCRIBING, RuntimeState.COOLDOWN, RuntimeState.ERROR},
    RuntimeState.TRANSCRIBING: {RuntimeState.UNDERSTANDING, RuntimeState.ERROR},
    RuntimeState.UNDERSTANDING: {
        RuntimeState.AWAITING_CONFIRMATION,
        RuntimeState.EXECUTING,
        RuntimeState.RESPONDING,
        RuntimeState.ERROR,
    },
    RuntimeState.AWAITING_CONFIRMATION: {
        RuntimeState.TRANSCRIBING,
        RuntimeState.EXECUTING,
        RuntimeState.RESPONDING,
        RuntimeState.COOLDOWN,
        RuntimeState.ERROR,
    },
    RuntimeState.EXECUTING: {RuntimeState.RESPONDING, RuntimeState.ERROR},
    RuntimeState.RESPONDING: {RuntimeState.COOLDOWN, RuntimeState.IDLE, RuntimeState.ERROR},
    RuntimeState.ERROR: {RuntimeState.COOLDOWN, RuntimeState.IDLE},
    RuntimeState.COOLDOWN: {RuntimeState.IDLE, RuntimeState.ERROR},
}


class InvalidStateTransition(ValueError):
    """Raised when a transition breaks the runtime contract."""


@dataclass(slots=True)
class RuntimeStateMachine:
    event_bus: EventBusProtocol | None = None
    current_state: RuntimeState = RuntimeState.IDLE
    history: list[StateTransition] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.history.append(
            StateTransition(
                previous_state=self.current_state,
                current_state=self.current_state,
                reason="initialized",
            )
        )

    def can_transition(self, next_state: RuntimeState) -> bool:
        if next_state == self.current_state:
            return True
        return next_state in _ALLOWED_TRANSITIONS.get(self.current_state, set())

    def transition_to(self, next_state: RuntimeState, reason: str) -> StateTransition:
        if not self.can_transition(next_state):
            raise InvalidStateTransition(
                f"cannot transition from {self.current_state} to {next_state}"
            )

        previous_state = self.current_state
        self.current_state = next_state
        transition = StateTransition(
            previous_state=previous_state,
            current_state=next_state,
            reason=reason,
        )
        self.history.append(transition)

        if self.event_bus is not None:
            self.event_bus.publish(transition)

        return transition
