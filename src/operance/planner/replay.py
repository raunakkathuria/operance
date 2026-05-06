"""Planner fixture replay and validation reporting."""

from __future__ import annotations

import json
from pathlib import Path

from ..registry import build_default_action_registry
from ..validator import PlanValidator
from .parser import PlannerParseError, parse_planner_payload


def run_planner_fixture(fixture_path: Path) -> dict[str, object]:
    records = [
        json.loads(line)
        for line in fixture_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    validator = PlanValidator(build_default_action_registry())
    results: list[dict[str, object]] = []
    passed = 0

    for record in records:
        transcript = str(record["transcript"])
        payload = record["planner_payload"]
        expected_valid = bool(record["expected_valid"])
        expected_tools = list(record.get("expected_tools", []))

        actual_valid = False
        actual_tools: list[str] = []
        error: str | None = None

        try:
            plan = parse_planner_payload(payload, original_text=transcript)
            actual_tools = [action.tool.value for action in plan.actions]
            actual_valid = validator.validate(plan).valid
        except PlannerParseError as exc:
            error = str(exc)

        is_match = actual_valid == expected_valid and actual_tools == expected_tools
        if is_match:
            passed += 1

        results.append(
            {
                "transcript": transcript,
                "expected_valid": expected_valid,
                "actual_valid": actual_valid,
                "expected_tools": expected_tools,
                "actual_tools": actual_tools,
                "error": error,
                "passed": is_match,
            }
        )

    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
    }
