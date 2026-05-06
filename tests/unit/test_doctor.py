def test_environment_report_includes_platform_and_checks() -> None:
    from operance.doctor import build_environment_report

    report = build_environment_report()

    assert "platform" in report
    assert "python_version" in report
    assert "checks" in report
    assert isinstance(report["checks"], list)
    assert report["checks"]


def test_environment_report_marks_linux_requirements_when_not_on_linux() -> None:
    from operance.doctor import build_environment_report

    report = build_environment_report(system_name="Darwin")

    statuses = {check["name"]: check["status"] for check in report["checks"]}

    assert statuses["linux_platform"] == "warn"
    assert statuses["kde_wayland_target"] == "warn"


def test_environment_report_includes_linux_tooling_checks() -> None:
    from operance.doctor import build_environment_report

    report = build_environment_report(system_name="Linux")

    check_names = {check["name"] for check in report["checks"]}

    assert "xdg_open_available" in check_names
    assert "notify_send_available" in check_names
    assert "gdbus_available" in check_names
    assert "wayland_session_accessible" in check_names
    assert "networkmanager_cli_available" in check_names
    assert "audio_cli_available" in check_names
    assert "audio_capture_cli_available" in check_names
    assert "audio_playback_cli_available" in check_names
    assert "clipboard_cli_available" in check_names
    assert "text_input_cli_available" in check_names
    assert "systemctl_user_available" in check_names
    assert "tray_user_service_installed" in check_names
    assert "tray_user_service_enabled" in check_names
    assert "tray_user_service_active" in check_names
    assert "voice_loop_user_service_installed" in check_names
    assert "voice_loop_user_service_enabled" in check_names
    assert "voice_loop_user_service_active" in check_names
    assert "voice_loop_user_config_available" in check_names
    assert "legacy_install_detected" not in check_names
    assert "voice_loop_runtime_status_available" in check_names
    assert "voice_loop_runtime_heartbeat_fresh" in check_names
    assert "voice_loop_wakeword_customized" in check_names
    assert "tray_ui_available" in check_names
    assert "wakeword_backend_available" in check_names
    assert "wakeword_model_asset_available" in check_names
    assert "wakeword_model_source_available" in check_names
    assert "stt_backend_available" in check_names
    assert "tts_backend_available" in check_names
    assert "tts_model_asset_available" in check_names
    assert "tts_model_source_available" in check_names
    assert "tts_voices_asset_available" in check_names
    assert "tts_voices_source_available" in check_names
    assert "planner_runtime_enabled" in check_names
    assert "planner_endpoint_healthy" in check_names
    assert "power_status_available" in check_names


def test_environment_report_includes_package_tooling_checks() -> None:
    from operance.doctor import build_environment_report

    report = build_environment_report(system_name="Linux")

    check_names = {check["name"] for check in report["checks"]}

    assert "deb_packaging_cli_available" in check_names
    assert "rpm_packaging_cli_available" in check_names
    assert "archive_packaging_cli_available" in check_names
    assert "deb_package_installer_available" in check_names
    assert "rpm_package_installer_available" in check_names


def test_probe_wayland_session_access_reports_missing_socket(tmp_path) -> None:
    from operance import doctor

    status, detail = doctor._probe_wayland_session_access(
        {
            "XDG_SESSION_TYPE": "wayland",
            "XDG_RUNTIME_DIR": str(tmp_path),
            "WAYLAND_DISPLAY": "wayland-9",
        }
    )

    assert status == "warn"
    assert detail["socket_path"] == str(tmp_path / "wayland-9")
    assert detail["message"] == "Wayland socket path does not exist."


