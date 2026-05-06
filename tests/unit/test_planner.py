import pytest

from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction


def test_planner_action_plan_rejects_more_than_two_actions() -> None:
    with pytest.raises(ValueError, match="at most 2 actions"):
        ActionPlan(
            source=PlanSource.PLANNER,
            original_text="set volume to 20 and mute and open firefox",
            actions=[
                TypedAction(tool=ToolName.AUDIO_SET_VOLUME, args={"percent": 20}, risk_tier=RiskTier.TIER_1),
                TypedAction(tool=ToolName.AUDIO_SET_MUTED, args={"muted": True}, risk_tier=RiskTier.TIER_1),
                TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": "firefox"}, risk_tier=RiskTier.TIER_0),
            ],
        )


def test_plan_preview_renders_single_action_plan() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="open firefox",
        actions=[
            TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": "firefox"}, risk_tier=RiskTier.TIER_0),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: launch firefox."


def test_plan_preview_renders_url_launch_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="open localhost:3000",
        actions=[
            TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": "localhost:3000"}, risk_tier=RiskTier.TIER_0),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: open URL http://localhost:3000."


def test_plan_preview_renders_recent_file_open_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="open recent file called notes.txt",
        actions=[
            TypedAction(
                tool=ToolName.FILES_OPEN,
                args={"location": "recent", "name": "notes.txt"},
                risk_tier=RiskTier.TIER_0,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: open recent file 'notes.txt'."


def test_plan_preview_renders_quit_app_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="quit firefox",
        actions=[
            TypedAction(tool=ToolName.APPS_QUIT, args={"app": "firefox"}, risk_tier=RiskTier.TIER_2),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: quit firefox."


def test_plan_preview_renders_wifi_status_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="check wifi status",
        actions=[
            TypedAction(tool=ToolName.NETWORK_WIFI_STATUS, args={}, risk_tier=RiskTier.TIER_0),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: check Wi-Fi status."


def test_plan_preview_renders_disconnect_current_wifi_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="disconnect wifi",
        actions=[
            TypedAction(tool=ToolName.NETWORK_DISCONNECT_CURRENT, args={}, risk_tier=RiskTier.TIER_2),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: disconnect current Wi-Fi."


def test_plan_preview_renders_connect_known_wifi_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="connect to wifi home",
        actions=[
            TypedAction(tool=ToolName.NETWORK_CONNECT_KNOWN_SSID, args={"ssid": "home"}, risk_tier=RiskTier.TIER_2),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: connect to known Wi-Fi 'home'."


def test_plan_preview_renders_audio_mute_status_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="check audio mute state",
        actions=[
            TypedAction(tool=ToolName.AUDIO_MUTE_STATUS, args={}, risk_tier=RiskTier.TIER_0),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: check whether audio is muted."


def test_plan_preview_renders_clipboard_set_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="copy build complete",
        actions=[
            TypedAction(tool=ToolName.CLIPBOARD_SET_TEXT, args={"text": "build complete"}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: copy text to clipboard."


def test_plan_preview_renders_clipboard_copy_selection_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="copy selection",
        actions=[
            TypedAction(tool=ToolName.CLIPBOARD_COPY_SELECTION, args={}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: copy selected text to clipboard."


def test_plan_preview_renders_clipboard_clear_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="clear clipboard",
        actions=[
            TypedAction(tool=ToolName.CLIPBOARD_CLEAR, args={}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: clear clipboard."


def test_plan_preview_renders_clipboard_paste_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="paste clipboard",
        actions=[
            TypedAction(tool=ToolName.CLIPBOARD_PASTE, args={}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: paste clipboard into the active window."


def test_plan_preview_renders_text_type_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="type build complete",
        actions=[
            TypedAction(tool=ToolName.TEXT_TYPE, args={"text": "build complete"}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: type text into the active window."


def test_plan_preview_renders_press_key_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="press enter",
        actions=[
            TypedAction(tool=ToolName.KEYS_PRESS, args={"key": "enter"}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: press the enter key."


def test_plan_preview_renders_maximize_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="maximize firefox",
        actions=[
            TypedAction(tool=ToolName.WINDOWS_MAXIMIZE, args={"window": "firefox"}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: maximize window 'firefox'."


def test_plan_preview_renders_set_fullscreen_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="fullscreen firefox",
        actions=[
            TypedAction(
                tool=ToolName.WINDOWS_SET_FULLSCREEN,
                args={"window": "firefox", "enabled": True},
                risk_tier=RiskTier.TIER_1,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: enable fullscreen for window 'firefox'."


def test_plan_preview_renders_set_keep_above_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="keep firefox above",
        actions=[
            TypedAction(
                tool=ToolName.WINDOWS_SET_KEEP_ABOVE,
                args={"window": "firefox", "enabled": True},
                risk_tier=RiskTier.TIER_1,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: keep window 'firefox' above others."


def test_plan_preview_renders_set_shaded_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="shade firefox",
        actions=[
            TypedAction(
                tool=ToolName.WINDOWS_SET_SHADED,
                args={"window": "firefox", "enabled": True},
                risk_tier=RiskTier.TIER_1,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: shade window 'firefox'."


def test_plan_preview_renders_set_keep_below_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="keep firefox below",
        actions=[
            TypedAction(
                tool=ToolName.WINDOWS_SET_KEEP_BELOW,
                args={"window": "firefox", "enabled": True},
                risk_tier=RiskTier.TIER_1,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: keep window 'firefox' below others."


def test_plan_preview_renders_set_on_all_desktops_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="show firefox on all desktops",
        actions=[
            TypedAction(
                tool=ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
                args={"window": "firefox", "enabled": True},
                risk_tier=RiskTier.TIER_1,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: show window 'firefox' on all desktops."


def test_plan_preview_renders_restore_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="restore firefox",
        actions=[
            TypedAction(tool=ToolName.WINDOWS_RESTORE, args={"window": "firefox"}, risk_tier=RiskTier.TIER_1),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: restore window 'firefox'."


def test_plan_preview_renders_close_window_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="close firefox",
        actions=[
            TypedAction(tool=ToolName.WINDOWS_CLOSE, args={"window": "firefox"}, risk_tier=RiskTier.TIER_2),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: close window 'firefox'."


def test_plan_preview_renders_delete_folder_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="delete projects folder",
        actions=[
            TypedAction(
                tool=ToolName.FILES_DELETE_FOLDER,
                args={"location": "desktop", "name": "projects"},
                risk_tier=RiskTier.TIER_2,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: delete folder 'projects'."


def test_plan_preview_renders_delete_file_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="delete notes file",
        actions=[
            TypedAction(
                tool=ToolName.FILES_DELETE_FILE,
                args={"location": "desktop", "name": "notes.txt"},
                risk_tier=RiskTier.TIER_2,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: delete file 'notes.txt'."


def test_plan_preview_renders_open_entry_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="open notes",
        actions=[
            TypedAction(
                tool=ToolName.FILES_OPEN,
                args={"location": "desktop", "name": "notes.txt"},
                risk_tier=RiskTier.TIER_0,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: open desktop entry 'notes.txt'."


def test_plan_preview_renders_rename_entry_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="rename projects",
        actions=[
            TypedAction(
                tool=ToolName.FILES_RENAME,
                args={"location": "desktop", "source_name": "projects", "target_name": "archive"},
                risk_tier=RiskTier.TIER_2,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: rename desktop entry 'projects' to 'archive'."


def test_plan_preview_renders_move_entry_action() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="move projects",
        actions=[
            TypedAction(
                tool=ToolName.FILES_MOVE,
                args={"location": "desktop", "name": "projects", "destination_folder": "archive"},
                risk_tier=RiskTier.TIER_2,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert preview == "Planned action: move desktop entry 'projects' to folder 'archive'."


def test_plan_preview_renders_two_step_plan() -> None:
    from operance.planner.preview import build_plan_preview

    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="turn wifi off and show a notification",
        actions=[
            TypedAction(
                tool=ToolName.NETWORK_SET_WIFI_ENABLED,
                args={"enabled": False},
                risk_tier=RiskTier.TIER_1,
            ),
            TypedAction(
                tool=ToolName.NOTIFICATIONS_SHOW,
                args={"title": "Wi-Fi", "message": "Wi-Fi disabled"},
                risk_tier=RiskTier.TIER_0,
            ),
        ],
    )

    preview = build_plan_preview(plan)

    assert (
        preview
        == "Planned actions: disable Wi-Fi, then show notification 'Wi-Fi'."
    )


def test_parse_planner_payload_builds_typed_action_plan() -> None:
    from operance.planner.parser import parse_planner_payload

    plan = parse_planner_payload(
        {
            "actions": [
                {"tool": "apps.launch", "args": {"app": "firefox"}},
                {"tool": "notifications.show", "args": {"title": "Opened", "message": "Firefox launched"}},
            ]
        },
        original_text="open firefox and notify me",
    )

    assert plan.source == PlanSource.PLANNER
    assert plan.original_text == "open firefox and notify me"
    assert len(plan.actions) == 2
    assert plan.actions[0].tool == ToolName.APPS_LAUNCH
    assert plan.actions[1].tool == ToolName.NOTIFICATIONS_SHOW


def test_parse_planner_payload_rejects_unknown_tool() -> None:
    from operance.planner.parser import PlannerParseError, parse_planner_payload

    with pytest.raises(PlannerParseError, match="unknown tool"):
        parse_planner_payload(
            {
                "actions": [
                    {"tool": "shell.exec", "args": {"command": "rm -rf /"}},
                ]
            },
            original_text="run shell command",
        )


def test_parse_planner_payload_rejects_non_dict_args() -> None:
    from operance.planner.parser import PlannerParseError, parse_planner_payload

    with pytest.raises(PlannerParseError, match="args must be an object"):
        parse_planner_payload(
            {
                "actions": [
                    {"tool": "apps.launch", "args": ["firefox"]},
                ]
            },
            original_text="open firefox",
        )


def test_planner_payload_schema_limits_actions_to_two_steps() -> None:
    from operance.planner.schema import build_planner_payload_schema

    schema = build_planner_payload_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["actions"]
    assert schema["properties"]["actions"]["minItems"] == 1
    assert schema["properties"]["actions"]["maxItems"] == 2
    assert "apps.launch" in schema["properties"]["actions"]["items"]["properties"]["tool"]["enum"]
