"""Public beta adoption checklist helpers."""

from __future__ import annotations


def build_public_beta_checklist(
    *,
    identity: dict[str, object],
    command_catalog: dict[str, object],
    release_status: dict[str, object],
    installed_readiness: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a concise public beta install, verify, try, and report checklist."""
    install_mode = _string_value(identity.get("install_mode"))
    command_prefix = "operance" if install_mode == "packaged" else "python3 -m operance.cli"
    command_summary = _dict_value(command_catalog.get("summary"))
    available_commands = _int_value(command_summary.get("available_commands"))
    installed_status = _string_value(_dict_value(installed_readiness).get("status"))
    packaged = install_mode == "packaged"
    ready = packaged and installed_status == "ok" and available_commands > 0
    install_command = _install_command(release_status)

    return {
        "status": "ready" if ready else ("source_checkout" if not packaged else "needs_attention"),
        "summary": _summary_text(
            packaged=packaged,
            installed_status=installed_status,
            available_commands=available_commands,
        ),
        "target": "Fedora KDE Plasma Wayland public beta",
        "install_mode": install_mode,
        "version": _string_value(identity.get("version")),
        "package_profile": _string_value(identity.get("package_profile")),
        "release": release_status,
        "checklist": [
            {
                "label": "Install packaged beta",
                "status": "done" if packaged else "recommended",
                "command": install_command,
            },
            {
                "label": "Verify installed runtime",
                "status": installed_status if packaged else "not_applicable",
                "command": f"{command_prefix} --installed-smoke" if packaged else None,
            },
            {
                "label": "List runnable commands",
                "status": "available" if available_commands > 0 else "needs_attention",
                "command": f"{command_prefix} --supported-commands --supported-commands-available-only",
            },
            {
                "label": "Run click-to-talk smoke",
                "status": "ready" if ready else "manual",
                "commands": _click_to_talk_smoke_commands(),
            },
            {
                "label": "Capture feedback if anything fails",
                "status": "available",
                "command": f"{command_prefix} --support-bundle",
                "issue_report_command": f"{command_prefix} --issue-report",
            },
        ],
        "try_commands": [item["say"] for item in _click_to_talk_smoke_commands()],
        "feedback": {
            "issue_url": "https://github.com/raunakkathuria/operance/issues/new/choose",
            "attach": [
                "support bundle archive",
                "issue-report.md draft",
                "spoken command or CLI transcript",
                "expected behavior",
                "actual behavior",
            ],
        },
        "next_steps": _next_steps(
            packaged=packaged,
            ready=ready,
            installed_status=installed_status,
            command_prefix=command_prefix,
            install_command=install_command,
        ),
    }


def _summary_text(*, packaged: bool, installed_status: str, available_commands: int) -> str:
    if packaged and installed_status == "ok" and available_commands > 0:
        return "Packaged beta is ready for tray click-to-talk testing."
    if packaged:
        return "Packaged beta is installed, but one or more readiness checks need attention."
    return "This is a source checkout; public beta testers should use the packaged RPM path."


def _next_steps(
    *,
    packaged: bool,
    ready: bool,
    installed_status: str,
    command_prefix: str,
    install_command: str,
) -> list[str]:
    if ready:
        return [
            "Click the tray icon and try the smoke commands.",
            f"Run {command_prefix} --support-bundle before changing the machine if anything fails.",
        ]
    if packaged and installed_status != "ok":
        return [
            f"Run {command_prefix} --installed-smoke and follow failed check suggestions.",
            f"Run {command_prefix} --support-bundle before changing the machine if the install path fails.",
        ]
    return [
        "Use the setup command from the current GitHub release assets.",
        f"Run {install_command}.",
    ]


def _install_command(release_status: dict[str, object]) -> str:
    setup_command = release_status.get("setup_command")
    if isinstance(setup_command, str) and setup_command:
        return setup_command
    return "bash ./setup.sh --package ./operance-0.1.0-1.noarch.rpm"


def _click_to_talk_smoke_commands() -> list[dict[str, str]]:
    return [
        {"say": "open browser", "expected": "The default browser opens."},
        {"say": "open google.com", "expected": "The default browser opens https://google.com."},
        {"say": "open firefox", "expected": "Firefox opens."},
        {"say": "open localhost:3000", "expected": "The default browser opens localhost:3000."},
        {"say": "what time is it", "expected": "Operance answers with the current local time."},
    ]


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_value(value: object) -> str:
    return str(value) if isinstance(value, str) and value else "unknown"


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0
