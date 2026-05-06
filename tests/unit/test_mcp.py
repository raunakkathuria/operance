from pathlib import Path


def test_mcp_server_lists_safe_tools() -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer()
    tools = server.list_tools()

    tool_names = {tool["name"] for tool in tools}

    assert "apps.launch" in tool_names
    assert "time.now" in tool_names
    assert "audio.set_volume" in tool_names
    assert "windows.set_fullscreen" in tool_names
    assert "windows.set_keep_above" in tool_names
    assert "windows.set_shaded" in tool_names
    assert "windows.set_keep_below" in tool_names
    assert "windows.set_on_all_desktops" in tool_names
    assert "clipboard.get_text" in tool_names
    assert "clipboard.set_text" in tool_names
    assert "clipboard.copy_selection" in tool_names
    assert "clipboard.clear" in tool_names
    assert "clipboard.paste" in tool_names
    assert "text.type" in tool_names
    assert "keys.press" in tool_names
    assert "operance.confirm_pending" in tool_names
    assert "operance.cancel_pending" in tool_names
    assert "operance.undo_last_action" in tool_names
    assert "operance.reset_planner_runtime" in tool_names
    assert "operance.restart_voice_loop_service" in tool_names


def test_mcp_server_lists_resources() -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer()
    resources = server.list_resources()

    resource_uris = {resource["uri"] for resource in resources}

    assert "operance://tools/catalog" in resource_uris
    assert "operance://policy/execution" in resource_uris
    assert "operance://runtime/status" in resource_uris
    assert "operance://runtime/audit" in resource_uris
    assert "operance://runtime/planner" in resource_uris
    assert "operance://runtime/confirmation" in resource_uris
    assert "operance://runtime/undo" in resource_uris
    assert "operance://runtime/voice-loop-config" in resource_uris
    assert "operance://runtime/voice-loop-status" in resource_uris
    assert "operance://runtime/voice-loop-service" in resource_uris


def test_mcp_server_reads_tool_catalog_resource() -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer()

    resource = server.read_resource("operance://tools/catalog")

    assert resource["uri"] == "operance://tools/catalog"
    assert resource["mimeType"] == "application/json"
    assert "apps.launch" in resource["text"]


def test_mcp_server_reads_runtime_status_resource(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    server.daemon.start()
    server.daemon.emit_wake_detected("operance")
    server.daemon.emit_transcript("open firefox", is_final=True)

    resource = server.read_resource("operance://runtime/status")

    assert resource["uri"] == "operance://runtime/status"
    assert resource["mimeType"] == "application/json"
    assert '"current_state": "RESPONDING"' in resource["text"]
    assert '"last_undo_tool": null' in resource["text"]
    assert '"planner_context_entry_count": 2' in resource["text"]
    assert '"planner_context_messages": [{"content": "open firefox", "role": "user"}, {"content": "Launched firefox", "role": "assistant"}]' in resource["text"]


def test_mcp_server_reads_runtime_audit_resource(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    server.daemon.emit_wake_detected("operance")
    server.daemon.emit_transcript("set volume to 50 percent", is_final=True)

    resource = server.read_resource("operance://runtime/audit")

    assert resource["uri"] == "operance://runtime/audit"
    assert resource["mimeType"] == "application/json"
    assert '"tool": "audio.set_volume"' in resource["text"]
    assert '"routing_reason": "deterministic_match"' in resource["text"]


def test_mcp_server_reads_runtime_planner_resource(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    class FailingPlannerClient:
        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            raise ValueError(f"planner failed for {transcript}")

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
        }
    )
    server.daemon.planner_client = FailingPlannerClient()
    server.daemon.emit_wake_detected("operance")
    server.daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)

    resource = server.read_resource("operance://runtime/planner")

    assert resource["uri"] == "operance://runtime/planner"
    assert resource["mimeType"] == "application/json"
    assert '"enabled": true' in resource["text"]
    assert '"last_routing_reason": "planner_failed"' in resource["text"]
    assert '"last_planner_error": "planner failed for let me know when this is done"' in resource["text"]


def test_mcp_server_reads_runtime_planner_resource_with_cooldown(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    class FailingPlannerClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            self.calls.append(transcript)
            raise ValueError(f"planner failed for {transcript}")

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES": "2",
            "OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS": "30",
        }
    )
    server.daemon.planner_client = FailingPlannerClient()
    server.daemon.emit_wake_detected("operance")
    server.daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)
    server.daemon.complete_response_cycle()
    server.daemon.emit_transcript("tell me when this finishes", confidence=0.93, is_final=True)
    server.daemon.complete_response_cycle()
    server.daemon.emit_transcript("let me know again", confidence=0.93, is_final=True)

    resource = server.read_resource("operance://runtime/planner")

    assert '"consecutive_failures": 2' in resource["text"]
    assert '"cooldown_active": true' in resource["text"]
    assert '"last_routing_reason": "planner_cooldown_active"' in resource["text"]


