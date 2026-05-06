"""Platform-neutral audio capture contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from ..models.base import SerializableModel, new_id, serialize_value, utc_now


@dataclass(slots=True, frozen=True)
class AudioInputDevice(SerializableModel):
    device_id: str
    name: str
    is_default: bool = False
    backend: str = "unknown"


@dataclass(slots=True, frozen=True)
class AudioFrame(SerializableModel):
    frame_id: str = field(default_factory=new_id)
    timestamp: object = field(default_factory=utc_now)
    sample_rate_hz: int = 16000
    channels: int = 1
    sample_count: int = 0
    sample_format: str = "s16le"
    source: str = "microphone"
    pcm_s16le: bytes = field(default=b"", repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "timestamp": serialize_value(self.timestamp),
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "sample_count": self.sample_count,
            "sample_format": self.sample_format,
            "source": self.source,
            "byte_count": len(self.pcm_s16le),
        }


class AudioCaptureSource(Protocol):
    def list_input_devices(self) -> list[AudioInputDevice]:
        """Return currently discoverable audio input devices."""

    def frames(self, *, max_frames: int | None = None) -> Iterable[AudioFrame]:
        """Yield captured audio frames."""
