from operance.planner.routing import PlannerRoutingDecision, PlannerRoutingPolicy


def test_planner_routing_prefers_deterministic_match() -> None:
    policy = PlannerRoutingPolicy()

    decision = policy.decide(
        transcript="open firefox",
        deterministic_matched=True,
        transcript_confidence=0.92,
        is_final=True,
    )

    assert decision == PlannerRoutingDecision(route="deterministic", reason="deterministic_match")


def test_planner_routing_rejects_low_confidence_transcript() -> None:
    policy = PlannerRoutingPolicy(min_confidence=0.7)

    decision = policy.decide(
        transcript="open firefox maybe",
        deterministic_matched=False,
        transcript_confidence=0.41,
        is_final=True,
    )

    assert decision == PlannerRoutingDecision(route="ignore", reason="low_confidence")


def test_planner_routing_sends_high_confidence_unknowns_to_planner() -> None:
    policy = PlannerRoutingPolicy(min_confidence=0.7)

    decision = policy.decide(
        transcript="open browser and tell me when done",
        deterministic_matched=False,
        transcript_confidence=0.88,
        is_final=True,
    )

    assert decision == PlannerRoutingDecision(route="planner", reason="fallback_to_planner")


def test_planner_routing_ignores_partial_transcripts() -> None:
    policy = PlannerRoutingPolicy()

    decision = policy.decide(
        transcript="open fire",
        deterministic_matched=False,
        transcript_confidence=0.9,
        is_final=False,
    )

    assert decision == PlannerRoutingDecision(route="ignore", reason="partial_transcript")
