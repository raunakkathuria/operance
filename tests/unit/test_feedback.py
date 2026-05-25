from operance.feedback import build_issue_report_draft


def test_build_issue_report_draft_summarizes_support_snapshot() -> None:
    snapshot = {
        "build": {
            "name": "operance",
            "version": "0.1.0",
            "install_mode": "packaged",
            "build_git_commit_short": "abc1234",
            "package_profile": "mvp",
        },
        "doctor": {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "linux_platform", "status": "ok"},
                {"name": "tray_user_service_active", "status": "warn", "detail": "inactive"},
            ],
        },
        "setup": {
            "summary_status": "partial",
            "ready_for_mvp": False,
        },
        "runnable_supported_commands": {
            "summary": {
                "available_commands": 7,
                "blocked_commands": 2,
            }
        },
        "planner_readiness": {
            "status": "ok",
            "safe_to_enable": True,
            "runtime_fallback_enabled": False,
        },
        "voice_loop_service": {
            "status": "warn",
            "recommended_command": "systemctl --user restart operance-tray.service",
        },
    }

    draft = build_issue_report_draft(
        snapshot,
        bundle_path="/tmp/operance-support.tar.gz",
    )

    assert "# Operance issue report" in draft
    assert "- Version: 0.1.0" in draft
    assert "- Install mode: packaged" in draft
    assert "- Build commit: abc1234" in draft
    assert "- Platform: Linux" in draft
    assert "- Python: 3.14.0" in draft
    assert "- Setup summary: partial" in draft
    assert "- MVP ready: no" in draft
    assert "- Runnable commands: 7 available, 2 blocked" in draft
    assert "- Planner: status=ok, safe_to_enable=yes, enabled=no" in draft
    assert "- Voice-loop service: warn" in draft
    assert "- tray_user_service_active: inactive" in draft
    assert "- Bundle: support bundle archive at `/tmp/operance-support.tar.gz`" in draft
    assert "## Expected behavior" in draft
    assert "## Actual behavior" in draft


def test_build_issue_report_draft_handles_sparse_snapshot() -> None:
    draft = build_issue_report_draft({})

    assert "- Version: unknown" in draft
    assert "- Platform: unknown" in draft
    assert "- Setup summary: unknown" in draft
    assert "- Doctor warnings: none" in draft
