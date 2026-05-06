"""Minimal JSON-RPC stdio loop for MCP tool smoke tests."""

from __future__ import annotations

import json
from typing import IO, Mapping

from .server import MCPServer

PROTOCOL_VERSION = "2025-03-26"
SERVER_VERSION = "0.1.0"


def run_stdio_session(
    input_stream: IO[str],
    output_stream: IO[str],
    env: Mapping[str, str] | None = None,
) -> None:
    server = MCPServer(env)
    try:
        for line in input_stream:
            if not line.strip():
                continue
            response = _handle_request(line, server)
            if response is None:
                continue
            output_stream.write(json.dumps(response, sort_keys=True))
            output_stream.write("\n")
    finally:
        server.stop()


def _handle_request(raw_line: str, server: MCPServer) -> dict[str, object] | None:
    try:
        request = json.loads(raw_line)
    except json.JSONDecodeError:
        return _error_response(None, -32700, "Parse error")
    if not isinstance(request, dict):
        return _error_response(None, -32600, "Invalid Request")
    if request.get("jsonrpc") != "2.0":
        return _error_response(request.get("id"), -32600, "Invalid Request")

    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    if not isinstance(method, str):
        return _error_response(request_id, -32600, "Invalid Request")

    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    if method == "initialize":
        requested_version = params.get("protocolVersion")
        if not isinstance(requested_version, str):
            return _error_response(request_id, -32602, "Invalid params")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "operance",
                    "version": SERVER_VERSION,
                },
            },
        }

    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {},
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": server.list_tools()},
        }

    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": server.list_resources()},
        }

    if method == "resources/read":
        uri = params.get("uri")
        if not isinstance(uri, str):
            return _error_response(request_id, -32602, "Invalid params")
        resource = server.read_resource(uri)
        if resource.get("status") == "not_found":
            return _error_response(request_id, -32001, str(resource["message"]))
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"contents": [resource]},
        }

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error_response(request_id, -32602, "Invalid params")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": server.call_tool(name, arguments),
        }

    return _error_response(request_id, -32601, "Method not found")


def _error_response(request_id: object, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
