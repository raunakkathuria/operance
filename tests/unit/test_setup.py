from __future__ import annotations

from subprocess import CompletedProcess


def _report(check_statuses: dict[str, str]) -> dict[str, object]:
    return {
        "platform": "Linux",
        "python_version": "3.14.0",
        "checks": [
            {
                "name": name,
                "status": status,
                "detail": name,
            }
            for name, status in check_statuses.items()
        ],
    }


def _action_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        action["action_id"]: action
        for action in payload["actions"]
    }


def _next_step_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        step["label"]: step
        for step in payload["next_steps"]
    }


def test_format_setup_step_line_includes_status_and_required_flag() -> None:
    from operance.ui.setup import SetupStep, _format_setup_step_line

    step = SetupStep(
        name="planner_endpoint_healthy",
        label="Planner endpoint health",
        status="warn",
        detail={"endpoint": "http://127.0.0.1:8080/v1/chat/completions"},
        required=False,
        recommended_command="python3 -m operance.cli --planner-health",
    )

    assert _format_setup_step_line(step) == "[warn] Planner endpoint health"

    required_step = SetupStep(
        name="virtualenv_active",
        label="Virtual environment",
        status="ok",
        detail="active",
        required=True,
        recommended_command=None,
    )

    assert _format_setup_step_line(required_step) == "[ok] Virtual environment [required]"


def test_build_setup_step_details_includes_detail_and_recommendation() -> None:
    from operance.ui.setup import SetupStep, _build_setup_step_details

    step = SetupStep(
        name="planner_endpoint_healthy",
        label="Planner endpoint health",
        status="warn",
        detail={"endpoint": "http://127.0.0.1:8080/v1/chat/completions"},
        required=False,
        recommended_command="python3 -m operance.cli --planner-health",
    )

    assert _build_setup_step_details(step) == "\n".join(
        [
            "Check: Planner endpoint health",
            "Status: warn",
            "Required: no",
            "Recommended command: python3 -m operance.cli --planner-health",
            "Detail: {'endpoint': 'http://127.0.0.1:8080/v1/chat/completions'}",
        ]
    )


def test_build_setup_run_results_text_includes_commands_and_status() -> None:
    from operance.ui.setup import SetupRunResult, _build_setup_run_results_text

    results = [
        SetupRunResult(
            action_id="probe_planner_health",
            label="Probe planner endpoint",
            command="python3 -m operance.cli --planner-health",
            status="success",
            returncode=0,
            stdout='{"status":"ok"}',
            stderr="",
            dry_run=False,
        ),
        SetupRunResult(
            action_id="install_local_app",
            label="Install local Linux app",
            command="./scripts/install_local_linux_app.sh --voice",
            status="planned",
            returncode=None,
            stdout=None,
            stderr=None,
            dry_run=True,
        ),
    ]

    assert _build_setup_run_results_text(results) == "\n".join(
        [
            "Probe planner endpoint: success",
            "  Command: python3 -m operance.cli --planner-health",
            "  Return code: 0",
            "Install local Linux app: planned",
            "  Command: ./scripts/install_local_linux_app.sh --voice",
        ]
    )


def test_build_setup_run_results_detail_includes_stdout_and_stderr() -> None:
    from operance.ui.setup import SetupRunResult, _build_setup_run_results_detail

    result = SetupRunResult(
        action_id="probe_planner_health",
        label="Probe planner endpoint",
        command="python3 -m operance.cli --planner-health",
        status="failed",
        returncode=1,
        stdout='{"status":"failed"}',
        stderr="connection refused",
        dry_run=False,
    )

    assert _build_setup_run_results_detail(result) == "\n".join(
        [
            "Action: Probe planner endpoint",
            "Status: failed",
            "Command: python3 -m operance.cli --planner-health",
            "Return code: 1",
            'Stdout: {"status":"failed"}',
            "Stderr: connection refused",
        ]
    )


def test_build_setup_summary_includes_next_steps_when_present() -> None:
    from operance.ui.setup import SetupNextStep, SetupSnapshot, _build_setup_summary

    snapshot = SetupSnapshot(
        summary_status="ready",
        ready_for_local_runtime=True,
        ready_for_mvp=True,
        ready_for_voice=True,
        ready_for_packaging=False,
        available_package_formats=[],
        next_steps=[
            SetupNextStep(
                label="Launch Operance MVP",
                command="./scripts/run_mvp.sh",
            ),
            SetupNextStep(
                label="Run click-to-talk probe",
                command="./scripts/run_click_to_talk.sh",
            ),
            SetupNextStep(
                label="Run tray app",
                command="./scripts/run_tray_app.sh",
            ),
            SetupNextStep(
                label="Show runnable commands",
                command="python3 -m operance.cli --supported-commands --supported-commands-available-only",
            ),
            SetupNextStep(
                label="Collect support bundle",
                command="python3 -m operance.cli --support-bundle",
            ),
        ],
        recommended_commands=[],
        blocked_recommendations=[],
        actions=[],
        steps=[],
    )

    assert _build_setup_summary(snapshot) == (
        "Setup status: ready. "
        "Local runtime ready: yes. "
        "MVP ready: yes. "
        "Voice ready: yes. "
        "Packaging ready: no. "
        "Next: Launch Operance MVP; Run click-to-talk probe; Run tray app; Show runnable commands; Collect support bundle."
    )


def test_build_setup_action_details_includes_unavailable_reason_and_suggested_command() -> None:
    from operance.ui.setup import SetupAction, _build_setup_action_details

    action = SetupAction(
        action_id="install_wakeword_model_asset",
        label="Install wake-word model asset",
        command="./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx",
        available=False,
        recommended=False,
        unavailable_reason="Blocked by: Wake-word model source.",
        suggested_command="python3 -m operance.cli --voice-asset-paths",
    )

    assert _build_setup_action_details(action) == "\n".join(
        [
            "Action: Install wake-word model asset",
            "Command: ./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx",
            "Recommended: no",
            "Available: no",
            "Unavailable reason: Blocked by: Wake-word model source.",
            "Suggested command: python3 -m operance.cli --voice-asset-paths",
        ]
    )


