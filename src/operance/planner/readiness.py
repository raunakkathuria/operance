"""Readiness checks for local OpenAI-compatible planner runtimes."""

from __future__ import annotations

from typing import Mapping

from ..config import PlannerSettings
from ..policy import ExecutionPolicy
from ..validator import PlanValidator
from .client import PlannerClientError
from .parser import PlannerParseError, parse_planner_payload
from .preview import build_plan_preview


DEFAULT_PLANNER_READINESS_TRANSCRIPT = "open firefox and notify me"


def build_planner_readiness_report(
    config: PlannerSettings,
    *,
    client: object,
    validator: PlanValidator,
    policy: ExecutionPolicy,
    transcript: str = DEFAULT_PLANNER_READINESS_TRANSCRIPT,
) -> dict[str, object]:
    health = _planner_client_health(client)
    checks: list[dict[str, object]] = [
        {
            "name": "planner_endpoint_healthy",
            "status": "ok" if health.get("status") == "ok" else "failed",
            "detail": health,
        }
    ]

    if health.get("status") != "ok":
        checks.append(
            {
                "name": "planner_smoke_valid",
                "status": "skipped",
                "detail": "planner endpoint health failed",
            }
        )
        return {
            "status": "failed",
            "runtime_fallback_enabled": config.enabled,
            "ready_for_live_fallback": False,
            "safe_to_enable": False,
            "smoke_checked": False,
            "execution": "not_executed",
            "transcript": transcript,
            "config": _planner_config_payload(config),
            "checks": checks,
            "next_steps": [
                "Start or fix the local OpenAI-compatible planner server, then rerun python3 -m operance.cli --planner-readiness.",
            ],
        }

    try:
        planner_payload = _planner_client_plan(client, transcript)
        plan = parse_planner_payload(planner_payload, original_text=transcript)
    except (PlannerClientError, PlannerParseError, ValueError) as exc:
        failure_detail = _planner_smoke_failure_detail(exc)
        checks.append(
            {
                "name": "planner_smoke_valid",
                "status": "failed",
                "detail": failure_detail["detail"],
            }
        )
        return {
            "status": "failed",
            "runtime_fallback_enabled": config.enabled,
            "ready_for_live_fallback": False,
            "safe_to_enable": False,
            "smoke_checked": True,
            "execution": "not_executed",
            "transcript": transcript,
            "config": _planner_config_payload(config),
            "checks": checks,
            "next_steps": failure_detail["next_steps"],
        }

    validation_result = validator.validate(plan)
    validation_payload = {
        "valid": validation_result.valid,
        "errors": validation_result.errors,
    }
    if not validation_result.valid or validation_result.normalized_plan is None:
        checks.append(
            {
                "name": "planner_smoke_valid",
                "status": "failed",
                "detail": {"validation": validation_payload},
            }
        )
        return {
            "status": "failed",
            "runtime_fallback_enabled": config.enabled,
            "ready_for_live_fallback": False,
            "safe_to_enable": False,
            "smoke_checked": True,
            "execution": "not_executed",
            "transcript": transcript,
            "config": _planner_config_payload(config),
            "planner_payload": planner_payload,
            "plan": plan.to_dict(),
            "checks": checks,
            "next_steps": [
                "Fix the local planner output so validation passes before enabling live fallback.",
            ],
        }

    normalized_plan = validation_result.normalized_plan
    policy_decision = policy.decide(normalized_plan)
    checks.append(
        {
            "name": "planner_smoke_valid",
            "status": "ok",
            "detail": {
                "validation": validation_payload,
                "policy": {
                    "action": policy_decision.action,
                    "reason": policy_decision.reason,
                },
                "preview": build_plan_preview(normalized_plan),
            },
        }
    )
    safe_to_enable = True
    next_steps = (
        ["Planner endpoint and smoke are valid. Live fallback is enabled for this environment."]
        if config.enabled
        else [
            "Planner endpoint and smoke are valid. Enable live fallback only when you are ready: export OPERANCE_PLANNER_ENABLED=1.",
        ]
    )
    return {
        "status": "ok",
        "runtime_fallback_enabled": config.enabled,
        "ready_for_live_fallback": config.enabled and safe_to_enable,
        "safe_to_enable": safe_to_enable,
        "smoke_checked": True,
        "execution": "not_executed",
        "transcript": transcript,
        "config": _planner_config_payload(config),
        "planner_payload": planner_payload,
        "plan": normalized_plan.to_dict(),
        "checks": checks,
        "next_steps": next_steps,
    }


