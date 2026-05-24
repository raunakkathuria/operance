"""First-run activation helpers for public beta onboarding."""

from __future__ import annotations

from .config import PlannerSettings
from .planner import build_planner_readiness_snapshot

PLANNER_SETUP_PROFILES = ("generic", "llama-cpp", "ollama")


def build_planner_setup_template(
    profile: str,
    *,
    command_prefix: str = "python3 -m operance.cli",
) -> dict[str, object]:
    """Build copy-paste local planner setup guidance without mutating the host."""
    normalized_profile = profile.strip().lower()
    if normalized_profile not in PLANNER_SETUP_PROFILES:
        raise ValueError(
            "planner setup profile must be one of: "
            + ", ".join(PLANNER_SETUP_PROFILES)
        )

    profile_payload = _planner_profile_payload(normalized_profile)
    environment = {
        "OPERANCE_PLANNER_ENDPOINT": profile_payload["endpoint"],
        "OPERANCE_PLANNER_MODEL": profile_payload["model"],
        "OPERANCE_PLANNER_TIMEOUT_SECONDS": profile_payload["timeout_seconds"],
        "OPERANCE_PLANNER_MAX_RETRIES": "1",
    }
    return {
        "status": "ok",
        "profile": normalized_profile,
        "label": profile_payload["label"],
        "description": profile_payload["description"],
        "server": profile_payload["server"],
        "environment": environment,
        "export_commands": [
            f"export {name}={value}"
            for name, value in environment.items()
        ],
        "validation_commands": [
            f"{command_prefix} --planner-status",
            f"{command_prefix} --planner-health",
            f"{command_prefix} --planner-readiness \"open firefox and notify me\"",
        ],
        "enable_command": "export OPERANCE_PLANNER_ENABLED=1",
        "safety_contract": _planner_safety_contract(),
        "next_steps": [
            "Start the local model server outside Operance.",
            "Export the planner environment variables.",
            "Run planner readiness before enabling live fallback.",
            "Enable live fallback only after readiness reports safe_to_enable=true.",
        ],
    }


def build_planner_status_report(
    config: PlannerSettings,
    *,
    environment_report: dict[str, object],
) -> dict[str, object]:
    """Build a non-executing local planner status report."""
    readiness = build_planner_readiness_snapshot(config, report=environment_report)
    status = str(readiness.get("status") or "warn")
    enabled = bool(readiness.get("runtime_fallback_enabled"))
    safe_to_enable = bool(readiness.get("safe_to_enable"))

    if enabled and status == "ok":
        mode = "enabled_ready"
        summary = "Local AI planner fallback is enabled and the endpoint is reachable."
    elif safe_to_enable:
        mode = "ready_to_enable"
        summary = "Local AI planner endpoint is reachable; live fallback is still disabled."
    elif enabled:
        mode = "enabled_needs_attention"
        summary = "Local AI planner fallback is enabled, but readiness checks need attention."
    else:
        mode = "disabled_needs_setup"
        summary = "Local AI planner fallback is disabled or not ready yet."

    return {
        "status": "ok" if mode in {"enabled_ready", "ready_to_enable"} else "warn",
        "mode": mode,
        "summary": summary,
        "config": readiness.get("config", {}),
        "checks": readiness.get("checks", []),
        "runtime_fallback_enabled": enabled,
        "safe_to_enable": safe_to_enable,
        "ready_for_live_fallback": bool(readiness.get("ready_for_live_fallback")),
        "smoke_checked": bool(readiness.get("smoke_checked")),
        "commands": {
            "health": "python3 -m operance.cli --planner-health",
            "readiness": "python3 -m operance.cli --planner-readiness",
            "smoke": "python3 -m operance.cli --planner-smoke \"open firefox and notify me\"",
            "execute": "python3 -m operance.cli --planner-execute \"let me know when this is done\"",
            "setup_template": "python3 -m operance.cli --planner-setup-template",
            "enable": "export OPERANCE_PLANNER_ENABLED=1",
        },
        "safety_contract": _planner_safety_contract(),
        "next_steps": readiness.get("next_steps", []),
    }


