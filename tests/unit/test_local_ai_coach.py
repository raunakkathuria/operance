from operance.local_ai_coach import build_local_ai_coach


def test_build_local_ai_coach_wraps_planner_setup_and_status() -> None:
    payload = build_local_ai_coach(
        planner_status={
            "status": "warn",
            "mode": "disabled_needs_setup",
            "safe_to_enable": False,
            "runtime_fallback_enabled": False,
            "config": {"model": "qwen2.5:3b"},
            "safety_contract": ["Validation and policy still run before execution."],
        },
        setup_template={
            "profile": "ollama",
            "server": {"command": "ollama run qwen2.5:3b"},
            "export_commands": [
                "export OPERANCE_PLANNER_ENDPOINT=http://127.0.0.1:11434/v1/chat/completions",
                "export OPERANCE_PLANNER_MODEL=qwen2.5:3b",
            ],
            "validation_commands": [
                "operance --planner-status",
                'operance --planner-readiness "open firefox and notify me"',
            ],
            "enable_command": "export OPERANCE_PLANNER_ENABLED=1",
            "safety_contract": [
                "The local model may only return the Operance typed action schema.",
                "Validation and policy still run before execution.",
            ],
        },
        command_prefix="operance",
    )

    assert payload["title"] == "Local AI setup"
    assert payload["summary"] == "Local AI planner fallback is optional and needs setup before use."
    assert payload["required_for_tray"] is False
    assert payload["profile"] == "ollama"
    assert payload["steps"][0]["command"] == "ollama run qwen2.5:3b"
    assert payload["steps"][1]["commands"][1] == "export OPERANCE_PLANNER_MODEL=qwen2.5:3b"
    assert payload["steps"][2]["commands"][1] == 'operance --planner-readiness "open firefox and notify me"'
    assert payload["steps"][3]["command"] == 'operance --planner-execute "let me know when this is done"'
    assert payload["steps"][4]["command"] == "export OPERANCE_PLANNER_ENABLED=1"
    assert payload["safety_contract"][0] == "The local model may only return the Operance typed action schema."


def test_build_local_ai_coach_summarizes_ready_to_enable_state() -> None:
    payload = build_local_ai_coach(
        planner_status={
            "status": "ok",
            "mode": "ready_to_enable",
            "safe_to_enable": True,
            "runtime_fallback_enabled": False,
        },
        setup_template={},
    )

    assert payload["summary"] == "Local AI planner readiness passed; live fallback is still opt-in."
