"""Supported-command catalog and user-facing help text."""

from __future__ import annotations

from .doctor import build_environment_report
from .models.actions import ToolName
from .platforms import get_platform_provider
from .registry import build_default_action_registry


def build_supported_command_catalog(
    report: dict[str, object] | None = None,
    *,
    available_only: bool = False,
) -> dict[str, object]:
    environment_report = build_environment_report() if report is None else report
    provider = get_platform_provider(
        system_name=str(environment_report.get("platform") or ""),
        provider_id=(
            str(environment_report["platform_provider"])
            if isinstance(environment_report.get("platform_provider"), str)
            else None
        ),
    )
    snapshot = _build_setup_snapshot(environment_report)
    steps_by_name = {step.name: step for step in snapshot.steps}
    registry = build_default_action_registry()

    commands_by_domain: dict[str, list[dict[str, object]]] = {}

    for spec in registry.list_specs():
        blockers = provider.tool_live_runtime_blockers(spec.name, steps_by_name)
        release_verification_status = _tool_release_verification_status(
            spec.name,
            provider.release_verified_tools,
        )
        live_runtime_status = _tool_live_runtime_status(blockers, release_verification_status)
        if available_only and live_runtime_status != "available":
            continue

        domain = spec.name.value.split(".", 1)[0]
        commands_by_domain.setdefault(domain, []).append(
            {
                "tool": spec.name.value,
                "description": spec.description,
                "example_transcripts": list(spec.example_transcripts),
                "usage_pattern": _tool_usage_pattern(spec.name),
                "risk_tier": spec.risk_tier.name.lower(),
                "requires_confirmation": spec.requires_confirmation,
                "undoable": spec.undoable,
                "live_runtime_status": live_runtime_status,
                "live_runtime_blockers": blockers,
                "release_verification_status": release_verification_status,
                "release_verification_target": provider.release_verification_target,
                "live_runtime_suggested_command": provider.tool_live_runtime_suggested_command(
                    spec.name,
                    steps_by_name,
                ),
            }
        )

    domains = [
        {
            "domain": domain,
            "label": domain.replace("_", " ").title(),
            "commands": commands_by_domain[domain],
        }
        for domain in sorted(commands_by_domain)
    ]
    all_commands = [
        command
        for domain in domains
        for command in domain["commands"]
    ]
    total_commands = len(all_commands)
    available_count = sum(1 for command in all_commands if command["live_runtime_status"] == "available")
    unverified_count = sum(1 for command in all_commands if command["live_runtime_status"] == "unverified")
    blocked_count = sum(1 for command in all_commands if command["live_runtime_status"] == "blocked")
    confirmation_count = sum(1 for command in all_commands if bool(command["requires_confirmation"]))
    return {
        "catalog_filter": "available_only" if available_only else "all",
        "summary": {
            "total_commands": total_commands,
            "available_commands": available_count,
            "unverified_commands": unverified_count,
            "confirmation_gated_commands": confirmation_count,
            "blocked_commands": blocked_count,
        },
        "domains": domains,
    }


def build_supported_command_help_text(catalog: dict[str, object]) -> dict[str, object]:
    summary = catalog.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    domains = catalog.get("domains")
    if not isinstance(domains, list):
        domains = []

    available_count = _int_value(summary.get("available_commands"))
    unverified_count = _int_value(summary.get("unverified_commands"))
    blocked_count = _int_value(summary.get("blocked_commands"))
    confirmation_count = _int_value(summary.get("confirmation_gated_commands"))

    examples: list[str] = []
    details_lines: list[str] = []

    for domain in domains:
        if not isinstance(domain, dict):
            continue
        label = str(domain.get("label") or domain.get("domain") or "Commands")
        commands = domain.get("commands")
        if not isinstance(commands, list):
            continue

        available_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "available"
        ]
        unverified_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "unverified"
        ]
        blocked_commands = [
            command for command in commands if isinstance(command, dict) and command.get("live_runtime_status") == "blocked"
        ]

        if available_commands:
            details_lines.append(f"{label}:")
            for command in available_commands:
                line = _command_example_text(command)
                details_lines.append(f"- {line}")
                if len(examples) < 6:
                    examples.append(line)

        if unverified_commands:
            details_lines.append(f"{label} not yet release-verified:")
            for command in unverified_commands:
                target = command.get("release_verification_target")
                target_text = (
                    f" -> {target}"
                    if isinstance(target, str) and target
                    else ""
                )
                details_lines.append(f"- {_command_example_text(command)}{target_text}")

        if blocked_commands:
            details_lines.append(f"{label} blocked:")
            for command in blocked_commands:
                blockers = command.get("live_runtime_blockers")
                blockers_text = ", ".join(str(blocker) for blocker in blockers) if isinstance(blockers, list) else "Unavailable"
                details_lines.append(f"- {_command_example_text(command)} -> {blockers_text}")

    if not details_lines:
        details_lines.append("No supported command metadata is available.")

    return {
        "title": "Supported commands",
        "summary": (
            f"{available_count} release-verified and available, "
            f"{unverified_count} unverified, {blocked_count} blocked, "
            f"{confirmation_count} confirmation-gated."
        ),
        "examples": examples,
        "details": "\n".join(details_lines),
    }


def _command_example_text(command: dict[str, object]) -> str:
    usage_pattern = command.get("usage_pattern")
    if isinstance(usage_pattern, str) and usage_pattern:
        return (
            f"{usage_pattern} (confirmation)"
            if bool(command.get("requires_confirmation"))
            else usage_pattern
        )
    example_transcripts = command.get("example_transcripts")
    if isinstance(example_transcripts, list):
        for example in example_transcripts:
            if isinstance(example, str) and example:
                return (
                    f"{example} (confirmation)"
                    if bool(command.get("requires_confirmation"))
                    else example
                )
    tool = str(command.get("tool") or "unknown")
    return (
        f"{tool} (confirmation)"
        if bool(command.get("requires_confirmation"))
        else tool
    )


def _tool_usage_pattern(tool: ToolName) -> str | None:
    patterns = {
        ToolName.APPS_LAUNCH: "open <app name> | open http://localhost:3000 | browse to localhost 3000 | open <app> and load <url>",
        ToolName.APPS_FOCUS: "focus <app name>",
        ToolName.APPS_QUIT: "quit <app name>",
        ToolName.FILES_OPEN: "open file on desktop called <name> | open recent file called <name>",
    }
    return patterns.get(tool)


def _tool_live_runtime_status(
    blockers: list[str],
    release_verification_status: str,
) -> str:
    if blockers:
        return "blocked"
    if release_verification_status != "verified":
        return "unverified"
    return "available"


def _tool_release_verification_status(
    tool: ToolName,
    release_verified_tools: frozenset[ToolName],
) -> str:
    if tool in release_verified_tools:
        return "verified"
    return "unverified"


def _build_setup_snapshot(report: dict[str, object]) -> object:
    from .ui.setup import build_setup_snapshot

    return build_setup_snapshot(report)


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0