def test_build_setup_snapshot_reports_partial_ready_state() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "warn",
                "tray_user_service_enabled": "warn",
                "tray_user_service_active": "warn",
                "voice_loop_user_service_installed": "warn",
                "voice_loop_user_service_enabled": "warn",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "planner_runtime_enabled": "ok",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "ok",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()

    assert payload["summary_status"] == "partial"
    assert payload["ready_for_local_runtime"] is True
    assert payload["ready_for_mvp"] is False
    assert payload["ready_for_voice"] is False
    assert payload["ready_for_packaging"] is True
    assert payload["available_package_formats"] == ["rpm"]
    assert payload["next_steps"] == [
        {
            "label": "Show runnable commands",
            "command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
        },
        {
            "label": "Collect support bundle",
            "command": "python3 -m operance.cli --support-bundle",
        }
    ]
    assert payload["recommended_commands"] == [
        "./scripts/install_local_linux_app.sh --voice",
        "python3 -m operance.cli --planner-health",
    ]
    assert [action["action_id"] for action in payload["actions"]] == [
        "bootstrap_dev_env",
        "install_local_app",
        "enable_tray_service",
        "restart_tray_service",
        "install_ui_backend",
        "install_voice_backends",
        "install_wayland_input_tools",
        "show_voice_asset_paths",
        "collect_support_bundle",
        "collect_support_snapshot",
        "install_wakeword_model_asset",
        "install_tts_assets",
        "list_audio_input_devices",
        "probe_microphone_capture",
        "probe_click_to_talk_path",
        "probe_wakeword_path",
        "calibrate_wakeword_threshold",
        "apply_calibrated_wakeword_threshold",
        "evaluate_wakeword_idle_rate",
        "probe_model_wakeword_path",
        "probe_stt_path",
        "probe_tts_path",
        "run_voice_self_test",
        "probe_planner_health",
        "install_voice_loop_service",
        "enable_voice_loop_service",
        "restart_voice_loop_service",
        "install_voice_loop_user_config",
        "inspect_voice_loop_config",
        "inspect_voice_loop_runtime_status",
        "configure_voice_loop_wakeword_model",
        "render_package_scaffolds",
        "install_deb_packaging_tools",
        "install_rpm_packaging_tools",
        "build_deb_package_artifact",
        "build_rpm_package_artifact",
        "run_beta_readiness_gate",
        "run_fedora_alpha_gate",
        "run_fedora_release_smoke",
        "install_deb_package_artifact",
        "install_rpm_package_artifact",
        "run_installed_rpm_beta_smoke",
        "uninstall_deb_package",
        "uninstall_rpm_package",
    ]
    actions = _action_map(payload)
    assert actions["bootstrap_dev_env"] == {
        "action_id": "bootstrap_dev_env",
        "available": True,
        "command": "./scripts/install_linux_dev.sh --ui --voice",
        "label": "Bootstrap local dev environment",
        "recommended": False,
    }
    assert actions["install_local_app"] == {
        "action_id": "install_local_app",
        "available": True,
        "command": "./scripts/install_local_linux_app.sh --voice",
        "label": "Install local Linux app",
        "recommended": True,
    }
    assert actions["install_wayland_input_tools"] == {
        "action_id": "install_wayland_input_tools",
        "available": False,
        "command": "./scripts/install_wayland_input_tools.sh",
        "label": "Install Wayland input tools",
        "recommended": False,
        "suggested_command": "python3 -m operance.cli --doctor",
    }
    assert actions["show_voice_asset_paths"] == {
        "action_id": "show_voice_asset_paths",
        "available": True,
        "command": "python3 -m operance.cli --voice-asset-paths",
        "label": "Show voice asset paths",
        "recommended": False,
    }
    assert actions["collect_support_bundle"] == {
        "action_id": "collect_support_bundle",
        "available": True,
        "command": "python3 -m operance.cli --support-bundle",
        "label": "Collect support bundle",
        "recommended": False,
    }
    assert actions["collect_support_snapshot"] == {
        "action_id": "collect_support_snapshot",
        "available": True,
        "command": "python3 -m operance.cli --support-snapshot",
        "label": "Collect support snapshot",
        "recommended": False,
    }
    assert actions["install_wakeword_model_asset"] == {
        "action_id": "install_wakeword_model_asset",
        "available": False,
        "command": "./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx",
        "label": "Install wake-word model asset",
        "recommended": False,
        "suggested_command": "python3 -m operance.cli --voice-asset-paths",
        "unavailable_reason": "Blocked by: Wake-word model source.",
    }
    assert actions["install_tts_assets"] == {
        "action_id": "install_tts_assets",
        "available": False,
        "command": "./scripts/install_tts_assets.sh --model /path/to/kokoro.onnx --voices /path/to/voices.bin",
        "label": "Install TTS assets",
        "recommended": False,
        "suggested_command": "python3 -m operance.cli --voice-asset-paths",
        "unavailable_reason": "Blocked by: TTS model source, TTS voices source.",
    }
    assert actions["list_audio_input_devices"] == {
        "action_id": "list_audio_input_devices",
        "available": True,
        "command": "python3 -m operance.cli --audio-list-devices",
        "label": "List audio input devices",
        "recommended": False,
    }
    assert actions["probe_microphone_capture"] == {
        "action_id": "probe_microphone_capture",
        "available": True,
        "command": "python3 -m operance.cli --audio-capture-frames 4",
        "label": "Probe microphone capture",
        "recommended": False,
    }
    assert actions["probe_click_to_talk_path"] == {
        "action_id": "probe_click_to_talk_path",
        "available": False,
        "command": "./scripts/run_click_to_talk.sh",
        "label": "Run click-to-talk probe",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Speech-to-text backend.",
    }
    assert actions["probe_wakeword_path"] == {
        "action_id": "probe_wakeword_path",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-probe-frames 8",
        "label": "Probe wake-word path",
        "recommended": False,
    }
    assert actions["calibrate_wakeword_threshold"] == {
        "action_id": "calibrate_wakeword_threshold",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-calibrate-frames 20",
        "label": "Calibrate wake-word threshold",
        "recommended": False,
    }
    assert actions["apply_calibrated_wakeword_threshold"] == {
        "action_id": "apply_calibrated_wakeword_threshold",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-calibrate-frames 20 --apply-suggested-threshold",
        "label": "Calibrate and apply wake-word threshold",
        "recommended": False,
    }
    assert actions["evaluate_wakeword_idle_rate"] == {
        "action_id": "evaluate_wakeword_idle_rate",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-eval-frames 50",
        "label": "Measure wake-word idle false activations",
        "recommended": False,
    }
    assert actions["probe_model_wakeword_path"] == {
        "action_id": "probe_model_wakeword_path",
        "available": False,
        "command": "python3 -m operance.cli --wakeword-probe-frames 8 --wakeword-model auto",
        "label": "Probe model-backed wake-word path",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Wake-word backend, Wake-word model asset.",
    }
    assert actions["probe_stt_path"] == {
        "action_id": "probe_stt_path",
        "available": False,
        "command": "python3 -m operance.cli --stt-probe-frames 12",
        "label": "Probe speech-to-text path",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Speech-to-text backend.",
    }
    assert actions["probe_tts_path"] == {
        "action_id": "probe_tts_path",
        "available": False,
        "command": 'python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-output /tmp/operance-tts-probe.wav --tts-play',
        "label": "Probe text-to-speech path",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Audio playback CLI, Text-to-speech backend, TTS model asset, TTS voices asset.",
    }
    assert actions["run_voice_self_test"] == {
        "action_id": "run_voice_self_test",
        "available": True,
        "command": "python3 -m operance.cli --voice-self-test",
        "label": "Run voice self-test",
        "recommended": False,
    }
    assert actions["probe_planner_health"] == {
        "action_id": "probe_planner_health",
        "available": True,
        "command": "python3 -m operance.cli --planner-health",
        "label": "Probe planner endpoint",
        "recommended": True,
    }
    assert actions["install_voice_loop_user_config"] == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": False,
    }
    assert actions["configure_voice_loop_wakeword_model"] == {
        "action_id": "configure_voice_loop_wakeword_model",
        "available": False,
        "command": "./scripts/update_voice_loop_user_config.sh --wakeword-model auto",
        "label": "Enable model-backed wake-word in voice-loop config",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Wake-word backend, Wake-word model asset.",
    }
    assert actions["render_package_scaffolds"] == {
        "action_id": "render_package_scaffolds",
        "available": True,
        "command": "./scripts/build_package_scaffolds.sh",
        "label": "Render package scaffolds",
        "recommended": False,
    }
    assert actions["install_deb_packaging_tools"]["available"] is False
    assert actions["install_rpm_packaging_tools"]["available"] is False
    assert actions["build_deb_package_artifact"]["available"] is False
    assert actions["build_rpm_package_artifact"] == {
        "action_id": "build_rpm_package_artifact",
        "available": True,
        "command": "./scripts/build_package_artifacts.sh --rpm",
        "label": "Build RPM package artifact",
        "recommended": False,
    }
    assert actions["run_fedora_release_smoke"]["available"] is False
    assert actions["install_deb_package_artifact"]["available"] is False
    assert actions["install_rpm_package_artifact"]["available"] is False
    assert actions["run_installed_rpm_beta_smoke"]["available"] is False
    assert actions["uninstall_deb_package"]["available"] is False
    assert actions["uninstall_rpm_package"]["available"] is False


