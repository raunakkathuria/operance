"""In-memory command latency tracking for deterministic demo flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil


@dataclass(slots=True, frozen=True)
class CommandMetrics:
    transcript: str
    matched: bool
    total_duration_ms: float
    planning_duration_ms: float
    execution_duration_ms: float | None
    response_duration_ms: float


@dataclass(slots=True)
class MetricsCollector:
    completed_commands: list[CommandMetrics] = field(default_factory=list)

    def record(self, metric: CommandMetrics) -> None:
        self.completed_commands.append(metric)

    def p95_total_duration_ms(self) -> float | None:
        if not self.completed_commands:
            return None

        ordered = sorted(metric.total_duration_ms for metric in self.completed_commands)
        index = max(0, ceil(len(ordered) * 0.95) - 1)
        return ordered[index]
