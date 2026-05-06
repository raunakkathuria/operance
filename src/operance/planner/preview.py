"""Plain-language preview rendering for planner-origin action plans."""

from __future__ import annotations

from ..launch_targets import is_url_like_target, normalize_launch_target
from ..models.actions import ActionPlan, ToolName


def build_plan_preview(plan: ActionPlan) -> str:
    descriptions = [_describe_action(action.tool, action.args) for action in plan.actions]

    if len(descriptions) == 1:
        return f"Planned action: {descriptions[0]}."

    if len(descriptions) == 2:
        return f"Planned actions: {descriptions[0]}, then {descriptions[1]}."

    raise ValueError("plan preview supports at most 2 actions")


def _describe_action(tool: ToolName, args: dict[str, object]) -> str:
    if tool == ToolName.APPS_LAUNCH:
        if is_url_like_target(str(args["app"])):
            return f"open URL {normalize_launch_target(str(args['app']))}"
        return f"launch {args['app']}"

    if tool == ToolName.APPS_QUIT:
        return f"quit {args['app']}"

    if tool == ToolName.NETWORK_SET_WIFI_ENABLED:
        enabled = bool(args["enabled"])
        return "enable Wi-Fi" if enabled else "disable Wi-Fi"

    if tool == ToolName.NETWORK_WIFI_STATUS:
        return "check Wi-Fi status"

    if tool == ToolName.NETWORK_DISCONNECT_CURRENT:
        return "disconnect current Wi-Fi"

    if tool == ToolName.NETWORK_CONNECT_KNOWN_SSID:
        return f"connect to known Wi-Fi {args['ssid']!r}"

    if tool == ToolName.NOTIFICATIONS_SHOW:
        return f"show notification {args['title']!r}"

    if tool == ToolName.AUDIO_SET_VOLUME:
        return f"set volume to {args['percent']}%"

    if tool == ToolName.AUDIO_MUTE_STATUS:
        return "check whether audio is muted"

    if tool == ToolName.CLIPBOARD_GET_TEXT:
        return "read clipboard text"

    if tool == ToolName.CLIPBOARD_SET_TEXT:
        return "copy text to clipboard"

    if tool == ToolName.CLIPBOARD_COPY_SELECTION:
        return "copy selected text to clipboard"

    if tool == ToolName.CLIPBOARD_CLEAR:
        return "clear clipboard"

    if tool == ToolName.CLIPBOARD_PASTE:
        return "paste clipboard into the active window"

    if tool == ToolName.TEXT_TYPE:
        return "type text into the active window"

    if tool == ToolName.KEYS_PRESS:
        return f"press the {args['key']} key"

    if tool == ToolName.AUDIO_SET_MUTED:
        muted = bool(args["muted"])
        return "mute audio" if muted else "unmute audio"

    if tool == ToolName.TIME_NOW:
        return "get the current time"

    if tool == ToolName.POWER_BATTERY_STATUS:
        return "check battery status"

    if tool == ToolName.FILES_LIST_RECENT:
        return "list recent files"

    if tool == ToolName.FILES_OPEN:
        if args.get("location") == "recent":
            return f"open recent file {args['name']!r}"
        return f"open desktop entry {args['name']!r}"

    if tool == ToolName.FILES_CREATE_FOLDER:
        return f"create folder {args['name']!r}"

    if tool == ToolName.FILES_DELETE_FOLDER:
        return f"delete folder {args['name']!r}"

    if tool == ToolName.FILES_DELETE_FILE:
        return f"delete file {args['name']!r}"

    if tool == ToolName.FILES_RENAME:
        return f"rename desktop entry {args['source_name']!r} to {args['target_name']!r}"

    if tool == ToolName.FILES_MOVE:
        return f"move desktop entry {args['name']!r} to folder {args['destination_folder']!r}"

    if tool == ToolName.APPS_FOCUS:
        return f"focus {args['app']}"

    if tool == ToolName.WINDOWS_LIST:
        return "list windows"

    if tool == ToolName.WINDOWS_SWITCH:
        return f"switch to window {args['window']!r}"

    if tool == ToolName.WINDOWS_MINIMIZE:
        return f"minimize window {args['window']!r}"

    if tool == ToolName.WINDOWS_MAXIMIZE:
        return f"maximize window {args['window']!r}"

    if tool == ToolName.WINDOWS_SET_FULLSCREEN:
        enabled = bool(args["enabled"])
        return (
            f"enable fullscreen for window {args['window']!r}"
            if enabled
            else f"disable fullscreen for window {args['window']!r}"
        )

    if tool == ToolName.WINDOWS_SET_KEEP_ABOVE:
        enabled = bool(args["enabled"])
        return (
            f"keep window {args['window']!r} above others"
            if enabled
            else f"stop keeping window {args['window']!r} above others"
        )

    if tool == ToolName.WINDOWS_SET_SHADED:
        enabled = bool(args["enabled"])
        return (
            f"shade window {args['window']!r}"
            if enabled
            else f"unshade window {args['window']!r}"
        )

    if tool == ToolName.WINDOWS_SET_KEEP_BELOW:
        enabled = bool(args["enabled"])
        return (
            f"keep window {args['window']!r} below others"
            if enabled
            else f"stop keeping window {args['window']!r} below others"
        )

    if tool == ToolName.WINDOWS_SET_ON_ALL_DESKTOPS:
        enabled = bool(args["enabled"])
        return (
            f"show window {args['window']!r} on all desktops"
            if enabled
            else f"show window {args['window']!r} only on this desktop"
        )

    if tool == ToolName.WINDOWS_RESTORE:
        return f"restore window {args['window']!r}"

    if tool == ToolName.WINDOWS_CLOSE:
        return f"close window {args['window']!r}"

    if tool == ToolName.AUDIO_GET_VOLUME:
        return "get volume"

    return tool.value
