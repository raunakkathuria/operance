from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction


def test_policy_auto_approves_tier_1_plan() -> None:
    from operance.policy import ExecutionPolicy

    policy = ExecutionPolicy()
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="set volume to 50 percent",
        actions=[
            TypedAction(
                tool=ToolName.AUDIO_SET_VOLUME,
                args={"percent": 50},
                risk_tier=RiskTier.TIER_1,
            )
        ],
    )

    decision = policy.decide(plan)

    assert decision.action == "auto_approve"


def test_policy_requires_confirmation_for_tier_2_plan() -> None:
    from operance.policy import ExecutionPolicy

    policy = ExecutionPolicy()
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="rename file",
        actions=[
            TypedAction(
                tool=ToolName.FILES_RENAME,
                args={"location": "desktop", "source_name": "clients", "target_name": "archive"},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )
        ],
    )

    decision = policy.decide(plan)

    assert decision.action == "require_confirmation"


def test_policy_denies_tier_3_plan() -> None:
    from operance.policy import ExecutionPolicy

    policy = ExecutionPolicy()
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="delete everything",
        actions=[
            TypedAction(
                tool=ToolName.FILES_CREATE_FOLDER,
                args={"location": "desktop", "name": "clients"},
                risk_tier=RiskTier.TIER_3,
            )
        ],
    )

    decision = policy.decide(plan)

    assert decision.action == "deny"