def test_probe_wayland_session_access_reports_accessible_socket(tmp_path) -> None:
    from operance import doctor

    socket_path = tmp_path / "wayland-7"
    socket_path.write_text("", encoding="utf-8")

    connected_paths: list[str] = []

    class _FakeSocket:
        def settimeout(self, timeout: float) -> None:
            assert timeout == 0.5

        def connect(self, path: str) -> None:
            connected_paths.append(path)

        def close(self) -> None:
            return None

    doctor_socket = doctor.socket
    original_socket_factory = doctor_socket.socket
    doctor_socket.socket = lambda *_args, **_kwargs: _FakeSocket()
    try:
        status, detail = doctor._probe_wayland_session_access(
            {
                "XDG_SESSION_TYPE": "wayland",
                "XDG_RUNTIME_DIR": str(tmp_path),
                "WAYLAND_DISPLAY": "wayland-7",
            }
        )
    finally:
        doctor_socket.socket = original_socket_factory

    assert status == "ok"
    assert connected_paths == [str(socket_path)]
    assert detail["socket_path"] == str(socket_path)
    assert detail["message"] == "Wayland session socket is accessible."


def test_probe_text_input_backend_reports_unsupported_protocol() -> None:
    from operance import doctor

    def run_command(command: list[str]) -> object:
        assert command == ["wtype", "-M", "shift", "-m", "shift"]
        return doctor.subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="Compositor does not support the virtual keyboard protocol",
        )

    status, detail = doctor._probe_text_input_backend(
        wayland_session_accessible=True,
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
    )

    assert status == "warn"
    assert detail == {
        "backend_status": "unsupported_protocol",
        "message": "wtype is installed but the compositor does not support the virtual keyboard protocol.",
        "probe_error": "Compositor does not support the virtual keyboard protocol",
        "wtype": "/usr/bin/wtype",
    }


