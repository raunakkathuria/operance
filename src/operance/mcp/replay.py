"""Stateful MCP fixture replay for local smoke testing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .server import MCPServer


def run_mcp_fixture(
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
    server = MCPServer(env)
    try:
        for record in records:
            method = record.get("method")
            if method == "tools/call":
                result = server.call_tool(
                    str(record["name"]),
                    _coerce_object(record.get("arguments", {}), "arguments"),
                )
            elif method == "resources/read":
                result = {"contents": [server.read_resource(str(record["uri"]))]}
            else:
                raise ValueError(f"unsupported MCP fixture method: {method}")

            expected_result = record.get("expected_result")
            is_match = True
            if expected_result is not None:
                is_match = _matches_expected(result, expected_result)
                if is_match:
                    passed += 1
            else:
                passed += 1

            results.append(
                {
                    "method": method,
                    "result": result,
                    "passed": is_match,
                }
            )
    finally:
        server.stop()

    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
    }


def _coerce_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _matches_expected(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            key in actual and _matches_expected(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) < len(expected):
            return False
        return all(_matches_expected(actual[index], value) for index, value in enumerate(expected))
    return actual == expected
