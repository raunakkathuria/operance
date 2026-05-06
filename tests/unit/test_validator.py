from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction


def test_default_action_registry_exposes_seed_command_specs() -> None:
    from operance.registry import build_default_action_registry

    registry = build_default_action_registry()

    launch_spec = registry.get(ToolName.APPS_LAUNCH)
    quit_spec = registry.get(ToolName.APPS_QUIT)
    volume_spec = registry.get(ToolName.AUDIO_SET_VOLUME)
    window_fullscreen_spec = registry.get(ToolName.WINDOWS_SET_FULLSCREEN)
    window_keep_above_spec = registry.get(ToolName.WINDOWS_SET_KEEP_ABOVE)
    window_shaded_spec = registry.get(ToolName.WINDOWS_SET_SHADED)
    window_keep_below_spec = registry.get(ToolName.WINDOWS_SET_KEEP_BELOW)
    window_all_desktops_spec = registry.get(ToolName.WINDOWS_SET_ON_ALL_DESKTOPS)
    clipboard_set_spec = registry.get(ToolName.CLIPBOARD_SET_TEXT)
    clipboard_copy_selection_spec = registry.get(ToolName.CLIPBOARD_COPY_SELECTION)
    clipboard_clear_spec = registry.get(ToolName.CLIPBOARD_CLEAR)
    clipboard_paste_spec = registry.get(ToolName.CLIPBOARD_PASTE)
    text_type_spec = registry.get(ToolName.TEXT_TYPE)
    key_press_spec = registry.get(ToolName.KEYS_PRESS)
    disconnect_spec = registry.get(ToolName.NETWORK_DISCONNECT_CURRENT)
    connect_ssid_spec = registry.get(ToolName.NETWORK_CONNECT_KNOWN_SSID)
    delete_file_spec = registry.get(ToolName.FILES_DELETE_FILE)
    rename_spec = registry.get(ToolName.FILES_RENAME)

    assert launch_spec is not None
    assert launch_spec.required_args == ("app",)
    assert launch_spec.risk_tier == RiskTier.TIER_0
    assert launch_spec.example_transcripts == (
        "open firefox",
        "open http://localhost:3000",
        "browse to localhost 3000",
        "browse to docs.python.org/3",
    )
    assert launch_spec.allowed_side_effects == ("launch_app", "open_url")
    assert launch_spec.result_schema["properties"]["tool"] == {"type": "string", "const": "apps.launch"}
    assert launch_spec.undo_summary is None

    assert quit_spec is not None
    assert quit_spec.required_args == ("app",)
    assert quit_spec.risk_tier == RiskTier.TIER_2
    assert quit_spec.requires_confirmation is True
    assert quit_spec.example_transcripts == ("quit firefox",)
    assert quit_spec.allowed_side_effects == ("quit_app", "close_app_windows")
    assert quit_spec.undo_summary == "No automatic undo is available after execution."

    assert volume_spec is not None
    assert volume_spec.required_args == ("percent",)
    assert volume_spec.risk_tier == RiskTier.TIER_1
    assert volume_spec.example_transcripts == ("set volume to 50 percent",)
    assert volume_spec.allowed_side_effects == ("set_audio_volume",)
    assert volume_spec.undo_summary == "Undo will restore the previous volume."

    assert window_fullscreen_spec is not None
    assert window_fullscreen_spec.required_args == ("window", "enabled")
    assert window_fullscreen_spec.risk_tier == RiskTier.TIER_1
    assert window_fullscreen_spec.requires_confirmation is False
    assert window_fullscreen_spec.undoable is False
    assert window_fullscreen_spec.example_transcripts == (
        "fullscreen window firefox",
        "exit fullscreen for window firefox",
    )
    assert window_fullscreen_spec.allowed_side_effects == ("set_window_fullscreen",)
    assert (
        window_fullscreen_spec.undo_summary
        == "No automatic undo is available because the previous window state is not tracked safely."
    )

    assert window_keep_above_spec is not None
    assert window_keep_above_spec.required_args == ("window", "enabled")
    assert window_keep_above_spec.risk_tier == RiskTier.TIER_1
    assert window_keep_above_spec.requires_confirmation is False
    assert window_keep_above_spec.undoable is False
    assert window_keep_above_spec.example_transcripts == (
        "keep window firefox above",
        "stop keeping window firefox above",
    )
    assert window_keep_above_spec.allowed_side_effects == ("set_window_keep_above",)
    assert (
        window_keep_above_spec.undo_summary
        == "No automatic undo is available because the previous window state is not tracked safely."
    )

    assert window_shaded_spec is not None
    assert window_shaded_spec.required_args == ("window", "enabled")
    assert window_shaded_spec.risk_tier == RiskTier.TIER_1
    assert window_shaded_spec.requires_confirmation is False
    assert window_shaded_spec.undoable is False
    assert window_shaded_spec.example_transcripts == (
        "shade window firefox",
        "unshade window firefox",
    )
    assert window_shaded_spec.allowed_side_effects == ("set_window_shaded",)
    assert (
        window_shaded_spec.undo_summary
        == "No automatic undo is available because the previous window state is not tracked safely."
    )

    assert window_keep_below_spec is not None
    assert window_keep_below_spec.required_args == ("window", "enabled")
    assert window_keep_below_spec.risk_tier == RiskTier.TIER_1
    assert window_keep_below_spec.requires_confirmation is False
    assert window_keep_below_spec.undoable is False
    assert window_keep_below_spec.example_transcripts == (
        "keep window firefox below",
        "stop keeping window firefox below",
    )
    assert window_keep_below_spec.allowed_side_effects == ("set_window_keep_below",)
    assert (
        window_keep_below_spec.undo_summary
        == "No automatic undo is available because the previous window state is not tracked safely."
    )

    assert window_all_desktops_spec is not None
    assert window_all_desktops_spec.required_args == ("window", "enabled")
    assert window_all_desktops_spec.risk_tier == RiskTier.TIER_1
    assert window_all_desktops_spec.requires_confirmation is False
    assert window_all_desktops_spec.undoable is False
    assert window_all_desktops_spec.example_transcripts == (
        "show window firefox on all desktops",
        "show window firefox only on this desktop",
    )
    assert window_all_desktops_spec.allowed_side_effects == ("set_window_on_all_desktops",)
    assert (
        window_all_desktops_spec.undo_summary
        == "No automatic undo is available because the previous window state is not tracked safely."
    )

    assert clipboard_set_spec is not None
    assert clipboard_set_spec.required_args == ("text",)
    assert clipboard_set_spec.risk_tier == RiskTier.TIER_1
    assert clipboard_set_spec.requires_confirmation is False
    assert clipboard_set_spec.undoable is True
    assert clipboard_set_spec.example_transcripts == ("copy build complete to clipboard",)
    assert clipboard_set_spec.allowed_side_effects == ("set_clipboard_text",)
    assert clipboard_set_spec.undo_summary == "Undo will restore the previous clipboard text."

    assert clipboard_copy_selection_spec is not None
    assert clipboard_copy_selection_spec.required_args == ()
    assert clipboard_copy_selection_spec.risk_tier == RiskTier.TIER_1
    assert clipboard_copy_selection_spec.requires_confirmation is False
    assert clipboard_copy_selection_spec.undoable is True
    assert clipboard_copy_selection_spec.example_transcripts == ("copy selection",)
    assert clipboard_copy_selection_spec.allowed_side_effects == ("copy_selection_to_clipboard",)
    assert clipboard_copy_selection_spec.undo_summary == "Undo will restore the previous clipboard text."

    assert clipboard_clear_spec is not None
    assert clipboard_clear_spec.required_args == ()
    assert clipboard_clear_spec.risk_tier == RiskTier.TIER_1
    assert clipboard_clear_spec.requires_confirmation is False
    assert clipboard_clear_spec.undoable is True
    assert clipboard_clear_spec.example_transcripts == ("clear clipboard",)
    assert clipboard_clear_spec.allowed_side_effects == ("clear_clipboard",)
    assert clipboard_clear_spec.undo_summary == "Undo will restore the previous clipboard text."

    assert clipboard_paste_spec is not None
    assert clipboard_paste_spec.required_args == ()
    assert clipboard_paste_spec.risk_tier == RiskTier.TIER_1
    assert clipboard_paste_spec.requires_confirmation is False
    assert clipboard_paste_spec.undoable is False
    assert clipboard_paste_spec.example_transcripts == ("paste clipboard",)
    assert clipboard_paste_spec.allowed_side_effects == ("paste_clipboard_text",)
    assert (
        clipboard_paste_spec.undo_summary
        == "No automatic undo is available because the target application state is not tracked safely."
    )

    assert text_type_spec is not None
    assert text_type_spec.required_args == ("text",)
    assert text_type_spec.risk_tier == RiskTier.TIER_1
    assert text_type_spec.requires_confirmation is False
    assert text_type_spec.undoable is False
    assert text_type_spec.example_transcripts == ("type build complete",)
    assert text_type_spec.allowed_side_effects == ("type_text",)
    assert (
        text_type_spec.undo_summary
        == "No automatic undo is available because the target application state is not tracked safely."
    )

    assert key_press_spec is not None
    assert key_press_spec.required_args == ("key",)
    assert key_press_spec.risk_tier == RiskTier.TIER_1
    assert key_press_spec.requires_confirmation is False
    assert key_press_spec.undoable is False
    assert key_press_spec.example_transcripts == ("press enter", "press control c", "press control shift p")
    assert key_press_spec.allowed_side_effects == ("press_key",)
    assert (
        key_press_spec.undo_summary
        == "No automatic undo is available because the target application state is not tracked safely."
    )

    assert disconnect_spec is not None
    assert disconnect_spec.required_args == ()
    assert disconnect_spec.risk_tier == RiskTier.TIER_2
    assert disconnect_spec.requires_confirmation is True
    assert disconnect_spec.allowed_side_effects == ("disconnect_wifi",)

    assert connect_ssid_spec is not None
    assert connect_ssid_spec.required_args == ("ssid",)
    assert connect_ssid_spec.risk_tier == RiskTier.TIER_2
    assert connect_ssid_spec.requires_confirmation is True
    assert connect_ssid_spec.undoable is False

    assert delete_file_spec is not None
    assert delete_file_spec.required_args == ("location", "name")
    assert delete_file_spec.risk_tier == RiskTier.TIER_2
    assert delete_file_spec.requires_confirmation is True
    assert delete_file_spec.undoable is False

    assert rename_spec is not None
    assert rename_spec.required_args == ("location", "source_name", "target_name")
    assert rename_spec.risk_tier == RiskTier.TIER_2
    assert rename_spec.requires_confirmation is True
    assert rename_spec.undoable is True
    assert rename_spec.example_transcripts == ("rename folder on desktop from projects to archive",)
    assert rename_spec.allowed_side_effects == ("rename_desktop_entry",)
    assert rename_spec.undo_summary == "Undo will restore the previous state."


