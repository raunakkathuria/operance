from operance.support_snapshot import (
    build_support_snapshot,
    build_support_snapshot_help_text,
    redact_support_snapshot,
)


def test_build_support_snapshot_reuses_one_doctor_report(monkeypatch) -> None:
    report = {
        "platform": "Linux",
        "python_version": "3.14.0",
        "checks": [{"name": "linux_platform", "status": "ok", "detail": "Linux"}],
    }
    received_reports: list[dict[str, object]] = []

    class _FakeSetupSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"summary_status": "ready", "ready_for_mvp": True}

    class _FakeVoiceLoopConfigSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"selected_args_file": "/home/test/.config/operance/voice-loop.args"}

    class _FakeVoiceLoopServiceSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"status": "warn", "recommended_command": "./scripts/install_voice_loop_user_service.sh"}

    monkeypatch.setattr("operance.support_snapshot.build_environment_report", lambda: report)
    monkeypatch.setattr(
        "operance.support_snapshot._build_setup_snapshot",
        lambda doctor_report: received_reports.append(doctor_report) or _FakeSetupSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_supported_command_catalog",
        lambda doctor_report, available_only=False: received_reports.append(doctor_report)
        or (
            {
                "catalog_filter": "available_only",
                "summary": {"available_commands": 3, "unverified_commands": 0, "blocked_commands": 0},
            }
            if available_only
            else {
                "catalog_filter": "all",
                "summary": {"available_commands": 3, "unverified_commands": 5, "blocked_commands": 2},
            }
        ),
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_voice_loop_config_snapshot",
        lambda env=None: _FakeVoiceLoopConfigSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_voice_loop_service_snapshot",
        lambda env=None, report=None: received_reports.append(report) or _FakeVoiceLoopServiceSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_snapshot._build_recent_audit_payload",
        lambda env=None, limit=20: {"count": 1, "entries": [{"status": "success", "transcript": "open firefox"}]},
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
    )

    snapshot = build_support_snapshot()

    assert snapshot == {
        "build": {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
        "doctor": report,
        "setup": {"summary_status": "ready", "ready_for_mvp": True},
        "supported_commands": {
            "catalog_filter": "all",
            "summary": {"available_commands": 3, "unverified_commands": 5, "blocked_commands": 2},
        },
        "runnable_supported_commands": {
            "catalog_filter": "available_only",
            "summary": {"available_commands": 3, "unverified_commands": 0, "blocked_commands": 0},
        },
        "voice_loop_config": {"selected_args_file": "/home/test/.config/operance/voice-loop.args"},
        "voice_loop_service": {
            "status": "warn",
            "recommended_command": "./scripts/install_voice_loop_user_service.sh",
        },
        "audit": {"count": 1, "entries": [{"status": "success", "transcript": "open firefox"}]},
    }
    assert received_reports == [report, report, report, report]


def test_build_support_snapshot_can_redact_home_paths(monkeypatch) -> None:
    report = {
        "platform": "Linux",
        "python_version": "3.14.0",
        "checks": [
            {
                "name": "voice_loop_user_config_available",
                "status": "ok",
                "detail": "/home/test/.config/operance/voice-loop.args",
            }
        ],
    }

    class _FakeSetupSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"summary_status": "ready", "ready_for_mvp": True}

    class _FakeVoiceLoopConfigSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"selected_args_file": "/home/test/.config/operance/voice-loop.args"}

    class _FakeVoiceLoopServiceSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"service_installed_detail": "/home/test/.config/systemd/user/operance-voice-loop.service"}

    monkeypatch.setattr("operance.support_snapshot.build_environment_report", lambda: report)
    monkeypatch.setattr("operance.support_snapshot._build_setup_snapshot", lambda doctor_report: _FakeSetupSnapshot())
    monkeypatch.setattr(
        "operance.support_snapshot.build_supported_command_catalog",
        lambda doctor_report, available_only=False: {
            "catalog_filter": "available_only" if available_only else "all",
            "summary": {
                "available_commands": 3,
                "unverified_commands": 0 if available_only else 5,
                "blocked_commands": 0 if available_only else 2,
            },
        },
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_voice_loop_config_snapshot",
        lambda env=None: _FakeVoiceLoopConfigSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_voice_loop_service_snapshot",
        lambda env=None, report=None: _FakeVoiceLoopServiceSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_snapshot._build_recent_audit_payload",
        lambda env=None, limit=20: {
            "count": 1,
            "entries": [
                {
                    "response_text": "/home/test/.operance/logs/trace.json",
                    "status": "failed",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "operance.support_snapshot.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
    )

    snapshot = build_support_snapshot(redact=True, home_dir="/home/test")

    assert snapshot["build"]["version"] == "0.1.0"
    assert snapshot["doctor"]["checks"][0]["detail"] == "~/.config/operance/voice-loop.args"
    assert snapshot["voice_loop_config"]["selected_args_file"] == "~/.config/operance/voice-loop.args"
    assert snapshot["voice_loop_service"]["service_installed_detail"] == (
        "~/.config/systemd/user/operance-voice-loop.service"
    )
    assert snapshot["runnable_supported_commands"]["catalog_filter"] == "available_only"
    assert snapshot["audit"]["entries"][0]["response_text"] == "~/.operance/logs/trace.json"


def test_build_support_snapshot_help_text_formats_summary_and_details() -> None:
    help_text = build_support_snapshot_help_text(
        {
            "build": {
                "name": "operance",
                "version": "0.1.0",
                "git_commit": "abc1234",
            },
            "doctor": {
                "checks": [
                    {"name": "text_input_cli_available", "status": "warn", "detail": "unsupported"},
                    {"name": "voice_loop_user_service_installed", "status": "warn", "detail": "not installed"},
                ]
            },
            "setup": {"summary_status": "ready", "ready_for_mvp": True},
            "supported_commands": {"summary": {"available_commands": 7, "unverified_commands": 23, "blocked_commands": 4}},
            "voice_loop_service": {
                "status": "warn",
                "recommended_command": "./scripts/install_voice_loop_user_service.sh",
            },
            "audit": {
                "count": 2,
                "entries": [
                    {"status": "success", "transcript": "open firefox"},
                    {"status": "failed", "transcript": "focus code"},
                ],
            },
        }
    )

    assert help_text["title"] == "Support snapshot"
    assert help_text["summary"] == (
        "MVP ready: yes | 7 release-verified and available | 23 unverified | 4 blocked."
    )
    assert help_text["highlights"] == [
        "Build: operance 0.1.0 (abc1234)",
        "Setup summary: ready",
        "Voice-loop service: warn",
        "Recent audit entries: 2",
        "Next voice-loop action: ./scripts/install_voice_loop_user_service.sh",
        "Doctor warnings: text_input_cli_available, voice_loop_user_service_installed",
    ]
    assert '"ready_for_mvp": true' in help_text["details"]
    assert '"available_commands": 7' in help_text["details"]
    assert '"unverified_commands": 23' in help_text["details"]


def test_redact_support_snapshot_replaces_home_prefix_recursively() -> None:
    redacted = redact_support_snapshot(
        {
            "doctor": {
                "checks": [
                    {"detail": "/home/test/.config/operance/voice-loop.args"},
                    {"detail": ["keep", "/home/test/.local/share/operance"]},
                ]
            },
            "notes": "Path: /home/test/Documents/personal/operance",
        },
        home_dir="/home/test",
    )

    assert redacted == {
        "doctor": {
            "checks": [
                {"detail": "~/.config/operance/voice-loop.args"},
                {"detail": ["keep", "~/.local/share/operance"]},
            ]
        },
        "notes": "Path: ~/Documents/personal/operance",
    }
