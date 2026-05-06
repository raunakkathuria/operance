"""Runtime event contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .actions import ActionPlan, ActionResult
from .base import SerializableModel, new_id, utc_now


class RuntimeState(StrEnum):
    IDLE = "IDLE"
    WAKE_DETECTED = "WAKE_DETECTED"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    UNDERSTANDING = "UNDERSTANDING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    RESPONDING = "RESPONDING"
    ERROR = "ERROR"
    COOLDOWN = "COOLDOWN"


@dataclass(slots=True, frozen=True)
class BaseEvent(SerializableModel):
    event_id: str = field(default_factory=new_id)
    timestamp: object = field(default_factory=utc_now)
    kind: str = field(default="event", init=False)


@dataclass(slots=True, frozen=True)
class WakeEvent(BaseEvent):
    detected: bool = True
    phrase: str | None = None
    kind: str = field(default="wake.detected", init=False)


@dataclass(slots=True, frozen=True)
class TranscriptEvent(BaseEvent):
    text: str = ""
    is_final: bool = True
    confidence: float = 1.0
    source: str = "microphone"
    kind: str = field(default="transcript.final", init=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(slots=True, frozen=True)
class StateTransition(BaseEvent):
    previous_state: RuntimeState = RuntimeState.IDLE
    current_state: RuntimeState = RuntimeState.IDLE
    reason: str = "initialized"
    kind: str = field(default="runtime.state_transition", init=False)


@dataclass(slots=True, frozen=True)
class ActionPlanEvent(BaseEvent):
    plan: ActionPlan | None = None
    kind: str = field(default="action.plan_generated", init=False)


@dataclass(slots=True, frozen=True)
class PlanValidationEvent(BaseEvent):
    result: object = None
    kind: str = field(default="action.plan_validated", init=False)


@dataclass(slots=True, frozen=True)
class ActionResultEvent(BaseEvent):
    result: ActionResult | None = None
    kind: str = field(default="action.result_generated", init=False)


@dataclass(slots=True, frozen=True)
class ResponseEvent(BaseEvent):
    text: str = ""
    status: str = "success"
    plan_id: str | None = None
    kind: str = field(default="response.generated", init=False)
