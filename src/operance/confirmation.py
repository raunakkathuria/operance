"""Helpers for session-scoped confirmation metadata."""

from __future__ import annotations

from .models.actions import ActionPlan, ToolName
from .planner import build_plan_preview
from .registry import describe_undo_behavior


def build_confirmation_metadata(
    plan: ActionPlan | None,
    *,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    if plan is None or not plan.actions:
        return {
            "pending_confirmation": False,
            "pending_plan_id": None,
            "pending_plan_preview": None,
            "pending_original_text": None,
            "pending_source": None,
            "pending_risk_tier": None,
            "pending_action": None,
            "pending_affected_resources": [],
            "pending_rollback_hint": None,
            "pending_timeout_seconds": None,
            "pending_timeout_behavior": None,
            "tool": None,
        }

    action = plan.actions[0]
    return {
        "pending_confirmation": True,
        "pending_plan_id": plan.plan_id,
        "pending_plan_preview": build_plan_preview(plan),
        "pending_original_text": plan.original_text,
        "pending_source": plan.source.value,
        "pending_risk_tier": int(action.risk_tier),
        "pending_action": action.to_dict(),
        "pending_affected_resources": _affected_resources(action.tool, action.args),
        "pending_rollback_hint": describe_undo_behavior(action.tool, action.undoable),
        "pending_timeout_seconds": timeout_seconds,
        "pending_timeout_behavior": _timeout_behavior(timeout_seconds),
        "tool": action.tool.value,
    }


def _affected_resources(tool: ToolName, args: dict[str, object]) -> list[str]:
    if tool == ToolName.APPS_QUIT:
        return [f"app: {args['app']}"]
    if tool == ToolName.WINDOWS_CLOSE:
        return [f"window: {args['window']}"]
    if tool == ToolName.FILES_DELETE_FOLDER:
        return [f"desktop folder: {args['name']}"]
    if tool == ToolName.FILES_DELETE_FILE:
        return [f"desktop file: {args['name']}"]
    if tool == ToolName.FILES_RENAME:
        return [f"desktop entry: {args['source_name']}", f"desktop name: {args['target_name']}"]
    if tool == ToolName.FILES_MOVE:
        return [f"desktop entry: {args['name']}", f"desktop folder: {args['destination_folder']}"]
    if tool == ToolName.NETWORK_DISCONNECT_CURRENT:
        return ["current Wi-Fi connection"]
    if tool == ToolName.NETWORK_SET_WIFI_ENABLED:
        return ["wi-fi state"]
    if tool == ToolName.NETWORK_CONNECT_KNOWN_SSID:
        return [f"known Wi-Fi network: {args['ssid']}"]
    if tool == ToolName.AUDIO_SET_VOLUME:
        return ["audio output volume"]
    return []


def _timeout_behavior(timeout_seconds: float | None) -> str | None:
    if timeout_seconds is None:
        return None
    return f"Pending command expires after {timeout_seconds:g} seconds without confirmation."
