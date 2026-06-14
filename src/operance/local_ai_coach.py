"""User-facing local AI planner onboarding guidance."""

from __future__ import annotations


def build_local_ai_coach(
    *,
    planner_status: dict[str, object],
    setup_template: dict[str, object],
    command_prefix: str = "python3 -m operance.cli",
) -> dict[str, object]:
    """Build a product-facing, non-mutating local AI setup guide."""

    status = str(planner_status.get("status") or "warn")
    mode = str(planner_status.get("mode") or "disabled_needs_setup")
    safe_to_enable = bool(planner_status.get("safe_to_enable"))
    runtime_fallback_enabled = bool(planner_status.get("runtime_fallback_enabled"))
    setup_profile = str(setup_template.get("profile") or "ollama")

    return {
        "title": "Local AI setup",
        "summary": _summary(
            status=status,
            mode=mode,
            safe_to_enable=safe_to_enable,
            runtime_fallback_enabled=runtime_fallback_enabled,
        ),
        "status": status,
        "mode": mode,
        "profile": setup_profile,
        "required_for_tray": False,
        "setup_policy": (
            "Optional. Operance does not install model servers, pull models, "
            "start servers, or enable planner fallback automatically."
        ),
        "steps": _steps(setup_template=setup_template, command_prefix=command_prefix),
        "safety_contract": setup_template.get("safety_contract") or planner_status.get("safety_contract") or [],
        "current_config": planner_status.get("config") or {},
        "next_steps": planner_status.get("next_steps") or [],
    }


def _summary(
    *,
    status: str,
    mode: str,
    safe_to_enable: bool,
    runtime_fallback_enabled: bool,
) -> str:
    if runtime_fallback_enabled and status == "ok":
        return "Local AI planner fallback is enabled and ready."
    if safe_to_enable:
        return "Local AI planner readiness passed; live fallback is still opt-in."
    if mode == "enabled_needs_attention":
        return "Local AI planner fallback is enabled, but readiness needs attention."
    return "Local AI planner fallback is optional and needs setup before use."


def _steps(*, setup_template: dict[str, object], command_prefix: str) -> list[dict[str, object]]:
    server = setup_template.get("server")
    server_command = None
    if isinstance(server, dict) and isinstance(server.get("command"), str):
        server_command = server["command"]

    export_commands = setup_template.get("export_commands")
    if not isinstance(export_commands, list):
        export_commands = []

    validation_commands = setup_template.get("validation_commands")
    if not isinstance(validation_commands, list):
        validation_commands = []

    return [
        {
            "label": "Start a local model server",
            "command": server_command,
            "description": "Run this outside Operance and keep it bound to localhost.",
        },
        {
            "label": "Point Operance at that server",
            "commands": [command for command in export_commands if isinstance(command, str)],
            "description": "Set endpoint, model, timeout, and retry environment variables.",
        },
        {
            "label": "Validate before enabling",
            "commands": [command for command in validation_commands if isinstance(command, str)],
            "description": "Readiness validates health, schema, policy, and confirmation gates without live fallback.",
        },
        {
            "label": "Run one explicit local AI execution test",
            "command": f'{command_prefix} --planner-execute "let me know when this is done"',
            "description": "This bypasses deterministic matching for one test and executes only auto-approved actions.",
        },
        {
            "label": "Enable live fallback only after readiness passes",
            "command": setup_template.get("enable_command"),
            "description": "Live fallback remains disabled until you opt in.",
        },
    ]