def test_build_setup_snapshot_recommends_voice_asset_path_inspection_for_missing_assets() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "warn",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "tts_model_asset_available": "warn",
                "tts_voices_asset_available": "warn",
            }
        )
    )

    steps = {step["name"]: step for step in snapshot.to_dict()["steps"]}

    assert steps["wakeword_model_asset_available"]["recommended_command"] == "python3 -m operance.cli --voice-asset-paths"
    assert steps["tts_model_asset_available"]["recommended_command"] == "python3 -m operance.cli --voice-asset-paths"
    assert steps["tts_voices_asset_available"]["recommended_command"] == "python3 -m operance.cli --voice-asset-paths"


def test_build_setup_snapshot_exposes_voice_asset_install_actions_when_sources_are_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "python_3_12_plus"},
                {"name": "virtualenv_active", "status": "ok", "detail": "virtualenv_active"},
                {"name": "linux_platform", "status": "ok", "detail": "linux_platform"},
                {"name": "kde_wayland_target", "status": "ok", "detail": "kde_wayland_target"},
                {"name": "xdg_open_available", "status": "ok", "detail": "xdg_open_available"},
                {"name": "gdbus_available", "status": "ok", "detail": "gdbus_available"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "networkmanager_cli_available"},
                {"name": "audio_cli_available", "status": "ok", "detail": "audio_cli_available"},
                {"name": "audio_capture_cli_available", "status": "ok", "detail": "audio_capture_cli_available"},
                {"name": "audio_playback_cli_available", "status": "ok", "detail": "audio_playback_cli_available"},
                {"name": "systemctl_user_available", "status": "ok", "detail": "systemctl_user_available"},
                {"name": "power_status_available", "status": "ok", "detail": "power_status_available"},
                {"name": "wakeword_backend_available", "status": "ok", "detail": "wakeword_backend_available"},
                {"name": "wakeword_model_asset_available", "status": "warn", "detail": "wakeword_model_asset_available"},
                {"name": "wakeword_model_source_available", "status": "ok", "detail": "/tmp/operance.onnx"},
                {"name": "stt_backend_available", "status": "ok", "detail": "stt_backend_available"},
                {"name": "tts_backend_available", "status": "ok", "detail": "tts_backend_available"},
                {"name": "tts_model_asset_available", "status": "warn", "detail": "tts_model_asset_available"},
                {"name": "tts_model_source_available", "status": "ok", "detail": "/tmp/kokoro.onnx"},
                {"name": "tts_voices_asset_available", "status": "warn", "detail": "tts_voices_asset_available"},
                {"name": "tts_voices_source_available", "status": "ok", "detail": "/tmp/voices.bin"},
            ],
        }
    )

    actions = _action_map(snapshot.to_dict())

    assert actions["install_wakeword_model_asset"] == {
        "action_id": "install_wakeword_model_asset",
        "available": True,
        "command": "./scripts/install_wakeword_model_asset.sh --source /tmp/operance.onnx",
        "label": "Install wake-word model asset",
        "recommended": True,
    }
    assert actions["install_tts_assets"] == {
        "action_id": "install_tts_assets",
        "available": True,
        "command": "./scripts/install_tts_assets.sh --model /tmp/kokoro.onnx --voices /tmp/voices.bin",
        "label": "Install TTS assets",
        "recommended": True,
    }


def test_build_setup_snapshot_recommends_voice_asset_install_actions_when_sources_are_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "python_3_12_plus"},
                {"name": "virtualenv_active", "status": "ok", "detail": "virtualenv_active"},
                {"name": "linux_platform", "status": "ok", "detail": "linux_platform"},
                {"name": "kde_wayland_target", "status": "ok", "detail": "kde_wayland_target"},
                {"name": "xdg_open_available", "status": "ok", "detail": "xdg_open_available"},
                {"name": "gdbus_available", "status": "ok", "detail": "gdbus_available"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "networkmanager_cli_available"},
                {"name": "audio_cli_available", "status": "ok", "detail": "audio_cli_available"},
                {"name": "audio_capture_cli_available", "status": "ok", "detail": "audio_capture_cli_available"},
                {"name": "audio_playback_cli_available", "status": "ok", "detail": "audio_playback_cli_available"},
                {"name": "systemctl_user_available", "status": "ok", "detail": "systemctl_user_available"},
                {"name": "power_status_available", "status": "ok", "detail": "power_status_available"},
                {"name": "tray_user_service_installed", "status": "ok", "detail": "tray_user_service_installed"},
                {"name": "tray_user_service_enabled", "status": "ok", "detail": "tray_user_service_enabled"},
                {"name": "tray_user_service_active", "status": "ok", "detail": "tray_user_service_active"},
                {"name": "voice_loop_user_service_installed", "status": "warn", "detail": "voice_loop_user_service_installed"},
                {"name": "voice_loop_user_service_enabled", "status": "warn", "detail": "voice_loop_user_service_enabled"},
                {"name": "voice_loop_user_service_active", "status": "warn", "detail": "voice_loop_user_service_active"},
                {"name": "voice_loop_user_config_available", "status": "warn", "detail": "voice_loop_user_config_available"},
                {"name": "tray_ui_available", "status": "ok", "detail": "tray_ui_available"},
                {"name": "wakeword_backend_available", "status": "ok", "detail": "wakeword_backend_available"},
                {"name": "wakeword_model_asset_available", "status": "warn", "detail": "wakeword_model_asset_available"},
                {"name": "wakeword_model_source_available", "status": "ok", "detail": "/tmp/operance.onnx"},
                {"name": "stt_backend_available", "status": "ok", "detail": "stt_backend_available"},
                {"name": "tts_backend_available", "status": "ok", "detail": "tts_backend_available"},
                {"name": "tts_model_asset_available", "status": "warn", "detail": "tts_model_asset_available"},
                {"name": "tts_model_source_available", "status": "ok", "detail": "/tmp/kokoro.onnx"},
                {"name": "tts_voices_asset_available", "status": "warn", "detail": "tts_voices_asset_available"},
                {"name": "tts_voices_source_available", "status": "ok", "detail": "/tmp/voices.bin"},
                {"name": "planner_runtime_enabled", "status": "warn", "detail": "planner_runtime_enabled"},
                {"name": "planner_endpoint_healthy", "status": "warn", "detail": "planner_endpoint_healthy"},
                {"name": "deb_packaging_cli_available", "status": "warn", "detail": "deb_packaging_cli_available"},
                {"name": "rpm_packaging_cli_available", "status": "warn", "detail": "rpm_packaging_cli_available"},
                {"name": "archive_packaging_cli_available", "status": "ok", "detail": "archive_packaging_cli_available"},
            ],
        }
    )

    payload = snapshot.to_dict()
    actions = _action_map(payload)

    assert "./scripts/install_wakeword_model_asset.sh --source /tmp/operance.onnx" in payload["recommended_commands"]
    assert "./scripts/install_tts_assets.sh --model /tmp/kokoro.onnx --voices /tmp/voices.bin" in payload["recommended_commands"]
    assert actions["install_wakeword_model_asset"]["recommended"] is True
    assert actions["install_tts_assets"]["recommended"] is True