def build_getting_started_report(
    *,
    setup_snapshot: object,
    command_catalog: dict[str, object],
    planner_status: dict[str, object],
    identity: dict[str, object],
) -> dict[str, object]:
    """Build one concise first-run activation report."""
    ready_for_mvp = bool(getattr(setup_snapshot, "ready_for_mvp", False))
    ready_for_local_runtime = bool(getattr(setup_snapshot, "ready_for_local_runtime", False))
    command_prefix = _command_prefix(identity)
    available_examples = _available_examples(command_catalog, limit=8)

    if ready_for_mvp:
        status = "ready"
        headline = "Operance is ready for the current click-to-talk developer path."
        primary_command = f"{command_prefix} --mvp-launch"
    elif ready_for_local_runtime:
        status = "partial"
        headline = "Operance core runtime is ready, but the click-to-talk path still needs setup."
        primary_command = f"{command_prefix} --setup-actions"
    else:
        status = "needs_setup"
        headline = "Operance needs setup before the current developer path is runnable."
        primary_command = f"{command_prefix} --setup-run-recommended --setup-dry-run"

    return {
        "status": status,
        "headline": headline,
        "product_summary": (
            "Operance turns natural language into safe typed desktop actions through "
            "a portable core and OS-specific adapters."
        ),
        "current_target": "Linux first: Fedora KDE Wayland developer beta.",
        "start_here": [
            {
                "label": "Check readiness",
                "command": f"{command_prefix} --doctor",
            },
            {
                "label": "Launch the preferred interaction path",
                "command": primary_command,
            },
            {
                "label": "Show runnable commands",
                "command": f"{command_prefix} --supported-commands --supported-commands-available-only",
            },
            {
                "label": "Capture a support bundle",
                "command": f"{command_prefix} --support-bundle",
            },
        ],
        "try_commands": available_examples,
        "local_ai_planner": {
            "mode": planner_status.get("mode"),
            "summary": planner_status.get("summary"),
            "readiness_command": planner_status.get("commands", {}).get("readiness")
            if isinstance(planner_status.get("commands"), dict)
            else None,
            "setup_template_command": planner_status.get("commands", {}).get("setup_template")
            if isinstance(planner_status.get("commands"), dict)
            else None,
            "safe_to_enable": planner_status.get("safe_to_enable"),
        },
        "contributor_next_steps": [
            "Read docs/contributing/command-authoring.md before adding commands.",
            "Keep new execution in adapters and availability in platform providers.",
            "Run pytest plus the release-readiness gate before opening a PR.",
        ],
    }


def _command_prefix(identity: dict[str, object]) -> str:
    if identity.get("install_mode") == "packaged":
        return "operance"
    return "python3 -m operance.cli"


def _available_examples(catalog: dict[str, object], *, limit: int) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    domains = catalog.get("domains")
    if not isinstance(domains, list):
        return examples

    for domain in domains:
        if not isinstance(domain, dict):
            continue
        label = str(domain.get("label") or domain.get("domain") or "Commands")
        commands = domain.get("commands")
        if not isinstance(commands, list):
            continue
        for command in sorted(
            (command for command in commands if isinstance(command, dict)),
            key=_command_priority,
        ):
            if command.get("live_runtime_status") != "available":
                continue
            example = _first_example(command)
            if example is None:
                continue
            examples.append({"group": label, "say": example})
            if len(examples) >= limit:
                return examples
    return examples


def _command_priority(command: dict[str, object]) -> tuple[int, str]:
    tool = str(command.get("tool") or "")
    priority = {
        "apps.launch": 0,
        "time.now": 1,
        "network.wifi_status": 2,
        "audio.get_volume": 3,
        "audio.mute_status": 4,
        "files.list_recent": 5,
        "windows.list": 6,
        "windows.switch": 7,
        "apps.focus": 8,
        "apps.quit": 9,
    }
    return (priority.get(tool, 100), tool)


def _first_example(command: dict[str, object]) -> str | None:
    usage_pattern = command.get("usage_pattern")
    if isinstance(usage_pattern, str) and usage_pattern:
        return usage_pattern
    example_transcripts = command.get("example_transcripts")
    if not isinstance(example_transcripts, list):
        return None
    for example in example_transcripts:
        if isinstance(example, str) and example:
            return example
    return None


def _planner_safety_contract() -> list[str]:
    return [
        "The local model may only return the Operance typed action schema.",
        "Validation and policy still run before execution.",
        "Confirmation-gated actions remain gated even when the model planned them.",
        "The planner path never executes raw shell, PowerShell, AppleScript, or KWin scripts.",
    ]


def _planner_profile_payload(profile: str) -> dict[str, object]:
    if profile == "llama-cpp":
        return {
            "label": "llama.cpp server",
            "description": "Use a local llama.cpp server exposing OpenAI-compatible chat completions.",
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
            "model": "qwen2.5-7b-instruct",
            "timeout_seconds": "60",
            "server": {
                "command": "llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080",
                "notes": [
                    "Use any instruction-tuned local model that follows JSON-schema prompts reliably.",
                    "Keep the server bound to localhost for the current beta path.",
                ],
            },
        }
    if profile == "ollama":
        return {
            "label": "Ollama OpenAI-compatible API",
            "description": "Use Ollama's local OpenAI-compatible chat-completions API.",
            "endpoint": "http://127.0.0.1:11434/v1/chat/completions",
            "model": "qwen2.5:3b",
            "timeout_seconds": "90",
            "server": {
                "command": "ollama run qwen2.5:3b",
                "notes": [
                    "Ollama must be running locally before Operance can probe planner health.",
                    "Use a different local model by changing OPERANCE_PLANNER_MODEL.",
                ],
            },
        }
    return {
        "label": "Generic OpenAI-compatible local server",
        "description": "Use any local server that exposes /v1/chat/completions and either /v1/models or /health.",
        "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
        "model": "qwen2.5-7b-instruct",
        "timeout_seconds": "60",
        "server": {
            "command": None,
            "notes": [
                "Start your local OpenAI-compatible server outside Operance.",
                "Set endpoint and model to match that server before running planner readiness.",
            ],
        },
    }
