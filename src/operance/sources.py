"""Transcript source abstractions for deterministic developer flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


class TranscriptSource(Protocol):
    def read_transcripts(self) -> Iterable[str]:
        """Yield normalized transcript strings."""


@dataclass(slots=True)
class IterableTranscriptSource:
    transcripts: Iterable[str]

    def read_transcripts(self) -> Iterable[str]:
        for transcript in self.transcripts:
            normalized = transcript.strip()
            if normalized:
                yield normalized


@dataclass(slots=True)
class FileTranscriptSource:
    path: Path

    def read_transcripts(self) -> Iterable[str]:
        if not self.path.exists():
            raise FileNotFoundError(f"transcript file not found: {self.path}")

        content = self.path.read_text(encoding="utf-8").splitlines()
        return IterableTranscriptSource(content).read_transcripts()
