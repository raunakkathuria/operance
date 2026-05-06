"""Platform-neutral wake-word detection contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models.base import SerializableModel, new_id, utc_now


@dataclass(slots=True, frozen=True)
class WakeWordDetection(SerializableModel):
    detection_id: str = field(default_factory=new_id)
    timestamp: object = field(default_factory=utc_now)
    phrase: str = "operance"
    confidence: float = 1.0


class WakeWordDetector(Protocol):
    def process_frame(self, frame) -> WakeWordDetection | None:
        """Return a detection when the wake phrase is observed."""