def test_environment_report_includes_tray_service_runtime_state(monkeypatch) -> None:
    from pathlib import Path

    from operance import doctor

    monkeypatch.setattr(doctor, "_tray_user_service_path", lambda: Path("/tmp/operance-tray.service"))
    monkeypatch.setattr(doctor, "_voice_loop_user_service_path", lambda: Path("/tmp/operance-voice-loop.service"))
    monkeypatch.setattr(
        doctor,
        "_probe_systemctl_user_service_state",
        lambda subcommand, unit_name, systemctl_path=None: (
            ("ok", "enabled") if subcommand == "is-enabled" else ("warn", "inactive")
        ),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["tray_user_service_enabled"]["status"] == "ok"
    assert checks["tray_user_service_enabled"]["detail"] == "enabled"
    assert checks["tray_user_service_active"]["status"] == "warn"
    assert checks["tray_user_service_active"]["detail"] == "inactive"
    assert checks["voice_loop_user_service_enabled"]["status"] == "ok"
    assert checks["voice_loop_user_service_enabled"]["detail"] == "enabled"
    assert checks["voice_loop_user_service_active"]["status"] == "warn"
    assert checks["voice_loop_user_service_active"]["detail"] == "inactive"


def test_environment_report_detects_packaged_user_service_units(monkeypatch, tmp_path) -> None:
    from operance import doctor

    packaged_unit_dir = tmp_path / "usr" / "lib" / "systemd" / "user"
    packaged_unit_dir.mkdir(parents=True)
    tray_unit = packaged_unit_dir / "operance-tray.service"
    voice_loop_unit = packaged_unit_dir / "operance-voice-loop.service"
    tray_unit.write_text("[Unit]\nDescription=Operance tray app\n", encoding="utf-8")
    voice_loop_unit.write_text("[Unit]\nDescription=Operance voice loop\n", encoding="utf-8")

    monkeypatch.setattr(
        doctor,
        "_user_service_candidate_paths",
        lambda unit_name: [
            tmp_path / "home" / ".config" / "systemd" / "user" / unit_name,
            packaged_unit_dir / unit_name,
        ],
    )
    monkeypatch.setattr(
        doctor,
        "_probe_systemctl_user_service_state",
        lambda subcommand, unit_name, systemctl_path=None: ("warn", "inactive"),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["tray_user_service_installed"]["status"] == "ok"
    assert checks["tray_user_service_installed"]["detail"] == str(tray_unit)
    assert checks["voice_loop_user_service_installed"]["status"] == "ok"
    assert checks["voice_loop_user_service_installed"]["detail"] == str(voice_loop_unit)


def test_environment_report_detects_voice_loop_user_config(monkeypatch, tmp_path) -> None:
    from operance import doctor

    config_path = tmp_path / "config" / "operance" / "voice-loop.args"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("--voice-loop-max-commands\n2\n", encoding="utf-8")

    monkeypatch.setattr(
        doctor,
        "_voice_loop_config_candidate_paths",
        lambda: [
            config_path,
            tmp_path / "etc" / "operance" / "voice-loop.args",
        ],
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_user_config_available"]["status"] == "ok"
    assert checks["voice_loop_user_config_available"]["detail"] == str(config_path)


def test_environment_report_ignores_unrelated_voice_loop_user_config(monkeypatch, tmp_path) -> None:
    from operance import doctor

    unrelated_config_path = tmp_path / "config" / "archived-app" / "voice-loop.args"
    unrelated_config_path.parent.mkdir(parents=True)
    unrelated_config_path.write_text("--wakeword-threshold\n0.844\n", encoding="utf-8")

    monkeypatch.setattr(
        doctor,
        "_voice_loop_config_candidate_paths",
        lambda: [
            tmp_path / "config" / "operance" / "voice-loop.args",
            tmp_path / "etc" / "operance" / "voice-loop.args",
        ],
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_user_config_available"]["status"] == "warn"
    assert checks["voice_loop_user_config_available"]["detail"] == str(
        tmp_path / "config" / "operance" / "voice-loop.args"
    )


def test_environment_report_reports_effective_voice_loop_wakeword_config(monkeypatch) -> None:
    from operance import doctor

    class _FakeVoiceLoopConfigSnapshot:
        selected_args_file = "/home/test/.config/operance/voice-loop.args"

        @property
        def effective(self):
            class _Effective:
                wakeword_mode = "energy_fallback"
                wakeword_threshold = 0.95

            return _Effective()

        def to_dict(self) -> dict[str, object]:
            return {
                "configured_args": ["--wakeword-threshold", "0.95"],
                "effective": {
                    "passthrough_args": [],
                    "voice_loop_max_commands": None,
                    "voice_loop_max_commands_source": "default",
                    "voice_loop_max_frames": None,
                    "voice_loop_max_frames_source": "default",
                    "wakeword_auto_model_path": None,
                    "wakeword_mode": "energy_fallback",
                    "wakeword_model": None,
                    "wakeword_model_source": "default",
                    "wakeword_threshold": 0.95,
                    "wakeword_threshold_source": "args_file",
                },
                "explicit_args_file": None,
                "launcher_mode": "repo_local",
                "search_paths": ["/repo/.operance/voice-loop.args", "/home/test/.config/operance/voice-loop.args"],
                "selected_args_file": "/home/test/.config/operance/voice-loop.args",
            }

    monkeypatch.setattr(doctor, "build_voice_loop_config_snapshot", lambda: _FakeVoiceLoopConfigSnapshot())

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_wakeword_customized"] == {
        "name": "voice_loop_wakeword_customized",
        "status": "ok",
        "detail": {
            "configured_args": ["--wakeword-threshold", "0.95"],
            "effective": {
                "passthrough_args": [],
                "voice_loop_max_commands": None,
                "voice_loop_max_commands_source": "default",
                "voice_loop_max_frames": None,
                "voice_loop_max_frames_source": "default",
                "wakeword_auto_model_path": None,
                "wakeword_mode": "energy_fallback",
                "wakeword_model": None,
                "wakeword_model_source": "default",
                "wakeword_threshold": 0.95,
                "wakeword_threshold_source": "args_file",
            },
            "explicit_args_file": None,
            "launcher_mode": "repo_local",
            "search_paths": ["/repo/.operance/voice-loop.args", "/home/test/.config/operance/voice-loop.args"],
            "selected_args_file": "/home/test/.config/operance/voice-loop.args",
        },
    }


def test_environment_report_reports_voice_loop_runtime_status(monkeypatch) -> None:
    from operance import doctor

    class _FakeVoiceLoopRuntimeStatusSnapshot:
        status_file_exists = True
        heartbeat_fresh = True
        status_file_path = "/repo/.operance/voice-loop-status.json"

        def to_dict(self) -> dict[str, object]:
            return {
                "awaiting_confirmation": False,
                "completed_commands": 1,
                "daemon_state": "IDLE",
                "heartbeat_age_seconds": 0.5,
                "heartbeat_fresh": True,
                "heartbeat_timeout_seconds": 30.0,
                "last_response_status": "success",
                "last_response_text": "Launched firefox",
                "last_transcript_final": True,
                "last_transcript_text": "open firefox",
                "last_wake_confidence": 0.88,
                "last_wake_phrase": "operance",
                "loop_state": "waiting_for_wake",
                "message": "Voice-loop runtime heartbeat is fresh.",
                "processed_frames": 12,
                "started_at": "2026-04-30T01:00:00+00:00",
                "status": "ok",
                "status_file_exists": True,
                "status_file_path": "/repo/.operance/voice-loop-status.json",
                "stopped_at": None,
                "stopped_reason": None,
                "updated_at": "2026-04-30T01:00:01+00:00",
                "wake_detections": 1,
            }

    monkeypatch.setattr(
        doctor,
        "build_voice_loop_runtime_status_snapshot",
        lambda: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_runtime_status_available"] == {
        "name": "voice_loop_runtime_status_available",
        "status": "ok",
        "detail": "/repo/.operance/voice-loop-status.json",
    }
    assert checks["voice_loop_runtime_heartbeat_fresh"]["status"] == "ok"
    assert checks["voice_loop_runtime_heartbeat_fresh"]["detail"]["loop_state"] == "waiting_for_wake"
    assert checks["voice_loop_runtime_heartbeat_fresh"]["detail"]["completed_commands"] == 1


def test_environment_report_treats_missing_voice_loop_runtime_status_as_informational_when_service_is_inactive(
    monkeypatch,
) -> None:
    from pathlib import Path

    from operance import doctor

    class _FakeVoiceLoopRuntimeStatusSnapshot:
        status_file_exists = False
        heartbeat_fresh = False
        status_file_path = "/repo/.operance/voice-loop-status.json"

        def to_dict(self) -> dict[str, object]:
            return {
                "heartbeat_fresh": False,
                "loop_state": "missing",
                "message": "No voice-loop runtime status file found.",
                "status": "warn",
                "status_file_exists": False,
                "status_file_path": "/repo/.operance/voice-loop-status.json",
            }

    monkeypatch.setattr(doctor, "_voice_loop_user_service_path", lambda: Path("/tmp/operance-voice-loop.service"))
    monkeypatch.setattr(
        doctor,
        "_probe_systemctl_user_service_state",
        lambda subcommand, unit_name, systemctl_path=None: ("warn", "inactive"),
    )
    monkeypatch.setattr(
        doctor,
        "build_voice_loop_runtime_status_snapshot",
        lambda: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_runtime_status_available"]["status"] == "ok"
    assert checks["voice_loop_runtime_status_available"]["detail"] == {
        "message": "Voice-loop user service is not active; runtime status is optional until the service runs.",
        "status_file_path": "/repo/.operance/voice-loop-status.json",
    }
    assert checks["voice_loop_runtime_heartbeat_fresh"]["status"] == "ok"
    assert checks["voice_loop_runtime_heartbeat_fresh"]["detail"]["message"] == (
        "Voice-loop user service is not active; no runtime status file has been written yet."
    )


def test_environment_report_treats_stale_voice_loop_runtime_status_as_informational_when_service_is_inactive(
    monkeypatch,
) -> None:
    from pathlib import Path

    from operance import doctor

    class _FakeVoiceLoopRuntimeStatusSnapshot:
        status_file_exists = True
        heartbeat_fresh = False
        status_file_path = "/repo/.operance/voice-loop-status.json"

        def to_dict(self) -> dict[str, object]:
            return {
                "heartbeat_age_seconds": 82.0,
                "heartbeat_fresh": False,
                "loop_state": "listening_for_command",
                "message": "Voice-loop runtime heartbeat is stale.",
                "status": "warn",
                "status_file_exists": True,
                "status_file_path": "/repo/.operance/voice-loop-status.json",
            }

    monkeypatch.setattr(doctor, "_voice_loop_user_service_path", lambda: Path("/tmp/operance-voice-loop.service"))
    monkeypatch.setattr(
        doctor,
        "_probe_systemctl_user_service_state",
        lambda subcommand, unit_name, systemctl_path=None: ("warn", "inactive"),
    )
    monkeypatch.setattr(
        doctor,
        "build_voice_loop_runtime_status_snapshot",
        lambda: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_runtime_status_available"] == {
        "name": "voice_loop_runtime_status_available",
        "status": "ok",
        "detail": "/repo/.operance/voice-loop-status.json",
    }
    assert checks["voice_loop_runtime_heartbeat_fresh"]["status"] == "ok"
    assert checks["voice_loop_runtime_heartbeat_fresh"]["detail"]["message"] == (
        "Voice-loop user service is not active; showing the last recorded runtime status."
    )
    assert checks["voice_loop_runtime_heartbeat_fresh"]["detail"]["heartbeat_fresh"] is False


def test_environment_report_warns_when_voice_loop_wakeword_config_matches_defaults(monkeypatch) -> None:
    from operance import doctor

    class _FakeVoiceLoopConfigSnapshot:
        selected_args_file = "/home/test/.config/operance/voice-loop.args"

        @property
        def effective(self):
            class _Effective:
                wakeword_mode = "energy_fallback"
                wakeword_threshold = 0.6

            return _Effective()

        def to_dict(self) -> dict[str, object]:
            return {
                "config_available": True,
                "configured_args": ["--wakeword-threshold", "0.6"],
                "effective": {
                    "passthrough_args": [],
                    "voice_loop_max_commands": None,
                    "voice_loop_max_commands_source": "default",
                    "voice_loop_max_frames": None,
                    "voice_loop_max_frames_source": "default",
                    "wakeword_auto_model_path": None,
                    "wakeword_mode": "energy_fallback",
                    "wakeword_model": None,
                    "wakeword_model_source": "default",
                    "wakeword_threshold": 0.6,
                    "wakeword_threshold_source": "args_file",
                },
                "explicit_args_file": None,
                "launcher_mode": "repo_local",
                "message": "Using selected voice-loop args file.",
                "search_paths": ["/repo/.operance/voice-loop.args", "/home/test/.config/operance/voice-loop.args"],
                "selected_args_file": "/home/test/.config/operance/voice-loop.args",
                "status": "ok",
            }

    monkeypatch.setattr(doctor, "build_voice_loop_config_snapshot", lambda: _FakeVoiceLoopConfigSnapshot())

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["voice_loop_wakeword_customized"] == {
        "name": "voice_loop_wakeword_customized",
        "status": "warn",
        "detail": {
            "config_available": True,
            "configured_args": ["--wakeword-threshold", "0.6"],
            "effective": {
                "passthrough_args": [],
                "voice_loop_max_commands": None,
                "voice_loop_max_commands_source": "default",
                "voice_loop_max_frames": None,
                "voice_loop_max_frames_source": "default",
                "wakeword_auto_model_path": None,
                "wakeword_mode": "energy_fallback",
                "wakeword_model": None,
                "wakeword_model_source": "default",
                "wakeword_threshold": 0.6,
                "wakeword_threshold_source": "args_file",
            },
            "explicit_args_file": None,
            "launcher_mode": "repo_local",
            "message": "Using selected voice-loop args file.",
            "search_paths": ["/repo/.operance/voice-loop.args", "/home/test/.config/operance/voice-loop.args"],
            "selected_args_file": "/home/test/.config/operance/voice-loop.args",
            "status": "ok",
        },
    }


def test_environment_report_reports_enabled_planner_health(monkeypatch) -> None:
    from operance import doctor
    from operance.config import AppConfig

    config = AppConfig.from_env(
        {
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_ENDPOINT": "http://127.0.0.1:8080/v1/chat/completions",
            "OPERANCE_PLANNER_MODEL": "qwen-test",
        }
    )

    monkeypatch.setattr(doctor, "_planner_config", lambda: config.planner)
    monkeypatch.setattr(
        doctor,
        "_probe_planner_health",
        lambda planner_config: (
            "ok",
            {
                "status": "ok",
                "endpoint": planner_config.endpoint,
                "probe": "models",
                "probe_url": "http://127.0.0.1:8080/v1/models",
                "model_ids": ["qwen-test"],
            },
        ),
    )

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["planner_runtime_enabled"] == {
        "name": "planner_runtime_enabled",
        "status": "ok",
        "detail": {
            "enabled": True,
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
            "model": "qwen-test",
        },
    }
    assert checks["planner_endpoint_healthy"]["status"] == "ok"
    assert checks["planner_endpoint_healthy"]["detail"]["probe"] == "models"


def test_environment_report_detects_tts_asset_paths(monkeypatch, tmp_path) -> None:
    from operance import doctor

    model_path = tmp_path / "kokoro.onnx"
    voices_path = tmp_path / "voices.bin"
    model_path.write_text("model", encoding="utf-8")
    voices_path.write_text("voices", encoding="utf-8")

    monkeypatch.setattr(doctor, "find_existing_tts_model_path", lambda: model_path)
    monkeypatch.setattr(doctor, "preferred_tts_model_path", lambda: model_path)
    monkeypatch.setattr(doctor, "find_existing_tts_voices_path", lambda: voices_path)
    monkeypatch.setattr(doctor, "preferred_tts_voices_path", lambda: voices_path)

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["tts_model_asset_available"] == {
        "name": "tts_model_asset_available",
        "status": "ok",
        "detail": str(model_path),
    }
    assert checks["tts_voices_asset_available"] == {
        "name": "tts_voices_asset_available",
        "status": "ok",
        "detail": str(voices_path),
    }


def test_environment_report_detects_wakeword_model_asset_path(monkeypatch, tmp_path) -> None:
    from operance import doctor

    model_path = tmp_path / "operance.onnx"
    model_path.write_text("model", encoding="utf-8")

    monkeypatch.setattr(doctor, "find_existing_wakeword_model_path", lambda: model_path)
    monkeypatch.setattr(doctor, "preferred_wakeword_model_path", lambda: model_path)

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["wakeword_model_asset_available"] == {
        "name": "wakeword_model_asset_available",
        "status": "ok",
        "detail": str(model_path),
    }


def test_environment_report_detects_voice_asset_source_paths(monkeypatch, tmp_path) -> None:
    from operance import doctor

    wakeword_source = tmp_path / "wakeword-source.onnx"
    tts_model_source = tmp_path / "kokoro-source.onnx"
    tts_voices_source = tmp_path / "voices-source.bin"
    wakeword_source.write_text("model", encoding="utf-8")
    tts_model_source.write_text("model", encoding="utf-8")
    tts_voices_source.write_text("voices", encoding="utf-8")

    monkeypatch.setenv("OPERANCE_WAKEWORD_MODEL_SOURCE", str(wakeword_source))
    monkeypatch.setenv("OPERANCE_TTS_MODEL_SOURCE", str(tts_model_source))
    monkeypatch.setenv("OPERANCE_TTS_VOICES_SOURCE", str(tts_voices_source))

    report = doctor.build_environment_report(system_name="Linux")
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["wakeword_model_source_available"] == {
        "name": "wakeword_model_source_available",
        "status": "ok",
        "detail": str(wakeword_source),
    }
    assert checks["tts_model_source_available"] == {
        "name": "tts_model_source_available",
        "status": "ok",
        "detail": str(tts_model_source),
    }
    assert checks["tts_voices_source_available"] == {
        "name": "tts_voices_source_available",
        "status": "ok",
        "detail": str(tts_voices_source),
    }
