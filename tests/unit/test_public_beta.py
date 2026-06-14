from __future__ import annotations

from operance.public_beta import build_public_beta_checklist


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
