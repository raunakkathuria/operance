import pytest

from operance.models.actions import PlanSource, RiskTier, ToolName


@pytest.mark.parametrize(
    ("text", "tool", "args", "risk_tier", "requires_confirmation"),
    [
        ("open firefox", ToolName.APPS_LAUNCH, {"app": "firefox"}, RiskTier.TIER_0, False),
        ("Open Firefox", ToolName.APPS_LAUNCH, {"app": "firefox"}, RiskTier.TIER_0, False),
        ("open terminal", ToolName.APPS_LAUNCH, {"app": "terminal"}, RiskTier.TIER_0, False),
        ("open code", ToolName.APPS_LAUNCH, {"app": "code"}, RiskTier.TIER_0, False),
        ("please open code", ToolName.APPS_LAUNCH, {"app": "code"}, RiskTier.TIER_0, False),
        ("open app code", ToolName.APPS_LAUNCH, {"app": "code"}, RiskTier.TIER_0, False),
        ("open http://localhost:3000", ToolName.APPS_LAUNCH, {"app": "http://localhost:3000"}, RiskTier.TIER_0, False),
        ("open localhost:3000", ToolName.APPS_LAUNCH, {"app": "localhost:3000"}, RiskTier.TIER_0, False),
        ("browse to localhost 3000", ToolName.APPS_LAUNCH, {"app": "http://localhost:3000"}, RiskTier.TIER_0, False),
        ("open url localhost port 3000", ToolName.APPS_LAUNCH, {"app": "http://localhost:3000"}, RiskTier.TIER_0, False),
        ("browse to docs.python.org/3", ToolName.APPS_LAUNCH, {"app": "https://docs.python.org/3"}, RiskTier.TIER_0, False),
        (
            "open url github.com/openai/openai-python",
            ToolName.APPS_LAUNCH,
            {"app": "https://github.com/openai/openai-python"},
            RiskTier.TIER_0,
            False,
        ),
        (
            "launch visual studio code",
            ToolName.APPS_LAUNCH,
            {"app": "visual studio code"},
            RiskTier.TIER_0,
            False,
        ),
        ("focus firefox", ToolName.APPS_FOCUS, {"app": "firefox"}, RiskTier.TIER_0, False),
        ("focus terminal", ToolName.APPS_FOCUS, {"app": "terminal"}, RiskTier.TIER_0, False),
        ("focus code", ToolName.APPS_FOCUS, {"app": "code"}, RiskTier.TIER_0, False),
        ("switch to code", ToolName.APPS_FOCUS, {"app": "code"}, RiskTier.TIER_0, False),
        ("focus app code", ToolName.APPS_FOCUS, {"app": "code"}, RiskTier.TIER_0, False),
        ("switch to app code", ToolName.APPS_FOCUS, {"app": "code"}, RiskTier.TIER_0, False),
        ("quit firefox", ToolName.APPS_QUIT, {"app": "firefox"}, RiskTier.TIER_2, True),
        ("list windows", ToolName.WINDOWS_LIST, {}, RiskTier.TIER_0, False),
        ("switch to window firefox", ToolName.WINDOWS_SWITCH, {"window": "firefox"}, RiskTier.TIER_0, False),
        ("minimize window firefox", ToolName.WINDOWS_MINIMIZE, {"window": "firefox"}, RiskTier.TIER_1, False),
        ("maximize window firefox", ToolName.WINDOWS_MAXIMIZE, {"window": "firefox"}, RiskTier.TIER_1, False),
        (
            "fullscreen window firefox",
            ToolName.WINDOWS_SET_FULLSCREEN,
            {"window": "firefox", "enabled": True},
            RiskTier.TIER_1,
            False,
        ),
        (
            "exit fullscreen for window firefox",
            ToolName.WINDOWS_SET_FULLSCREEN,
            {"window": "firefox", "enabled": False},
            RiskTier.TIER_1,
            False,
        ),
        (
            "keep window firefox above",
            ToolName.WINDOWS_SET_KEEP_ABOVE,
            {"window": "firefox", "enabled": True},
            RiskTier.TIER_1,
            False,
        ),
        (
            "stop keeping window firefox above",
            ToolName.WINDOWS_SET_KEEP_ABOVE,
            {"window": "firefox", "enabled": False},
            RiskTier.TIER_1,
            False,
        ),
        (
            "shade window firefox",
            ToolName.WINDOWS_SET_SHADED,
            {"window": "firefox", "enabled": True},
            RiskTier.TIER_1,
            False,
        ),
        (
            "unshade window firefox",
            ToolName.WINDOWS_SET_SHADED,
            {"window": "firefox", "enabled": False},
            RiskTier.TIER_1,
            False,
        ),
        (
            "keep window firefox below",
            ToolName.WINDOWS_SET_KEEP_BELOW,
            {"window": "firefox", "enabled": True},
            RiskTier.TIER_1,
            False,
        ),
        (
            "stop keeping window firefox below",
            ToolName.WINDOWS_SET_KEEP_BELOW,
            {"window": "firefox", "enabled": False},
            RiskTier.TIER_1,
            False,
        ),
        (
            "show window firefox on all desktops",
            ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
            {"window": "firefox", "enabled": True},
            RiskTier.TIER_1,
            False,
        ),
        (
            "show window firefox only on this desktop",
            ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
            {"window": "firefox", "enabled": False},
            RiskTier.TIER_1,
            False,
        ),
        ("restore window firefox", ToolName.WINDOWS_RESTORE, {"window": "firefox"}, RiskTier.TIER_1, False),
        ("close window firefox", ToolName.WINDOWS_CLOSE, {"window": "firefox"}, RiskTier.TIER_2, True),
        ("what time is it", ToolName.TIME_NOW, {}, RiskTier.TIER_0, False),
        ("what is my battery level", ToolName.POWER_BATTERY_STATUS, {}, RiskTier.TIER_0, False),
        ("what is the volume", ToolName.AUDIO_GET_VOLUME, {}, RiskTier.TIER_0, False),
        ("is audio muted", ToolName.AUDIO_MUTE_STATUS, {}, RiskTier.TIER_0, False),
        ("what is on the clipboard", ToolName.CLIPBOARD_GET_TEXT, {}, RiskTier.TIER_0, False),
        ("copy build complete to clipboard", ToolName.CLIPBOARD_SET_TEXT, {"text": "build complete"}, RiskTier.TIER_1, False),
        ("copy selection", ToolName.CLIPBOARD_COPY_SELECTION, {}, RiskTier.TIER_1, False),
        ("copy selected text", ToolName.CLIPBOARD_COPY_SELECTION, {}, RiskTier.TIER_1, False),
        ("clear clipboard", ToolName.CLIPBOARD_CLEAR, {}, RiskTier.TIER_1, False),
        ("paste clipboard", ToolName.CLIPBOARD_PASTE, {}, RiskTier.TIER_1, False),
        ("paste from clipboard", ToolName.CLIPBOARD_PASTE, {}, RiskTier.TIER_1, False),
        ("type build complete", ToolName.TEXT_TYPE, {"text": "build complete"}, RiskTier.TIER_1, False),
        ("press enter", ToolName.KEYS_PRESS, {"key": "enter"}, RiskTier.TIER_1, False),
        ("press control c", ToolName.KEYS_PRESS, {"key": "ctrl+c"}, RiskTier.TIER_1, False),
        ("press ctrl shift p", ToolName.KEYS_PRESS, {"key": "ctrl+shift+p"}, RiskTier.TIER_1, False),
        ("hit escape", ToolName.KEYS_PRESS, {"key": "escape"}, RiskTier.TIER_1, False),
        ("wifi status", ToolName.NETWORK_WIFI_STATUS, {}, RiskTier.TIER_0, False),
        ("disconnect wifi", ToolName.NETWORK_DISCONNECT_CURRENT, {}, RiskTier.TIER_2, True),
        ("connect to wifi home", ToolName.NETWORK_CONNECT_KNOWN_SSID, {"ssid": "home"}, RiskTier.TIER_2, True),
        ("set volume to 50 percent", ToolName.AUDIO_SET_VOLUME, {"percent": 50}, RiskTier.TIER_1, False),
        ("set volume to 90 percent", ToolName.AUDIO_SET_VOLUME, {"percent": 90}, RiskTier.TIER_2, True),
        ("mute audio", ToolName.AUDIO_SET_MUTED, {"muted": True}, RiskTier.TIER_1, False),
        ("unmute audio", ToolName.AUDIO_SET_MUTED, {"muted": False}, RiskTier.TIER_1, False),
        ("turn wi-fi off", ToolName.NETWORK_SET_WIFI_ENABLED, {"enabled": False}, RiskTier.TIER_2, True),
        ("turn wifi on", ToolName.NETWORK_SET_WIFI_ENABLED, {"enabled": True}, RiskTier.TIER_1, False),
        (
            "show a notification saying build complete",
            ToolName.NOTIFICATIONS_SHOW,
            {"message": "build complete", "title": "Operance"},
            RiskTier.TIER_0,
            False,
        ),
        (
            "show files modified today",
            ToolName.FILES_LIST_RECENT,
            {"modified_since": "today"},
            RiskTier.TIER_0,
            False,
        ),
        (
            "open file on desktop called notes.txt",
            ToolName.FILES_OPEN,
            {"location": "desktop", "name": "notes.txt"},
            RiskTier.TIER_0,
            False,
        ),
        (
            "open recent file called notes.txt",
            ToolName.FILES_OPEN,
            {"location": "recent", "name": "notes.txt"},
            RiskTier.TIER_0,
            False,
        ),
        (
            "create folder on desktop called projects",
            ToolName.FILES_CREATE_FOLDER,
            {"location": "desktop", "name": "projects"},
            RiskTier.TIER_1,
            False,
        ),
        (
            "delete folder on desktop called projects",
            ToolName.FILES_DELETE_FOLDER,
            {"location": "desktop", "name": "projects"},
            RiskTier.TIER_2,
            True,
        ),
        (
            "delete file on desktop called notes.txt",
            ToolName.FILES_DELETE_FILE,
            {"location": "desktop", "name": "notes.txt"},
            RiskTier.TIER_2,
            True,
        ),
        (
            "rename folder on desktop from projects to archive",
            ToolName.FILES_RENAME,
            {"location": "desktop", "source_name": "projects", "target_name": "archive"},
            RiskTier.TIER_2,
            True,
        ),
        (
            "move folder on desktop called projects to archive",
            ToolName.FILES_MOVE,
            {"location": "desktop", "name": "projects", "destination_folder": "archive"},
            RiskTier.TIER_2,
            True,
        ),
    ],
)
def test_deterministic_intent_matcher_builds_expected_action_plan(
    text: str,
    tool: ToolName,
    args: dict[str, object],
    risk_tier: RiskTier,
    requires_confirmation: bool,
) -> None:
    from operance.intent import DeterministicIntentMatcher

    matcher = DeterministicIntentMatcher()
    plan = matcher.match(text)

    assert plan is not None
    assert plan.source == PlanSource.DETERMINISTIC
    assert plan.original_text == text
    assert len(plan.actions) == 1
    assert plan.actions[0].tool == tool
    assert plan.actions[0].args == args
    assert plan.actions[0].risk_tier == risk_tier
    assert plan.actions[0].requires_confirmation is requires_confirmation


