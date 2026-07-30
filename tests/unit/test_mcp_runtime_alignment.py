from __future__ import annotations

import json
from pathlib import Path

from operance.mcp.server import MCPServer


def _server(tmp_path: Path) -> MCPServer:
    return MCPServer(
        env={
            "OPERANCE_DEVELOPER_MODE": "1",
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )


def _resource(server: MCPServer, uri: str) -> dict[str, object]:
    return json.loads(server.read_resource(uri)["text"])


def test_status_resource_counts_mcp_commands(tmp_path: Path) -> None:
    server = _server(tmp_path)

    assert _resource(server, "operance://runtime/status")["completed_commands"] == 0

    server.call_tool("apps.launch", {"app": "firefox"})
    server.call_tool("time.now", {})

    assert _resource(server, "operance://runtime/status")["completed_commands"] == 2


def test_status_resource_reports_mcp_plan_source(tmp_path: Path) -> None:
    server = _server(tmp_path)

    server.call_tool("apps.launch", {"app": "firefox"})

    status = _resource(server, "operance://runtime/status")
    assert status["last_plan_source"] == "mcp"
    assert status["last_transcript"] == "mcp:apps.launch"


def test_audit_entry_records_mcp_plan_source(tmp_path: Path) -> None:
    server = _server(tmp_path)

    server.call_tool("apps.launch", {"app": "firefox"})

    entry = _resource(server, "operance://runtime/audit")["entries"][0]
    assert entry["plan_source"] == "mcp"
    assert entry["tool"] == "apps.launch"
    assert entry["status"] == "success"


def test_mcp_outcome_does_not_inherit_previous_planner_routing_state(tmp_path: Path) -> None:
    server = _server(tmp_path)
    server.daemon.last_routing_reason = "planner_low_confidence"
    server.daemon.last_planner_error = "connection refused"
    server.daemon.last_plan_source = "planner"

    server.call_tool("time.now", {})

    entry = _resource(server, "operance://runtime/audit")["entries"][0]
    assert entry["plan_source"] == "mcp"
    assert entry["routing_reason"] is None
    assert entry["planner_error"] is None


def test_reset_planner_runtime_keeps_its_own_routing_reason(tmp_path: Path) -> None:
    server = _server(tmp_path)

    server.call_tool("operance.reset_planner_runtime")

    assert server.daemon.last_routing_reason == "planner_runtime_reset"
    entry = _resource(server, "operance://runtime/audit")["entries"][0]
    assert entry["routing_reason"] == "planner_runtime_reset"


def test_unknown_tool_is_recorded_as_unmatched(tmp_path: Path) -> None:
    server = _server(tmp_path)

    server.call_tool("not.a.tool", {})

    metrics = server.daemon.metrics.completed_commands
    assert len(metrics) == 1
    assert metrics[0].matched is False


def test_mcp_calls_do_not_enter_the_voice_state_machine(tmp_path: Path) -> None:
    """MCP is not a voice interaction, so it must not fake voice states."""

    server = _server(tmp_path)
    before = server.daemon.state_machine.current_state

    server.call_tool("apps.launch", {"app": "firefox"})

    assert server.daemon.state_machine.current_state == before


def test_mcp_records_measured_command_duration(tmp_path: Path) -> None:
    server = _server(tmp_path)

    server.call_tool("time.now", {})

    metric = server.daemon.metrics.completed_commands[0]
    assert metric.total_duration_ms > 0.0
    assert metric.transcript == "mcp:time.now"
