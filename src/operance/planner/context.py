"""Short-lived planner context storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(slots=True, frozen=True)
class PlannerContextEntry:
    role: str
    content: str
    timestamp: datetime


@dataclass(slots=True)
class PlannerContextWindow:
    ttl_seconds: int = 300
    max_entries: int = 4
    _entries: list[PlannerContextEntry] = field(default_factory=list)

    def add(self, role: str, content: str, *, now: datetime | None = None) -> None:
        timestamp = now or datetime.now(UTC)
        self._entries.append(PlannerContextEntry(role=role, content=content, timestamp=timestamp))
        self._entries = self._entries[-self.max_entries :]

    def active_messages(self, *, now: datetime | None = None) -> list[dict[str, str]]:
        current_time = now or datetime.now(UTC)
        cutoff = current_time - timedelta(seconds=self.ttl_seconds)
        self._entries = [entry for entry in self._entries if entry.timestamp >= cutoff]
        return [
            {"role": entry.role, "content": entry.content}
            for entry in self._entries
        ]
