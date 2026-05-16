import json
from pathlib import Path
import subprocess
import sys

import pytest

from operance.cli import main
from operance.corpus import DEFAULT_COMMAND_CORPUS


class _FakeAudioCaptureSource:
    def list_input_devices(self) -> list[object]:
        from operance.audio.capture import AudioInputDevice

        return [AudioInputDevice(device_id="42", name="alsa_input.usb-mic", is_default=True, backend="pactl")]

    def frames(self, *, max_frames: int | None = None):
        from operance.audio.capture import AudioFrame

        frame_total = max_frames if max_frames is not None else 1
        for _ in range(frame_total):
            yield AudioFrame(
                sample_rate_hz=16000,
                channels=1,
                sample_count=1600,
                source="alsa_input.usb-mic",
                pcm_s16le=b"\x00\x00" * 1600,
            )


class _FakeWakeWordDetector:
    def __init__(self) -> None:
        self.calls = 0

    def process_frame(self, frame) -> object | None:
        self.calls += 1
        if self.calls == 2:
            from operance.wakeword import WakeWordDetection

            return WakeWordDetection(phrase="operance", confidence=0.91)
        return None


class _FakeSpeechTranscriber:
    def __init__(self) -> None:
        self.calls = 0

    def process_frame(self, frame) -> object | None:
        self.calls += 1
        if self.calls == 2:
            from operance.stt import TranscriptSegment

            return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
        return None

    def finish(self) -> list[object]:
        return []

    def close(self) -> None:
        return None


class _FakeVoiceSessionWakeWordDetector:
    def __init__(self) -> None:
        self.calls = 0

    def process_frame(self, frame) -> object | None:
        self.calls += 1
        if self.calls == 2:
            from operance.wakeword import WakeWordDetection

            return WakeWordDetection(phrase="operance", confidence=0.89)
        return None