def test_validator_normalizes_action_metadata_from_registry() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="set volume to 50 percent",
        actions=[
            TypedAction(
                tool=ToolName.AUDIO_SET_VOLUME,
                args={"percent": 50},
                risk_tier=RiskTier.TIER_0,
                requires_confirmation=True,
                undoable=False,
            )
        ],
    )

    result = validator.validate(plan)

    assert result.valid is True
    assert result.normalized_plan is not None
    assert result.normalized_plan.actions[0].risk_tier == RiskTier.TIER_1
    assert result.normalized_plan.actions[0].requires_confirmation is False


def test_validator_preserves_stricter_incoming_action_metadata() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="turn wifi off",
        actions=[
            TypedAction(
                tool=ToolName.NETWORK_SET_WIFI_ENABLED,
                args={"enabled": False},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
                undoable=False,
            )
        ],
    )

    result = validator.validate(plan)

    assert result.valid is True
    assert result.normalized_plan is not None
    assert result.normalized_plan.actions[0].risk_tier == RiskTier.TIER_2
    assert result.normalized_plan.actions[0].requires_confirmation is True


def test_validator_derives_confirmation_for_high_risk_action_args() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="set volume to 90 percent",
        actions=[
            TypedAction(
                tool=ToolName.AUDIO_SET_VOLUME,
                args={"percent": 90},
            )
        ],
    )

    result = validator.validate(plan)

    assert result.valid is True
    assert result.normalized_plan is not None
    assert result.normalized_plan.actions[0].risk_tier == RiskTier.TIER_2
    assert result.normalized_plan.actions[0].requires_confirmation is True


