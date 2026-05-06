"""Portable in-process MCP server skeleton."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Mapping

from ..audit import AuditEntry
from ..confirmation import build_confirmation_metadata
from ..daemon import OperanceDaemon
from ..models.actions import ActionPlan, PlanSource, ToolName, TypedAction
from ..registry import _tool_result_schema
from ..ui.setup import run_setup_action
from ..voice import build_voice_loop_runtime_status_snapshot
from ..voice.config import build_voice_loop_config_snapshot
from ..voice.service import build_voice_loop_service_snapshot

_CONTROL_TOOLS = (
    {
        "name": "operance.confirm_pending",
        "description": "Confirm and execute the current pending command",
        "required_args": [],
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "result_schema": _tool_result_schema("operance.confirm_pending", const_tool=False),
        "example_transcripts": [],
        "risk_tier": 0,
        "requires_confirmation": False,
        "undoable": False,
        "allowed_side_effects": ["execute_pending_command"],
        "undo_summary": None,
    },
    {
        "name": "operance.cancel_pending",
        "description": "Cancel the current pending command",
        "required_args": [],
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "result_schema": _tool_result_schema("operance.cancel_pending", const_tool=False),
        "example_transcripts": [],
        "risk_tier": 0,
        "requires_confirmation": False,
        "undoable": False,
        "allowed_side_effects": ["cancel_pending_command"],
        "undo_summary": None,
    },
    {
        "name": "operance.undo_last_action",
        "description": "Undo the last reversible action in this MCP session",
        "required_args": [],
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "result_schema": _tool_result_schema("operance.undo_last_action", const_tool=False),
        "example_transcripts": [],
        "risk_tier": 0,
        "requires_confirmation": False,
        "undoable": False,
        "allowed_side_effects": ["undo_last_action"],
        "undo_summary": None,
    },
    {
        "name": "operance.reset_planner_runtime",
        "description": "Clear planner cooldown and recent planner error state in this MCP session",
        "required_args": [],
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "result_schema": _tool_result_schema("operance.reset_planner_runtime", const_tool=False),
        "example_transcripts": [],
        "risk_tier": 0,
        "requires_confirmation": False,
        "undoable": False,
        "allowed_side_effects": ["reset_planner_runtime_state"],
        "undo_summary": None,
    },
    {
        "name": "operance.restart_voice_loop_service",
        "description": "Restart the repo-local voice-loop user service through the shared setup runner",
        "required_args": [],
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "result_schema": _tool_result_schema("operance.restart_voice_loop_service", const_tool=False),
        "example_transcripts": [],
        "risk_tier": 1,
        "requires_confirmation": False,
        "undoable": False,
        "allowed_side_effects": ["restart_voice_loop_user_service"],
        "undo_summary": None,
    },
)


class MCPServer:
    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self.env = dict(env or {})
        self.daemon = OperanceDaemon.build_default(self.env)
        self.daemon.start()

    def list_tools(self) -> list[dict[str, object]]:
        tools = [
            {
                "name": spec.name.value,
                "description": spec.description,
                "required_args": list(spec.required_args),
                "input_schema": deepcopy(spec.input_schema),
                "result_schema": deepcopy(spec.result_schema),
                "example_transcripts": list(spec.example_transcripts),
                "risk_tier": int(spec.risk_tier),
                "requires_confirmation": spec.requires_confirmation,
                "undoable": spec.undoable,
                "allowed_side_effects": list(spec.allowed_side_effects),
                "undo_summary": spec.undo_summary,
            }
            for spec in self.daemon.validator.registry.list_specs()
        ]
        tools.extend(deepcopy(tool) for tool in _CONTROL_TOOLS)
        return tools

    def list_resources(self) -> list[dict[str, object]]:
        return [
            {
                "uri": "operance://tools/catalog",
                "name": "Approved tool catalog",
                "description": "Current approved tools with schemas and risk metadata.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://policy/execution",
                "name": "Execution policy summary",
                "description": "Current execution policy tiers and confirmation rules.",
                "mimeType": "text/plain",
            },
            {
                "uri": "operance://runtime/status",
                "name": "Runtime status snapshot",
                "description": "Current daemon runtime state and latest command context.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/audit",
                "name": "Recent audit entries",
                "description": "Recent persisted runtime audit entries for this data directory.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/planner",
                "name": "Planner runtime snapshot",
                "description": "Current planner configuration and latest planner routing diagnostics.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/confirmation",
                "name": "Pending confirmation state",
                "description": "Current pending confirmation state for this MCP session.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/undo",
                "name": "Undo state",
                "description": "Current undo availability for this MCP session.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/voice-loop-config",
                "name": "Voice-loop config snapshot",
                "description": "Effective repo-local voice-loop args and wake-word settings.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/voice-loop-status",
                "name": "Voice-loop runtime status",
                "description": "Latest repo-local continuous voice-loop heartbeat and counters.",
                "mimeType": "application/json",
            },
            {
                "uri": "operance://runtime/voice-loop-service",
                "name": "Voice-loop service status",
                "description": "Combined repo-local voice-loop service, config, and runtime health snapshot.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str) -> dict[str, object]:
        if uri == "operance://tools/catalog":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({"tools": self.list_tools()}, sort_keys=True),
            }

        if uri == "operance://policy/execution":
            return {
                "uri": uri,
                "mimeType": "text/plain",
                "text": _policy_summary(),
            }

        if uri == "operance://runtime/status":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(self.daemon.status_snapshot().to_dict(), sort_keys=True),
            }

        if uri == "operance://runtime/audit":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(self._audit_snapshot(), sort_keys=True),
            }

        if uri == "operance://runtime/planner":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(self._planner_snapshot(), sort_keys=True),
            }

        if uri == "operance://runtime/confirmation":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(self._confirmation_snapshot(), sort_keys=True),
            }

        if uri == "operance://runtime/undo":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(self._undo_snapshot(), sort_keys=True),
            }

        if uri == "operance://runtime/voice-loop-config":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(build_voice_loop_config_snapshot(env=self.env).to_dict(), sort_keys=True),
            }

        if uri == "operance://runtime/voice-loop-status":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(build_voice_loop_runtime_status_snapshot(env=self.env).to_dict(), sort_keys=True),
            }

        if uri == "operance://runtime/voice-loop-service":
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(build_voice_loop_service_snapshot(env=self.env).to_dict(), sort_keys=True),
            }

        return {
            "status": "not_found",
            "message": f"Unknown resource: {uri}",
            "uri": uri,
        }

    def call_tool(self, name: str, args: Mapping[str, object] | None = None) -> dict[str, object]:
        if name == "operance.confirm_pending":
            return self._resolve_pending_confirmation(confirm=True)

        if name == "operance.cancel_pending":
            return self._resolve_pending_confirmation(confirm=False)

        if name == "operance.undo_last_action":
            return self._undo_last_action()

        if name == "operance.reset_planner_runtime":
            return self._reset_planner_runtime()

        if name == "operance.restart_voice_loop_service":
            return self._restart_voice_loop_service()

        tool = self._tool_from_name(name)
        if tool is None:
            message = f"Unknown tool: {name}"
            self._record_outcome(
                transcript=f"mcp:{name}",
                tool_name=name,
                status="not_found",
                message=message,
            )
            return {
                "status": "not_found",
                "message": message,
                "tool": name,
            }

        transcript = f"mcp:{name}"
        plan = ActionPlan(
            source=PlanSource.PLANNER,
            original_text=transcript,
            actions=[TypedAction(tool=tool, args=dict(args or {}))],
        )

        validation_result = self.daemon.validator.validate(plan)
        if not validation_result.valid or validation_result.normalized_plan is None:
            message = "; ".join(validation_result.errors) or "Command validation failed."
            self._record_outcome(
                transcript=transcript,
                tool_name=name,
                status="denied",
                message=message,
            )
            return {"status": "denied", "message": message, "tool": name}

        normalized_plan = validation_result.normalized_plan
        policy_decision = self.daemon.policy.decide(normalized_plan)
        if policy_decision.action == "deny":
            message = f"Command denied: {policy_decision.reason}"
            self._record_outcome(
                transcript=transcript,
                tool_name=name,
                status="denied",
                message=message,
            )
            return {"status": "denied", "message": message, "tool": name}

        if policy_decision.action == "require_confirmation":
            self.daemon.set_pending_confirmation(normalized_plan)
            message, status = self.daemon.response_builder.confirmation_required()
            confirmation_metadata = build_confirmation_metadata(
                normalized_plan,
                timeout_seconds=self.daemon.config.runtime.confirmation_timeout_seconds,
            )
            self._record_outcome(
                transcript=transcript,
                tool_name=name,
                status=status,
                message=message,
            )
            return {
                "status": status,
                "message": message,
                "tool": name,
                "pending_plan_id": confirmation_metadata["pending_plan_id"],
                "pending_preview": confirmation_metadata["pending_plan_preview"],
                "pending_original_text": confirmation_metadata["pending_original_text"],
                "pending_source": confirmation_metadata["pending_source"],
                "pending_risk_tier": confirmation_metadata["pending_risk_tier"],
                "pending_action": confirmation_metadata["pending_action"],
                "pending_affected_resources": confirmation_metadata["pending_affected_resources"],
                "pending_rollback_hint": confirmation_metadata["pending_rollback_hint"],
                "pending_timeout_seconds": confirmation_metadata["pending_timeout_seconds"],
                "pending_timeout_behavior": confirmation_metadata["pending_timeout_behavior"],
            }

        try:
            result = self.daemon.executor.execute(normalized_plan)
        except ValueError as exc:
            self._record_outcome(
                transcript=transcript,
                tool_name=name,
                status="failed",
                message=str(exc),
            )
            return {"status": "failed", "message": str(exc), "tool": name}

        message, status = self.daemon.response_builder.from_action_result(result)
        self.daemon.last_undo_token = result.results[0].undo_token if result.results else None
        self.daemon.last_undo_tool = (
            result.results[0].tool.value
            if result.results and result.results[0].undo_token is not None
            else None
        )
        self._record_outcome(
            transcript=transcript,
            tool_name=name,
            status=status,
            message=message,
        )
        return {"status": status, "message": message, "tool": name}

    def stop(self) -> None:
        self.daemon.stop()

    def _record_outcome(
        self,
        *,
        transcript: str,
        tool_name: str,
        status: str,
        message: str,
    ) -> None:
        self.daemon.last_transcript = transcript
        self.daemon.last_response = message
        self.daemon.last_command_status = status
        self.daemon.audit_store.append(
            AuditEntry(
                transcript=transcript,
                status=status,
                tool=tool_name,
                response_text=message,
            )
        )

    def _resolve_pending_confirmation(self, *, confirm: bool) -> dict[str, object]:
        pending_plan = self.daemon.pending_confirmation_plan
        control_tool = "operance.confirm_pending" if confirm else "operance.cancel_pending"
        if not isinstance(pending_plan, ActionPlan):
            message = "No pending command requires confirmation."
            self._record_outcome(
                transcript=f"mcp:{control_tool}",
                tool_name=control_tool,
                status="failed",
                message=message,
            )
            return {"status": "failed", "message": message, "tool": control_tool}

        target_tool = pending_plan.actions[0].tool.value
        if self.daemon.pending_confirmation_has_expired():
            expired_plan = self.daemon.clear_pending_confirmation()
            message, status = self.daemon.response_builder.confirmation_expired()
            self._record_outcome(
                transcript=f"mcp:{control_tool}",
                tool_name=target_tool,
                status=status,
                message=message,
            )
            return {
                "status": status,
                "message": message,
                "tool": target_tool,
                "plan_id": expired_plan.plan_id if expired_plan is not None else pending_plan.plan_id,
            }

        if confirm:
            try:
                result = self.daemon.executor.execute(pending_plan)
            except ValueError as exc:
                self.daemon.clear_pending_confirmation()
                self._record_outcome(
                    transcript=f"mcp:{control_tool}",
                    tool_name=target_tool,
                    status="failed",
                    message=str(exc),
                )
                return {"status": "failed", "message": str(exc), "tool": target_tool}

            self.daemon.clear_pending_confirmation()
            message, status = self.daemon.response_builder.from_action_result(result)
            self.daemon.last_undo_token = result.results[0].undo_token if result.results else None
            self.daemon.last_undo_tool = (
                result.results[0].tool.value
                if result.results and result.results[0].undo_token is not None
                else None
            )
            self._record_outcome(
                transcript=f"mcp:{control_tool}",
                tool_name=target_tool,
                status=status,
                message=message,
            )
            return {"status": status, "message": message, "tool": target_tool, "plan_id": result.plan_id}

        self.daemon.clear_pending_confirmation()
        message, status = self.daemon.response_builder.confirmation_cancelled()
        self._record_outcome(
            transcript=f"mcp:{control_tool}",
            tool_name=target_tool,
            status=status,
            message=message,
        )
        return {
            "status": status,
            "message": message,
            "tool": target_tool,
            "plan_id": pending_plan.plan_id,
        }

    def _confirmation_snapshot(self) -> dict[str, object]:
        return build_confirmation_metadata(
            self.daemon.pending_confirmation_plan if isinstance(self.daemon.pending_confirmation_plan, ActionPlan) else None,
            timeout_seconds=(
                self.daemon.config.runtime.confirmation_timeout_seconds
                if isinstance(self.daemon.pending_confirmation_plan, ActionPlan)
                else None
            ),
        )

    def _undo_snapshot(self) -> dict[str, object]:
        return {
            "undo_available": self.daemon.last_undo_token is not None,
            "last_undo_tool": self.daemon.last_undo_tool,
        }

    def _planner_snapshot(self) -> dict[str, object]:
        status = self.daemon.status_snapshot()
        return {
            "enabled": self.daemon.config.planner.enabled,
            "endpoint": self.daemon.config.planner.endpoint,
            "model": self.daemon.config.planner.model,
            "min_confidence": self.daemon.config.planner.min_confidence,
            "max_consecutive_failures": self.daemon.config.planner.max_consecutive_failures,
            "failure_cooldown_seconds": self.daemon.config.planner.failure_cooldown_seconds,
            "last_transcript": status.last_transcript,
            "last_plan_source": status.last_plan_source,
            "last_routing_reason": status.last_routing_reason,
            "last_planner_error": status.last_planner_error,
            "consecutive_failures": status.planner_consecutive_failures,
            "cooldown_active": status.planner_cooldown_remaining_seconds is not None,
            "cooldown_remaining_seconds": status.planner_cooldown_remaining_seconds,
            "planner_context_entry_count": status.planner_context_entry_count,
            "planner_context_messages": status.planner_context_messages,
        }

    def _audit_snapshot(self) -> dict[str, object]:
        entries = self.daemon.audit_store.list_recent(limit=20)
        return {
            "count": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        }

    def _undo_last_action(self) -> dict[str, object]:
        if self.daemon.last_undo_token is None:
            message = "No undoable action is available."
            self._record_outcome(
                transcript="mcp:operance.undo_last_action",
                tool_name="operance.undo_last_action",
                status="failed",
                message=message,
            )
            return {"status": "failed", "message": message, "tool": "operance.undo_last_action"}

        target_tool = self.daemon.last_undo_tool or "operance.undo_last_action"
        message = self.daemon.undo_last_action()
        if message is None:
            message = "No undoable action is available."
            self._record_outcome(
                transcript="mcp:operance.undo_last_action",
                tool_name="operance.undo_last_action",
                status="failed",
                message=message,
            )
            return {"status": "failed", "message": message, "tool": "operance.undo_last_action"}

        self._record_outcome(
            transcript="mcp:operance.undo_last_action",
            tool_name=target_tool,
            status="undone",
            message=message,
        )
        return {"status": "undone", "message": message, "tool": target_tool}

    def _reset_planner_runtime(self) -> dict[str, object]:
        message = self.daemon.reset_planner_runtime()
        self._record_outcome(
            transcript="mcp:operance.reset_planner_runtime",
            tool_name="operance.reset_planner_runtime",
            status="success",
            message=message,
        )
        return {
            "status": "success",
            "message": message,
            "tool": "operance.reset_planner_runtime",
        }

    def _restart_voice_loop_service(self) -> dict[str, object]:
        tool_name = "operance.restart_voice_loop_service"
        try:
            result = run_setup_action("restart_voice_loop_service")
        except ValueError as exc:
            message = str(exc)
            self._record_outcome(
                transcript=f"mcp:{tool_name}",
                tool_name=tool_name,
                status="failed",
                message=message,
            )
            return {"status": "failed", "message": message, "tool": tool_name}

        message = _setup_run_result_message(result)
        self._record_outcome(
            transcript=f"mcp:{tool_name}",
            tool_name=tool_name,
            status=result.status,
            message=message,
        )
        return {
            "status": result.status,
            "message": message,
            "tool": tool_name,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @staticmethod
    def _tool_from_name(name: str) -> ToolName | None:
        try:
            return ToolName(name)
        except ValueError:
            return None


def _policy_summary() -> str:
    return "\n".join(
        [
            "Tier 0 and Tier 1 actions auto-approve by default.",
            "Tier 2+ actions or tools marked as requiring confirmation stop before execution.",
            "Tier 3+ actions are denied before execution.",
            "Stateful MCP sessions can resolve pending confirmations with operance.confirm_pending or operance.cancel_pending.",
            "Stateful MCP sessions can reset planner cooldown and planner-error state with operance.reset_planner_runtime.",
            "Stateful MCP sessions can restart the repo-local voice-loop user service with operance.restart_voice_loop_service.",
            "All MCP tool calls use the same validator, policy, executor, and audit path as local calls.",
        ]
    )


def _setup_run_result_message(result: object) -> str:
    status = getattr(result, "status", None)
    if status == "success":
        return "Restarted voice-loop user service."
    stderr = str(getattr(result, "stderr", "") or "").strip()
    if stderr:
        return stderr
    stdout = str(getattr(result, "stdout", "") or "").strip()
    if stdout:
        return stdout
    label = str(getattr(result, "label", "Setup action") or "Setup action")
    return f"{label} failed."
