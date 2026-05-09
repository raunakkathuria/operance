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
    parser.add_argument(
        "--check-tray-service",
        action="store_true",
        help="Also verify that operance-tray.service is not shadowed by a stale source-checkout unit.",
    )
    parser.add_argument(
        "--systemctl-command",
        default="systemctl",
        help="systemctl command to use for tray service inspection. Defaults to systemctl.",
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


def _tray_service_failures(
    *,
    expected_command: str,
    systemctl_command: str,
) -> list[str]:
    completed = subprocess.run(
        [
            systemctl_command,
            "--user",
            "show",
            "operance-tray.service",
            "-p",
            "LoadState",
            "-p",
            "ActiveState",
            "-p",
            "FragmentPath",
            "-p",
            "ExecStart",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return [f"operance-tray.service: could not inspect user service ({_command_detail(completed)})"]

    properties: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value

    load_state = properties.get("LoadState")
    if load_state in {None, "", "not-found"}:
        return []

    failures: list[str] = []
    fragment_path = properties.get("FragmentPath") or ""
    exec_start = properties.get("ExecStart") or ""
    if expected_command not in exec_start:
        failures.append(
            "operance-tray.service: expected installed command in ExecStart; "
            f"expected={expected_command!r} exec_start={exec_start!r}"
        )

    if fragment_path.startswith("/home/") and "/.config/systemd/user/" in fragment_path:
        failures.append(
            "operance-tray.service: user unit shadows the packaged unit; "
            f"fragment={fragment_path!r}"
        )

    return failures


def _command_detail(completed: subprocess.CompletedProcess[str]) -> str:
    return (completed.stderr or completed.stdout or "").strip() or f"exit code {completed.returncode}"


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

    if args.check_tray_service:
        failures.extend(
            _tray_service_failures(
                expected_command=args.command,
                systemctl_command=args.systemctl_command,
            )
        )

    if failures:
        print("installed MVP runtime check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "required_checks": list(required_checks),
                "status": "ok",
                "tray_service_checked": bool(args.check_tray_service),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
