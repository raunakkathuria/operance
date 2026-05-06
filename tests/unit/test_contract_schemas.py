def test_action_plan_schema_matches_current_contract_shape() -> None:
    from operance.schemas import build_action_plan_schema

    schema = build_action_plan_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["plan_id", "source", "original_text", "actions"]
    assert schema["properties"]["source"]["enum"] == ["deterministic", "planner"]
    assert schema["properties"]["actions"]["minItems"] == 1
    assert "tool" in schema["properties"]["actions"]["items"]["properties"]


def test_action_result_schema_matches_current_contract_shape() -> None:
    from operance.schemas import build_action_result_schema

    schema = build_action_result_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["plan_id", "status", "results"]
    assert schema["properties"]["status"]["enum"] == [
        "success",
        "partial",
        "failed",
        "denied",
        "cancelled",
    ]
    assert "undo_token" in schema["properties"]["results"]["items"]["properties"]
