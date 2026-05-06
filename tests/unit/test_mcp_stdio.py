import io
import json
from pathlib import Path


def test_mcp_stdio_session_initializes_server_capabilities() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-03-26","clientInfo":{"name":"test-client","version":"0.1.0"}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 0
    assert response["result"]["protocolVersion"] == "2025-03-26"
    assert response["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert response["result"]["serverInfo"]["name"] == "operance"


def test_mcp_stdio_session_rejects_non_object_requests() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('["not","an","object"]\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] is None
    assert response["error"]["code"] == -32600


def test_mcp_stdio_session_rejects_requests_without_string_method() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","id":11,"method":123}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 11
    assert response["error"]["code"] == -32600


def test_mcp_stdio_session_rejects_requests_without_jsonrpc_2() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"id":12,"method":"ping"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 12
    assert response["error"]["code"] == -32600


def test_mcp_stdio_session_returns_supported_protocol_version() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":10,"method":"initialize","params":{"protocolVersion":"2099-01-01","clientInfo":{"name":"test-client","version":"0.1.0"}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 10
    assert response["result"]["protocolVersion"] == "2025-03-26"


def test_mcp_stdio_session_lists_tools() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "tools" in response["result"]
    assert any(tool["name"] == "apps.launch" for tool in response["result"]["tools"])


def test_mcp_stdio_session_lists_resources() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","id":5,"method":"resources/list"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert any(
        resource["uri"] == "operance://tools/catalog"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/audit"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/planner"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/confirmation"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/undo"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/voice-loop-config"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/voice-loop-status"
        for resource in response["result"]["resources"]
    )
    assert any(
        resource["uri"] == "operance://runtime/voice-loop-service"
        for resource in response["result"]["resources"]
    )


def test_mcp_stdio_session_reads_resource() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":6,"method":"resources/read","params":{"uri":"operance://tools/catalog"}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert response["result"]["contents"][0]["uri"] == "operance://tools/catalog"
    assert "apps.launch" in response["result"]["contents"][0]["text"]


def test_mcp_stdio_session_reads_runtime_confirmation_resource(tmp_path: Path) -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":31,"method":"tools/call","params":{"name":"windows.close","arguments":{"window":"firefox"}}}\n'
        '{"jsonrpc":"2.0","id":32,"method":"resources/read","params":{"uri":"operance://runtime/confirmation"}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(
        input_stream,
        output_stream,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]

    assert responses[0]["result"]["status"] == "awaiting_confirmation"
    assert responses[1]["result"]["contents"][0]["uri"] == "operance://runtime/confirmation"
    assert '"pending_confirmation": true' in responses[1]["result"]["contents"][0]["text"]


def test_mcp_stdio_session_reads_runtime_voice_loop_config_resource(monkeypatch) -> None:
    from operance.mcp.stdio import run_stdio_session

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

    monkeypatch.setattr("operance.mcp.server.build_voice_loop_config_snapshot", lambda env=None: _FakeVoiceLoopConfigSnapshot())
    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":40,"method":"resources/read","params":{"uri":"operance://runtime/voice-loop-config"}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["result"]["contents"][0]["uri"] == "operance://runtime/voice-loop-config"
    assert '"wakeword_threshold": 0.95' in response["result"]["contents"][0]["text"]


def test_mcp_stdio_session_reads_runtime_voice_loop_status_resource(monkeypatch) -> None:
    from operance.mcp.stdio import run_stdio_session

    class _FakeVoiceLoopRuntimeStatusSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "awaiting_confirmation": False,
                "completed_commands": 2,
                "daemon_state": "IDLE",
                "heartbeat_age_seconds": 0.8,
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
                "processed_frames": 20,
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
        "operance.mcp.server.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _FakeVoiceLoopRuntimeStatusSnapshot(),
    )
    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":41,"method":"resources/read","params":{"uri":"operance://runtime/voice-loop-status"}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["result"]["contents"][0]["uri"] == "operance://runtime/voice-loop-status"
    assert '"completed_commands": 2' in response["result"]["contents"][0]["text"]