def test_mcp_server_reads_runtime_confirmation_resource(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    server.call_tool("windows.close", {"window": "firefox"})

    resource = server.read_resource("operance://runtime/confirmation")

    assert resource["uri"] == "operance://runtime/confirmation"
    assert resource["mimeType"] == "application/json"
    assert '"pending_confirmation": true' in resource["text"]
    assert "close window 'firefox'" in resource["text"]
    assert '"pending_original_text": "mcp:windows.close"' in resource["text"]
    assert '"pending_source": "planner"' in resource["text"]
    assert '"pending_risk_tier": 2' in resource["text"]
    assert '"pending_affected_resources": ["window: firefox"]' in resource["text"]
    assert '"pending_rollback_hint": "No automatic undo is available after execution."' in resource["text"]
    assert '"pending_timeout_seconds": 30.0' in resource["text"]
    assert '"pending_timeout_behavior": "Pending command expires after 30 seconds without confirmation."' in resource["text"]
    assert '"tool": "windows.close"' in resource["text"]


def test_mcp_server_reads_runtime_undo_resource(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    server.call_tool("audio.set_volume", {"percent": 50})

    resource = server.read_resource("operance://runtime/undo")

    assert resource["uri"] == "operance://runtime/undo"
    assert resource["mimeType"] == "application/json"
    assert '"undo_available": true' in resource["text"]
    assert '"last_undo_tool": "audio.set_volume"' in resource["text"]


def test_mcp_server_reads_runtime_voice_loop_config_resource(monkeypatch) -> None:
    from operance.mcp.server import MCPServer

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
    server = MCPServer()

    resource = server.read_resource("operance://runtime/voice-loop-config")

    assert resource["uri"] == "operance://runtime/voice-loop-config"
    assert resource["mimeType"] == "application/json"
    assert '"selected_args_file": "/repo/.operance/voice-loop.args"' in resource["text"]
    assert '"wakeword_threshold": 0.95' in resource["text"]


def test_mcp_server_reads_runtime_voice_loop_status_resource(monkeypatch) -> None:
    from operance.mcp.server import MCPServer

    class _FakeVoiceLoopRuntimeStatusSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "awaiting_confirmation": False,
                "completed_commands": 2,
                "daemon_state": "IDLE",
                "heartbeat_age_seconds": 0.9,
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
    server = MCPServer()

    resource = server.read_resource("operance://runtime/voice-loop-status")

    assert resource["uri"] == "operance://runtime/voice-loop-status"
    assert resource["mimeType"] == "application/json"
    assert '"status_file_path": "/repo/.operance/voice-loop-status.json"' in resource["text"]
    assert '"completed_commands": 2' in resource["text"]


def test_mcp_server_reads_runtime_voice_loop_service_resource(monkeypatch) -> None:
    from operance.mcp.server import MCPServer

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
    server = MCPServer()

    resource = server.read_resource("operance://runtime/voice-loop-service")

    assert resource["uri"] == "operance://runtime/voice-loop-service"
    assert resource["mimeType"] == "application/json"
    assert '"recommended_command": "./scripts/control_systemd_user_services.sh restart --voice-loop"' in resource["text"]
    assert '"heartbeat_fresh": false' in resource["text"]


def test_mcp_server_can_restart_voice_loop_service(monkeypatch) -> None:
    from operance.mcp.server import MCPServer
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
    server = MCPServer()

    result = server.call_tool("operance.restart_voice_loop_service")

    assert result["status"] == "success"
    assert result["message"] == "Restarted voice-loop user service."
    assert result["tool"] == "operance.restart_voice_loop_service"
    assert result["command"] == "./scripts/control_systemd_user_services.sh restart --voice-loop"
    audit = server.read_resource("operance://runtime/audit")
    assert '"tool": "operance.restart_voice_loop_service"' in audit["text"]


def test_mcp_server_exposes_tool_input_schemas() -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer()
    tools = {tool["name"]: tool for tool in server.list_tools()}

    assert tools["apps.launch"]["input_schema"] == {
        "type": "object",
        "properties": {
            "app": {"type": "string"},
        },
        "required": ["app"],
        "additionalProperties": False,
    }
    assert tools["apps.quit"]["input_schema"] == {
        "type": "object",
        "properties": {
            "app": {"type": "string"},
        },
        "required": ["app"],
        "additionalProperties": False,
    }
    assert tools["audio.set_volume"]["input_schema"] == {
        "type": "object",
        "properties": {
            "percent": {"type": "integer", "minimum": 0, "maximum": 100},
        },
        "required": ["percent"],
        "additionalProperties": False,
    }
    assert tools["audio.get_volume"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["audio.mute_status"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["clipboard.get_text"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["clipboard.set_text"]["input_schema"] == {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
        "additionalProperties": False,
    }
    assert tools["clipboard.copy_selection"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["clipboard.clear"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["clipboard.paste"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["text.type"]["input_schema"] == {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
        "additionalProperties": False,
    }
    assert tools["keys.press"]["input_schema"] == {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
        },
        "required": ["key"],
        "additionalProperties": False,
    }
    assert tools["network.connect_known_ssid"]["input_schema"] == {
        "type": "object",
        "properties": {
            "ssid": {"type": "string"},
        },
        "required": ["ssid"],
        "additionalProperties": False,
    }
    assert tools["network.disconnect_current"]["input_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert tools["windows.switch"]["input_schema"] == {
        "type": "object",
        "properties": {
            "window": {"type": "string"},
        },
        "required": ["window"],
        "additionalProperties": False,
    }
    assert tools["windows.minimize"]["input_schema"] == {
        "type": "object",
        "properties": {
            "window": {"type": "string"},
        },
        "required": ["window"],
        "additionalProperties": False,
    }
    assert tools["windows.maximize"]["input_schema"] == {
        "type": "object",
        "properties": {
            "window": {"type": "string"},
        },
        "required": ["window"],
        "additionalProperties": False,
    }
    assert tools["windows.restore"]["input_schema"] == {
        "type": "object",
        "properties": {
            "window": {"type": "string"},
        },
        "required": ["window"],
        "additionalProperties": False,
    }
    assert tools["files.delete_folder"]["input_schema"] == {
        "type": "object",
        "properties": {
            "location": {"type": "string", "enum": ["desktop"]},
            "name": {"type": "string"},
        },
        "required": ["location", "name"],
        "additionalProperties": False,
    }
    assert tools["files.delete_file"]["input_schema"] == {
        "type": "object",
        "properties": {
            "location": {"type": "string", "enum": ["desktop"]},
            "name": {"type": "string"},
        },
        "required": ["location", "name"],
        "additionalProperties": False,
    }
    assert tools["files.rename"]["input_schema"] == {
        "type": "object",
        "properties": {
            "location": {"type": "string", "enum": ["desktop"]},
            "source_name": {"type": "string"},
            "target_name": {"type": "string"},
        },
        "required": ["location", "source_name", "target_name"],
        "additionalProperties": False,
    }
    assert tools["files.move"]["input_schema"] == {
        "type": "object",
        "properties": {
            "location": {"type": "string", "enum": ["desktop"]},
            "name": {"type": "string"},
            "destination_folder": {"type": "string"},
        },
        "required": ["location", "name", "destination_folder"],
        "additionalProperties": False,
    }
    assert tools["windows.close"]["input_schema"] == {
        "type": "object",
        "properties": {
            "window": {"type": "string"},
        },
        "required": ["window"],
        "additionalProperties": False,
    }
    assert tools["apps.launch"]["result_schema"] == {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
            "tool": {"type": "string", "const": "apps.launch"},
        },
        "required": ["status", "message", "tool"],
        "additionalProperties": True,
    }
    assert tools["apps.launch"]["example_transcripts"] == [
        "open firefox",
        "open http://localhost:3000",
        "browse to localhost 3000",
        "browse to docs.python.org/3",
    ]
    assert tools["audio.set_muted"]["example_transcripts"] == ["mute audio", "unmute audio"]
    assert tools["apps.launch"]["allowed_side_effects"] == ["launch_app", "open_url"]
    assert tools["time.now"]["allowed_side_effects"] == []
    assert tools["audio.set_volume"]["allowed_side_effects"] == ["set_audio_volume"]
    assert tools["audio.set_volume"]["undo_summary"] == "Undo will restore the previous volume."
    assert (
        tools["windows.minimize"]["undo_summary"]
        == "No automatic undo is available because the previous window state is not tracked safely."
    )
    assert tools["operance.confirm_pending"]["result_schema"] == {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
            "tool": {"type": "string"},
        },
        "required": ["status", "message", "tool"],
        "additionalProperties": True,
    }
    assert tools["operance.confirm_pending"]["allowed_side_effects"] == ["execute_pending_command"]
    assert tools["operance.confirm_pending"]["example_transcripts"] == []
    assert tools["operance.confirm_pending"]["undo_summary"] is None
    assert tools["operance.reset_planner_runtime"]["allowed_side_effects"] == ["reset_planner_runtime_state"]
    assert tools["operance.reset_planner_runtime"]["example_transcripts"] == []
    assert tools["operance.reset_planner_runtime"]["undo_summary"] is None


def test_mcp_server_requires_confirmation_for_close_window(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("windows.close", {"window": "firefox"})

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "windows.close"
    assert result["pending_preview"] == "Planned action: close window 'firefox'."
    assert result["pending_source"] == "planner"
    assert result["pending_risk_tier"] == 2
    assert result["pending_action"]["tool"] == "windows.close"
    assert result["pending_action"]["args"] == {"window": "firefox"}
    assert result["pending_action"]["risk_tier"] == 2
    assert result["pending_original_text"] == "mcp:windows.close"
    assert result["pending_affected_resources"] == ["window: firefox"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."
    assert result["pending_timeout_seconds"] == 30.0
    assert result["pending_timeout_behavior"] == "Pending command expires after 30 seconds without confirmation."


def test_mcp_server_requires_confirmation_for_quit_app(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("apps.quit", {"app": "firefox"})

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "apps.quit"
    assert result["pending_preview"] == "Planned action: quit firefox."
    assert result["pending_affected_resources"] == ["app: firefox"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."


def test_mcp_server_requires_confirmation_for_delete_folder(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "files.delete_folder",
        {"location": "desktop", "name": "projects"},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "files.delete_folder"
    assert result["pending_preview"] == "Planned action: delete folder 'projects'."
    assert result["pending_affected_resources"] == ["desktop folder: projects"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."


def test_mcp_server_requires_confirmation_for_delete_file(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "files.delete_file",
        {"location": "desktop", "name": "notes.txt"},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "files.delete_file"
    assert result["pending_preview"] == "Planned action: delete file 'notes.txt'."
    assert result["pending_affected_resources"] == ["desktop file: notes.txt"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."


def test_mcp_server_requires_confirmation_for_rename_entry(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "files.rename",
        {"location": "desktop", "source_name": "projects", "target_name": "archive"},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "files.rename"
    assert result["pending_preview"] == "Planned action: rename desktop entry 'projects' to 'archive'."
    assert result["pending_affected_resources"] == ["desktop entry: projects", "desktop name: archive"]
    assert result["pending_rollback_hint"] == "Undo will restore the previous state."


def test_mcp_server_requires_confirmation_for_move_entry(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "files.move",
        {"location": "desktop", "name": "projects", "destination_folder": "archive"},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "files.move"
    assert result["pending_preview"] == "Planned action: move desktop entry 'projects' to folder 'archive'."
    assert result["pending_affected_resources"] == ["desktop entry: projects", "desktop folder: archive"]
    assert result["pending_rollback_hint"] == "Undo will restore the previous state."


def test_mcp_server_requires_confirmation_for_wifi_disable(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "network.set_wifi_enabled",
        {"enabled": False},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "network.set_wifi_enabled"
    assert result["pending_preview"] == "Planned action: disable Wi-Fi."
    assert result["pending_affected_resources"] == ["wi-fi state"]
    assert result["pending_rollback_hint"] == "Undo will restore the previous Wi-Fi state."


def test_mcp_server_requires_confirmation_for_disconnect_current_wifi(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "network.disconnect_current",
        {},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "network.disconnect_current"
    assert result["pending_preview"] == "Planned action: disconnect current Wi-Fi."
    assert result["pending_affected_resources"] == ["current Wi-Fi connection"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."


def test_mcp_server_requires_confirmation_for_connect_known_ssid(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "network.connect_known_ssid",
        {"ssid": "home"},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "network.connect_known_ssid"
    assert result["pending_preview"] == "Planned action: connect to known Wi-Fi 'home'."
    assert result["pending_affected_resources"] == ["known Wi-Fi network: home"]
    assert result["pending_rollback_hint"] == "No automatic undo is available after execution."


def test_mcp_server_requires_confirmation_for_high_volume(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool(
        "audio.set_volume",
        {"percent": 90},
    )

    assert result["status"] == "awaiting_confirmation"
    assert result["message"] == "Command requires confirmation."
    assert result["tool"] == "audio.set_volume"
    assert result["pending_preview"] == "Planned action: set volume to 90%."
    assert result["pending_affected_resources"] == ["audio output volume"]
    assert result["pending_rollback_hint"] == "Undo will restore the previous volume."


def test_mcp_server_invokes_tool_through_validated_runtime(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("apps.launch", {"app": "firefox"})

    assert result["status"] == "success"
    assert result["message"] == "Launched firefox"
    assert result["tool"] == "apps.launch"


def test_mcp_server_can_confirm_pending_command(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    gated = server.call_tool("windows.close", {"window": "firefox"})
    confirmed = server.call_tool("operance.confirm_pending", {})

    assert gated["status"] == "awaiting_confirmation"
    assert gated["pending_plan_id"] is not None
    assert confirmed["status"] == "success"
    assert confirmed["message"] == "Closed window Firefox"
    assert confirmed["tool"] == "windows.close"


def test_mcp_server_can_cancel_pending_command(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    gated = server.call_tool("files.delete_folder", {"location": "desktop", "name": "projects"})
    cancelled = server.call_tool("operance.cancel_pending", {})

    assert gated["status"] == "awaiting_confirmation"
    assert cancelled["status"] == "cancelled"
    assert cancelled["message"] == "Cancelled pending command."
    assert cancelled["tool"] == "files.delete_folder"


def test_mcp_server_reports_expired_pending_command(tmp_path: Path, monkeypatch) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    gated = server.call_tool("windows.close", {"window": "firefox"})
    server.daemon.pending_confirmation_started_at = 0.0
    monkeypatch.setattr("operance.daemon.monotonic", lambda: 1000.0)
    expired = server.call_tool("operance.confirm_pending", {})

    assert gated["status"] == "awaiting_confirmation"
    assert expired["status"] == "expired"
    assert expired["message"] == "Pending command expired."
    assert expired["tool"] == "windows.close"


def test_mcp_server_can_undo_last_reversible_action(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    applied = server.call_tool("audio.set_volume", {"percent": 50})
    undone = server.call_tool("operance.undo_last_action", {})

    assert applied["status"] == "success"
    assert undone["status"] == "undone"
    assert undone["message"] == "Volume restored to 30%"
    assert undone["tool"] == "audio.set_volume"


def test_mcp_server_reports_no_pending_command_for_confirmation_tool(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("operance.confirm_pending", {})

    assert result["status"] == "failed"
    assert result["message"] == "No pending command requires confirmation."
    assert result["tool"] == "operance.confirm_pending"


def test_mcp_server_can_reset_planner_runtime(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    class FailingPlannerClient:
        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            raise ValueError(f"planner failed for {transcript}")

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
            "OPERANCE_PLANNER_MAX_CONSECUTIVE_FAILURES": "2",
            "OPERANCE_PLANNER_FAILURE_COOLDOWN_SECONDS": "30",
        }
    )
    server.daemon.planner_client = FailingPlannerClient()
    server.daemon.emit_wake_detected("operance")
    server.daemon.emit_transcript("let me know when this is done", confidence=0.93, is_final=True)
    server.daemon.complete_response_cycle()
    server.daemon.emit_transcript("tell me when this finishes", confidence=0.93, is_final=True)

    result = server.call_tool("operance.reset_planner_runtime", {})
    snapshot = server.daemon.status_snapshot()

    assert result["status"] == "success"
    assert result["message"] == "Planner runtime state reset."
    assert result["tool"] == "operance.reset_planner_runtime"
    assert snapshot.last_routing_reason == "planner_runtime_reset"
    assert snapshot.last_planner_error is None
    assert snapshot.planner_consecutive_failures == 0
    assert snapshot.planner_cooldown_remaining_seconds is None


def test_mcp_server_reports_no_undoable_action_when_none_pending(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("operance.undo_last_action", {})

    assert result["status"] == "failed"
    assert result["message"] == "No undoable action is available."
    assert result["tool"] == "operance.undo_last_action"


def test_mcp_server_rejects_invalid_tool_args(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("apps.launch", {})

    assert result["status"] == "denied"
    assert "missing required args" in result["message"]


def test_mcp_server_reports_unknown_tool(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    result = server.call_tool("shell.exec", {"command": "rm -rf /"})

    assert result["status"] == "not_found"


def test_mcp_server_reports_unknown_resource() -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer()

    result = server.read_resource("operance://missing")

    assert result["status"] == "not_found"


def test_mcp_server_audits_unknown_tool_requests(tmp_path: Path) -> None:
    from operance.mcp.server import MCPServer

    server = MCPServer(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    server.call_tool("shell.exec", {"command": "rm -rf /"})

    entries = server.daemon.audit_store.list_entries()

    assert len(entries) == 1
    assert entries[0].status == "not_found"
    assert entries[0].tool == "shell.exec"
