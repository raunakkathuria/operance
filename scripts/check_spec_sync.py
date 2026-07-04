#!/usr/bin/env python3
"""Check that behavior-changing file sets include spec/doc evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import subprocess
import sys


BEHAVIOR_PREFIXES = (
    "src/operance/",
    "scripts/",
    "packaging/",
    "site/",
    ".github/workflows/",
)
TEST_PREFIXES = ("tests/",)
DOC_PREFIXES = ("docs/",)
DOC_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/goal_spec.md",
}
SPEC_PREFIXES = ("docs/specs/",)


@dataclass(slots=True, frozen=True)
class SpecSyncReport:
    changed_files: tuple[str, ...]
    behavior_files: tuple[str, ...]
    test_files: tuple[str, ...]
    doc_files: tuple[str, ...]
    spec_files: tuple[str, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def build_report(changed_files: list[str]) -> SpecSyncReport:
    normalized = tuple(sorted(_normalize_path(path) for path in changed_files if path.strip()))
    behavior_files = tuple(
        path
        for path in normalized
        if _matches_prefix(path, BEHAVIOR_PREFIXES) and not _matches_prefix(path, TEST_PREFIXES)
    )
    test_files = tuple(path for path in normalized if _matches_prefix(path, TEST_PREFIXES))
    doc_files = tuple(
        path
        for path in normalized
        if path in DOC_FILES or _matches_prefix(path, DOC_PREFIXES)
    )
    spec_files = tuple(path for path in normalized if _matches_prefix(path, SPEC_PREFIXES))

    errors: list[str] = []
    warnings: list[str] = []

    if behavior_files and "CHANGELOG.md" not in normalized:
        errors.append("Behavior-changing files changed without CHANGELOG.md.")

    doc_evidence_files = tuple(path for path in doc_files if path != "CHANGELOG.md")

    if behavior_files and not doc_evidence_files:
        errors.append("Behavior-changing files changed without README/docs/spec/template evidence.")

    if behavior_files and not spec_files:
        warnings.append(
            "No docs/specs/ file changed. Confirm the linked goal-spec issue covers scope, "
            "or update a spec when product behavior changed."
        )

    if test_files and not behavior_files and not doc_files:
        warnings.append("Tests changed without implementation or documentation changes.")

    return SpecSyncReport(
        changed_files=normalized,
        behavior_files=behavior_files,
        test_files=test_files,
        doc_files=doc_files,
        spec_files=spec_files,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def changed_files_from_git(base: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", base, "--"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def format_report(report: SpecSyncReport) -> str:
    lines = [
        f"changed_files={len(report.changed_files)}",
        f"behavior_files={len(report.behavior_files)}",
        f"test_files={len(report.test_files)}",
        f"doc_files={len(report.doc_files)}",
        f"spec_files={len(report.spec_files)}",
    ]
    if report.errors:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report.errors)
    if report.warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in report.warnings)
    if not report.errors:
        lines.append("status=ok")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff against, for example origin/main.",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed file path. Repeat to bypass git diff, mainly for tests.",
    )
    args = parser.parse_args(argv)

    changed_files = (
        list(args.changed_file)
        if args.changed_file
        else changed_files_from_git(args.base or "origin/main")
    )
    report = build_report(changed_files)
    print(format_report(report))
    return 0 if report.ok else 1


def _normalize_path(path: str) -> str:
    return path.strip().removeprefix("./")


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