def test_mcp_stdio_session_reads_runtime_voice_loop_service_resource(monkeypatch) -> None:
    from operance.mcp.stdio import run_stdio_session

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
        "operance.mcp.server.build_voice_loop_service_snapshot",
        lambda env=None: _FakeVoiceLoopServiceSnapshot(),
    )
    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":42,"method":"resources/read","params":{"uri":"operance://runtime/voice-loop-service"}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["result"]["contents"][0]["uri"] == "operance://runtime/voice-loop-service"
    assert '"recommended_command": "./scripts/control_systemd_user_services.sh restart --voice-loop"' in response["result"]["contents"][0]["text"]


def test_mcp_stdio_session_calls_tool(tmp_path: Path) -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"apps.launch","arguments":{"app":"firefox"}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(
        input_stream,
        output_stream,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert response["result"]["status"] == "success"
    assert response["result"]["message"] == "Launched firefox"


def test_mcp_stdio_session_can_restart_voice_loop_service(monkeypatch) -> None:
    from operance.mcp.stdio import run_stdio_session
    from operance.ui.setup import SetupRunResult

    monkeypatch.setattr(
        "operance.mcp.server.run_setup_action",
        lambda action_id: SetupRunResult(
            action_id=action_id,
            label="Restart voice-loop user service",
            command="./scripts/control_systemd_user_services.sh restart --voice-loop",
            status="success",
            returncode=0,
            stdout="+ systemctl --user restart operance-voice-loop.service",
            stderr="",
            dry_run=False,
        ),
    )
    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"operance.restart_voice_loop_service","arguments":{}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["id"] == 7
    assert response["result"]["status"] == "success"
    assert response["result"]["message"] == "Restarted voice-loop user service."
    assert response["result"]["tool"] == "operance.restart_voice_loop_service"


def test_mcp_stdio_session_can_confirm_pending_command(tmp_path: Path) -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":21,"method":"tools/call","params":{"name":"windows.close","arguments":{"window":"firefox"}}}\n'
        '{"jsonrpc":"2.0","id":22,"method":"tools/call","params":{"name":"operance.confirm_pending","arguments":{}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(
        input_stream,
        output_stream,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]

    assert responses[0]["id"] == 21
    assert responses[0]["result"]["status"] == "awaiting_confirmation"
    assert responses[1]["id"] == 22
    assert responses[1]["result"]["status"] == "success"
    assert responses[1]["result"]["message"] == "Closed window Firefox"


def test_mcp_stdio_session_can_undo_last_action(tmp_path: Path) -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO(
        '{"jsonrpc":"2.0","id":41,"method":"tools/call","params":{"name":"audio.set_volume","arguments":{"percent":50}}}\n'
        '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"operance.undo_last_action","arguments":{}}}\n'
    )
    output_stream = io.StringIO()

    run_stdio_session(
        input_stream,
        output_stream,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]

    assert responses[0]["result"]["status"] == "success"
    assert responses[1]["result"]["status"] == "undone"
    assert responses[1]["result"]["message"] == "Volume restored to 30%"


def test_mcp_stdio_session_rejects_unknown_method() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","id":3,"method":"notifications/list"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert response["error"]["code"] == -32601


def test_mcp_stdio_session_responds_to_ping() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","id":4,"method":"ping"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    response = json.loads(output_stream.getvalue())

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert response["result"] == {}


def test_mcp_stdio_session_ignores_initialized_notification() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    assert output_stream.getvalue() == ""


def test_mcp_stdio_session_ignores_other_notifications_without_id() -> None:
    from operance.mcp.stdio import run_stdio_session

    input_stream = io.StringIO('{"jsonrpc":"2.0","method":"notifications/tools/list_changed"}\n')
    output_stream = io.StringIO()

    run_stdio_session(input_stream, output_stream)

    assert output_stream.getvalue() == ""
