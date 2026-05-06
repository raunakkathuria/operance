from operance.supported_commands import build_supported_command_catalog, build_supported_command_help_text


def test_build_supported_command_help_text_renders_examples_and_blockers() -> None:
    help_text = build_supported_command_help_text(
        {
            "summary": {
                "total_commands": 5,
                "available_commands": 2,
                "unverified_commands": 1,
                "confirmation_gated_commands": 1,
                "blocked_commands": 2,
            },
            "domains": [
                {
                    "domain": "apps",
                    "label": "Apps",
                    "commands": [
                        {
                            "tool": "apps.launch",
                            "example_transcripts": ["open firefox"],
                            "usage_pattern": "open <app name>",
                            "requires_confirmation": False,
                            "live_runtime_status": "available",
                            "live_runtime_blockers": [],
                        },
                        {
                            "tool": "apps.quit",
                            "example_transcripts": ["quit firefox"],
                            "usage_pattern": "quit <app name>",
                            "requires_confirmation": True,
                            "live_runtime_status": "available",
                            "live_runtime_blockers": [],
                        },
                        {
                            "tool": "apps.focus",
                            "example_transcripts": ["focus firefox"],
                            "usage_pattern": "focus <app name>",
                            "requires_confirmation": False,
                            "live_runtime_status": "unverified",
                            "release_verification_target": "fedora_kde_wayland_developer_alpha",
                            "live_runtime_blockers": [],
                        },
                    ],
                },
                {
                    "domain": "clipboard",
                    "label": "Clipboard",
                    "commands": [
                        {
                            "tool": "clipboard.paste",
                            "example_transcripts": ["paste clipboard"],
                            "requires_confirmation": False,
                            "live_runtime_status": "blocked",
                            "live_runtime_blockers": ["Wayland text input backend"],
                        },
                        {
                            "tool": "clipboard.copy_selection",
                            "example_transcripts": ["copy selection"],
                            "requires_confirmation": False,
                            "live_runtime_status": "blocked",
                            "live_runtime_blockers": ["Wayland text input backend"],
                        },
                    ],
                },
            ],
        }
    )

    assert help_text["title"] == "Supported commands"
    assert help_text["summary"] == (
        "2 release-verified and available, 1 unverified, 2 blocked, 1 confirmation-gated."
    )
    assert help_text["examples"] == [
        "open <app name>",
        "quit <app name> (confirmation)",
    ]
    assert "Apps:" in help_text["details"]
    assert "- open <app name>" in help_text["details"]
    assert "- quit <app name> (confirmation)" in help_text["details"]
    assert "Apps not yet release-verified:" in help_text["details"]
    assert "- focus <app name> -> fedora_kde_wayland_developer_alpha" in help_text["details"]
    assert "Clipboard blocked:" in help_text["details"]
    assert "- paste clipboard -> Wayland text input backend" in help_text["details"]


def test_build_supported_command_catalog_can_filter_available_commands_only() -> None:
    report = {
        "platform": "Linux",
        "python_version": "3.14.0",
        "checks": [
            {"name": "python_3_12_plus", "status": "ok", "detail": "3.14.0"},
            {"name": "virtualenv_active", "status": "ok", "detail": "active"},
            {"name": "linux_platform", "status": "ok", "detail": "Linux"},
            {"name": "kde_wayland_target", "status": "ok", "detail": {"session_type": "wayland", "desktop_session": "KDE"}},
            {"name": "wayland_session_accessible", "status": "ok", "detail": "ok"},
            {"name": "xdg_open_available", "status": "ok", "detail": "/usr/bin/xdg-open"},
            {"name": "notify_send_available", "status": "ok", "detail": "/usr/bin/notify-send"},
            {"name": "gdbus_available", "status": "ok", "detail": "/usr/bin/gdbus"},
            {"name": "networkmanager_cli_available", "status": "ok", "detail": "/usr/bin/nmcli"},
            {"name": "audio_cli_available", "status": "ok", "detail": {"wpctl": "/usr/bin/wpctl"}},
            {"name": "clipboard_cli_available", "status": "ok", "detail": {"wl-copy": "/usr/bin/wl-copy", "wl-paste": "/usr/bin/wl-paste"}},
            {"name": "text_input_cli_available", "status": "warn", "detail": {"wtype": None}},
            {"name": "systemctl_user_available", "status": "ok", "detail": "/usr/bin/systemctl"},
            {"name": "power_status_available", "status": "ok", "detail": {"upower": "/usr/bin/upower"}},
        ],
    }

    catalog = build_supported_command_catalog(report, available_only=True)
    commands = {
        command["tool"]: command
        for domain in catalog["domains"]
        for command in domain["commands"]
    }

    assert catalog["catalog_filter"] == "available_only"
    assert "apps.launch" in commands
    assert "windows.list" not in commands
    assert "text.type" not in commands
    assert catalog["summary"]["unverified_commands"] == 0
    assert catalog["summary"]["blocked_commands"] == 0
