"""Issue-report draft helpers for public beta feedback."""

from __future__ import annotations


def build_issue_report_draft(
    snapshot: dict[str, object],
    *,
    bundle_path: str | None = None,
) -> str:
    """Build a paste-ready GitHub issue draft from a redacted support snapshot."""
    build = _dict_value(snapshot.get("build"))
    doctor = _dict_value(snapshot.get("doctor"))
    setup = _dict_value(snapshot.get("setup"))
    runnable_commands = _dict_value(snapshot.get("runnable_supported_commands"))
    runnable_summary = _dict_value(runnable_commands.get("summary"))
    planner = _dict_value(snapshot.get("planner_readiness"))
    voice_loop = _dict_value(snapshot.get("voice_loop_service"))
    warning_checks = _warning_checks(doctor.get("checks"))

    lines = [
        "# Operance issue report",
        "",
        "## Summary",
        "",
        "<Describe the problem in one or two sentences.>",
        "",
        "## Environment",
        "",
        f"- Version: {_string_value(build.get('version'))}",
        f"- Install mode: {_string_value(build.get('install_mode'))}",
        f"- Package profile: {_string_value(build.get('package_profile'))}",
        f"- Build commit: {_string_value(build.get('build_git_commit_short') or build.get('git_commit'))}",
        f"- Platform: {_string_value(doctor.get('platform'))}",
        f"- Python: {_string_value(doctor.get('python_version'))}",
        f"- Setup summary: {_string_value(setup.get('summary_status'))}",
        f"- MVP ready: {_yes_no(setup.get('ready_for_mvp'))}",
        (
            "- Runnable commands: "
            f"{_int_value(runnable_summary.get('available_commands'))} available, "
            f"{_int_value(runnable_summary.get('blocked_commands'))} blocked"
        ),
        (
            "- Planner: "
            f"status={_string_value(planner.get('status'))}, "
            f"safe_to_enable={_yes_no(planner.get('safe_to_enable'))}, "
            f"enabled={_yes_no(planner.get('runtime_fallback_enabled'))}"
        ),
        f"- Voice-loop service: {_string_value(voice_loop.get('status'))}",
        "",
        "## Reproduction",
        "",
        "1. <Command, tray action, or voice phrase>",
        "2. <What happened next>",
        "3. <Any repeatability detail>",
        "",
        "## Expected behavior",
        "",
        "<What should have happened?>",
        "",
        "## Actual behavior",
        "",
        "<What happened instead?>",
        "",
        "## Diagnostic highlights",
        "",
        _format_warning_checks(warning_checks),
    ]
    recommended_command = voice_loop.get("recommended_command")
    if isinstance(recommended_command, str) and recommended_command:
        lines.append(f"- Recommended voice-loop action: `{recommended_command}`")
    if bundle_path:
        lines.append(f"- Bundle: support bundle archive at `{bundle_path}`")
    else:
        lines.append("- Bundle: attach the generated support bundle archive if available.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Support bundles are redacted by default.",
            "- Do not paste secrets, private URLs, tokens, or unredacted local paths into public issues.",
        ]
    )
    return "\n".join(lines) + "\n"


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_value(value: object) -> str:
    return str(value) if isinstance(value, str) and value else "unknown"


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def _yes_no(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _warning_checks(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [
        check
        for check in value
        if isinstance(check, dict) and check.get("status") in {"warn", "failed"}
    ]


def _format_warning_checks(checks: list[dict[str, object]]) -> str:
    if not checks:
        return "- Doctor warnings: none"
    lines = ["- Doctor warnings:"]
    for check in checks[:8]:
        name = _string_value(check.get("name"))
        detail = check.get("detail")
        if isinstance(detail, (str, int, float, bool)):
            lines.append(f"  - {name}: {detail}")
        else:
            lines.append(f"  - {name}: {check.get('status')}")
    return "\n".join(lines)
