from __future__ import annotations

import subprocess

import pytest

from operance.adapters.conformance import ADAPTER_TOOL_CONTRACTS, validate_adapter_set
from operance.adapters.mock import build_mock_adapter_set
from operance.executor import ActionExecutor
from operance.intent.deterministic import DeterministicIntentMatcher
from operance.models.actions import (
    ActionPlan,
    PlanSource,
    RiskTier,
    ToolName,
    TypedAction,
)
from operance.policy import ExecutionPolicy
from operance.registry import build_default_action_registry
from operance.validator import PlanValidator


MEDIA_TOOLS = ("media.play_pause", "media.next", "media.previous")


@pytest.mark.parametrize(
    ("transcript", "expected_tool"),
    [
        ("pause", ToolName.MEDIA_PLAY_PAUSE),
        ("play", ToolName.MEDIA_PLAY_PAUSE),
        ("pause music", ToolName.MEDIA_PLAY_PAUSE),
        ("play music", ToolName.MEDIA_PLAY_PAUSE),
        ("pause the music", ToolName.MEDIA_PLAY_PAUSE),
        ("resume music", ToolName.MEDIA_PLAY_PAUSE),
        ("play pause", ToolName.MEDIA_PLAY_PAUSE),
        ("next track", ToolName.MEDIA_NEXT),
        ("next song", ToolName.MEDIA_NEXT),
        ("skip song", ToolName.MEDIA_NEXT),
        ("skip this track", ToolName.MEDIA_NEXT),
        ("previous track", ToolName.MEDIA_PREVIOUS),
        ("previous song", ToolName.MEDIA_PREVIOUS),
        ("go back a track", ToolName.MEDIA_PREVIOUS),
    ],
)
def test_media_phrases_route_to_typed_actions(transcript: str, expected_tool: ToolName) -> None:
    plan = DeterministicIntentMatcher().match(transcript)

    assert plan is not None, transcript
    assert len(plan.actions) == 1
    assert plan.actions[0].tool == expected_tool
    assert plan.actions[0].args == {}


@pytest.mark.parametrize(
    ("transcript", "expected_tool"),
    [
        ("open firefox", ToolName.APPS_LAUNCH),
        ("quit firefox", ToolName.APPS_QUIT),
        ("mute", ToolName.AUDIO_SET_MUTED),
        ("what time is it", ToolName.TIME_NOW),
    ],
)
def test_existing_commands_are_not_shadowed(transcript: str, expected_tool: ToolName) -> None:
    plan = DeterministicIntentMatcher().match(transcript)

    assert plan is not None, transcript
    assert plan.actions[0].tool == expected_tool


@pytest.mark.parametrize("tool_value", MEDIA_TOOLS)
def test_media_tools_are_registered_with_safe_metadata(tool_value: str) -> None:
    spec = build_default_action_registry().get(ToolName(tool_value))

    assert spec is not None
    assert spec.requires_confirmation is False
    assert spec.risk_tier == RiskTier.TIER_1
    assert spec.usage_pattern


@pytest.mark.parametrize("tool_value", MEDIA_TOOLS)
def test_media_tools_declare_an_adapter_contract(tool_value: str) -> None:
    contract = ADAPTER_TOOL_CONTRACTS.get(ToolName(tool_value))

    assert contract is not None
    assert contract.adapter == "media"
    # Simple passthroughs, so dispatch is declarative and needs no executor branch.
    assert contract.call is not None
    assert contract.call.args == ()


@pytest.mark.parametrize("tool_value", MEDIA_TOOLS)
def test_media_commands_execute_and_auto_approve(tool_value: str, tmp_path) -> None:
    tool = ToolName(tool_value)
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text=f"test {tool_value}",
        actions=[TypedAction(tool=tool, args={}, risk_tier=RiskTier.TIER_1)],
    )
    validation = PlanValidator(build_default_action_registry()).validate(plan)
    assert validation.valid, validation.errors
    assert validation.normalized_plan is not None

    assert ExecutionPolicy().decide(validation.normalized_plan).action == "auto_approve"

    result = ActionExecutor(adapters=build_mock_adapter_set(desktop_dir=tmp_path)).execute(
        validation.normalized_plan
    )
    assert result.status == "success"


def test_mock_adapter_set_exposes_media(tmp_path) -> None:
    adapters = build_mock_adapter_set(desktop_dir=tmp_path)

    assert adapters.media is not None
    assert validate_adapter_set(adapters).status == "ok"


def test_linux_media_adapter_controls_the_active_mpris_player() -> None:
    from operance.adapters.linux import LinuxMediaAdapter

    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if any("ListNames" in part for part in command):
            stdout = "(['org.freedesktop.DBus', 'org.mpris.MediaPlayer2.vlc'],)"
            return subprocess.CompletedProcess(command, 0, stdout, "")
        return subprocess.CompletedProcess(command, 0, "()", "")

    adapter = LinuxMediaAdapter(
        run_command=fake_run,
        resolve_executable=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None,
    )

    message = adapter.play_pause()

    assert "vlc" in message.lower() or "play" in message.lower()
    player_call = commands[-1]
    assert "org.mpris.MediaPlayer2.vlc" in player_call
    assert "org.mpris.MediaPlayer2.Player.PlayPause" in player_call


def test_linux_media_adapter_reports_when_no_player_is_running() -> None:
    from operance.adapters.linux import LinuxMediaAdapter

    adapter = LinuxMediaAdapter(
        run_command=lambda command: subprocess.CompletedProcess(
            command, 0, "(['org.freedesktop.DBus'],)", ""
        ),
        resolve_executable=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None,
    )

    with pytest.raises(ValueError, match="no media player"):
        adapter.play_pause()


def test_linux_media_adapter_requires_gdbus() -> None:
    from operance.adapters.linux import LinuxMediaAdapter

    adapter = LinuxMediaAdapter(
        run_command=lambda command: subprocess.CompletedProcess(command, 0, "", ""),
        resolve_executable=lambda name: None,
    )

    with pytest.raises(ValueError, match="gdbus"):
        adapter.play_pause()


def test_media_tools_are_not_release_verified_yet() -> None:
    """Promotion needs live Fedora KDE Wayland evidence, which this change does not add."""

    from operance.platforms.linux import CURRENT_RELEASE_VERIFIED_TOOLS

    for tool_value in MEDIA_TOOLS:
        assert ToolName(tool_value) not in CURRENT_RELEASE_VERIFIED_TOOLS
