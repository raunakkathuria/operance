"""Platform-neutral speech transcription contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..audio.capture import AudioFrame
from ..models.base import SerializableModel, new_id, utc_now


@dataclass(slots=True, frozen=True)
class TranscriptSegment(SerializableModel):
    segment_id: str = field(default_factory=new_id)
    timestamp: object = field(default_factory=utc_now)
    text: str = ""
    confidence: float = 1.0
    is_final: bool = True


class SpeechTranscriber(Protocol):
    def process_frame(self, frame: AudioFrame) -> TranscriptSegment | None:
        """Return transcript output when enough audio has been accumulated."""

    def finish(self) -> list[TranscriptSegment]:
        """Flush any remaining completed transcript segments at end of stream."""

    def close(self) -> None:
        """Release backend resources."""