def test_deterministic_intent_matcher_returns_none_for_unknown_command() -> None:
    from operance.intent import DeterministicIntentMatcher

    matcher = DeterministicIntentMatcher()

    assert matcher.match("install updates") is None
    assert matcher.match("open firefox and notify me") is None
    assert matcher.match("open firefox and load notes") is None
    assert matcher.match("focus localhost:3000") is None


@pytest.mark.parametrize(
    ("text", "expected_url"),
    [
        ("open firefox and load localhost:3000", "http://localhost:3000"),
        ("open firefox and open localhost:3000", "localhost:3000"),
        ("launch firefox then browse to localhost 3000", "http://localhost:3000"),
        ("open firefox then load docs.python.org/3", "https://docs.python.org/3"),
    ],
)
def test_deterministic_intent_matcher_builds_two_step_launch_plan(text: str, expected_url: str) -> None:
    from operance.intent import DeterministicIntentMatcher

    matcher = DeterministicIntentMatcher()

    plan = matcher.match(text)

    assert plan is not None
    assert plan.source == PlanSource.DETERMINISTIC
    assert plan.original_text == text
    assert len(plan.actions) == 2
    assert [action.tool for action in plan.actions] == [ToolName.APPS_LAUNCH, ToolName.APPS_LAUNCH]
    assert [action.args for action in plan.actions] == [{"app": "firefox"}, {"app": expected_url}]
    assert all(action.risk_tier == RiskTier.TIER_0 for action in plan.actions)
    assert all(action.requires_confirmation is False for action in plan.actions)