def build_planner_readiness_snapshot(
    config: PlannerSettings,
    *,
    report: Mapping[str, object],
) -> dict[str, object]:
    checks_by_name = _checks_by_name(report)
    runtime_check = checks_by_name.get(
        "planner_runtime_enabled",
        {"name": "planner_runtime_enabled", "status": "warn", "detail": {"enabled": config.enabled}},
    )
    health_check = checks_by_name.get(
        "planner_endpoint_healthy",
        {"name": "planner_endpoint_healthy", "status": "warn", "detail": "not checked"},
    )
    endpoint_healthy = health_check.get("status") == "ok"
    safe_to_enable = bool(endpoint_healthy)
    ready_for_live_fallback = config.enabled and safe_to_enable
    status = "ok" if ready_for_live_fallback else ("ready_to_enable" if safe_to_enable else "warn")
    return {
        "status": status,
        "runtime_fallback_enabled": config.enabled,
        "ready_for_live_fallback": ready_for_live_fallback,
        "safe_to_enable": safe_to_enable,
        "smoke_checked": False,
        "config": _planner_config_payload(config),
        "checks": [dict(runtime_check), dict(health_check)],
        "next_steps": [
            "Run python3 -m operance.cli --planner-readiness before relying on live fallback.",
        ],
    }


def _planner_config_payload(config: PlannerSettings) -> dict[str, object]:
    return {
        "enabled": config.enabled,
        "endpoint": config.endpoint,
        "model": config.model,
        "min_confidence": config.min_confidence,
        "timeout_seconds": config.timeout_seconds,
        "max_retries": config.max_retries,
        "max_consecutive_failures": config.max_consecutive_failures,
        "failure_cooldown_seconds": config.failure_cooldown_seconds,
    }


def _planner_smoke_failure_detail(exc: Exception) -> dict[str, object]:
    message = str(exc)
    normalized = message.lower()
    if isinstance(exc, PlannerClientError) and ("timed out" in normalized or "timeout" in normalized):
        return {
            "detail": {
                "message": message,
                "kind": "request_timeout",
            },
            "next_steps": [
                "Warm the local model with a direct prompt, or increase OPERANCE_PLANNER_TIMEOUT_SECONDS, then rerun python3 -m operance.cli --planner-readiness.",
                "For Ollama first-run testing, try: export OPERANCE_PLANNER_TIMEOUT_SECONDS=90.",
            ],
        }
    if isinstance(exc, PlannerClientError):
        return {
            "detail": {
                "message": message,
                "kind": "request_failed",
            },
            "next_steps": [
                "Fix the local planner server response, then rerun python3 -m operance.cli --planner-readiness.",
            ],
        }
    return {
        "detail": {
            "message": message,
            "kind": "schema_or_parse_error",
        },
        "next_steps": [
            "Fix the local planner response so it returns only the Operance typed action schema.",
        ],
    }


def _checks_by_name(report: Mapping[str, object]) -> dict[str, dict[str, object]]:
    checks = report.get("checks")
    if not isinstance(checks, list):
        return {}

    checks_by_name: dict[str, dict[str, object]] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        name = check.get("name")
        if isinstance(name, str):
            checks_by_name[name] = dict(check)
    return checks_by_name


def _planner_client_health(client: object) -> dict[str, object]:
    health = getattr(client, "health")()
    if not isinstance(health, dict):
        return {"status": "failed", "message": "planner health did not return an object"}
    return health


def _planner_client_plan(client: object, transcript: str) -> dict[str, object]:
    payload = getattr(client, "plan")(transcript)
    if not isinstance(payload, dict):
        raise PlannerClientError("planner smoke response must decode to a JSON object")
    return payload
