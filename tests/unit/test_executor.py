from pathlib import Path

import pytest

from operance.intent import DeterministicIntentMatcher
from operance.models.actions import ToolName


@pytest.mark.parametrize(
    ("text", "expected_tool", "expected_status", "expected_message"),
    [
        ("open firefox", ToolName.APPS_LAUNCH, "success", "Launched firefox"),
        ("open terminal", ToolName.APPS_LAUNCH, "success", "Launched terminal"),
        ("open code", ToolName.APPS_LAUNCH, "success", "Launched code"),
        ("open localhost:3000", ToolName.APPS_LAUNCH, "success", "Opened http://localhost:3000"),
        ("browse to localhost 3000", ToolName.APPS_LAUNCH, "success", "Opened http://localhost:3000"),
        ("browse to docs.python.org/3", ToolName.APPS_LAUNCH, "success", "Opened https://docs.python.org/3"),
        ("focus firefox", ToolName.APPS_FOCUS, "success", "Focused firefox"),
        ("focus code", ToolName.APPS_FOCUS, "success", "Focused code"),
        ("quit firefox", ToolName.APPS_QUIT, "success", "Quit firefox"),
        ("list windows", ToolName.WINDOWS_LIST, "success", "Open windows: Firefox; Terminal"),
        ("switch to window firefox", ToolName.WINDOWS_SWITCH, "success", "Switched to window Firefox"),
        ("minimize window firefox", ToolName.WINDOWS_MINIMIZE, "success", "Minimized window Firefox"),
        ("maximize window firefox", ToolName.WINDOWS_MAXIMIZE, "success", "Maximized window Firefox"),
        ("fullscreen window firefox", ToolName.WINDOWS_SET_FULLSCREEN, "success", "Enabled fullscreen for window Firefox"),
        ("keep window firefox above", ToolName.WINDOWS_SET_KEEP_ABOVE, "success", "Enabled keep-above for window Firefox"),
        ("shade window firefox", ToolName.WINDOWS_SET_SHADED, "success", "Shaded window Firefox"),
        ("keep window firefox below", ToolName.WINDOWS_SET_KEEP_BELOW, "success", "Enabled keep-below for window Firefox"),
        ("show window firefox on all desktops", ToolName.WINDOWS_SET_ON_ALL_DESKTOPS, "success", "Enabled all-desktops for window Firefox"),
        ("restore window firefox", ToolName.WINDOWS_RESTORE, "success", "Restored window Firefox"),
        ("close window firefox", ToolName.WINDOWS_CLOSE, "success", "Closed window Firefox"),
        ("what time is it", ToolName.TIME_NOW, "success", "It is 09:41"),
        ("what is my battery level", ToolName.POWER_BATTERY_STATUS, "success", "Battery is 87%"),
        ("what is the volume", ToolName.AUDIO_GET_VOLUME, "success", "Volume is 30%"),
        ("is audio muted", ToolName.AUDIO_MUTE_STATUS, "success", "Audio is unmuted"),
        ("what is on the clipboard", ToolName.CLIPBOARD_GET_TEXT, "success", "Clipboard contains: Initial clipboard text"),
        ("copy build complete to clipboard", ToolName.CLIPBOARD_SET_TEXT, "success", "Copied text to clipboard"),
        ("copy selection", ToolName.CLIPBOARD_COPY_SELECTION, "success", "Copied selection to clipboard"),
        ("clear clipboard", ToolName.CLIPBOARD_CLEAR, "success", "Cleared clipboard"),
        ("paste clipboard", ToolName.CLIPBOARD_PASTE, "success", "Pasted clipboard into active window"),
        ("type build complete", ToolName.TEXT_TYPE, "success", "Typed text into active window"),
        ("press enter", ToolName.KEYS_PRESS, "success", "Pressed Enter key"),
        ("press control c", ToolName.KEYS_PRESS, "success", "Pressed Ctrl+C shortcut"),
        ("wifi status", ToolName.NETWORK_WIFI_STATUS, "success", "Wi-Fi is on"),
        ("disconnect wifi", ToolName.NETWORK_DISCONNECT_CURRENT, "success", "Disconnected Wi-Fi home"),
        ("connect to wifi home", ToolName.NETWORK_CONNECT_KNOWN_SSID, "success", "Connected to Wi-Fi home"),
        ("set volume to 50 percent", ToolName.AUDIO_SET_VOLUME, "success", "Volume set to 50%"),
        ("mute audio", ToolName.AUDIO_SET_MUTED, "success", "Audio muted"),
        ("unmute audio", ToolName.AUDIO_SET_MUTED, "success", "Audio unmuted"),
        ("turn wifi off", ToolName.NETWORK_SET_WIFI_ENABLED, "success", "Wi-Fi turned off"),
        ("turn wi-fi on", ToolName.NETWORK_SET_WIFI_ENABLED, "success", "Wi-Fi turned on"),
        (
            "show a notification saying build complete",
            ToolName.NOTIFICATIONS_SHOW,
            "success",
            "Notification shown",
        ),
        (
            "show files modified today",
            ToolName.FILES_LIST_RECENT,
            "success",
            "Found 2 recent files",
        ),
        (
            "open file on desktop called notes.txt",
            ToolName.FILES_OPEN,
            "success",
            "Opened desktop entry notes.txt",
        ),
        (
            "open recent file called notes.txt",
            ToolName.FILES_OPEN,
            "success",
            "Opened recent file notes.txt",
        ),
        (
            "create folder on desktop called projects",
            ToolName.FILES_CREATE_FOLDER,
            "success",
            "Created folder projects on desktop",
        ),
        (
            "delete folder on desktop called projects",
            ToolName.FILES_DELETE_FOLDER,
            "success",
            "Deleted folder projects from desktop",
        ),
        (
            "delete file on desktop called notes.txt",
            ToolName.FILES_DELETE_FILE,
            "success",
            "Deleted file notes.txt from desktop",
        ),
        (
            "rename folder on desktop from projects to archive",
            ToolName.FILES_RENAME,
            "success",
            "Renamed desktop entry projects to archive",
        ),
        (
            "move folder on desktop called projects to archive",
            ToolName.FILES_MOVE,
            "success",
            "Moved desktop entry projects to archive",
        ),
    ],
)
def test_executor_runs_seed_commands_against_mock_adapters(
    tmp_path: Path,
    text: str,
    expected_tool: ToolName,
    expected_status: str,
    expected_message: str,
) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    matcher = DeterministicIntentMatcher()
    plan = matcher.match(text)
    assert plan is not None

    adapters = build_mock_adapter_set(
        desktop_dir=tmp_path / "Desktop",
        recent_files=["notes.txt", "todo.md"],
    )
    if expected_tool == ToolName.FILES_DELETE_FOLDER:
        (tmp_path / "Desktop" / "projects").mkdir()
    if expected_tool == ToolName.NETWORK_DISCONNECT_CURRENT:
        assert adapters.network is not None
        adapters.network.connected_ssid = "home"
    if expected_tool == ToolName.FILES_OPEN and "desktop called" in text:
        (tmp_path / "Desktop" / "notes.txt").write_text("notes", encoding="utf-8")
    if expected_tool == ToolName.FILES_RENAME:
        (tmp_path / "Desktop" / "projects").mkdir()
    if expected_tool == ToolName.FILES_MOVE:
        (tmp_path / "Desktop" / "projects").mkdir()
        (tmp_path / "Desktop" / "archive").mkdir()
    executor = ActionExecutor(adapters=adapters)

    result = executor.execute(plan)

    assert result.status == "success"
    assert len(result.results) == 1
    assert result.results[0].tool == expected_tool
    assert result.results[0].status == expected_status
    assert result.results[0].message == expected_message


