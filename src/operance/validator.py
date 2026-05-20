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

            schema_errors = _validate_args_against_input_schema(action.args, spec.input_schema)
            if schema_errors:
                errors.extend(f"{action.tool.value}: {error}" for error in schema_errors)
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


def _validate_args_against_input_schema(
    args: dict[str, object],
    schema: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    properties_value = schema.get("properties", {})
    properties = properties_value if isinstance(properties_value, dict) else {}

    if schema.get("additionalProperties") is False:
        unexpected_args = sorted(arg for arg in args if arg not in properties)
        if unexpected_args:
            errors.append(f"unexpected args: {', '.join(unexpected_args)}")

    for arg_name, value in args.items():
        property_schema = properties.get(arg_name)
        if not isinstance(property_schema, dict):
            continue

        expected_type = property_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{arg_name} must be a string")
            continue
        if expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"{arg_name} must be a boolean")
            continue
        if expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append(f"{arg_name} must be an integer")
            continue

        enum_values = property_schema.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            errors.append(f"{arg_name} must be one of: {', '.join(str(item) for item in enum_values)}")
            continue

        if isinstance(value, int) and not isinstance(value, bool):
            minimum = property_schema.get("minimum")
            if isinstance(minimum, int | float) and value < minimum:
                errors.append(f"{arg_name} must be at least {minimum}")
                continue
            maximum = property_schema.get("maximum")
            if isinstance(maximum, int | float) and value > maximum:
                errors.append(f"{arg_name} must be at most {maximum}")

    return errors