def test_build_setup_snapshot_reports_blocked_voice_asset_recommendations_when_sources_are_missing() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "python_3_12_plus"},
                {"name": "virtualenv_active", "status": "ok", "detail": "virtualenv_active"},
                {"name": "linux_platform", "status": "ok", "detail": "linux_platform"},
                {"name": "kde_wayland_target", "status": "ok", "detail": "kde_wayland_target"},
                {"name": "xdg_open_available", "status": "ok", "detail": "xdg_open_available"},
                {"name": "gdbus_available", "status": "ok", "detail": "gdbus_available"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "networkmanager_cli_available"},
                {"name": "audio_cli_available", "status": "ok", "detail": "audio_cli_available"},
                {"name": "audio_capture_cli_available", "status": "ok", "detail": "audio_capture_cli_available"},
                {"name": "audio_playback_cli_available", "status": "ok", "detail": "audio_playback_cli_available"},
                {"name": "systemctl_user_available", "status": "ok", "detail": "systemctl_user_available"},
                {"name": "power_status_available", "status": "ok", "detail": "power_status_available"},
                {"name": "tray_user_service_installed", "status": "ok", "detail": "tray_user_service_installed"},
                {"name": "tray_user_service_enabled", "status": "ok", "detail": "tray_user_service_enabled"},
                {"name": "tray_user_service_active", "status": "ok", "detail": "tray_user_service_active"},
                {"name": "voice_loop_user_service_installed", "status": "ok", "detail": "voice_loop_user_service_installed"},
                {"name": "voice_loop_user_service_enabled", "status": "ok", "detail": "voice_loop_user_service_enabled"},
                {"name": "voice_loop_user_service_active", "status": "ok", "detail": "voice_loop_user_service_active"},
                {"name": "voice_loop_user_config_available", "status": "ok", "detail": "voice_loop_user_config_available"},
                {"name": "tray_ui_available", "status": "ok", "detail": "tray_ui_available"},
                {"name": "wakeword_backend_available", "status": "ok", "detail": "wakeword_backend_available"},
                {"name": "wakeword_model_asset_available", "status": "warn", "detail": "wakeword_model_asset_available"},
                {"name": "wakeword_model_source_available", "status": "warn", "detail": "not set"},
                {"name": "stt_backend_available", "status": "ok", "detail": "stt_backend_available"},
                {"name": "tts_backend_available", "status": "ok", "detail": "tts_backend_available"},
                {"name": "tts_model_asset_available", "status": "warn", "detail": "tts_model_asset_available"},
                {"name": "tts_model_source_available", "status": "warn", "detail": "not set"},
                {"name": "tts_voices_asset_available", "status": "warn", "detail": "tts_voices_asset_available"},
                {"name": "tts_voices_source_available", "status": "warn", "detail": "not set"},
            ],
        }
    )

    payload = snapshot.to_dict()

    assert payload["recommended_commands"] == []
    assert payload["blocked_recommendations"] == [
        {
            "label": "Install wake-word model asset",
            "reason": "Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
            "suggested_command": "python3 -m operance.cli --voice-asset-paths",
        },
        {
            "label": "Install TTS assets",
            "reason": "Set OPERANCE_TTS_MODEL_SOURCE and OPERANCE_TTS_VOICES_SOURCE or copy both files to candidate paths before setup can stage them.",
            "suggested_command": "python3 -m operance.cli --voice-asset-paths",
        },
    ]


def test_build_setup_snapshot_reports_required_runtime_gaps() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "warn",
                "linux_platform": "ok",
                "kde_wayland_target": "warn",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "warn",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "warn",
                "voice_loop_user_service_installed": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()

    assert payload["summary_status"] == "needs_attention"
    assert payload["ready_for_local_runtime"] is False
    assert payload["ready_for_voice"] is False
    assert payload["ready_for_packaging"] is False
    assert payload["recommended_commands"] == ["./scripts/install_linux_dev.sh --ui --voice"]
    assert payload["steps"][1] == {
        "detail": "virtualenv_active",
        "label": "Virtual environment",
        "name": "virtualenv_active",
        "recommended_command": "./scripts/install_linux_dev.sh",
        "required": True,
        "status": "warn",
    }
    assert payload["actions"][0] == {
        "action_id": "bootstrap_dev_env",
        "available": True,
        "command": "./scripts/install_linux_dev.sh --ui --voice",
        "label": "Bootstrap local dev environment",
        "recommended": True,
    }
    voice_loop_service_action = next(
        action for action in payload["actions"] if action["action_id"] == "install_voice_loop_service"
    )
    voice_loop_config_action = next(
        action for action in payload["actions"] if action["action_id"] == "install_voice_loop_user_config"
    )
    enable_tray_action = next(
        action for action in payload["actions"] if action["action_id"] == "enable_tray_service"
    )
    restart_tray_action = next(
        action for action in payload["actions"] if action["action_id"] == "restart_tray_service"
    )
    enable_voice_loop_action = next(
        action for action in payload["actions"] if action["action_id"] == "enable_voice_loop_service"
    )
    restart_voice_loop_action = next(
        action for action in payload["actions"] if action["action_id"] == "restart_voice_loop_service"
    )

    assert voice_loop_service_action == {
        "action_id": "install_voice_loop_service",
        "available": False,
        "command": "./scripts/install_voice_loop_user_service.sh",
        "label": "Install voice-loop user service",
        "recommended": False,
        "suggested_command": 'python3 -m pip install -e ".[dev,voice]"',
        "unavailable_reason": "Blocked by: Virtual environment, KDE Wayland session, Audio capture CLI, Speech-to-text backend.",
    }
    assert voice_loop_config_action == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": False,
    }
    assert enable_tray_action["available"] is False
    assert restart_tray_action["available"] is False
    assert enable_voice_loop_action["available"] is False
    assert restart_voice_loop_action["available"] is False
    assert next(
        action for action in payload["actions"] if action["action_id"] == "list_audio_input_devices"
    )["available"] is False
    assert next(
        action for action in payload["actions"] if action["action_id"] == "probe_microphone_capture"
    )["available"] is False
    assert next(
        action for action in payload["actions"] if action["action_id"] == "probe_click_to_talk_path"
    )["available"] is False


def test_build_setup_snapshot_reports_wayland_input_backend_blockers() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "wayland_session_accessible": "warn",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "clipboard_cli_available": "warn",
                "text_input_cli_available": "warn",
                "systemctl_user_available": "ok",
                "rpm_package_installer_available": "ok",
                "power_status_available": "ok",
                "wakeword_model_asset_available": "ok",
                "wakeword_model_source_available": "ok",
                "tts_model_asset_available": "ok",
                "tts_model_source_available": "ok",
                "tts_voices_asset_available": "ok",
                "tts_voices_source_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()
    step_names = {step["name"] for step in payload["steps"]}
    steps = {step["name"]: step for step in payload["steps"]}

    assert "clipboard_cli_available" in step_names
    assert "text_input_cli_available" in step_names
    assert "wayland_session_accessible" in step_names
    assert steps["clipboard_cli_available"]["recommended_command"] == "./scripts/install_wayland_input_tools.sh"
    assert steps["text_input_cli_available"]["recommended_command"] == "./scripts/install_wayland_input_tools.sh"
    actions = _action_map(payload)
    assert actions["install_wayland_input_tools"] == {
        "action_id": "install_wayland_input_tools",
        "available": True,
        "command": "./scripts/install_wayland_input_tools.sh",
        "label": "Install Wayland input tools",
        "recommended": False,
    }
    assert payload["blocked_recommendations"] == [
        {
            "label": "Install Wayland clipboard CLI",
            "reason": "Install wl-copy and wl-paste so clipboard read, write, and clear commands can run on Wayland.",
            "suggested_command": "./scripts/install_wayland_input_tools.sh",
        },
        {
            "label": "Install Wayland text input CLI",
            "reason": "Install wtype so text injection, key press, and selection-copy commands can drive the focused Wayland window.",
            "suggested_command": "./scripts/install_wayland_input_tools.sh",
        },
        {
            "label": "Fix Wayland session access",
            "reason": "Run Operance from the logged-in KDE Wayland user session so clipboard and text-input commands can reach the Wayland socket.",
            "suggested_command": "python3 -m operance.cli --doctor",
        },
    ]


def test_build_setup_snapshot_targets_text_input_only_install_when_clipboard_is_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "wayland_session_accessible": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "clipboard_cli_available": "ok",
                "text_input_cli_available": "warn",
                "systemctl_user_available": "ok",
                "rpm_package_installer_available": "ok",
                "power_status_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()
    steps = {step["name"]: step for step in payload["steps"]}
    actions = _action_map(payload)

    assert steps["text_input_cli_available"]["recommended_command"] == (
        "./scripts/install_wayland_input_tools.sh --text-input-only"
    )
    assert actions["install_wayland_input_tools"] == {
        "action_id": "install_wayland_input_tools",
        "available": True,
        "command": "./scripts/install_wayland_input_tools.sh --text-input-only",
        "label": "Install Wayland input tools",
        "recommended": False,
    }