def test_executor_runs_two_step_launch_plan_against_mock_adapters(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    matcher = DeterministicIntentMatcher()
    plan = matcher.match("open firefox and load localhost:3000")
    assert plan is not None

    executor = ActionExecutor(adapters=build_mock_adapter_set(desktop_dir=tmp_path / "Desktop"))

    result = executor.execute(plan)

    assert result.status == "success"
    assert [item.tool for item in result.results] == [ToolName.APPS_LAUNCH, ToolName.APPS_LAUNCH]
    assert [item.message for item in result.results] == ["Launched firefox", "Opened http://localhost:3000"]


def test_executor_returns_failed_result_when_app_launch_adapter_fails() -> None:
    from operance.adapters.base import AdapterSet
    from operance.executor import ActionExecutor
    from operance.models.actions import ActionPlan, ActionResultItem, PlanSource, ToolName, TypedAction

    class FailingAppsAdapter:
        def launch(self, app: str) -> str:
            raise ValueError(f"launcher failed for {app}")

        def focus(self, app: str) -> str:
            raise ValueError(f"focus failed for {app}")

        def quit(self, app: str) -> str:
            raise ValueError(f"quit failed for {app}")

    executor = ActionExecutor(adapters=AdapterSet(apps=FailingAppsAdapter()))
    plan = ActionPlan(
        plan_id="plan-1",
        original_text="open firefox",
        source=PlanSource.DETERMINISTIC,
        actions=[TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": "firefox"})],
    )

    result = executor.execute(plan)

    assert result.status == "failed"
    assert result.results == [
        ActionResultItem(
            tool=ToolName.APPS_LAUNCH,
            status="failed",
            message="launcher failed for firefox",
        )
    ]


def test_executor_updates_mock_state_for_mutating_actions(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    volume_plan = matcher.match("set volume to 50 percent")
    mute_plan = matcher.match("mute audio")
    wifi_plan = matcher.match("turn wifi off")
    connect_wifi_plan = matcher.match("connect to wifi home")
    disconnect_wifi_plan = matcher.match("disconnect wifi")
    folder_plan = matcher.match("create folder on desktop called projects")
    clipboard_plan = matcher.match("copy build complete to clipboard")
    clear_clipboard_plan = matcher.match("clear clipboard")
    paste_clipboard_plan = matcher.match("paste clipboard")
    type_text_plan = matcher.match("type build complete")
    press_enter_plan = matcher.match("press enter")
    press_palette_plan = matcher.match("press control shift p")

    assert volume_plan is not None
    assert mute_plan is not None
    assert wifi_plan is not None
    assert connect_wifi_plan is not None
    assert disconnect_wifi_plan is not None
    assert folder_plan is not None
    assert clipboard_plan is not None
    assert clear_clipboard_plan is not None
    assert paste_clipboard_plan is not None
    assert type_text_plan is not None
    assert press_enter_plan is not None
    assert press_palette_plan is not None

    executor.execute(volume_plan)
    executor.execute(mute_plan)
    executor.execute(wifi_plan)
    executor.execute(connect_wifi_plan)
    executor.execute(disconnect_wifi_plan)
    executor.execute(folder_plan)
    executor.execute(clipboard_plan)
    executor.execute(paste_clipboard_plan)
    executor.execute(clear_clipboard_plan)
    executor.execute(type_text_plan)
    executor.execute(press_enter_plan)
    executor.execute(press_palette_plan)

    assert adapters.audio is not None
    assert adapters.audio.volume == 50
    assert adapters.audio.muted is True
    assert adapters.clipboard is not None
    assert adapters.clipboard.text == ""
    assert adapters.text_input is not None
    assert adapters.text_input.paste_count == 1
    assert adapters.text_input.typed_texts == ["build complete"]
    assert adapters.text_input.pressed_keys == ["enter", "ctrl+shift+p"]
    assert adapters.network is not None
    assert adapters.network.wifi_enabled is True
    assert adapters.network.connected_ssid is None
    assert (tmp_path / "Desktop" / "projects").exists()


def test_executor_deletes_existing_folder(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    desktop_dir = tmp_path / "Desktop"
    adapters = build_mock_adapter_set(desktop_dir=desktop_dir)
    folder = desktop_dir / "projects"
    folder.mkdir()
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("delete folder on desktop called projects")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Deleted folder projects from desktop"
    assert folder.exists() is False


def test_executor_deletes_existing_file(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    desktop_dir = tmp_path / "Desktop"
    adapters = build_mock_adapter_set(desktop_dir=desktop_dir)
    file_path = desktop_dir / "notes.txt"
    file_path.write_text("notes", encoding="utf-8")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("delete file on desktop called notes.txt")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Deleted file notes.txt from desktop"
    assert file_path.exists() is False


def test_executor_returns_undo_token_and_reverts_reversible_action(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("set volume to 50 percent")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].undo_token is not None
    assert adapters.audio is not None
    assert adapters.audio.volume == 50

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Volume restored to 30%"
    assert adapters.audio.volume == 30


def test_executor_restores_previous_clipboard_text_on_undo(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("copy build complete to clipboard")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].undo_token is not None
    assert adapters.clipboard is not None
    assert adapters.clipboard.text == "build complete"

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Clipboard restored"
    assert adapters.clipboard.text == "Initial clipboard text"


def test_executor_copies_selection_to_clipboard_and_can_undo(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("copy selection")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Copied selection to clipboard"
    assert result.results[0].undo_token is not None
    assert adapters.clipboard is not None
    assert adapters.clipboard.text == "Selected mock text"
    assert adapters.text_input is not None
    assert adapters.text_input.copy_selection_count == 1

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Clipboard restored"
    assert adapters.clipboard.text == "Initial clipboard text"


def test_executor_clears_clipboard_and_can_undo(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("clear clipboard")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Cleared clipboard"
    assert result.results[0].undo_token is not None
    assert adapters.clipboard is not None
    assert adapters.clipboard.text == ""

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Clipboard restored"
    assert adapters.clipboard.text == "Initial clipboard text"


def test_executor_fails_to_paste_empty_clipboard(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    adapters = build_mock_adapter_set(desktop_dir=tmp_path / "Desktop")
    assert adapters.clipboard is not None
    adapters.clipboard.text = ""
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("paste clipboard")
    assert plan is not None

    result = executor.execute(plan)

    assert result.status == "failed"
    assert result.results[0].status == "failed"
    assert result.results[0].message == "Clipboard is empty"
    assert adapters.text_input is not None
    assert adapters.text_input.paste_count == 0


def test_executor_renames_existing_desktop_entry_and_can_undo(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    desktop_dir = tmp_path / "Desktop"
    adapters = build_mock_adapter_set(desktop_dir=desktop_dir)
    source = desktop_dir / "projects"
    source.mkdir()
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("rename folder on desktop from projects to archive")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Renamed desktop entry projects to archive"
    assert result.results[0].undo_token is not None
    assert source.exists() is False
    renamed = desktop_dir / "archive"
    assert renamed.exists() is True

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Renamed desktop entry archive to projects"
    assert source.exists() is True
    assert renamed.exists() is False


def test_executor_moves_existing_desktop_entry_and_can_undo(tmp_path: Path) -> None:
    from operance.adapters.mock import build_mock_adapter_set
    from operance.executor import ActionExecutor

    desktop_dir = tmp_path / "Desktop"
    adapters = build_mock_adapter_set(desktop_dir=desktop_dir)
    source = desktop_dir / "projects"
    destination_dir = desktop_dir / "archive"
    source.mkdir()
    destination_dir.mkdir()
    matcher = DeterministicIntentMatcher()
    executor = ActionExecutor(adapters=adapters)

    plan = matcher.match("move folder on desktop called projects to archive")
    assert plan is not None

    result = executor.execute(plan)

    assert result.results[0].message == "Moved desktop entry projects to archive"
    assert result.results[0].undo_token is not None
    moved = destination_dir / "projects"
    assert source.exists() is False
    assert moved.exists() is True

    undo_result = executor.undo(result.results[0].undo_token)

    assert undo_result == "Moved desktop entry projects to Desktop"
    assert source.exists() is True
    assert moved.exists() is False