def test_validator_rejects_missing_required_args() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="open firefox",
        actions=[TypedAction(tool=ToolName.APPS_LAUNCH, args={})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors
    assert "missing required args" in result.errors[0]


def test_validator_rejects_blank_known_ssid() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="connect to wifi",
        actions=[TypedAction(tool=ToolName.NETWORK_CONNECT_KNOWN_SSID, args={"ssid": "   "})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["network.connect_known_ssid: ssid must be a non-empty string"]


def test_validator_rejects_blank_clipboard_text() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="copy nothing",
        actions=[TypedAction(tool=ToolName.CLIPBOARD_SET_TEXT, args={"text": "   "})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["clipboard.set_text: text must be a non-empty string"]


def test_validator_rejects_blank_typed_text() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="type nothing",
        actions=[TypedAction(tool=ToolName.TEXT_TYPE, args={"text": "   "})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["text.type: text must be a non-empty string"]


def test_validator_rejects_unsupported_pressed_key() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="press capslock",
        actions=[TypedAction(tool=ToolName.KEYS_PRESS, args={"key": "capslock"})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == [
        "keys.press: key must be one of: backspace, enter, escape, tab, ctrl+c, ctrl+v, ctrl+l, ctrl+r, ctrl+t, ctrl+w, ctrl+shift+p"
    ]


def test_validator_rejects_non_boolean_fullscreen_flag() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="fullscreen firefox",
        actions=[TypedAction(tool=ToolName.WINDOWS_SET_FULLSCREEN, args={"window": "firefox", "enabled": "yes"})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["windows.set_fullscreen: enabled must be a boolean"]


def test_validator_rejects_blank_keep_above_window_name() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="pin firefox",
        actions=[TypedAction(tool=ToolName.WINDOWS_SET_KEEP_ABOVE, args={"window": "   ", "enabled": True})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["windows.set_keep_above: window must be a non-empty string"]


def test_validator_rejects_non_boolean_shaded_flag() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="shade firefox",
        actions=[TypedAction(tool=ToolName.WINDOWS_SET_SHADED, args={"window": "firefox", "enabled": 1})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["windows.set_shaded: enabled must be a boolean"]


def test_validator_rejects_blank_keep_below_window_name() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="keep firefox below",
        actions=[TypedAction(tool=ToolName.WINDOWS_SET_KEEP_BELOW, args={"window": "", "enabled": True})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["windows.set_keep_below: window must be a non-empty string"]


def test_validator_rejects_non_boolean_all_desktops_flag() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="show firefox everywhere",
        actions=[TypedAction(tool=ToolName.WINDOWS_SET_ON_ALL_DESKTOPS, args={"window": "firefox", "enabled": "true"})],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["windows.set_on_all_desktops: enabled must be a boolean"]


def test_validator_rejects_unsafe_desktop_entry_names() -> None:
    from operance.registry import build_default_action_registry
    from operance.validator import PlanValidator

    validator = PlanValidator(registry=build_default_action_registry())
    plan = ActionPlan(
        source=PlanSource.PLANNER,
        original_text="rename desktop entry",
        actions=[
            TypedAction(
                tool=ToolName.FILES_RENAME,
                args={
                    "location": "desktop",
                    "source_name": "../projects",
                    "target_name": "archive",
                },
            )
        ],
    )

    result = validator.validate(plan)

    assert result.valid is False
    assert result.normalized_plan is None
    assert result.errors == ["files.rename: source_name must be a simple desktop entry name"]
