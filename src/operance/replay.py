"""Transcript replay and regression reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .session import process_transcript


def run_replay_fixture(
    fixture_path: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    records = [
        json.loads(line)
        for line in fixture_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    results: list[dict[str, object]] = []
    passed = 0

    for record in records:
        actual = process_transcript(record["transcript"], env)
        is_match = (
            actual["response"] == record["expected_response"]
            and actual["status"] == record["expected_status"]
        )
        if is_match:
            passed += 1

        results.append(
            {
                "transcript": record["transcript"],
                "expected_response": record["expected_response"],
                "expected_status": record["expected_status"],
                "actual_response": actual["response"],
                "actual_status": actual["status"],
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
