"""Platform-neutral audio playback contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AudioPlaybackSink(Protocol):
    def play_file(self, path: Path) -> None:
        """Play one saved audio file."""
