#!/usr/bin/env python3
"""Validate installed Operance package build identity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", default="operance", help="Installed operance command to inspect")
    parser.add_argument("--package-profile", help="Expected package profile, for example mvp")
    args = parser.parse_args()

    completed = subprocess.run(
        [args.command, "--about"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        print("installed build identity check failed:", file=sys.stderr)
        print((completed.stderr or completed.stdout or "").strip(), file=sys.stderr)
        return 1

    try:
        identity = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(f"installed build identity check failed: invalid JSON: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    if identity.get("install_mode") != "packaged":
        failures.append(f"install_mode={identity.get('install_mode')!r}")
    if not identity.get("build_git_commit"):
        failures.append("build_git_commit missing")
    if not identity.get("build_git_commit_short"):
        failures.append("build_git_commit_short missing")
    if not identity.get("build_time"):
        failures.append("build_time missing")
    if not identity.get("install_root"):
        failures.append("install_root missing")
    if args.package_profile and identity.get("package_profile") != args.package_profile:
        failures.append(f"package_profile={identity.get('package_profile')!r}")

    if failures:
        print("installed build identity check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(json.dumps({"identity_checked": True, "status": "ok"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
