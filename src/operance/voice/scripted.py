"""Scripted developer voice pipeline for non-audio environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..daemon import OperanceDaemon
from ..models.events import ResponseEvent


@dataclass(slots=True, frozen=True)
class ScriptedVoiceStep:
    kind: str
    text: str | None = None
    confidence: float = 1.0

    @classmethod
    def wake(cls, phrase: str = "operance") -> "ScriptedVoiceStep":
        return cls(kind="wake", text=phrase, confidence=1.0)

    @classmethod
    def partial_transcript(cls, text: str, confidence: float = 1.0) -> "ScriptedVoiceStep":
        return cls(kind="transcript_partial", text=text, confidence=confidence)

    @classmethod
    def final_transcript(cls, text: str, confidence: float = 1.0) -> "ScriptedVoiceStep":
        return cls(kind="transcript_final", text=text, confidence=confidence)


def run_scripted_voice_session(
    steps: list[ScriptedVoiceStep],
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    daemon = OperanceDaemon.build_default(env)
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    daemon.start()
    try:
        for step in steps:
            if step.kind == "wake":
                daemon.emit_wake_detected(step.text)
                continue

            if step.kind == "transcript_partial":
                daemon.emit_transcript(step.text or "", confidence=step.confidence, is_final=False)
                continue

            if step.kind == "transcript_final":
                daemon.emit_transcript(step.text or "", confidence=step.confidence, is_final=True)
                continue

            raise ValueError(f"unsupported scripted voice step: {step.kind}")
    finally:
        daemon.stop()

    return {
        "responses": [response.text for response in responses],
        "completed_commands": len(daemon.metrics.completed_commands),
        "final_state": daemon.state_machine.current_state.value,
    }