def test_build_setup_snapshot_reports_unsupported_text_input_backend() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "3.14.0"},
                {"name": "virtualenv_active", "status": "ok", "detail": "active"},
                {"name": "linux_platform", "status": "ok", "detail": "Linux"},
                {
                    "name": "kde_wayland_target",
                    "status": "ok",
                    "detail": {"session_type": "wayland", "desktop_session": "KDE"},
                },
                {"name": "wayland_session_accessible", "status": "ok", "detail": "ok"},
                {"name": "xdg_open_available", "status": "ok", "detail": "/usr/bin/xdg-open"},
                {"name": "gdbus_available", "status": "ok", "detail": "/usr/bin/gdbus"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "/usr/bin/nmcli"},
                {"name": "audio_cli_available", "status": "ok", "detail": {"wpctl": "/usr/bin/wpctl"}},
                {
                    "name": "audio_capture_cli_available",
                    "status": "ok",
                    "detail": {"pw-record": "/usr/bin/pw-record"},
                },
                {
                    "name": "audio_playback_cli_available",
                    "status": "ok",
                    "detail": {"pw-play": "/usr/bin/pw-play"},
                },
                {
                    "name": "clipboard_cli_available",
                    "status": "ok",
                    "detail": {"wl-copy": "/usr/bin/wl-copy", "wl-paste": "/usr/bin/wl-paste"},
                },
                {
                    "name": "text_input_cli_available",
                    "status": "warn",
                    "detail": {
                        "backend_status": "unsupported_protocol",
                        "message": (
                            "wtype is installed but the compositor does not support "
                            "the virtual keyboard protocol."
                        ),
                        "probe_error": "Compositor does not support the virtual keyboard protocol",
                        "wtype": "/usr/bin/wtype",
                    },
                },
                {"name": "systemctl_user_available", "status": "ok", "detail": "/usr/bin/systemctl"},
                {"name": "rpm_package_installer_available", "status": "ok", "detail": "/usr/bin/dnf"},
                {"name": "power_status_available", "status": "ok", "detail": {"upower": "/usr/bin/upower"}},
                {"name": "wakeword_model_asset_available", "status": "ok", "detail": "/tmp/operance.onnx"},
                {"name": "wakeword_model_source_available", "status": "ok", "detail": "/tmp/operance.onnx"},
                {"name": "tts_model_asset_available", "status": "ok", "detail": "/tmp/kokoro.onnx"},
                {"name": "tts_model_source_available", "status": "ok", "detail": "/tmp/kokoro.onnx"},
                {"name": "tts_voices_asset_available", "status": "ok", "detail": "/tmp/voices.bin"},
                {"name": "tts_voices_source_available", "status": "ok", "detail": "/tmp/voices.bin"},
            ],
        }
    )

    payload = snapshot.to_dict()
    steps = {step["name"]: step for step in payload["steps"]}
    actions = _action_map(payload)

    assert steps["text_input_cli_available"]["recommended_command"] == "python3 -m operance.cli --doctor"
    assert actions["install_wayland_input_tools"] == {
        "action_id": "install_wayland_input_tools",
        "available": False,
        "command": "./scripts/install_wayland_input_tools.sh",
        "label": "Install Wayland input tools",
        "recommended": False,
        "suggested_command": "python3 -m operance.cli --doctor",
        "unavailable_reason": "Blocked by: Wayland text input backend unsupported in this session.",
    }
    assert payload["blocked_recommendations"] == [
        {
            "label": "Fix Wayland text input backend",
            "reason": (
                "wtype is installed but the compositor does not support the virtual "
                "keyboard protocol, so text injection, key press, and selection-copy "
                "commands remain disabled."
            ),
            "suggested_command": "python3 -m operance.cli --doctor",
        }
    ]


def test_run_setup_action_dry_run_returns_planned_result() -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "ok",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    result = run_setup_action("install_ui_backend", snapshot=snapshot, dry_run=True)

    assert result.to_dict() == {
        "action_id": "install_ui_backend",
        "command": 'python3 -m pip install -e ".[dev,ui]"',
        "dry_run": True,
        "label": "Install tray UI backend",
        "returncode": None,
        "status": "planned",
        "stderr": None,
        "stdout": None,
    }


def test_run_setup_action_reports_unavailable_reason() -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "warn",
                "wakeword_model_source_available": "warn",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "tts_model_asset_available": "ok",
                "tts_voices_asset_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    try:
        run_setup_action("install_wakeword_model_asset", snapshot=snapshot)
    except ValueError as exc:
        assert str(exc) == (
            "setup action is not available: install_wakeword_model_asset"
            " (Blocked by: Wake-word model source.)"
        )
    else:
        raise AssertionError("expected setup action to be unavailable")


