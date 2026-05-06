import pytest

from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction
from operance.models.events import TranscriptEvent


def test_transcript_event_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        TranscriptEvent(text="open firefox", confidence=1.5)


def test_action_plan_serializes_enum_fields() -> None:
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="open firefox",
        actions=[
            TypedAction(
                tool=ToolName.APPS_LAUNCH,
                args={"app": "firefox"},
                risk_tier=RiskTier.TIER_0,
            )
        ],
    )

    serialized = plan.to_dict()

    assert serialized["source"] == "deterministic"
    assert serialized["actions"][0]["tool"] == "apps.launch"
    assert serialized["actions"][0]["risk_tier"] == 0


def test_action_plan_requires_at_least_one_action() -> None:
    with pytest.raises(ValueError, match="at least one action"):
        ActionPlan(source=PlanSource.DETERMINISTIC, original_text="noop", actions=[])
