#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


DEFAULT_REQUIRED_CHECKS = ("tray_ui_available", "stt_backend_available")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that an installed Operance command has the packaged MVP runtime dependencies."
    )
    parser.add_argument(
        "--command",
        default="operance",
        help="Installed Operance command to inspect. Defaults to operance.",
    )
    parser.add_argument(
        "--require-check",
        action="append",
        dest="required_checks",
        help="Doctor check that must report status=ok. Defaults to the MVP tray and STT runtime checks.",
    )
    return parser.parse_args()


def _doctor_payload(command: str) -> dict[str, Any]:
    completed = subprocess.run(
        [command, "--doctor"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or "operance --doctor failed")

    for line in reversed([item.strip() for item in completed.stdout.splitlines() if item.strip()]):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("checks"), list):
            return payload
    raise SystemExit("could not find a doctor JSON payload in command output")


def _config_payload(command: str) -> dict[str, Any]:
    completed = subprocess.run(
        [command, "--print-config"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            completed.stderr.strip() or completed.stdout.strip() or "operance --print-config failed"
        )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"could not parse config JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("config payload is not a JSON object")
    return payload


def _checks_by_name(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for item in payload.get("checks", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            checks[item["name"]] = item
    return checks


def main() -> int:
    args = _parse_args()
    required_checks = tuple(args.required_checks or DEFAULT_REQUIRED_CHECKS)
    checks = _checks_by_name(_doctor_payload(args.command))
    config = _config_payload(args.command)
    failures: list[str] = []

    for check_name in required_checks:
        check = checks.get(check_name)
        if check is None:
            failures.append(f"{check_name}: missing")
            continue
        if check.get("status") != "ok":
            failures.append(f"{check_name}: status={check.get('status')} detail={check.get('detail')}")

    runtime = config.get("runtime")
    developer_mode = runtime.get("developer_mode") if isinstance(runtime, dict) else None
    if developer_mode is not False:
        failures.append(f"runtime.developer_mode: expected false, got {developer_mode!r}")

    if failures:
        print("installed MVP runtime check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(json.dumps({"required_checks": list(required_checks), "status": "ok"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
