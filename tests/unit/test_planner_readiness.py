from operance.config import PlannerSettings


def test_planner_readiness_report_passes_without_enabling_runtime_fallback() -> None:
    from operance.planner.readiness import build_planner_readiness_report
    from operance.policy import ExecutionPolicy
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    class FakePlannerClient:
        config = None

        def health(self) -> dict[str, object]:
            return {"status": "ok", "probe": "models", "model_ids": ["qwen-test"]}

        def plan(self, transcript: str) -> dict[str, object]:
            return {
                "actions": [
                    {"tool": "apps.launch", "args": {"app": "firefox"}},
                    {
                        "tool": "notifications.show",
                        "args": {"title": "Opened", "message": "Firefox launched"},
                    },
                ]
            }

    report = build_planner_readiness_report(
        PlannerSettings(enabled=False, model="qwen-test"),
        client=FakePlannerClient(),
        validator=PlanValidator(build_default_action_registry()),
        policy=ExecutionPolicy(),
    )

    assert report["status"] == "ok"
    assert report["runtime_fallback_enabled"] is False
    assert report["safe_to_enable"] is True
    assert report["ready_for_live_fallback"] is False
    assert report["execution"] == "not_executed"
    assert report["config"]["model"] == "qwen-test"
    assert report["checks"] == [
        {
            "name": "planner_endpoint_healthy",
            "status": "ok",
            "detail": {"status": "ok", "probe": "models", "model_ids": ["qwen-test"]},
        },
        {
            "name": "planner_smoke_valid",
            "status": "ok",
            "detail": {
                "policy": {"action": "auto_approve", "reason": "auto-approved"},
                "preview": "Planned actions: launch firefox, then show notification 'Opened'.",
                "validation": {"errors": [], "valid": True},
            },
        },
    ]
    assert report["next_steps"] == [
        "Planner endpoint and smoke are valid. Enable live fallback only when you are ready: export OPERANCE_PLANNER_ENABLED=1.",
    ]


def test_planner_readiness_report_preserves_confirmation_gate_for_risky_plan() -> None:
    from operance.planner.readiness import build_planner_readiness_report
    from operance.policy import ExecutionPolicy
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    class FakePlannerClient:
        config = None

        def health(self) -> dict[str, object]:
            return {"status": "ok", "probe": "models", "model_ids": ["qwen-test"]}

        def plan(self, transcript: str) -> dict[str, object]:
            return {"actions": [{"tool": "apps.quit", "args": {"app": "firefox"}}]}

    report = build_planner_readiness_report(
        PlannerSettings(enabled=True),
        client=FakePlannerClient(),
        validator=PlanValidator(build_default_action_registry()),
        policy=ExecutionPolicy(),
        transcript="quit firefox",
    )

    assert report["status"] == "ok"
    assert report["safe_to_enable"] is True
    assert report["ready_for_live_fallback"] is True
    assert report["checks"][1]["detail"]["policy"] == {
        "action": "require_confirmation",
        "reason": "confirmation required",
    }
    assert report["checks"][1]["detail"]["validation"] == {"errors": [], "valid": True}


def test_planner_readiness_report_fails_when_endpoint_health_fails() -> None:
    from operance.planner.readiness import build_planner_readiness_report
    from operance.policy import ExecutionPolicy
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    class FakePlannerClient:
        config = None

        def health(self) -> dict[str, object]:
            return {"status": "failed", "errors": [{"message": "connection refused"}]}

        def plan(self, transcript: str) -> dict[str, object]:
            raise AssertionError("smoke should not run after failed health")

    report = build_planner_readiness_report(
        PlannerSettings(enabled=True),
        client=FakePlannerClient(),
        validator=PlanValidator(build_default_action_registry()),
        policy=ExecutionPolicy(),
    )

    assert report["status"] == "failed"
    assert report["safe_to_enable"] is False
    assert report["ready_for_live_fallback"] is False
    assert report["checks"][1] == {
        "name": "planner_smoke_valid",
        "status": "skipped",
        "detail": "planner endpoint health failed",
    }


def test_planner_readiness_report_fails_for_invalid_model_args() -> None:
    from operance.planner.readiness import build_planner_readiness_report
    from operance.policy import ExecutionPolicy
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    class FakePlannerClient:
        config = None

        def health(self) -> dict[str, object]:
            return {"status": "ok", "probe": "models", "model_ids": ["qwen-test"]}

        def plan(self, transcript: str) -> dict[str, object]:
            return {
                "actions": [
                    {
                        "tool": "apps.launch",
                        "args": {"app": "firefox", "shell_command": "rm -rf ~"},
                    }
                ]
            }

    report = build_planner_readiness_report(
        PlannerSettings(enabled=True),
        client=FakePlannerClient(),
        validator=PlanValidator(build_default_action_registry()),
        policy=ExecutionPolicy(),
    )

    assert report["status"] == "failed"
    assert report["checks"][1] == {
        "name": "planner_smoke_valid",
        "status": "failed",
        "detail": {
            "validation": {
                "valid": False,
                "errors": ["apps.launch: unexpected args: shell_command"],
            },
        },
    }


def test_planner_readiness_snapshot_uses_doctor_checks_without_smoke() -> None:
    from operance.planner.readiness import build_planner_readiness_snapshot

    snapshot = build_planner_readiness_snapshot(
        PlannerSettings(enabled=True, model="qwen-test"),
        report={
            "checks": [
                {"name": "planner_runtime_enabled", "status": "ok", "detail": {"enabled": True}},
                {"name": "planner_endpoint_healthy", "status": "ok", "detail": {"probe": "models"}},
            ]
        },
    )

    assert snapshot == {
        "status": "ok",
        "runtime_fallback_enabled": True,
        "ready_for_live_fallback": True,
        "safe_to_enable": True,
        "smoke_checked": False,
        "config": {
            "enabled": True,
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
            "failure_cooldown_seconds": 30.0,
            "max_consecutive_failures": 2,
            "max_retries": 1,
            "min_confidence": 0.7,
            "model": "qwen-test",
            "timeout_seconds": 30.0,
        },
        "checks": [
            {"name": "planner_runtime_enabled", "status": "ok", "detail": {"enabled": True}},
            {"name": "planner_endpoint_healthy", "status": "ok", "detail": {"probe": "models"}},
        ],
        "next_steps": [
            "Run python3 -m operance.cli --planner-readiness before relying on live fallback.",
        ],
    }