def test_run_setup_action_executes_shell_script_through_bash(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "ok",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("install_local_app", snapshot=snapshot)

    assert calls == [["bash", "./scripts/install_local_linux_app.sh", "--voice"]]
    assert result.status == "success"
    assert result.stdout == "ok"


def test_run_setup_action_executes_voice_probe_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "ok",
                "planner_runtime_enabled": "ok",
                "planner_endpoint_healthy": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"success"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("probe_stt_path", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--stt-probe-frames", "12"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"success"}'


def test_run_setup_action_executes_planner_health_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "planner_runtime_enabled": "ok",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("probe_planner_health", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--planner-health"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_tts_probe_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "ok",
                "tts_model_asset_available": "ok",
                "tts_voices_asset_available": "ok",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("probe_tts_path", snapshot=snapshot)

    assert calls == [[
        "python3",
        "-m",
        "operance.cli",
        "--tts-probe-text",
        "Hello from Operance",
        "--tts-output",
        "/tmp/operance-tts-probe.wav",
        "--tts-play",
    ]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_tts_asset_install_script(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "python_3_12_plus"},
                {"name": "virtualenv_active", "status": "ok", "detail": "virtualenv_active"},
                {"name": "linux_platform", "status": "ok", "detail": "linux_platform"},
                {"name": "kde_wayland_target", "status": "ok", "detail": "kde_wayland_target"},
                {"name": "xdg_open_available", "status": "ok", "detail": "xdg_open_available"},
                {"name": "gdbus_available", "status": "ok", "detail": "gdbus_available"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "networkmanager_cli_available"},
                {"name": "audio_cli_available", "status": "ok", "detail": "audio_cli_available"},
                {"name": "audio_capture_cli_available", "status": "ok", "detail": "audio_capture_cli_available"},
                {"name": "audio_playback_cli_available", "status": "ok", "detail": "audio_playback_cli_available"},
                {"name": "systemctl_user_available", "status": "ok", "detail": "systemctl_user_available"},
                {"name": "power_status_available", "status": "ok", "detail": "power_status_available"},
                {"name": "wakeword_backend_available", "status": "ok", "detail": "wakeword_backend_available"},
                {"name": "wakeword_model_asset_available", "status": "ok", "detail": "wakeword_model_asset_available"},
                {"name": "wakeword_model_source_available", "status": "warn", "detail": "not set"},
                {"name": "stt_backend_available", "status": "ok", "detail": "stt_backend_available"},
                {"name": "tts_backend_available", "status": "ok", "detail": "tts_backend_available"},
                {"name": "tts_model_asset_available", "status": "warn", "detail": "tts_model_asset_available"},
                {"name": "tts_model_source_available", "status": "ok", "detail": "/tmp/kokoro.onnx"},
                {"name": "tts_voices_asset_available", "status": "warn", "detail": "tts_voices_asset_available"},
                {"name": "tts_voices_source_available", "status": "ok", "detail": "/tmp/voices.bin"},
            ],
        }
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("install_tts_assets", snapshot=snapshot)

    assert calls == [[
        "bash",
        "./scripts/install_tts_assets.sh",
        "--model",
        "/tmp/kokoro.onnx",
        "--voices",
        "/tmp/voices.bin",
    ]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_wakeword_calibration_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("calibrate_wakeword_threshold", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--wakeword-calibrate-frames", "20"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_apply_wakeword_calibration_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("apply_calibrated_wakeword_threshold", snapshot=snapshot)

    assert calls == [[
        "python3",
        "-m",
        "operance.cli",
        "--wakeword-calibrate-frames",
        "20",
        "--apply-suggested-threshold",
    ]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_model_wakeword_probe_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "ok",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("probe_model_wakeword_path", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--wakeword-probe-frames", "8", "--wakeword-model", "auto"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_wakeword_idle_evaluation_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("evaluate_wakeword_idle_rate", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--wakeword-eval-frames", "50"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_voice_loop_wakeword_model_config_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "ok",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("configure_voice_loop_wakeword_model", snapshot=snapshot)

    assert calls == [["bash", "./scripts/update_voice_loop_user_config.sh", "--wakeword-model", "auto"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_run_setup_action_executes_voice_self_test_command(monkeypatch) -> None:
    from operance.ui import build_setup_snapshot
    from operance.ui.setup import run_setup_action

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "warn",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "planner_runtime_enabled": "warn",
                "planner_endpoint_healthy": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)

    result = run_setup_action("run_voice_self_test", snapshot=snapshot)

    assert calls == [["python3", "-m", "operance.cli", "--voice-self-test"]]
    assert result.status == "success"
    assert result.stdout == '{"status":"ok"}'


def test_build_setup_snapshot_requires_audio_playback_for_voice_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "warn",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    assert snapshot.ready_for_local_runtime is True
    assert snapshot.ready_for_voice is False


def test_build_setup_snapshot_exposes_tts_probe_action_when_assets_are_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "ok",
                "tts_model_asset_available": "ok",
                "tts_voices_asset_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["probe_tts_path"]

    assert action == {
        "action_id": "probe_tts_path",
        "available": True,
        "command": 'python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-output /tmp/operance-tts-probe.wav --tts-play',
        "label": "Probe text-to-speech path",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_model_wakeword_probe_action_when_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "ok",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["probe_model_wakeword_path"]

    assert action == {
        "action_id": "probe_model_wakeword_path",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-probe-frames 8 --wakeword-model auto",
        "label": "Probe model-backed wake-word path",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_wakeword_idle_evaluation_action_when_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "warn",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["evaluate_wakeword_idle_rate"]

    assert action == {
        "action_id": "evaluate_wakeword_idle_rate",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-eval-frames 50",
        "label": "Measure wake-word idle false activations",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_voice_loop_wakeword_model_config_action_when_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "wakeword_model_asset_available": "ok",
                "stt_backend_available": "warn",
                "tts_backend_available": "warn",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["configure_voice_loop_wakeword_model"]

    assert action == {
        "action_id": "configure_voice_loop_wakeword_model",
        "available": True,
        "command": "./scripts/update_voice_loop_user_config.sh --wakeword-model auto",
        "label": "Enable model-backed wake-word in voice-loop config",
        "recommended": False,
    }


def test_build_setup_snapshot_recommends_voice_loop_install_and_config_when_voice_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "warn",
                "voice_loop_user_service_enabled": "warn",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()
    actions = _action_map(payload)
    next_steps = _next_step_map(payload)

    assert payload["summary_status"] == "ready"
    assert payload["ready_for_mvp"] is True
    assert payload["recommended_commands"] == [
        "./scripts/install_voice_loop_user_service.sh",
        "./scripts/install_voice_loop_user_config.sh",
    ]
    assert next_steps == {
        "Launch Operance MVP": {
            "label": "Launch Operance MVP",
            "command": "./scripts/run_mvp.sh",
        },
        "Run click-to-talk probe": {
            "label": "Run click-to-talk probe",
            "command": "./scripts/run_click_to_talk.sh",
        },
        "Run tray app": {
            "label": "Run tray app",
            "command": "./scripts/run_tray_app.sh",
        },
        "Show runnable commands": {
            "label": "Show runnable commands",
            "command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
        },
        "Collect support bundle": {
            "label": "Collect support bundle",
            "command": "python3 -m operance.cli --support-bundle",
        },
    }
    assert actions["install_voice_loop_service"] == {
        "action_id": "install_voice_loop_service",
        "available": True,
        "command": "./scripts/install_voice_loop_user_service.sh",
        "label": "Install voice-loop user service",
        "recommended": True,
    }
    assert actions["install_voice_loop_user_config"] == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": True,
    }

    voice_loop_step = next(
        step for step in payload["steps"] if step["name"] == "voice_loop_user_service_installed"
    )
    voice_loop_config_step = next(
        step for step in payload["steps"] if step["name"] == "voice_loop_user_config_available"
    )
    assert voice_loop_step["recommended_command"] == "./scripts/install_voice_loop_user_service.sh"
    assert voice_loop_config_step["recommended_command"] == "./scripts/install_voice_loop_user_config.sh"


def test_build_setup_snapshot_recommends_voice_loop_config_when_service_is_installed() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()

    assert payload["recommended_commands"] == ["./scripts/install_voice_loop_user_config.sh"]
    assert _action_map(payload)["install_voice_loop_user_config"] == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": True,
    }


def test_build_setup_snapshot_recommends_voice_loop_wakeword_tuning_when_config_uses_defaults() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "voice_loop_wakeword_customized": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()
    actions = _action_map(payload)
    wakeword_step = next(
        step for step in payload["steps"] if step["name"] == "voice_loop_wakeword_customized"
    )

    assert payload["recommended_commands"] == [
        "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config --apply-suggested-threshold",
        "python3 -m operance.cli --wakeword-eval-frames 50 --use-voice-loop-config",
    ]
    assert wakeword_step["recommended_command"] == (
        "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config --apply-suggested-threshold"
    )
    assert actions["calibrate_wakeword_threshold"] == {
        "action_id": "calibrate_wakeword_threshold",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config",
        "label": "Calibrate wake-word threshold",
        "recommended": False,
    }
    assert actions["apply_calibrated_wakeword_threshold"] == {
        "action_id": "apply_calibrated_wakeword_threshold",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config --apply-suggested-threshold",
        "label": "Calibrate and apply wake-word threshold",
        "recommended": True,
    }
    assert actions["evaluate_wakeword_idle_rate"] == {
        "action_id": "evaluate_wakeword_idle_rate",
        "available": True,
        "command": "python3 -m operance.cli --wakeword-eval-frames 50 --use-voice-loop-config",
        "label": "Measure wake-word idle false activations",
        "recommended": True,
    }


def test_build_setup_snapshot_exposes_voice_loop_config_inspection_action() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["inspect_voice_loop_config"]

    assert action == {
        "action_id": "inspect_voice_loop_config",
        "available": True,
        "command": "python3 -m operance.cli --voice-loop-config",
        "label": "Inspect voice-loop config",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_voice_loop_runtime_status_action() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "voice_loop_runtime_status_available": "ok",
                "voice_loop_runtime_heartbeat_fresh": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    action = _action_map(snapshot.to_dict())["inspect_voice_loop_runtime_status"]

    assert action == {
        "action_id": "inspect_voice_loop_runtime_status",
        "available": True,
        "command": "python3 -m operance.cli --voice-loop-status",
        "label": "Inspect voice-loop runtime status",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_voice_loop_wakeword_config_step() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [
                {"name": "python_3_12_plus", "status": "ok", "detail": "python_3_12_plus"},
                {"name": "virtualenv_active", "status": "ok", "detail": "virtualenv_active"},
                {"name": "linux_platform", "status": "ok", "detail": "linux_platform"},
                {"name": "kde_wayland_target", "status": "ok", "detail": "kde_wayland_target"},
                {"name": "xdg_open_available", "status": "ok", "detail": "xdg_open_available"},
                {"name": "gdbus_available", "status": "ok", "detail": "gdbus_available"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "networkmanager_cli_available"},
                {"name": "audio_cli_available", "status": "ok", "detail": "audio_cli_available"},
                {"name": "audio_capture_cli_available", "status": "ok", "detail": "audio_capture_cli_available"},
                {"name": "systemctl_user_available", "status": "ok", "detail": "systemctl_user_available"},
                {"name": "power_status_available", "status": "ok", "detail": "power_status_available"},
                {"name": "voice_loop_user_config_available", "status": "warn", "detail": "voice_loop_user_config_available"},
                {"name": "voice_loop_wakeword_customized", "status": "warn", "detail": {"wakeword_threshold": 0.6}},
            ],
        }
    )

    step = next(item for item in snapshot.to_dict()["steps"] if item["name"] == "voice_loop_wakeword_customized")

    assert step == {
        "detail": {"wakeword_threshold": 0.6},
        "label": "Voice-loop wake-word config",
        "name": "voice_loop_wakeword_customized",
        "recommended_command": "./scripts/install_voice_loop_user_config.sh",
        "required": False,
        "status": "warn",
    }


def test_build_setup_snapshot_uses_voice_loop_config_for_voice_diagnostics_when_available() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "audio_playback_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    actions = _action_map(snapshot.to_dict())

    assert actions["probe_wakeword_path"]["command"] == "python3 -m operance.cli --wakeword-probe-frames 8 --use-voice-loop-config"
    assert actions["calibrate_wakeword_threshold"]["command"] == "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config"
    assert actions["apply_calibrated_wakeword_threshold"]["command"] == (
        "python3 -m operance.cli --wakeword-calibrate-frames 20 --use-voice-loop-config --apply-suggested-threshold"
    )
    assert actions["evaluate_wakeword_idle_rate"]["command"] == "python3 -m operance.cli --wakeword-eval-frames 50 --use-voice-loop-config"
    assert actions["run_voice_self_test"]["command"] == "python3 -m operance.cli --voice-self-test --use-voice-loop-config"


def test_build_setup_snapshot_recommends_service_enable_actions_for_disabled_units() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "warn",
                "tray_user_service_active": "warn",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "warn",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()

    assert payload["recommended_commands"] == [
        "./scripts/control_systemd_user_services.sh enable",
        "./scripts/control_systemd_user_services.sh enable --voice-loop",
        "./scripts/install_voice_loop_user_config.sh",
    ]
    assert next(
        action for action in payload["actions"] if action["action_id"] == "enable_tray_service"
    ) == {
        "action_id": "enable_tray_service",
        "available": True,
        "command": "./scripts/control_systemd_user_services.sh enable",
        "label": "Enable tray user service",
        "recommended": True,
    }
    assert next(
        action for action in payload["actions"] if action["action_id"] == "enable_voice_loop_service"
    ) == {
        "action_id": "enable_voice_loop_service",
        "available": True,
        "command": "./scripts/control_systemd_user_services.sh enable --voice-loop",
        "label": "Enable voice-loop user service",
        "recommended": True,
    }
    assert next(
        action for action in payload["actions"] if action["action_id"] == "install_voice_loop_user_config"
    ) == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": True,
    }


def test_build_setup_snapshot_recommends_service_restart_actions_for_inactive_units() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "warn",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()

    assert payload["recommended_commands"] == [
        "./scripts/control_systemd_user_services.sh restart",
        "./scripts/control_systemd_user_services.sh restart --voice-loop",
        "./scripts/install_voice_loop_user_config.sh",
    ]
    assert next(
        action for action in payload["actions"] if action["action_id"] == "restart_tray_service"
    ) == {
        "action_id": "restart_tray_service",
        "available": True,
        "command": "./scripts/control_systemd_user_services.sh restart",
        "label": "Restart tray user service",
        "recommended": True,
    }
    assert next(
        action for action in payload["actions"] if action["action_id"] == "restart_voice_loop_service"
    ) == {
        "action_id": "restart_voice_loop_service",
        "available": True,
        "command": "./scripts/control_systemd_user_services.sh restart --voice-loop",
        "label": "Restart voice-loop user service",
        "recommended": True,
    }
    assert next(
        action for action in payload["actions"] if action["action_id"] == "install_voice_loop_user_config"
    ) == {
        "action_id": "install_voice_loop_user_config",
        "available": True,
        "command": "./scripts/install_voice_loop_user_config.sh",
        "label": "Seed voice-loop user config",
        "recommended": True,
    }


def test_build_setup_snapshot_recommends_voice_loop_restart_when_heartbeat_is_stale() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "ok",
                "voice_loop_user_service_enabled": "ok",
                "voice_loop_user_service_active": "ok",
                "voice_loop_user_config_available": "ok",
                "voice_loop_runtime_status_available": "ok",
                "voice_loop_runtime_heartbeat_fresh": "warn",
                "voice_loop_wakeword_customized": "ok",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "ok",
            }
        )
    )

    payload = snapshot.to_dict()
    runtime_step = next(
        step for step in payload["steps"] if step["name"] == "voice_loop_runtime_heartbeat_fresh"
    )

    assert payload["recommended_commands"] == ["./scripts/control_systemd_user_services.sh restart --voice-loop"]
    assert runtime_step["recommended_command"] == "./scripts/control_systemd_user_services.sh restart --voice-loop"
    assert next(
        action for action in payload["actions"] if action["action_id"] == "restart_voice_loop_service"
    ) == {
        "action_id": "restart_voice_loop_service",
        "available": True,
        "command": "./scripts/control_systemd_user_services.sh restart --voice-loop",
        "label": "Restart voice-loop user service",
        "recommended": True,
    }


def test_build_setup_snapshot_exposes_package_actions_when_tooling_is_ready(
    monkeypatch,
    tmp_path,
) -> None:
    from operance.ui import build_setup_snapshot

    monkeypatch.setattr(
        "operance.platforms.linux._default_deb_package_artifact_path",
        lambda: tmp_path / "missing-operance_0.1.0_all.deb",
    )
    monkeypatch.setattr(
        "operance.platforms.linux._default_rpm_package_artifact_path",
        lambda: tmp_path / "missing-operance-0.1.0-1.noarch.rpm",
    )

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "warn",
                "voice_loop_user_service_enabled": "warn",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "ok",
                "rpm_packaging_cli_available": "ok",
                "archive_packaging_cli_available": "ok",
                "deb_package_installer_available": "warn",
                "rpm_package_installer_available": "ok",
            }
        )
    )

    actions = _action_map(snapshot.to_dict())

    assert actions["render_package_scaffolds"] == {
        "action_id": "render_package_scaffolds",
        "available": True,
        "command": "./scripts/build_package_scaffolds.sh",
        "label": "Render package scaffolds",
        "recommended": False,
    }
    assert actions["build_deb_package_artifact"] == {
        "action_id": "build_deb_package_artifact",
        "available": True,
        "command": "./scripts/build_package_artifacts.sh --deb",
        "label": "Build Debian package artifact",
        "recommended": False,
    }
    assert actions["install_deb_packaging_tools"] == {
        "action_id": "install_deb_packaging_tools",
        "available": False,
        "command": "./scripts/install_packaging_tools.sh --deb",
        "label": "Install Debian packaging tools",
        "recommended": False,
        "unavailable_reason": "Blocked by: Debian package installer.",
        "suggested_command": "python3 -m operance.cli --doctor",
    }
    assert actions["install_rpm_packaging_tools"] == {
        "action_id": "install_rpm_packaging_tools",
        "available": False,
        "command": "./scripts/install_packaging_tools.sh --rpm",
        "label": "Install RPM packaging tools",
        "recommended": False,
        "unavailable_reason": "Blocked by: RPM packaging CLI already available.",
    }
    assert actions["build_rpm_package_artifact"] == {
        "action_id": "build_rpm_package_artifact",
        "available": True,
        "command": "./scripts/build_package_artifacts.sh --rpm",
        "label": "Build RPM package artifact",
        "recommended": False,
    }
    assert actions["run_fedora_release_smoke"] == {
        "action_id": "run_fedora_release_smoke",
        "available": True,
        "command": "./scripts/run_fedora_release_smoke.sh --reset-user-services",
        "label": "Run Fedora release smoke",
        "recommended": False,
    }
    assert actions["run_beta_readiness_gate"] == {
        "action_id": "run_beta_readiness_gate",
        "available": True,
        "command": "./scripts/run_beta_readiness_gate.sh",
        "label": "Run beta readiness gate",
        "recommended": False,
    }
    assert actions["run_fedora_alpha_gate"] == {
        "action_id": "run_fedora_alpha_gate",
        "available": True,
        "command": "./scripts/run_fedora_alpha_gate.sh --reset-user-services",
        "label": "Run Fedora alpha gate",
        "recommended": False,
    }
    assert actions["install_deb_package_artifact"]["available"] is False
    assert actions["install_rpm_package_artifact"]["available"] is False
    assert actions["run_installed_rpm_beta_smoke"]["available"] is False


def test_build_setup_snapshot_exposes_package_install_and_uninstall_actions(
    monkeypatch,
    tmp_path,
) -> None:
    from operance.ui import build_setup_snapshot

    deb_artifact = tmp_path / "operance_0.1.0_all.deb"
    rpm_artifact = tmp_path / "operance-0.1.0-1.noarch.rpm"
    deb_artifact.write_text("deb", encoding="utf-8")
    rpm_artifact.write_text("rpm", encoding="utf-8")

    monkeypatch.setattr("operance.platforms.linux._default_deb_package_artifact_path", lambda: deb_artifact)
    monkeypatch.setattr("operance.platforms.linux._default_rpm_package_artifact_path", lambda: rpm_artifact)

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_user_service_installed": "ok",
                "tray_user_service_enabled": "ok",
                "tray_user_service_active": "ok",
                "voice_loop_user_service_installed": "warn",
                "voice_loop_user_service_enabled": "warn",
                "voice_loop_user_service_active": "warn",
                "voice_loop_user_config_available": "warn",
                "tray_ui_available": "ok",
                "wakeword_backend_available": "ok",
                "stt_backend_available": "ok",
                "tts_backend_available": "ok",
                "audio_playback_cli_available": "ok",
                "deb_packaging_cli_available": "warn",
                "rpm_packaging_cli_available": "warn",
                "archive_packaging_cli_available": "warn",
                "deb_package_installer_available": "ok",
                "rpm_package_installer_available": "ok",
            }
        )
    )

    actions = _action_map(snapshot.to_dict())

    assert actions["install_deb_package_artifact"] == {
        "action_id": "install_deb_package_artifact",
        "available": True,
        "command": f"./scripts/install_package_artifact.sh --package {deb_artifact} --installer apt",
        "label": "Install Debian package artifact",
        "recommended": False,
    }
    assert actions["install_deb_packaging_tools"] == {
        "action_id": "install_deb_packaging_tools",
        "available": True,
        "command": "./scripts/install_packaging_tools.sh --deb",
        "label": "Install Debian packaging tools",
        "recommended": True,
    }
    assert actions["install_rpm_package_artifact"] == {
        "action_id": "install_rpm_package_artifact",
        "available": True,
        "command": (
            f"./scripts/install_package_artifact.sh --package {rpm_artifact} --installer dnf "
            "--replace-existing --reset-user-services"
        ),
        "label": "Install RPM package artifact",
        "recommended": False,
    }
    assert actions["install_rpm_packaging_tools"] == {
        "action_id": "install_rpm_packaging_tools",
        "available": True,
        "command": "./scripts/install_packaging_tools.sh --rpm",
        "label": "Install RPM packaging tools",
        "recommended": True,
    }
    assert actions["run_installed_rpm_beta_smoke"] == {
        "action_id": "run_installed_rpm_beta_smoke",
        "available": True,
        "command": (
            f"./scripts/run_installed_beta_smoke.sh --package {rpm_artifact} --installer dnf "
            "--require-mvp-runtime --reset-user-services --uninstall-after"
        ),
        "label": "Run installed RPM beta smoke",
        "recommended": False,
    }
    assert actions["run_fedora_release_smoke"] == {
        "action_id": "run_fedora_release_smoke",
        "available": False,
        "command": "./scripts/run_fedora_release_smoke.sh --reset-user-services",
        "label": "Run Fedora release smoke",
        "recommended": False,
        "unavailable_reason": "Blocked by: Archive CLI, RPM packaging CLI.",
    }
    assert actions["uninstall_deb_package"] == {
        "action_id": "uninstall_deb_package",
        "available": True,
        "command": "./scripts/uninstall_native_package.sh --installer apt",
        "label": "Uninstall Debian package",
        "recommended": False,
    }
    assert actions["uninstall_rpm_package"] == {
        "action_id": "uninstall_rpm_package",
        "available": True,
        "command": "./scripts/uninstall_native_package.sh --installer dnf",
        "label": "Uninstall RPM package",
        "recommended": False,
    }


