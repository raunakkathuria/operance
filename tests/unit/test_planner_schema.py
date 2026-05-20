from operance.models.actions import ToolName


def test_planner_payload_schema_uses_tool_specific_action_contracts() -> None:
    from operance.planner.schema import build_planner_payload_schema

    schema = build_planner_payload_schema()
    action_schema = schema["properties"]["actions"]["items"]
    variants = action_schema["oneOf"]
    launch_variant = next(
        variant
        for variant in variants
        if variant["properties"]["tool"]["const"] == ToolName.APPS_LAUNCH.value
    )

    assert launch_variant["properties"]["args"]["required"] == ["app"]
    assert launch_variant["properties"]["args"]["properties"]["app"] == {"type": "string"}
    assert launch_variant["properties"]["args"]["additionalProperties"] is False


def test_planner_payload_schema_covers_registered_tools() -> None:
    from operance.planner.schema import build_planner_payload_schema
    from operance.registry import build_default_action_registry

    schema = build_planner_payload_schema()
    variants = schema["properties"]["actions"]["items"]["oneOf"]

    assert {variant["properties"]["tool"]["const"] for variant in variants} == {
        spec.name.value for spec in build_default_action_registry().list_specs()
    }
