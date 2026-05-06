"""Execution policy decisions for validated action plans."""

from __future__ import annotations

from dataclasses import dataclass

from .models.actions import ActionPlan, RiskTier


@dataclass(slots=True, frozen=True)
class PolicyDecision:
    action: str
    reason: str


@dataclass(slots=True)
class ExecutionPolicy:
    def decide(self, plan: ActionPlan) -> PolicyDecision:
        highest_risk = max(action.risk_tier for action in plan.actions)
        requires_confirmation = any(action.requires_confirmation for action in plan.actions)

        if highest_risk >= RiskTier.TIER_3:
            return PolicyDecision(action="deny", reason="risk tier too high")

        if highest_risk >= RiskTier.TIER_2 or requires_confirmation:
            return PolicyDecision(action="require_confirmation", reason="confirmation required")

        return PolicyDecision(action="auto_approve", reason="auto-approved")