def test_build_setup_snapshot_exposes_fedora_alpha_gate_next_step_when_checkout_and_packaging_are_ready() -> None:
    from operance.ui import build_setup_snapshot

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "ok",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_ui_available": "ok",
                "stt_backend_available": "ok",
                "archive_packaging_cli_available": "ok",
                "rpm_packaging_cli_available": "ok",
                "rpm_package_installer_available": "ok",
            }
        )
    )

    next_steps = _next_step_map(snapshot.to_dict())

    assert next_steps["Run beta readiness gate"] == {
        "label": "Run beta readiness gate",
        "command": "./scripts/run_beta_readiness_gate.sh",
    }
    assert next_steps["Run Fedora alpha gate"] == {
        "label": "Run Fedora alpha gate",
        "command": "./scripts/run_fedora_alpha_gate.sh --reset-user-services",
    }


def test_build_setup_snapshot_prefers_installed_rpm_smoke_next_step_when_artifact_exists_without_checkout_gate(
    monkeypatch,
    tmp_path,
) -> None:
    from operance.ui import build_setup_snapshot

    rpm_artifact = tmp_path / "operance-0.1.0-1.noarch.rpm"
    rpm_artifact.write_text("rpm", encoding="utf-8")
    monkeypatch.setattr("operance.platforms.linux._default_rpm_package_artifact_path", lambda: rpm_artifact)

    snapshot = build_setup_snapshot(
        _report(
            {
                "python_3_12_plus": "ok",
                "virtualenv_active": "warn",
                "linux_platform": "ok",
                "kde_wayland_target": "ok",
                "xdg_open_available": "ok",
                "gdbus_available": "ok",
                "networkmanager_cli_available": "ok",
                "audio_cli_available": "ok",
                "audio_capture_cli_available": "ok",
                "systemctl_user_available": "ok",
                "power_status_available": "ok",
                "tray_ui_available": "ok",
                "stt_backend_available": "ok",
                "archive_packaging_cli_available": "ok",
                "rpm_packaging_cli_available": "ok",
                "rpm_package_installer_available": "ok",
            }
        )
    )

    next_steps = _next_step_map(snapshot.to_dict())

    assert next_steps["Run installed RPM beta smoke"] == {
        "label": "Run installed RPM beta smoke",
        "command": (
            f"./scripts/run_installed_beta_smoke.sh --package {rpm_artifact} "
            "--installer dnf --require-mvp-runtime --reset-user-services --uninstall-after"
        ),
    }
