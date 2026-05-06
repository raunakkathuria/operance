import json


def test_planner_prompt_includes_transcript_and_tool_catalog() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("open firefox and notify me")

    assert messages[0]["role"] == "system"
    assert "Use only the approved tools" in messages[0]["content"]
    assert "apps.launch" in messages[0]["content"]
    assert "notifications.show" in messages[0]["content"]
    assert messages[1] == {
        "role": "user",
        "content": "open firefox and notify me",
    }


def test_planner_prompt_includes_tool_examples() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("open firefox")
    system_content = messages[0]["content"]

    assert 'example="open firefox"' in system_content
    assert 'example="quit firefox"' in system_content


def test_planner_prompt_includes_tool_safety_hints() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("quit firefox")
    system_content = messages[0]["content"]

    assert "apps.launch: Launch an application or open a URL | args=app | risk=tier_0 | confirmation=not_required" in system_content
    assert "apps.quit: Quit an application | args=app | risk=tier_2 | confirmation=required" in system_content


def test_planner_prompt_includes_required_arg_hints() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("open firefox")
    system_content = messages[0]["content"]

    assert "apps.launch: Launch an application or open a URL | args=app" in system_content
    assert "notifications.show: Show a notification | args=title,message" in system_content
    assert "time.now: Get the current time | args=none" in system_content


def test_planner_prompt_includes_two_step_output_schema() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("open firefox")
    system_content = messages[0]["content"]

    assert '"maxItems": 2' in system_content
    assert '"required": ["actions"]' in system_content
    assert '"tool"' in system_content
    assert '"args"' in system_content


def test_planner_prompt_serializes_schema_as_json() -> None:
    from operance.planner.prompt import build_planner_messages

    messages = build_planner_messages("open firefox")
    schema_line = next(line for line in messages[0]["content"].splitlines() if line.startswith("Output schema: "))

    parsed = json.loads(schema_line.removeprefix("Output schema: "))

    assert parsed["type"] == "object"
    assert parsed["properties"]["actions"]["maxItems"] == 2