def test_cli_process_transcript_prints_response_payload(capsys) -> None:
    exit_code = main(["--transcript", "open firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "open firefox"
    assert payload["response"] == "Launched firefox"
    assert payload["status"] == "success"
    assert payload["simulated"] is True


def test_cli_version_prints_project_identity(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.OperanceDaemon.build_default",
        lambda env: (_ for _ in ()).throw(AssertionError("daemon should not be built for --version")),
    )
    monkeypatch.setattr(
        "operance.cli.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
    )

    exit_code = main(["--version"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "operance 0.1.0 (abc1234)"


def test_cli_process_generic_app_transcript_prints_response_payload(capsys) -> None:
    exit_code = main(["--transcript", "open code"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "open code"
    assert payload["response"] == "Launched code"
    assert payload["status"] == "success"
    assert payload["simulated"] is True


def test_cli_process_unknown_transcript_prints_fallback_response(capsys) -> None:
    exit_code = main(["--transcript", "install updates"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "install updates"
    assert payload["response"] == "I did not understand that command."
    assert payload["status"] == "unmatched"
    assert payload["simulated"] is True


def test_cli_process_volume_transcript_prints_volume_payload(capsys) -> None:
    exit_code = main(["--transcript", "what is the volume"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "what is the volume"
    assert payload["response"] == "Volume is 30%"
    assert payload["status"] == "success"


def test_cli_process_audio_mute_status_transcript_prints_audio_payload(capsys) -> None:
    exit_code = main(["--transcript", "is audio muted"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "is audio muted"
    assert payload["response"] == "Audio is unmuted"
    assert payload["status"] == "success"


def test_cli_process_wifi_status_transcript_prints_wifi_payload(capsys) -> None:
    exit_code = main(["--transcript", "wifi status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "wifi status"
    assert payload["response"] == "Wi-Fi is on"
    assert payload["status"] == "success"


def test_cli_process_windows_list_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "list windows"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "list windows"
    assert payload["response"] == "Open windows: Firefox; Terminal"
    assert payload["status"] == "success"


def test_cli_process_minimize_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "minimize window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "minimize window firefox"
    assert payload["response"] == "Minimized window Firefox"
    assert payload["status"] == "success"


def test_cli_process_maximize_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "maximize window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "maximize window firefox"
    assert payload["response"] == "Maximized window Firefox"
    assert payload["status"] == "success"


def test_cli_process_restore_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "restore window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "restore window firefox"
    assert payload["response"] == "Restored window Firefox"
    assert payload["status"] == "success"


def test_cli_process_close_window_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "close window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "close window firefox"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_quit_app_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "quit firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "quit firefox"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_delete_folder_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "delete folder on desktop called projects"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "delete folder on desktop called projects"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_delete_file_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "delete file on desktop called notes.txt"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "delete file on desktop called notes.txt"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_rename_entry_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "rename folder on desktop from projects to archive"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "rename folder on desktop from projects to archive"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_move_entry_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "move folder on desktop called projects to archive"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "move folder on desktop called projects to archive"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_wifi_disable_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "turn wifi off"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "turn wifi off"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_wifi_disconnect_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "disconnect wifi"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "disconnect wifi"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_connect_known_wifi_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "connect to wifi home"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "connect to wifi home"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_high_volume_transcript_requires_confirmation(capsys) -> None:
    exit_code = main(["--transcript", "set volume to 90 percent"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "set volume to 90 percent"
    assert payload["response"] == "Command requires confirmation."
    assert payload["status"] == "awaiting_confirmation"


def test_cli_process_clear_clipboard_transcript_prints_clipboard_payload(capsys) -> None:
    exit_code = main(["--transcript", "clear clipboard"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "clear clipboard"
    assert payload["response"] == "Cleared clipboard"
    assert payload["status"] == "success"


def test_cli_process_paste_clipboard_transcript_prints_clipboard_payload(capsys) -> None:
    exit_code = main(["--transcript", "paste clipboard"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "paste clipboard"
    assert payload["response"] == "Pasted clipboard into active window"
    assert payload["status"] == "success"


def test_cli_process_copy_selection_transcript_prints_clipboard_payload(capsys) -> None:
    exit_code = main(["--transcript", "copy selection"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "copy selection"
    assert payload["response"] == "Copied selection to clipboard"
    assert payload["status"] == "success"


def test_cli_process_type_text_transcript_prints_text_input_payload(capsys) -> None:
    exit_code = main(["--transcript", "type build complete"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "type build complete"
    assert payload["response"] == "Typed text into active window"
    assert payload["status"] == "success"


def test_cli_process_press_key_transcript_prints_key_payload(capsys) -> None:
    exit_code = main(["--transcript", "press enter"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "press enter"
    assert payload["response"] == "Pressed Enter key"
    assert payload["status"] == "success"


def test_cli_process_press_modifier_key_transcript_prints_key_payload(capsys) -> None:
    exit_code = main(["--transcript", "press control c"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "press control c"
    assert payload["response"] == "Pressed Ctrl+C shortcut"
    assert payload["status"] == "success"


def test_cli_process_fullscreen_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "fullscreen window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "fullscreen window firefox"
    assert payload["response"] == "Enabled fullscreen for window Firefox"
    assert payload["status"] == "success"


def test_cli_process_keep_above_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "keep window firefox above"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "keep window firefox above"
    assert payload["response"] == "Enabled keep-above for window Firefox"
    assert payload["status"] == "success"


def test_cli_process_shade_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "shade window firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "shade window firefox"
    assert payload["response"] == "Shaded window Firefox"
    assert payload["status"] == "success"


def test_cli_process_keep_below_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "keep window firefox below"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "keep window firefox below"
    assert payload["response"] == "Enabled keep-below for window Firefox"
    assert payload["status"] == "success"


def test_cli_process_all_desktops_window_transcript_prints_window_payload(capsys) -> None:
    exit_code = main(["--transcript", "show window firefox on all desktops"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["transcript"] == "show window firefox on all desktops"
    assert payload["response"] == "Enabled all-desktops for window Firefox"
    assert payload["status"] == "success"


def test_cli_run_corpus_prints_summary(capsys) -> None:
    exit_code = main(["--run-corpus"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert payload["matched_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert payload["successful_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert payload["success_rate"] == 1.0
    assert payload["p95_latency_ms"] is not None


def test_cli_supported_commands_prints_catalog_with_live_blockers(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.build_environment_report",
        lambda: {
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
                {"name": "audio_capture_cli_available", "status": "ok", "detail": {"pw-record": "/usr/bin/pw-record"}},
                {"name": "clipboard_cli_available", "status": "ok", "detail": {"wl-copy": "/usr/bin/wl-copy", "wl-paste": "/usr/bin/wl-paste"}},
                {"name": "text_input_cli_available", "status": "warn", "detail": {"wtype": None}},
                {"name": "systemctl_user_available", "status": "ok", "detail": "/usr/bin/systemctl"},
                {"name": "rpm_package_installer_available", "status": "ok", "detail": "/usr/bin/dnf"},
                {"name": "power_status_available", "status": "ok", "detail": {"upower": "/usr/bin/upower"}},
            ],
        },
    )

    exit_code = main(["--supported-commands"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    commands = {
        command["tool"]: command
        for domain in payload["domains"]
        for command in domain["commands"]
    }

    assert exit_code == 0
    assert payload["summary"]["total_commands"] >= 1
    assert commands["apps.launch"]["live_runtime_status"] == "available"
    assert commands["apps.launch"]["release_verification_status"] == "verified"
    assert commands["apps.launch"]["example_transcripts"] == [
        "open firefox",
        "open http://localhost:3000",
        "browse to localhost 3000",
        "browse to docs.python.org/3",
    ]
    assert commands["apps.launch"]["usage_pattern"] == (
        "open <app name> | open http://localhost:3000 | browse to localhost 3000"
    )
    assert commands["windows.list"]["live_runtime_status"] == "unverified"
    assert commands["windows.list"]["release_verification_target"] == "fedora_kde_wayland"
    assert commands["text.type"]["live_runtime_status"] == "blocked"
    assert commands["text.type"]["live_runtime_blockers"] == ["Wayland text input CLI"]
    assert commands["text.type"]["live_runtime_suggested_command"] == (
        "./scripts/install_wayland_input_tools.sh --text-input-only"
    )
    assert commands["apps.quit"]["requires_confirmation"] is True


def test_cli_supported_commands_available_only_filters_blocked_entries(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.build_environment_report",
        lambda: {
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
                {"name": "audio_capture_cli_available", "status": "ok", "detail": {"pw-record": "/usr/bin/pw-record"}},
                {"name": "clipboard_cli_available", "status": "ok", "detail": {"wl-copy": "/usr/bin/wl-copy", "wl-paste": "/usr/bin/wl-paste"}},
                {"name": "text_input_cli_available", "status": "warn", "detail": {"wtype": None}},
                {"name": "systemctl_user_available", "status": "ok", "detail": "/usr/bin/systemctl"},
                {"name": "rpm_package_installer_available", "status": "ok", "detail": "/usr/bin/dnf"},
                {"name": "power_status_available", "status": "ok", "detail": {"upower": "/usr/bin/upower"}},
            ],
        },
    )

    exit_code = main(["--supported-commands", "--supported-commands-available-only"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    commands = {
        command["tool"]: command
        for domain in payload["domains"]
        for command in domain["commands"]
    }

    assert exit_code == 0
    assert payload["catalog_filter"] == "available_only"
    assert "apps.launch" in commands
    assert "windows.list" not in commands
    assert "text.type" not in commands
    assert payload["summary"]["unverified_commands"] == 0
    assert payload["summary"]["blocked_commands"] == 0


def test_cli_supported_commands_prints_runtime_guidance_for_unsupported_text_input(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.build_environment_report",
        lambda: {
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
                {"name": "notify_send_available", "status": "ok", "detail": "/usr/bin/notify-send"},
                {"name": "gdbus_available", "status": "ok", "detail": "/usr/bin/gdbus"},
                {"name": "networkmanager_cli_available", "status": "ok", "detail": "/usr/bin/nmcli"},
                {"name": "audio_cli_available", "status": "ok", "detail": {"wpctl": "/usr/bin/wpctl"}},
                {
                    "name": "audio_capture_cli_available",
                    "status": "ok",
                    "detail": {"pw-record": "/usr/bin/pw-record"},
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
            ],
        },
    )

    exit_code = main(["--supported-commands"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    commands = {
        command["tool"]: command
        for domain in payload["domains"]
        for command in domain["commands"]
    }

    assert exit_code == 0
    assert commands["text.type"]["live_runtime_status"] == "blocked"
    assert commands["text.type"]["live_runtime_blockers"] == ["Wayland text input CLI"]
    assert commands["text.type"]["live_runtime_suggested_command"] == "python3 -m operance.cli --doctor"


def test_cli_process_transcript_file_prints_batch_results(tmp_path, capsys) -> None:
    transcript_file = tmp_path / "transcripts.txt"
    transcript_file.write_text("open firefox\ninstall updates\n", encoding="utf-8")

    exit_code = main(["--transcript-file", str(transcript_file)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total_transcripts"] == 2
    assert payload["results"][0]["response"] == "Launched firefox"
    assert payload["results"][0]["simulated"] is True
    assert payload["results"][1]["status"] == "unmatched"
    assert payload["results"][1]["simulated"] is True


def test_cli_interactive_mode_reads_from_stdin(monkeypatch, capsys) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("open firefox\nwhat time is it\nexit\n"))

    exit_code = main(["--interactive"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total_transcripts"] == 2
    assert payload["results"][0]["response"] == "Launched firefox"
    assert payload["results"][1]["response"] == "It is 09:41"
    assert all(result["simulated"] is True for result in payload["results"])


def test_cli_status_prints_structured_snapshot(capsys) -> None:
    exit_code = main(["--status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["current_state"] == "IDLE"
    assert payload["completed_commands"] == 0
    assert payload["p95_latency_ms"] is None
    assert payload["pending_plan_preview"] is None
    assert payload["pending_original_text"] is None
    assert payload["pending_action"] is None
    assert payload["pending_affected_resources"] == []
    assert payload["pending_rollback_hint"] is None
    assert payload["undo_available"] is False
    assert payload["last_undo_tool"] is None


def test_cli_tray_snapshot_prints_projected_status(monkeypatch, capsys) -> None:
    class _FakeVoiceLoopRuntimeStatusSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {}

        status = "ok"
        loop_state = "waiting_for_wake"
        heartbeat_fresh = True
        message = "Voice-loop runtime heartbeat is fresh."
        last_transcript_text = "open firefox"
        last_response_text = "Launched firefox"

    monkeypatch.setattr(
        "operance.cli.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )
    exit_code = main(["--tray-snapshot"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["current_state"] == "IDLE"
    assert payload["tray_state"] == "idle"
    assert payload["mic_state"] == "inactive"
    assert payload["state_label"] == "Idle"
    assert payload["voice_loop_status"] == "ok"
    assert payload["voice_loop_state"] == "waiting_for_wake"
    assert payload["voice_loop_heartbeat_fresh"] is True
    assert payload["voice_loop_message"] == "Voice-loop runtime heartbeat is fresh."
    assert payload["voice_loop_activity"] == "Waiting for wake word"
    assert payload["voice_loop_last_transcript"] == "open firefox"
    assert payload["voice_loop_last_response"] == "Launched firefox"
    assert payload["last_command_preview"] is None
    assert payload["can_confirm"] is False
    assert payload["can_cancel"] is False
    assert payload["can_undo"] is False
    assert payload["can_restart_voice_loop_service"] is False


def test_cli_tray_run_prints_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.run_tray_app",
        lambda env=None: (_ for _ in ()).throw(ValueError("PySide6 is not installed")),
    )

    exit_code = main(["--tray-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "PySide6 is not installed",
        "status": "failed",
    }


def test_cli_action_plan_schema_prints_contract_schema(capsys) -> None:
    exit_code = main(["--action-plan-schema"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["type"] == "object"
    assert payload["required"] == ["plan_id", "source", "original_text", "actions"]


def test_cli_action_result_schema_prints_contract_schema(capsys) -> None:
    exit_code = main(["--action-result-schema"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["type"] == "object"
    assert payload["required"] == ["plan_id", "status", "results"]


def test_cli_doctor_prints_environment_report(capsys) -> None:
    exit_code = main(["--doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "platform" in payload
    assert "python_version" in payload
    assert "checks" in payload


def test_cli_support_snapshot_prints_aggregated_debug_payload(monkeypatch, capsys) -> None:
    snapshot = {
        "doctor": {
            "platform": "Linux",
            "python_version": "3.14.0",
            "checks": [{"name": "linux_platform", "status": "ok", "detail": "Linux"}],
        },
        "setup": {"summary_status": "ready", "ready_for_mvp": True},
        "supported_commands": {"summary": {"available_commands": 3}},
        "voice_loop_config": {"selected_args_file": "/home/test/.config/operance/voice-loop.args"},
        "voice_loop_service": {
            "status": "warn",
            "recommended_command": "./scripts/install_voice_loop_user_service.sh",
        },
    }
    seen_redact: list[bool] = []

    monkeypatch.setattr(
        "operance.cli.build_support_snapshot",
        lambda env=None, redact=False: seen_redact.append(redact) or snapshot,
    )

    exit_code = main(["--support-snapshot"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == snapshot
    assert seen_redact == [True]


def test_cli_support_snapshot_raw_disables_default_redaction(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.build_support_snapshot",
        lambda env=None, redact=False: {"redact": redact},
    )

    exit_code = main(["--support-snapshot", "--support-snapshot-raw"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {"redact": False}


def test_cli_support_snapshot_can_write_json_to_file(monkeypatch, capsys, tmp_path: Path) -> None:
    snapshot = {"doctor": {"platform": "Linux"}, "setup": {"summary_status": "ready"}}
    output_path = tmp_path / "support-snapshot.json"

    monkeypatch.setattr(
        "operance.cli.build_support_snapshot",
        lambda env=None, redact=False: snapshot,
    )

    exit_code = main(
        [
            "--support-snapshot",
            "--support-snapshot-out",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == snapshot
    assert json.loads(output_path.read_text(encoding="utf-8")) == snapshot


def test_cli_support_snapshot_raw_requires_support_snapshot(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--support-snapshot-raw"])

    captured = capsys.readouterr()
    assert "--support-snapshot-raw requires --support-snapshot" in captured.err


def test_cli_support_snapshot_out_requires_support_snapshot(capsys, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--support-snapshot-out", str(tmp_path / "snapshot.json")])

    captured = capsys.readouterr()
    assert "--support-snapshot-out requires --support-snapshot" in captured.err


def test_cli_support_bundle_writes_default_artifact(monkeypatch, capsys) -> None:
    result = {
        "bundle_path": "/tmp/operance-support.tar.gz",
        "included_files": ["manifest.json", "support-snapshot.json"],
        "warning_count": 0,
        "warnings": [],
        "redacted": True,
    }
    calls: list[Path | None] = []

    monkeypatch.setattr(
        "operance.cli.write_support_bundle_artifact",
        lambda *, output_path=None, env=None, redact=True: calls.append(output_path) or result,
    )

    exit_code = main(["--support-bundle"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == result
    assert calls == [None]


def test_cli_support_bundle_can_write_to_requested_path(monkeypatch, capsys, tmp_path: Path) -> None:
    output_path = tmp_path / "bundle.tar.gz"
    result = {
        "bundle_path": str(output_path),
        "included_files": ["manifest.json", "support-snapshot.json"],
        "warning_count": 1,
        "warnings": ["operance-tray.service logs unavailable"],
        "redacted": True,
    }
    calls: list[Path | None] = []

    monkeypatch.setattr(
        "operance.cli.write_support_bundle_artifact",
        lambda *, output_path=None, env=None, redact=True: calls.append(output_path) or result,
    )

    exit_code = main(
        [
            "--support-bundle",
            "--support-bundle-out",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == result
    assert calls == [output_path]


def test_cli_support_bundle_out_requires_support_bundle(capsys, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--support-bundle-out", str(tmp_path / "bundle.tar.gz")])

    captured = capsys.readouterr()
    assert "--support-bundle-out requires --support-bundle" in captured.err


def test_cli_setup_snapshot_prints_structured_setup_status(capsys) -> None:
    exit_code = main(["--setup-snapshot"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "summary_status" in payload
    assert "ready_for_local_runtime" in payload
    assert "ready_for_mvp" in payload
    assert "next_steps" in payload
    assert "recommended_commands" in payload
    assert "steps" in payload


def test_cli_setup_actions_prints_structured_actions(capsys) -> None:
    exit_code = main(["--setup-actions"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "summary_status" in payload
    assert "next_steps" in payload
    assert "actions" in payload
    assert payload["actions"]
    assert payload["actions"][0]["action_id"] == "bootstrap_dev_env"


def test_cli_setup_actions_includes_unavailable_reasons(monkeypatch, capsys) -> None:
    class _FakeAction:
        def to_dict(self) -> dict[str, object]:
            return {
                "action_id": "install_wakeword_model_asset",
                "available": False,
                "command": "./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx",
                "label": "Install wake-word model asset",
                "recommended": False,
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
                "unavailable_reason": "Blocked by: Wake-word model source.",
            }

    class _FakeSnapshot:
        summary_status = "partial"
        blocked_recommendations: list[dict[str, object]] = []
        next_steps: list[dict[str, object]] = []
        actions = [_FakeAction()]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())

    exit_code = main(["--setup-actions"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "actions": [
            {
                "action_id": "install_wakeword_model_asset",
                "available": False,
                "command": "./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx",
                "label": "Install wake-word model asset",
                "recommended": False,
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
                "unavailable_reason": "Blocked by: Wake-word model source.",
            }
        ],
        "blocked_recommendations": [],
        "next_steps": [],
        "summary_status": "partial",
    }


def test_cli_voice_asset_paths_prints_existing_and_preferred_locations(monkeypatch, capsys, tmp_path) -> None:
    wakeword_path = tmp_path / "wakeword" / "operance.onnx"
    tts_model_path = tmp_path / "tts" / "kokoro.onnx"
    tts_voices_path = tmp_path / "tts" / "voices.bin"
    wakeword_source_path = tmp_path / "sources" / "operance.onnx"
    tts_model_source_path = tmp_path / "sources" / "kokoro.onnx"
    tts_voices_source_path = tmp_path / "sources" / "voices.bin"
    wakeword_source_path.parent.mkdir(parents=True)
    wakeword_source_path.write_bytes(b"model")
    tts_model_source_path.write_bytes(b"model")
    tts_voices_source_path.write_bytes(b"voices")

    monkeypatch.setattr("operance.cli.wakeword_model_candidate_paths", lambda env=None: [wakeword_path])
    monkeypatch.setattr("operance.cli.tts_model_candidate_paths", lambda env=None: [tts_model_path])
    monkeypatch.setattr("operance.cli.tts_voices_candidate_paths", lambda env=None: [tts_voices_path])
    monkeypatch.setattr("operance.cli.find_existing_wakeword_model_path", lambda env=None: wakeword_path)
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: tts_voices_path)
    monkeypatch.setenv("OPERANCE_WAKEWORD_MODEL_SOURCE", str(wakeword_source_path))
    monkeypatch.setenv("OPERANCE_TTS_MODEL_SOURCE", str(tts_model_source_path))
    monkeypatch.setenv("OPERANCE_TTS_VOICES_SOURCE", str(tts_voices_source_path))

    exit_code = main(["--voice-asset-paths"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "install_commands": {
            "tts_assets": f"./scripts/install_tts_assets.sh --model {tts_model_source_path} --voices {tts_voices_source_path}",
            "wakeword_model": f"./scripts/install_wakeword_model_asset.sh --source {wakeword_source_path}",
        },
        "tts_model": {
            "candidate_paths": [str(tts_model_path)],
            "existing_path": None,
            "preferred_path": str(tts_model_path),
            "set_source_example": "export OPERANCE_TTS_MODEL_SOURCE=/path/to/kokoro.onnx",
            "source_env_var": "OPERANCE_TTS_MODEL_SOURCE",
            "source_path": str(tts_model_source_path),
            "source_status": "ok",
            "status": "warn",
        },
        "tts_voices": {
            "candidate_paths": [str(tts_voices_path)],
            "existing_path": str(tts_voices_path),
            "preferred_path": str(tts_voices_path),
            "set_source_example": "export OPERANCE_TTS_VOICES_SOURCE=/path/to/voices.bin",
            "source_env_var": "OPERANCE_TTS_VOICES_SOURCE",
            "source_path": str(tts_voices_source_path),
            "source_status": "ok",
            "status": "ok",
        },
        "wakeword_model": {
            "candidate_paths": [str(wakeword_path)],
            "existing_path": str(wakeword_path),
            "preferred_path": str(wakeword_path),
            "set_source_example": "export OPERANCE_WAKEWORD_MODEL_SOURCE=/path/to/operance.onnx",
            "source_env_var": "OPERANCE_WAKEWORD_MODEL_SOURCE",
            "source_path": str(wakeword_source_path),
            "source_status": "ok",
            "status": "ok",
        },
    }


def test_cli_voice_asset_paths_reports_source_env_vars_when_sources_are_missing(monkeypatch, capsys, tmp_path) -> None:
    wakeword_path = tmp_path / "wakeword" / "operance.onnx"
    tts_model_path = tmp_path / "tts" / "kokoro.onnx"
    tts_voices_path = tmp_path / "tts" / "voices.bin"

    monkeypatch.setattr("operance.cli.wakeword_model_candidate_paths", lambda env=None: [wakeword_path])
    monkeypatch.setattr("operance.cli.tts_model_candidate_paths", lambda env=None: [tts_model_path])
    monkeypatch.setattr("operance.cli.tts_voices_candidate_paths", lambda env=None: [tts_voices_path])
    monkeypatch.setattr("operance.cli.find_existing_wakeword_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: None)

    exit_code = main(["--voice-asset-paths"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["wakeword_model"]["source_env_var"] == "OPERANCE_WAKEWORD_MODEL_SOURCE"
    assert payload["wakeword_model"]["set_source_example"] == "export OPERANCE_WAKEWORD_MODEL_SOURCE=/path/to/operance.onnx"
    assert payload["tts_model"]["source_env_var"] == "OPERANCE_TTS_MODEL_SOURCE"
    assert payload["tts_model"]["set_source_example"] == "export OPERANCE_TTS_MODEL_SOURCE=/path/to/kokoro.onnx"
    assert payload["tts_voices"]["source_env_var"] == "OPERANCE_TTS_VOICES_SOURCE"
    assert payload["tts_voices"]["set_source_example"] == "export OPERANCE_TTS_VOICES_SOURCE=/path/to/voices.bin"


def test_cli_voice_loop_config_prints_effective_repo_local_config(monkeypatch, capsys) -> None:
    class _FakeVoiceLoopConfigSnapshot:
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
                "selected_args_file": "/repo/.operance/voice-loop.args",
            }

    monkeypatch.setattr("operance.cli.build_voice_loop_config_snapshot", lambda env=None: _FakeVoiceLoopConfigSnapshot())

    exit_code = main(["--voice-loop-config"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["launcher_mode"] == "repo_local"
    assert payload["selected_args_file"] == "/repo/.operance/voice-loop.args"
    assert payload["effective"]["wakeword_threshold"] == 0.95
    assert payload["effective"]["wakeword_threshold_source"] == "args_file"


def test_cli_voice_loop_status_prints_runtime_snapshot(monkeypatch, capsys) -> None:
    class _FakeVoiceLoopRuntimeStatusSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "awaiting_confirmation": False,
                "completed_commands": 2,
                "daemon_state": "IDLE",
                "heartbeat_age_seconds": 1.2,
                "heartbeat_fresh": True,
                "heartbeat_timeout_seconds": 30.0,
                "last_response_status": "success",
                "last_response_text": "Volume is 30%",
                "last_transcript_final": True,
                "last_transcript_text": "what is the volume",
                "last_wake_confidence": 0.91,
                "last_wake_phrase": "operance",
                "loop_state": "waiting_for_wake",
                "message": "Voice-loop runtime heartbeat is fresh.",
                "processed_frames": 42,
                "started_at": "2026-04-30T01:00:00+00:00",
                "status": "ok",
                "status_file_exists": True,
                "status_file_path": "/repo/.operance/voice-loop-status.json",
                "stopped_at": None,
                "stopped_reason": None,
                "updated_at": "2026-04-30T01:00:01+00:00",
                "wake_detections": 2,
            }

    monkeypatch.setattr(
        "operance.cli.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )

    exit_code = main(["--voice-loop-status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["loop_state"] == "waiting_for_wake"
    assert payload["status_file_path"] == "/repo/.operance/voice-loop-status.json"
    assert payload["completed_commands"] == 2


def test_cli_voice_loop_service_status_prints_combined_snapshot(monkeypatch, capsys) -> None:
    class _FakeVoiceLoopServiceSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "status": "warn",
                "message": "Voice-loop user service is active but the runtime heartbeat is stale.",
                "recommended_command": "./scripts/control_systemd_user_services.sh restart --voice-loop",
                "service_installed": True,
                "service_installed_detail": "/repo/.config/systemd/user/operance-voice-loop.service",
                "service_enabled": True,
                "service_enabled_detail": "enabled",
                "service_active": True,
                "service_active_detail": "active",
                "config": {"selected_args_file": "/repo/.operance/voice-loop.args"},
                "runtime": {"status_file_path": "/repo/.operance/voice-loop-status.json", "heartbeat_fresh": False},
            }

    monkeypatch.setattr(
        "operance.cli.build_voice_loop_service_snapshot",
        lambda env=None: _FakeVoiceLoopServiceSnapshot(),
    )

    exit_code = main(["--voice-loop-service-status"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warn"
    assert payload["recommended_command"] == "./scripts/control_systemd_user_services.sh restart --voice-loop"
    assert payload["config"]["selected_args_file"] == "/repo/.operance/voice-loop.args"
    assert payload["runtime"]["heartbeat_fresh"] is False


def test_cli_setup_run_action_prints_dry_run_result(capsys) -> None:
    exit_code = main(["--setup-run-action", "install_ui_backend", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "install_ui_backend"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_recommended_reports_blocked_recommendations(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        summary_status = "partial"
        blocked_recommendations = [
            {
                "label": "Install wake-word model asset",
                "reason": "Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
            }
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr("operance.cli.run_setup_actions", lambda *args, **kwargs: [])

    exit_code = main(["--setup-run-recommended", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "blocked_recommendations": [
            {
                "label": "Install wake-word model asset",
                "reason": "Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
            }
        ],
        "message": "No recommended setup actions are currently runnable.",
        "requested": "recommended",
        "results": [],
    }


def test_cli_setup_run_recommended_reports_next_steps_when_no_changes_are_needed(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        blocked_recommendations: list[dict[str, object]] = []
        next_steps = [
            {
                "label": "Launch Operance MVP",
                "command": "./scripts/run_mvp.sh",
            },
            {
                "label": "Run click-to-talk probe",
                "command": "./scripts/run_click_to_talk.sh",
            },
            {
                "label": "Run tray app",
                "command": "./scripts/run_tray_app.sh",
            },
            {
                "label": "Show runnable commands",
                "command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
            },
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr("operance.cli.run_setup_actions", lambda *args, **kwargs: [])

    exit_code = main(["--setup-run-recommended", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "message": "No setup changes are needed right now. Try one of the next steps.",
        "next_steps": [
            {
                "label": "Launch Operance MVP",
                "command": "./scripts/run_mvp.sh",
            },
            {
                "label": "Run click-to-talk probe",
                "command": "./scripts/run_click_to_talk.sh",
            },
            {
                "label": "Run tray app",
                "command": "./scripts/run_tray_app.sh",
            },
            {
                "label": "Show runnable commands",
                "command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
            },
        ],
        "requested": "recommended",
        "results": [],
    }


def test_cli_setup_run_action_supports_voice_loop_service(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "install_voice_loop_service",
                    "command": "./scripts/install_voice_loop_user_service.sh",
                    "dry_run": True,
                    "label": "Install voice-loop user service",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "install_voice_loop_service", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "install_voice_loop_service"
    assert payload["command"] == "./scripts/install_voice_loop_user_service.sh"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_action_returns_nonzero_when_action_fails(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "install_voice_loop_service",
                    "command": "./scripts/install_voice_loop_user_service.sh",
                    "dry_run": False,
                    "label": "Install voice-loop user service",
                    "returncode": 1,
                    "status": "failed",
                    "stderr": "permission denied",
                    "stdout": "",
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "install_voice_loop_service"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["returncode"] == 1


def test_cli_setup_run_action_supports_voice_loop_user_config(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "install_voice_loop_user_config",
                    "command": "./scripts/install_voice_loop_user_config.sh",
                    "dry_run": True,
                    "label": "Seed voice-loop user config",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "install_voice_loop_user_config", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "install_voice_loop_user_config"
    assert payload["command"] == "./scripts/install_voice_loop_user_config.sh"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_action_supports_voice_diagnostics(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "probe_stt_path",
                    "command": "python3 -m operance.cli --stt-probe-frames 12",
                    "dry_run": True,
                    "label": "Probe speech-to-text path",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "probe_stt_path", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "probe_stt_path"
    assert payload["command"] == "python3 -m operance.cli --stt-probe-frames 12"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_action_supports_service_control(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "enable_voice_loop_service",
                    "command": "./scripts/control_systemd_user_services.sh enable --voice-loop",
                    "dry_run": True,
                    "label": "Enable voice-loop user service",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "enable_voice_loop_service", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "enable_voice_loop_service"
    assert payload["command"] == "./scripts/control_systemd_user_services.sh enable --voice-loop"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_action_supports_package_build(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "build_rpm_package_artifact",
                    "command": "./scripts/build_package_artifacts.sh --rpm",
                    "dry_run": True,
                    "label": "Build RPM package artifact",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-action", "build_rpm_package_artifact", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "build_rpm_package_artifact"
    assert payload["command"] == "./scripts/build_package_artifacts.sh --rpm"
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True


def test_cli_setup_run_recommended_prints_result_list(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "install_local_app",
                    "command": "./scripts/install_local_linux_app.sh",
                    "dry_run": True,
                    "label": "Install local Linux app",
                    "returncode": None,
                    "status": "planned",
                    "stderr": None,
                    "stdout": None,
                }
            )
        ],
    )

    exit_code = main(["--setup-run-recommended", "--setup-dry-run"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "requested": "recommended",
        "results": [
            {
                "action_id": "install_local_app",
                "command": "./scripts/install_local_linux_app.sh",
                "dry_run": True,
                "label": "Install local Linux app",
                "returncode": None,
                "status": "planned",
                "stderr": None,
                "stdout": None,
            }
        ],
    }


def test_cli_setup_run_recommended_returns_nonzero_when_any_action_fails(monkeypatch, capsys) -> None:
    class _FakeSetupRunResult:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def to_dict(self) -> dict[str, object]:
            return dict(self._payload)

    class _FakeSnapshot:
        blocked_recommendations = []

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr(
        "operance.cli.run_setup_actions",
        lambda *args, **kwargs: [
            _FakeSetupRunResult(
                {
                    "action_id": "enable_tray_service",
                    "command": "./scripts/control_systemd_user_services.sh enable",
                    "dry_run": False,
                    "label": "Enable tray user service",
                    "returncode": 0,
                    "status": "success",
                    "stderr": "",
                    "stdout": "ok",
                }
            ),
            _FakeSetupRunResult(
                {
                    "action_id": "install_voice_loop_user_config",
                    "command": "./scripts/install_voice_loop_user_config.sh",
                    "dry_run": False,
                    "label": "Seed voice-loop user config",
                    "returncode": 1,
                    "status": "failed",
                    "stderr": "read-only file system",
                    "stdout": "",
                }
            ),
        ],
    )

    exit_code = main(["--setup-run-recommended"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["requested"] == "recommended"
    assert payload["results"][0]["status"] == "success"
    assert payload["results"][1]["status"] == "failed"


def test_cli_setup_app_prints_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.run_setup_app",
        lambda: (_ for _ in ()).throw(ValueError("PySide6 is not installed")),
    )

    exit_code = main(["--setup-app"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "PySide6 is not installed",
        "status": "failed",
    }


def test_cli_tts_probe_prints_synthesized_metadata(monkeypatch, tmp_path: Path, capsys) -> None:
    from operance.tts import SynthesizedAudio

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.5, -0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text("fake-audio", encoding="utf-8")

    monkeypatch.setattr(
        "operance.cli.build_default_speech_synthesizer",
        lambda **kwargs: FakeSpeechSynthesizer(),
    )

    output_path = tmp_path / "tts.wav"
    exit_code = main(
        [
            "--tts-probe-text",
            "Hello from Operance",
            "--tts-model",
            "model.onnx",
            "--tts-voices",
            "voices.bin",
            "--tts-output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["text"] == "Hello from Operance"
    assert payload["voice"] == "af_sarah"
    assert payload["sample_rate_hz"] == 24000
    assert payload["sample_count"] == 3
    assert payload["output_path"] == str(output_path)
    assert output_path.read_text(encoding="utf-8") == "fake-audio"


def test_cli_tts_probe_can_play_saved_output(monkeypatch, tmp_path: Path, capsys) -> None:
    from operance.tts import SynthesizedAudio

    played_paths: list[Path] = []

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.5, -0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text("fake-audio", encoding="utf-8")

    class FakePlaybackSink:
        def play_file(self, path: Path) -> None:
            played_paths.append(path)

    monkeypatch.setattr(
        "operance.cli.build_default_speech_synthesizer",
        lambda **kwargs: FakeSpeechSynthesizer(),
    )
    monkeypatch.setattr("operance.cli.build_default_audio_playback_sink", lambda: FakePlaybackSink())

    output_path = tmp_path / "tts.wav"
    exit_code = main(
        [
            "--tts-probe-text",
            "Hello from Operance",
            "--tts-model",
            "model.onnx",
            "--tts-voices",
            "voices.bin",
            "--tts-output",
            str(output_path),
            "--tts-play",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["played_output"] is True
    assert played_paths == [output_path]
    assert output_path.read_text(encoding="utf-8") == "fake-audio"


def test_cli_tts_probe_uses_env_default_asset_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    from operance.tts import SynthesizedAudio

    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "kokoro.onnx"
    voices_path = tmp_path / "voices.bin"
    model_path.write_text("model", encoding="utf-8")
    voices_path.write_text("voices", encoding="utf-8")

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.5, -0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text("fake-audio", encoding="utf-8")

    def fake_build_default_speech_synthesizer(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeSpeechSynthesizer()

    monkeypatch.setenv("OPERANCE_TTS_MODEL", str(model_path))
    monkeypatch.setenv("OPERANCE_TTS_VOICES", str(voices_path))
    monkeypatch.setattr(
        "operance.cli.build_default_speech_synthesizer",
        fake_build_default_speech_synthesizer,
    )

    output_path = tmp_path / "tts.wav"
    exit_code = main(
        [
            "--tts-probe-text",
            "Hello from Operance",
            "--tts-output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_kwargs["model_path"] == str(model_path)
    assert captured_kwargs["voices_path"] == str(voices_path)
    assert payload["output_path"] == str(output_path)


def test_cli_audio_list_devices_prints_capture_devices(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())

    exit_code = main(["--audio-list-devices"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["devices"] == [
        {
            "backend": "pactl",
            "device_id": "42",
            "is_default": True,
            "name": "alsa_input.usb-mic",
        }
    ]


def test_cli_audio_capture_frames_prints_frame_metadata(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())

    exit_code = main(["--audio-capture-frames", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["captured_frames"] == 2
    assert len(payload["frames"]) == 2
    assert payload["frames"][0]["sample_count"] == 1600
    assert payload["frames"][0]["source"] == "alsa_input.usb-mic"
    assert payload["frames"][0]["sample_format"] == "s16le"
    assert payload["frames"][0]["byte_count"] == 3200
    assert "pcm_s16le" not in payload["frames"][0]


def test_cli_wakeword_probe_prints_detections(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeWakeWordDetector())

    exit_code = main(["--wakeword-probe-frames", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 2
    assert payload["detections"] == [
        {
            "confidence": 0.91,
            "detection_id": payload["detections"][0]["detection_id"],
            "frame_index": 2,
            "phrase": "operance",
            "timestamp": payload["detections"][0]["timestamp"],
        }
    ]


def test_cli_wakeword_probe_passes_model_path(monkeypatch, tmp_path, capsys) -> None:
    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)

    exit_code = main(["--wakeword-probe-frames", "2", "--wakeword-model", str(model_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 2
    assert captured_kwargs["model_path"] == str(model_path)


def test_cli_wakeword_probe_uses_auto_model_path(monkeypatch, tmp_path, capsys) -> None:
    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.find_existing_wakeword_model_path", lambda env=None: model_path)
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)

    exit_code = main(["--wakeword-probe-frames", "2", "--wakeword-model", "auto"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 2
    assert captured_kwargs["model_path"] == str(model_path)


def test_cli_wakeword_probe_can_use_voice_loop_config(monkeypatch, tmp_path, capsys) -> None:
    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    class _FakeVoiceLoopConfigSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "configured_args": ["--wakeword-threshold", "0.95", "--wakeword-model", "auto"],
                "effective": {
                    "passthrough_args": [],
                    "voice_loop_max_commands": None,
                    "voice_loop_max_commands_source": "default",
                    "voice_loop_max_frames": None,
                    "voice_loop_max_frames_source": "default",
                    "wakeword_auto_model_path": str(model_path),
                    "wakeword_mode": "auto_model",
                    "wakeword_model": "auto",
                    "wakeword_model_source": "args_file",
                    "wakeword_threshold": 0.95,
                    "wakeword_threshold_source": "args_file",
                },
                "explicit_args_file": None,
                "launcher_mode": "repo_local",
                "search_paths": ["/repo/.operance/voice-loop.args"],
                "selected_args_file": "/repo/.operance/voice-loop.args",
            }

        @property
        def effective(self):
            class _Effective:
                wakeword_threshold = 0.95
                wakeword_model = "auto"
                wakeword_mode = "auto_model"

            return _Effective()

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_voice_loop_config_snapshot", lambda env=None: _FakeVoiceLoopConfigSnapshot())
    monkeypatch.setattr("operance.cli.find_existing_wakeword_model_path", lambda env=None: model_path)
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)

    exit_code = main(["--wakeword-probe-frames", "2", "--use-voice-loop-config"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_kwargs["threshold"] == 0.95
    assert captured_kwargs["model_path"] == str(model_path)
    assert payload["requested_voice_loop_config"] is True
    assert payload["using_voice_loop_config"] is True
    assert payload["voice_loop_config_status"] == "ok"
    assert payload["effective_wakeword_threshold"] == 0.95
    assert payload["effective_wakeword_model"] == "auto"


def test_cli_wakeword_probe_reports_missing_voice_loop_config_when_requested(monkeypatch, capsys) -> None:
    captured_kwargs: dict[str, object] = {}

    class _FakeVoiceLoopConfigSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "configured_args": [],
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
                    "wakeword_threshold_source": "default",
                },
                "explicit_args_file": None,
                "launcher_mode": "repo_local",
                "search_paths": ["/repo/.operance/voice-loop.args"],
                "selected_args_file": None,
            }

        @property
        def effective(self):
            class _Effective:
                wakeword_threshold = 0.6
                wakeword_model = None
                wakeword_mode = "energy_fallback"

            return _Effective()

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_voice_loop_config_snapshot", lambda env=None: _FakeVoiceLoopConfigSnapshot())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)

    exit_code = main(["--wakeword-probe-frames", "2", "--use-voice-loop-config"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_kwargs["threshold"] == 0.6
    assert payload["requested_voice_loop_config"] is True
    assert payload["using_voice_loop_config"] is False
    assert payload["voice_loop_config_status"] == "warn"
    assert payload["voice_loop_config_message"] == (
        "Requested voice-loop config, but no args file was found; using defaults."
    )
    assert payload["voice_loop_config"]["selected_args_file"] is None


def test_cli_wakeword_calibration_prints_suggested_threshold(monkeypatch, capsys) -> None:
    captured_args: dict[str, object] = {}

    def fake_run_wakeword_calibration(source, *, max_frames: int, base_threshold: float) -> dict[str, object]:
        captured_args["max_frames"] = max_frames
        captured_args["base_threshold"] = base_threshold
        return {
            "ambient_detector_confidence": 0.22,
            "processed_frames": max_frames,
            "ambient_peak_confidence": 0.22,
            "base_threshold": base_threshold,
            "suggested_threshold": base_threshold,
        }

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.run_wakeword_calibration", fake_run_wakeword_calibration)

    exit_code = main(["--wakeword-calibrate-frames", "3"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "ambient_detector_confidence": 0.22,
        "ambient_peak_confidence": 0.22,
        "base_threshold": 0.6,
        "processed_frames": 3,
        "suggested_threshold": 0.6,
        "suggested_voice_loop_config_command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.6",
    }
    assert captured_args == {
        "base_threshold": 0.6,
        "max_frames": 3,
    }


def test_cli_wakeword_calibration_can_apply_suggested_threshold(monkeypatch, capsys) -> None:
    expected_script = Path(__file__).resolve().parents[2] / "scripts" / "update_voice_loop_user_config.sh"

    def fake_run_wakeword_calibration(source, *, max_frames: int, base_threshold: float) -> dict[str, object]:
        return {
            "ambient_detector_confidence": 0.22,
            "processed_frames": max_frames,
            "ambient_peak_confidence": 0.22,
            "base_threshold": base_threshold,
            "suggested_threshold": 0.83,
        }

    def fake_subprocess_run(argv, **kwargs):
        assert argv == [
            "bash",
            str(expected_script),
            "--wakeword-threshold",
            "0.83",
        ]
        return subprocess.CompletedProcess(argv, 0, stdout="+ write /home/test/.config/operance/voice-loop.args\n", stderr="")

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.run_wakeword_calibration", fake_run_wakeword_calibration)
    monkeypatch.setattr("operance.cli.subprocess.run", fake_subprocess_run)

    exit_code = main(["--wakeword-calibrate-frames", "3", "--apply-suggested-threshold"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["suggested_threshold"] == 0.83
    assert payload["voice_loop_config_update"] == {
        "command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.83",
        "returncode": 0,
        "status": "ok",
        "stderr": "",
        "stdout": "+ write /home/test/.config/operance/voice-loop.args\n",
    }


def test_cli_wakeword_calibration_fails_when_threshold_update_fails(monkeypatch, capsys) -> None:
    def fake_run_wakeword_calibration(source, *, max_frames: int, base_threshold: float) -> dict[str, object]:
        return {
            "ambient_detector_confidence": 0.22,
            "processed_frames": max_frames,
            "ambient_peak_confidence": 0.22,
            "base_threshold": base_threshold,
            "suggested_threshold": 0.91,
        }

    def fake_subprocess_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="permission denied\n")

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.run_wakeword_calibration", fake_run_wakeword_calibration)
    monkeypatch.setattr("operance.cli.subprocess.run", fake_subprocess_run)

    exit_code = main(["--wakeword-calibrate-frames", "3", "--apply-suggested-threshold"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["voice_loop_config_update"] == {
        "command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.91",
        "returncode": 1,
        "status": "failed",
        "stderr": "permission denied\n",
        "stdout": "",
    }


def test_cli_apply_suggested_threshold_requires_wakeword_calibration(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--apply-suggested-threshold"])

    captured = capsys.readouterr()

    assert "--apply-suggested-threshold requires --wakeword-calibrate-frames" in captured.err


def test_cli_wakeword_idle_evaluation_prints_false_activation_summary(monkeypatch, capsys) -> None:
    captured_args: dict[str, object] = {}

    def fake_run_wakeword_idle_evaluation(source, detector, *, max_frames: int) -> dict[str, object]:
        captured_args["max_frames"] = max_frames
        return {
            "processed_frames": max_frames,
            "detection_count": 1,
            "idle_false_activation_rate": 0.25,
            "detections": [],
        }

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeWakeWordDetector())
    monkeypatch.setattr("operance.cli.run_wakeword_idle_evaluation", fake_run_wakeword_idle_evaluation)

    exit_code = main(["--wakeword-eval-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "detection_count": 1,
        "detections": [],
        "idle_false_activation_rate": 0.25,
        "processed_frames": 4,
    }
    assert captured_args == {"max_frames": 4}


def test_cli_voice_self_test_prints_composite_summary(monkeypatch, tmp_path, capsys) -> None:
    model_path = tmp_path / "kokoro.onnx"
    voices_path = tmp_path / "voices.bin"
    model_path.write_bytes(b"model")
    voices_path.write_bytes(b"voices")

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeWakeWordDetector())
    monkeypatch.setattr(
        "operance.cli.run_wakeword_idle_evaluation",
        lambda source, detector, *, max_frames: {
            "processed_frames": max_frames,
            "detection_count": 0,
            "idle_false_activation_rate": 0.0,
            "detections": [],
        },
    )
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())
    monkeypatch.setattr(
        "operance.cli.run_stt_probe",
        lambda source, transcriber, *, max_frames: {
            "processed_frames": max_frames,
            "segments": [{"text": "open firefox"}],
        },
    )
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: model_path)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: voices_path)
    monkeypatch.setattr("operance.cli.build_default_speech_synthesizer", lambda **kwargs: object())
    monkeypatch.setattr(
        "operance.cli.run_tts_probe",
        lambda synthesizer, text, *, output_path=None: {
            "text": text,
            "voice": "af_sarah",
            "sample_rate_hz": 24000,
            "sample_count": 100,
            "duration_seconds": 0.2,
            "output_path": None,
        },
    )

    exit_code = main(["--voice-self-test"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary_status"] == "ok"
    assert payload["capture"]["status"] == "ok"
    assert payload["capture"]["captured_frames"] == 2
    assert payload["wakeword_idle_eval"]["status"] == "ok"
    assert payload["stt"]["status"] == "ok"
    assert payload["tts"]["status"] == "ok"


def test_cli_voice_self_test_includes_voice_loop_config_context_when_requested(monkeypatch, capsys) -> None:
    class _FakeVoiceLoopConfigSnapshot:
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
                "search_paths": ["/repo/.operance/voice-loop.args"],
                "selected_args_file": "/repo/.operance/voice-loop.args",
            }

        @property
        def effective(self):
            class _Effective:
                wakeword_threshold = 0.95
                wakeword_model = None
                wakeword_mode = "energy_fallback"

            return _Effective()

    captured_kwargs: dict[str, object] = {}

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)
    monkeypatch.setattr(
        "operance.cli.run_wakeword_idle_evaluation",
        lambda source, detector, *, max_frames: {
            "processed_frames": max_frames,
            "detection_count": 0,
            "idle_false_activation_rate": 0.0,
            "detections": [],
        },
    )
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.build_voice_loop_config_snapshot", lambda env=None: _FakeVoiceLoopConfigSnapshot())
    monkeypatch.setattr(
        "operance.cli._build_voice_asset_paths_payload",
        lambda env: {
            "tts_model": {"candidate_paths": ["/tmp/kokoro.onnx"], "existing_path": None, "preferred_path": "/tmp/kokoro.onnx", "status": "warn"},
            "tts_voices": {"candidate_paths": ["/tmp/voices.bin"], "existing_path": None, "preferred_path": "/tmp/voices.bin", "status": "warn"},
            "wakeword_model": {"candidate_paths": ["/tmp/operance.onnx"], "existing_path": None, "preferred_path": "/tmp/operance.onnx", "status": "warn"},
        },
    )

    exit_code = main(["--voice-self-test", "--use-voice-loop-config"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_kwargs["threshold"] == 0.95
    assert payload["requested_voice_loop_config"] is True
    assert payload["using_voice_loop_config"] is True
    assert payload["voice_loop_config_status"] == "ok"
    assert payload["effective_wakeword_threshold"] == 0.95
    assert payload["voice_loop_config"]["selected_args_file"] == "/repo/.operance/voice-loop.args"


def test_cli_voice_self_test_skips_optional_backends(monkeypatch, capsys) -> None:
    asset_paths_payload = {
        "tts_model": {
            "candidate_paths": ["/tmp/kokoro.onnx"],
            "existing_path": None,
            "preferred_path": "/tmp/kokoro.onnx",
            "status": "warn",
        },
        "tts_voices": {
            "candidate_paths": ["/tmp/voices.bin"],
            "existing_path": None,
            "preferred_path": "/tmp/voices.bin",
            "status": "warn",
        },
        "wakeword_model": {
            "candidate_paths": ["/tmp/operance.onnx"],
            "existing_path": None,
            "preferred_path": "/tmp/operance.onnx",
            "status": "warn",
        },
    }

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeWakeWordDetector())
    monkeypatch.setattr(
        "operance.cli.run_wakeword_idle_evaluation",
        lambda source, detector, *, max_frames: {
            "processed_frames": max_frames,
            "detection_count": 0,
            "idle_false_activation_rate": 0.0,
            "detections": [],
        },
    )
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli._build_voice_asset_paths_payload", lambda env: asset_paths_payload)

    exit_code = main(["--voice-self-test"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary_status"] == "partial"
    assert payload["capture"]["status"] == "ok"
    assert payload["wakeword_idle_eval"]["status"] == "ok"
    assert payload["stt"] == {
        "message": "moonshine-voice is not installed",
        "status": "skipped",
    }
    assert payload["tts"] == {
        "asset_paths": {
            "tts_model": asset_paths_payload["tts_model"],
            "tts_voices": asset_paths_payload["tts_voices"],
        },
        "message": "TTS model assets are not available",
        "recommended_command": "python3 -m operance.cli --voice-asset-paths",
        "status": "skipped",
    }


def test_cli_voice_self_test_warns_on_idle_false_activations(monkeypatch, capsys) -> None:
    asset_paths_payload = {
        "tts_model": {
            "candidate_paths": ["/tmp/kokoro.onnx"],
            "existing_path": None,
            "preferred_path": "/tmp/kokoro.onnx",
            "status": "warn",
        },
        "tts_voices": {
            "candidate_paths": ["/tmp/voices.bin"],
            "existing_path": None,
            "preferred_path": "/tmp/voices.bin",
            "status": "warn",
        },
        "wakeword_model": {
            "candidate_paths": ["/tmp/operance.onnx"],
            "existing_path": None,
            "preferred_path": "/tmp/operance.onnx",
            "status": "warn",
        },
    }

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeWakeWordDetector())
    monkeypatch.setattr(
        "operance.cli.run_wakeword_idle_evaluation",
        lambda source, detector, *, max_frames: {
            "activation_frames": 2,
            "processed_frames": max_frames,
            "detection_count": 2,
            "idle_false_activation_rate": 0.04,
            "detections": [],
            "current_threshold": 0.6,
            "max_detection_confidence": 0.862,
            "suggested_threshold": 0.95,
            "suggested_voice_loop_config_command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.95",
        },
    )
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )
    monkeypatch.setattr("operance.cli.find_existing_tts_model_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli.find_existing_tts_voices_path", lambda env=None: None)
    monkeypatch.setattr("operance.cli._build_voice_asset_paths_payload", lambda env: asset_paths_payload)

    exit_code = main(["--voice-self-test"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary_status"] == "partial"
    assert payload["wakeword_idle_eval"] == {
        "activation_frames": 2,
        "current_threshold": 0.6,
        "detection_count": 2,
        "detections": [],
        "idle_false_activation_rate": 0.04,
        "max_detection_confidence": 0.862,
        "message": "Idle false activations detected during wake-word evaluation.",
        "processed_frames": 50,
        "status": "warn",
        "suggested_threshold": 0.95,
        "suggested_voice_loop_config_command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.95",
    }
    assert payload["tts"] == {
        "asset_paths": {
            "tts_model": asset_paths_payload["tts_model"],
            "tts_voices": asset_paths_payload["tts_voices"],
        },
        "message": "TTS model assets are not available",
        "recommended_command": "python3 -m operance.cli --voice-asset-paths",
        "status": "skipped",
    }


def test_cli_stt_probe_prints_segments(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())

    exit_code = main(["--stt-probe-frames", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 2
    assert payload["segments"] == [
        {
            "confidence": 0.93,
            "frame_index": 2,
            "is_final": True,
            "segment_id": payload["segments"][0]["segment_id"],
            "text": "open firefox",
            "timestamp": payload["segments"][0]["timestamp"],
        }
    ]


def test_cli_stt_probe_prints_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )

    exit_code = main(["--stt-probe-frames", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "moonshine-voice is not installed",
        "status": "failed",
    }


def test_cli_voice_session_prints_daemon_results(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeVoiceSessionWakeWordDetector())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())

    exit_code = main(["--voice-session-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 4
    assert payload["wake_detections"][0]["frame_index"] == 2
    assert payload["wake_detections"][0]["phrase"] == "operance"
    assert payload["transcripts"] == [
        {
            "confidence": 0.93,
            "frame_index": 4,
            "is_final": True,
            "segment_id": payload["transcripts"][0]["segment_id"],
            "text": "open firefox",
            "timestamp": payload["transcripts"][0]["timestamp"],
        }
    ]
    assert payload["responses"] == [
        {
            "plan_id": payload["responses"][0]["plan_id"],
            "status": "success",
            "text": "Launched firefox",
        }
    ]
    assert payload["completed_commands"] == 1
    assert payload["final_state"] == "IDLE"


def test_cli_click_to_talk_prints_daemon_results(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())

    exit_code = main(["--click-to-talk-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 2
    assert payload["transcripts"] == [
        {
            "confidence": 0.93,
            "frame_index": 2,
            "is_final": True,
            "segment_id": payload["transcripts"][0]["segment_id"],
            "text": "open firefox",
            "timestamp": payload["transcripts"][0]["timestamp"],
        }
    ]
    assert payload["response"] == {
        "simulated": True,
        "status": "success",
        "text": "Launched firefox",
    }
    assert payload["completed_commands"] == 1
    assert payload["final_state"] == "IDLE"


def test_cli_click_to_talk_uses_default_frame_limit(monkeypatch, capsys) -> None:
    captured_max_frames: dict[str, int] = {}

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: object())

    def fake_run_manual_voice_session(daemon, source, build_transcriber, *, max_frames: int) -> dict[str, object]:
        captured_max_frames["value"] = max_frames
        return {
            "processed_frames": 0,
            "transcripts": [],
            "response": {
                "status": "no_transcript",
                "text": "I did not catch a command.",
            },
            "completed_commands": 0,
            "final_state": "IDLE",
            "stopped_reason": "frame_limit",
        }

    monkeypatch.setattr("operance.cli.run_manual_voice_session", fake_run_manual_voice_session)

    exit_code = main(["--click-to-talk"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_max_frames["value"] == 40
    assert payload["response"] == {
        "status": "no_transcript",
        "text": "I did not catch a command.",
    }


def test_cli_click_to_talk_rejects_mixed_default_and_explicit_flags(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--click-to-talk", "--click-to-talk-frames", "4"])

    captured = capsys.readouterr()

    assert "--click-to-talk and --click-to-talk-frames cannot be used together" in captured.err


def test_cli_click_to_talk_prints_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )

    exit_code = main(["--click-to-talk-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "moonshine-voice is not installed",
        "status": "failed",
    }


def test_cli_click_to_talk_prints_non_value_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.build_default_audio_capture_source",
        lambda device_name=None: (_ for _ in ()).throw(RuntimeError("microphone permission denied")),
    )

    exit_code = main(["--click-to-talk-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "microphone permission denied",
        "status": "failed",
    }


def test_cli_mvp_launch_prefers_tray_when_available(monkeypatch) -> None:
    class _FakeSnapshot:
        ready_for_mvp = True
        steps = [
            {
                "name": "tray_ui_available",
                "status": "ok",
            }
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr("operance.cli.run_tray_app", lambda env=None: 7)

    exit_code = main(["--mvp-launch"])

    assert exit_code == 7


def test_cli_mvp_launch_reports_existing_tray_service(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        ready_for_mvp = True
        steps = [
            {
                "name": "tray_user_service_active",
                "status": "ok",
            },
            {
                "name": "tray_ui_available",
                "status": "ok",
            },
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr(
        "operance.cli.run_tray_app",
        lambda env=None: (_ for _ in ()).throw(AssertionError("tray app should not launch twice")),
    )

    exit_code = main(["--mvp-launch"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "message": "Tray service is already active. Use the existing tray icon.",
        "runnable_commands_command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
        "service": "tray",
        "status": "already_running",
        "supported_commands_command": "python3 -m operance.cli --supported-commands",
    }


def test_cli_mvp_launch_reports_existing_manual_tray_instance(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        ready_for_mvp = True
        steps = [
            {
                "name": "tray_user_service_active",
                "status": "warn",
            },
            {
                "name": "tray_ui_available",
                "status": "ok",
            },
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr(
        "operance.cli.run_tray_app",
        lambda env=None: (_ for _ in ()).throw(
            ValueError("Operance tray is already running. Use the existing tray icon.")
        ),
    )

    exit_code = main(["--mvp-launch"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "message": "Operance tray is already running. Use the existing tray icon.",
        "runnable_commands_command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
        "service": "tray",
        "status": "already_running",
        "supported_commands_command": "python3 -m operance.cli --supported-commands",
    }


def test_cli_mvp_launch_falls_back_to_click_to_talk_when_tray_is_unavailable(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        ready_for_mvp = True
        steps = [
            {
                "name": "tray_ui_available",
                "status": "warn",
            }
        ]

    captured_max_frames: dict[str, int] = {}

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: object())

    def fake_run_manual_voice_session(daemon, source, build_transcriber, *, max_frames: int) -> dict[str, object]:
        captured_max_frames["value"] = max_frames
        return {
            "processed_frames": 0,
            "transcripts": [],
            "response": {
                "status": "no_transcript",
                "text": "I did not catch a command.",
            },
            "completed_commands": 0,
            "final_state": "IDLE",
            "stopped_reason": "frame_limit",
        }

    monkeypatch.setattr("operance.cli.run_manual_voice_session", fake_run_manual_voice_session)

    exit_code = main(["--mvp-launch"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured_max_frames["value"] == 40
    assert payload["response"] == {
        "status": "no_transcript",
        "text": "I did not catch a command.",
    }


def test_cli_mvp_launch_reports_setup_guidance_when_not_ready(monkeypatch, capsys) -> None:
    class _FakeSnapshot:
        summary_status = "partial"
        ready_for_local_runtime = True
        ready_for_mvp = False
        recommended_commands = ["./scripts/install_linux_dev.sh --voice"]
        next_steps: list[dict[str, object]] = []
        blocked_recommendations = [
            {
                "label": "Install wake-word model asset",
                "reason": "Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
            }
        ]

    monkeypatch.setattr("operance.cli.build_setup_snapshot", lambda: _FakeSnapshot())

    exit_code = main(["--mvp-launch"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "blocked_recommendations": [
            {
                "label": "Install wake-word model asset",
                "reason": "Set OPERANCE_WAKEWORD_MODEL_SOURCE or copy a model file to a candidate path before setup can stage it.",
                "suggested_command": "python3 -m operance.cli --voice-asset-paths",
            }
        ],
        "message": "MVP launch prerequisites are not ready.",
        "ready_for_local_runtime": True,
        "ready_for_mvp": False,
        "recommended_command": "python3 -m operance.cli --setup-run-recommended --setup-dry-run",
        "recommended_commands": ["./scripts/install_linux_dev.sh --voice"],
        "runnable_commands_command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
        "status": "blocked",
        "supported_commands_command": "python3 -m operance.cli --supported-commands",
        "summary_status": "partial",
    }


def test_cli_voice_session_passes_wakeword_model_path(monkeypatch, tmp_path, capsys) -> None:
    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeVoiceSessionWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())

    exit_code = main(["--voice-session-frames", "4", "--wakeword-model", str(model_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 4
    assert captured_kwargs["model_path"] == str(model_path)


def test_cli_voice_session_uses_auto_wakeword_model_path(monkeypatch, tmp_path, capsys) -> None:
    captured_kwargs: dict[str, object] = {}
    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    def build_detector(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeVoiceSessionWakeWordDetector()

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.find_existing_wakeword_model_path", lambda env=None: model_path)
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", build_detector)
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())

    exit_code = main(["--voice-session-frames", "4", "--wakeword-model", "auto"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["processed_frames"] == 4
    assert captured_kwargs["model_path"] == str(model_path)


def test_cli_voice_session_prints_backend_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeVoiceSessionWakeWordDetector())
    monkeypatch.setattr(
        "operance.cli.build_default_speech_transcriber",
        lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
    )

    exit_code = main(["--voice-session-frames", "4"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload == {
        "message": "moonshine-voice is not installed",
        "status": "failed",
    }


def test_cli_voice_session_can_emit_saved_tts_responses(monkeypatch, tmp_path, capsys) -> None:
    from operance.tts import SynthesizedAudio

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.5, -0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text("fake-audio", encoding="utf-8")

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeVoiceSessionWakeWordDetector())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())
    monkeypatch.setattr(
        "operance.cli.build_default_speech_synthesizer",
        lambda **kwargs: FakeSpeechSynthesizer(),
    )

    output_dir = tmp_path / "spoken"
    exit_code = main(
        [
            "--voice-session-frames",
            "4",
            "--voice-session-tts-output-dir",
            str(output_dir),
            "--tts-model",
            "model.onnx",
            "--tts-voices",
            "voices.bin",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["spoken_responses"] == [
        {
            "duration_seconds": 3 / 24000,
            "output_path": str(output_dir / "response-001.wav"),
            "plan_id": payload["spoken_responses"][0]["plan_id"],
            "sample_count": 3,
            "sample_rate_hz": 24000,
            "status": "success",
            "text": "Launched firefox",
            "voice": "af_sarah",
        }
    ]
    assert (output_dir / "response-001.wav").read_text(encoding="utf-8") == "fake-audio"


def test_cli_voice_session_can_play_saved_tts_responses(monkeypatch, tmp_path, capsys) -> None:
    from operance.tts import SynthesizedAudio

    played_paths: list[Path] = []

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.5, -0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text("fake-audio", encoding="utf-8")

    class FakePlaybackSink:
        def play_file(self, path: Path) -> None:
            played_paths.append(path)

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: _FakeAudioCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: _FakeVoiceSessionWakeWordDetector())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: _FakeSpeechTranscriber())
    monkeypatch.setattr(
        "operance.cli.build_default_speech_synthesizer",
        lambda **kwargs: FakeSpeechSynthesizer(),
    )
    monkeypatch.setattr("operance.cli.build_default_audio_playback_sink", lambda: FakePlaybackSink())

    output_dir = tmp_path / "spoken"
    exit_code = main(
        [
            "--voice-session-frames",
            "4",
            "--voice-session-tts-output-dir",
            str(output_dir),
            "--voice-session-tts-play",
            "--tts-model",
            "model.onnx",
            "--tts-voices",
            "voices.bin",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert played_paths == [output_dir / "response-001.wav"]
    assert payload["spoken_responses"][0]["played_output"] is True


def test_cli_voice_loop_prints_summary_until_command_limit(monkeypatch, capsys) -> None:
    from operance.stt import TranscriptSegment
    from operance.wakeword import WakeWordDetection

    class FakeLoopCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 10
            for _ in range(frame_total):
                yield _FakeAudioCaptureSource().frames(max_frames=1).__next__()

    class FakeLoopWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls in {2, 6}:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeLoopSpeechTranscriber:
        def __init__(self, text: str) -> None:
            self.text = text
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text=self.text, confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    planned_transcribers = [
        FakeLoopSpeechTranscriber("open firefox"),
        FakeLoopSpeechTranscriber("what is the volume"),
    ]

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: FakeLoopCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: FakeLoopWakeWordDetector())
    monkeypatch.setattr("operance.cli.build_default_speech_transcriber", lambda: planned_transcribers.pop(0))

    exit_code = main(["--voice-loop", "--voice-loop-max-commands", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert [item["text"] for item in payload["responses"]] == ["Launched firefox", "Volume is 30%"]
    assert payload["completed_commands"] == 2
    assert payload["stopped_reason"] == "command_limit"


def test_cli_voice_loop_reports_interrupts(monkeypatch, capsys) -> None:
    class InterruptedCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield _FakeAudioCaptureSource().frames(max_frames=1).__next__()
            raise KeyboardInterrupt

    class SilentWakeWordDetector:
        def process_frame(self, frame):
            return None

    monkeypatch.setattr("operance.cli.build_default_audio_capture_source", lambda device_name=None: InterruptedCaptureSource())
    monkeypatch.setattr("operance.cli.build_default_wakeword_detector", lambda **kwargs: SilentWakeWordDetector())

    exit_code = main(["--voice-loop", "--voice-loop-max-frames", "10"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["stopped_reason"] == "interrupted"
    assert payload["processed_frames"] == 1


def test_cli_mcp_list_tools_prints_tool_metadata(capsys) -> None:
    exit_code = main(["--mcp-list-tools"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    tool_names = {tool["name"] for tool in payload["tools"]}

    assert exit_code == 0
    assert "apps.launch" in tool_names
    assert payload["tools"][0]["input_schema"]["type"] == "object"


def test_cli_mcp_list_resources_prints_resource_metadata(capsys) -> None:
    exit_code = main(["--mcp-list-resources"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    resource_uris = {resource["uri"] for resource in payload["resources"]}

    assert exit_code == 0
    assert "operance://tools/catalog" in resource_uris
    assert "operance://policy/execution" in resource_uris
    assert "operance://runtime/status" in resource_uris
    assert "operance://runtime/audit" in resource_uris
    assert "operance://runtime/planner" in resource_uris
    assert "operance://runtime/confirmation" in resource_uris
    assert "operance://runtime/undo" in resource_uris


def test_cli_audit_log_prints_recent_entries(tmp_path, capsys) -> None:
    from operance.daemon import OperanceDaemon

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 50 percent", is_final=True)
    daemon.stop()

    exit_code = main(
        [
            "--audit-log",
            "--audit-limit",
            "5",
            "--data-dir",
            str(tmp_path / "data"),
            "--desktop-dir",
            str(tmp_path / "Desktop"),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["count"] == 1
    assert payload["entries"][0]["tool"] == "audio.set_volume"
    assert payload["entries"][0]["routing_reason"] == "deterministic_match"


def test_cli_mcp_call_tool_prints_result(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "--mcp-call-tool",
            "apps.launch",
            "--mcp-tool-args",
            '{"app":"firefox"}',
            "--data-dir",
            str(tmp_path / "data"),
            "--desktop-dir",
            str(tmp_path / "Desktop"),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["message"] == "Launched firefox"
    assert payload["tool"] == "apps.launch"


def test_cli_mcp_read_resource_prints_contents(capsys) -> None:
    exit_code = main(["--mcp-read-resource", "operance://tools/catalog"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["uri"] == "operance://tools/catalog"
    assert payload["mimeType"] == "application/json"
    assert "apps.launch" in payload["text"]


def test_cli_mcp_fixture_runs_stateful_sequence(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "mcp_fixture.jsonl"
    fixture_path.write_text(
        "\n".join(
            [
                '{"method":"tools/call","name":"windows.close","arguments":{"window":"firefox"},"expected_result":{"status":"awaiting_confirmation"}}',
                '{"method":"resources/read","uri":"operance://runtime/confirmation","expected_result":{"contents":[{"uri":"operance://runtime/confirmation"}]}}',
                '{"method":"tools/call","name":"operance.confirm_pending","arguments":{},"expected_result":{"status":"success","tool":"windows.close"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--mcp-fixture",
            str(fixture_path),
            "--data-dir",
            str(tmp_path / "data"),
            "--desktop-dir",
            str(tmp_path / "Desktop"),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total"] == 3
    assert payload["passed"] == 3
    assert payload["failed"] == 0
    assert payload["results"][0]["result"]["status"] == "awaiting_confirmation"
    assert payload["results"][1]["result"]["contents"][0]["uri"] == "operance://runtime/confirmation"
    assert payload["results"][2]["result"]["status"] == "success"
    assert payload["results"][2]["result"]["message"] == "Closed window Firefox"


def test_cli_mcp_fixture_can_undo_reversible_action(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "mcp_undo_fixture.jsonl"
    fixture_path.write_text(
        "\n".join(
            [
                '{"method":"tools/call","name":"audio.set_volume","arguments":{"percent":50}}',
                '{"method":"resources/read","uri":"operance://runtime/undo"}',
                '{"method":"tools/call","name":"operance.undo_last_action","arguments":{}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--mcp-fixture",
            str(fixture_path),
            "--data-dir",
            str(tmp_path / "data"),
            "--desktop-dir",
            str(tmp_path / "Desktop"),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["results"][0]["result"]["status"] == "success"
    assert '"undo_available": true' in payload["results"][1]["result"]["contents"][0]["text"]
    assert '"last_undo_tool": "audio.set_volume"' in payload["results"][1]["result"]["contents"][0]["text"]
    assert payload["results"][2]["result"]["status"] == "undone"
    assert payload["results"][2]["result"]["message"] == "Volume restored to 30%"


def test_cli_mcp_stdio_runs_transport_loop(tmp_path, monkeypatch, capsys) -> None:
    import io

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO('{"jsonrpc":"2.0","id":7,"method":"tools/list"}\n'),
    )

    exit_code = main(
        [
            "--mcp-stdio",
            "--data-dir",
            str(tmp_path / "data"),
            "--desktop-dir",
            str(tmp_path / "Desktop"),
        ]
    )

    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == 0
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 7
    assert any(tool["name"] == "apps.launch" for tool in response["result"]["tools"])


def test_cli_planner_preview_prints_preview_payload(capsys) -> None:
    exit_code = main(
        [
            "--planner-transcript",
            "open firefox and notify me",
            "--planner-payload",
            '{"actions":[{"tool":"apps.launch","args":{"app":"firefox"}},{"tool":"notifications.show","args":{"title":"Opened","message":"Firefox launched"}}]}',
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["preview"] == "Planned actions: launch firefox, then show notification 'Opened'."
    assert payload["plan"]["source"] == "planner"
    assert len(payload["plan"]["actions"]) == 2


def test_cli_planner_schema_prints_schema_payload(capsys) -> None:
    exit_code = main(["--planner-schema"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["type"] == "object"
    assert payload["properties"]["actions"]["maxItems"] == 2


def test_cli_planner_prompt_prints_prompt_messages(capsys) -> None:
    exit_code = main(["--planner-prompt", "quit firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["messages"][-1] == {"role": "user", "content": "quit firefox"}
    assert "apps.quit: Quit an application | args=app | risk=tier_2 | confirmation=required" in payload["messages"][0]["content"]
    assert 'example="quit firefox"' in payload["messages"][0]["content"]


def test_cli_planner_prompt_supports_context_entries(capsys) -> None:
    exit_code = main(
        [
            "--planner-prompt",
            "also notify me",
            "--planner-context-entry",
            "assistant:Planned action: launch firefox.",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["messages"][1] == {"role": "assistant", "content": "Planned action: launch firefox."}
    assert payload["messages"][-1] == {"role": "user", "content": "also notify me"}


def test_cli_planner_request_prints_request_payload(capsys) -> None:
    exit_code = main(["--planner-request", "open firefox"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["model"] == "qwen2.5-7b-instruct"
    assert payload["messages"][-1] == {"role": "user", "content": "open firefox"}
    assert payload["response_format"]["json_schema"]["name"] == "operance_action_plan"


def test_cli_planner_request_supports_context_entries(capsys) -> None:
    exit_code = main(
        [
            "--planner-request",
            "also notify me",
            "--planner-context-entry",
            "user:open firefox",
            "--planner-context-entry",
            "assistant:Planned action: launch firefox.",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["messages"][1] == {"role": "user", "content": "open firefox"}
    assert payload["messages"][2] == {"role": "assistant", "content": "Planned action: launch firefox."}
    assert payload["messages"][-1] == {"role": "user", "content": "also notify me"}


def test_cli_planner_health_prints_health_payload(monkeypatch, capsys) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"data": [{"id": "qwen-test"}]}).encode("utf-8")

    def fake_urlopen(request, timeout: float):  # type: ignore[no-untyped-def]
        return FakeResponse()

    monkeypatch.setattr("operance.planner.client.urlopen", fake_urlopen)

    exit_code = main(["--planner-health"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["probe"] == "models"
    assert payload["model_ids"] == ["qwen-test"]


def test_cli_setup_run_action_supports_planner_health(monkeypatch, capsys) -> None:
    from subprocess import CompletedProcess

    def fake_run(args: list[str], capture_output: bool, check: bool, text: bool) -> CompletedProcess[str]:
        assert args == ["python3", "-m", "operance.cli", "--planner-health"]
        return CompletedProcess(args=args, returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr("operance.ui.setup.subprocess.run", fake_run)
    monkeypatch.setattr(
        "operance.ui.setup.build_environment_report",
        lambda: {
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
                {"name": "planner_runtime_enabled", "status": "ok", "detail": "planner_runtime_enabled"},
                {"name": "planner_endpoint_healthy", "status": "warn", "detail": "planner_endpoint_healthy"},
            ],
        },
    )

    exit_code = main(
        [
            "--setup-run-action",
            "probe_planner_health",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["action_id"] == "probe_planner_health"
    assert payload["command"] == "python3 -m operance.cli --planner-health"
    assert payload["status"] == "success"


def test_cli_planner_route_prints_routing_decision(capsys) -> None:
    exit_code = main(
        [
            "--planner-route",
            "open browser and notify me",
            "--planner-confidence",
            "0.88",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {"reason": "fallback_to_planner", "route": "planner"}


def test_cli_planner_fixture_prints_regression_summary(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "planner_fixture.jsonl"
    fixture_path.write_text(
        '{"transcript":"open firefox","planner_payload":{"actions":[{"tool":"apps.launch","args":{"app":"firefox"}}]},"expected_valid":true,"expected_tools":["apps.launch"]}\n',
        encoding="utf-8",
    )

    exit_code = main(["--planner-fixture", str(fixture_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total"] == 1
    assert payload["passed"] == 1
    assert payload["failed"] == 0


def test_cli_replay_file_prints_regression_summary(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_text(
        '{"transcript":"open firefox","expected_response":"Launched firefox","expected_status":"success"}\n',
        encoding="utf-8",
    )

    exit_code = main(["--replay-file", str(fixture_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["total"] == 1
    assert payload["passed"] == 1
    assert payload["failed"] == 0
