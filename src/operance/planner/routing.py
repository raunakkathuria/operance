"""Fallback routing rules for deterministic and planner handling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PlannerRoutingDecision:
    route: str
    reason: str


@dataclass(slots=True, frozen=True)
class PlannerRoutingPolicy:
    min_confidence: float = 0.7

    def decide(
        self,
        *,
        transcript: str,
        deterministic_matched: bool,
        transcript_confidence: float,
        is_final: bool,
    ) -> PlannerRoutingDecision:
        if not is_final:
            return PlannerRoutingDecision(route="ignore", reason="partial_transcript")

        if deterministic_matched:
            return PlannerRoutingDecision(route="deterministic", reason="deterministic_match")

        if transcript_confidence < self.min_confidence:
            return PlannerRoutingDecision(route="ignore", reason="low_confidence")

        return PlannerRoutingDecision(route="planner", reason="fallback_to_planner")
