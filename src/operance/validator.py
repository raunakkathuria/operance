"""Plan validation and normalization for typed actions."""

from __future__ import annotations

from dataclasses import dataclass

from .models.actions import ActionPlan, TypedAction
from .models.base import SerializableModel
from .registry import ActionRegistry, derive_action_safety_metadata


@dataclass(slots=True, frozen=True)
class ValidationResult(SerializableModel):
    valid: bool
    errors: list[str]
    normalized_plan: ActionPlan | None = None


@dataclass(slots=True)
class PlanValidator:
    registry: ActionRegistry

    def validate(self, plan: ActionPlan) -> ValidationResult:
        errors: list[str] = []
        normalized_actions: list[TypedAction] = []

        for action in plan.actions:
            spec = self.registry.get(action.tool)
            if spec is None:
                errors.append(f"unknown tool: {action.tool.value}")
                continue

            missing_args = [arg for arg in spec.required_args if arg not in action.args]
            if missing_args:
                errors.append(
                    f"{action.tool.value}: missing required args: {', '.join(missing_args)}"
                )
                continue

            if spec.validate_args is not None:
                arg_errors = spec.validate_args(action.args)
                errors.extend(f"{action.tool.value}: {error}" for error in arg_errors)
                if arg_errors:
                    continue

            risk_tier, requires_confirmation = derive_action_safety_metadata(
                action.tool,
                action.args,
                base_risk_tier=max(action.risk_tier, spec.risk_tier),
                requires_confirmation=spec.requires_confirmation,
            )

            normalized_actions.append(
                TypedAction(
                    tool=action.tool,
                    args=action.args,
                    risk_tier=risk_tier,
                    requires_confirmation=requires_confirmation,
                    undoable=spec.undoable,
                )
            )

        if errors:
            return ValidationResult(valid=False, errors=errors, normalized_plan=None)

        return ValidationResult(
            valid=True,
            errors=[],
            normalized_plan=ActionPlan(
                source=plan.source,
                original_text=plan.original_text,
                actions=normalized_actions,
                plan_id=plan.plan_id,
            ),
        )
