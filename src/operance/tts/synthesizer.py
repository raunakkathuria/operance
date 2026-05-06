"""Platform-neutral speech synthesis contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True, frozen=True)
class SynthesizedAudio:
    text: str
    voice: str
    sample_rate_hz: int
    samples: list[float]

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate_hz <= 0:
            return 0.0
        return self.sample_count / self.sample_rate_hz


class SpeechSynthesizer(Protocol):
    def synthesize(self, text: str) -> SynthesizedAudio:
        """Return synthesized audio for one utterance."""

    def save(self, audio: SynthesizedAudio, path: Path) -> None:
        """Persist synthesized audio to disk."""
