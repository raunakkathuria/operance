from __future__ import annotations

from operance.public_beta import build_beta_feedback_guide, build_public_beta_checklist


def test_public_beta_checklist_reports_ready_packaged_path() -> None:
    setup_command = (
        "bash <(curl -fsSL https://github.com/raunakkathuria/operance/releases/download/v0.1.0-beta.10/setup.sh) "
        "--release-url https://github.com/raunakkathuria/operance/releases/download/v0.1.0-beta.10"
    )
    payload = build_public_beta_checklist(
        identity={"install_mode": "packaged", "version": "0.1.0", "package_profile": "mvp"},
        command_catalog={"summary": {"available_commands": 8}},
        release_status={
            "message": "Update available: v0.1.0-beta.10.",
            "setup_command": setup_command,
        },
        installed_readiness={"status": "ok"},
    )

    assert payload["status"] == "ready"
    assert payload["summary"] == "Packaged beta is ready for tray click-to-talk testing."
    assert payload["target"] == "Fedora KDE Plasma Wayland public beta"
    assert payload["checklist"][0] == {
        "label": "Install packaged beta",
        "status": "done",
        "command": setup_command,
    }
    assert payload["checklist"][1] == {
        "label": "Verify installed runtime",
        "status": "ok",
        "command": "operance --installed-smoke",
    }
    assert payload["checklist"][3]["commands"][0]["say"] == "open browser"
    assert payload["checklist"][3]["commands"][2] == {
        "say": "search google for linux automation",
        "expected": "The default browser opens a Google search.",
    }
    assert payload["checklist"][4]["command"] == "operance --support-bundle"
    assert payload["checklist"][4]["issue_report_command"] == "operance --issue-report"
    assert payload["workflow"]["install_readiness"]["status"] == "done"
    assert payload["workflow"]["tray_readiness"]["command"] == "operance --installed-smoke"
    assert payload["workflow"]["command_script"]["commands"][0] == "open browser"
    assert payload["workflow"]["failure_reporting"]["issue_report_command"] == "operance --issue-report"
    assert payload["feedback"]["guide_command"] == "operance --beta-feedback"
    assert payload["feedback"]["issue_url"] == "https://github.com/raunakkathuria/operance/issues/new/choose"


def test_public_beta_checklist_points_source_checkouts_to_release_assets() -> None:
    payload = build_public_beta_checklist(
        identity={"install_mode": "source", "version": "0.1.0"},
        command_catalog={"summary": {"available_commands": 4}},
        release_status={},
    )

    assert payload["status"] == "source_checkout"
    assert payload["summary"] == "This is a source checkout; public beta testers should use the packaged RPM path."
    assert payload["checklist"][0]["status"] == "recommended"
    assert payload["checklist"][0]["command"] == "bash ./setup.sh --package ./operance-0.1.0-1.noarch.rpm"
    assert payload["checklist"][1] == {
        "label": "Verify installed runtime",
        "status": "not_applicable",
        "command": None,
    }
    assert "Use the setup command from the current GitHub release assets." in payload["next_steps"]


def test_beta_feedback_guide_builds_ten_minute_loop_for_packaged_path() -> None:
    payload = build_beta_feedback_guide(
        identity={"install_mode": "packaged", "version": "0.1.0"},
        release_status={"setup_command": "bash ./setup.sh --release-url https://example.test/release"},
    )

    assert payload["title"] == "10-minute beta feedback loop"
    assert payload["time_budget_minutes"] == 10
    assert payload["sections"][0] == {
        "label": "Install",
        "goal": "Use the packaged release path for beta testing.",
        "commands": [
            "bash ./setup.sh --release-url https://example.test/release",
            "operance --version",
        ],
    }
    assert payload["sections"][1]["commands"][0] == "operance --installed-smoke"
    assert payload["sections"][2]["commands"] == [
        "open browser",
        "open google.com",
        "search google for linux automation",
        "open firefox",
        "open downloads",
        "what time is it",
        "wifi status",
        "what is the volume",
        "set volume to 50 percent",
    ]
    assert payload["sections"][3]["commands"] == ["operance --issue-report", "operance --support-bundle"]
    assert "command was misunderstood" in payload["report_even_if"]
