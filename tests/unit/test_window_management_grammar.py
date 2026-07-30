from __future__ import annotations

import pytest

from operance.confirmation import build_confirmation_metadata
from operance.intent.deterministic import DeterministicIntentMatcher
from operance.models.actions import ToolName
from operance.policy import ExecutionPolicy
from operance.registry import build_default_action_registry
from operance.validator import PlanValidator


@pytest.mark.parametrize(
    ("transcript", "expected_tool", "expected_window"),
    [
        ("minimize window firefox", ToolName.WINDOWS_MINIMIZE, "firefox"),
        ("minimize firefox", ToolName.WINDOWS_MINIMIZE, "firefox"),
        ("minimize the firefox window", ToolName.WINDOWS_MINIMIZE, "firefox"),
        ("minimise firefox", ToolName.WINDOWS_MINIMIZE, "firefox"),
        ("maximize window firefox", ToolName.WINDOWS_MAXIMIZE, "firefox"),
        ("maximize firefox", ToolName.WINDOWS_MAXIMIZE, "firefox"),
        ("maximize the firefox window", ToolName.WINDOWS_MAXIMIZE, "firefox"),
        ("restore window firefox", ToolName.WINDOWS_RESTORE, "firefox"),
        ("restore firefox", ToolName.WINDOWS_RESTORE, "firefox"),
        ("restore the firefox window", ToolName.WINDOWS_RESTORE, "firefox"),
        ("unminimize firefox", ToolName.WINDOWS_RESTORE, "firefox"),
        ("close window firefox", ToolName.WINDOWS_CLOSE, "firefox"),
        ("close the firefox window", ToolName.WINDOWS_CLOSE, "firefox"),
    ],
)
def test_window_management_phrases_route_to_typed_actions(
    transcript: str,
    expected_tool: ToolName,
    expected_window: str,
) -> None:
    plan = DeterministicIntentMatcher().match(transcript)

    assert plan is not None, transcript
    assert len(plan.actions) == 1
    assert plan.actions[0].tool == expected_tool
    assert plan.actions[0].args == {"window": expected_window}


@pytest.mark.parametrize(
    ("transcript", "expected_tool"),
    [
        ("quit firefox", ToolName.APPS_QUIT),
        ("focus firefox", ToolName.APPS_FOCUS),
        ("switch to firefox", ToolName.APPS_FOCUS),
        ("open firefox", ToolName.APPS_LAUNCH),
    ],
)
def test_existing_app_commands_are_not_shadowed(transcript: str, expected_tool: ToolName) -> None:
    plan = DeterministicIntentMatcher().match(transcript)

    assert plan is not None, transcript
    assert plan.actions[0].tool == expected_tool


def test_bare_close_does_not_guess_between_closing_a_window_and_quitting_an_app() -> None:
    """`close firefox` is ambiguous, so it must fall through to recovery guidance."""

    assert DeterministicIntentMatcher().match("close firefox") is None


def test_window_management_phrases_validate() -> None:
    validator = PlanValidator(build_default_action_registry())

    for transcript in ("minimize firefox", "maximize firefox", "restore firefox"):
        plan = DeterministicIntentMatcher().match(transcript)
        assert plan is not None
        result = validator.validate(plan)
        assert result.valid, (transcript, result.errors)


def test_closing_a_window_stays_confirmation_gated_with_a_preview() -> None:
    validator = PlanValidator(build_default_action_registry())
    plan = DeterministicIntentMatcher().match("close the firefox window")
    assert plan is not None

    result = validator.validate(plan)
    assert result.valid and result.normalized_plan is not None
    decision = ExecutionPolicy().decide(result.normalized_plan)

    assert decision.action == "require_confirmation"

    metadata = build_confirmation_metadata(result.normalized_plan, timeout_seconds=30.0)
    assert "close window" in str(metadata["pending_plan_preview"])
    assert metadata["pending_affected_resources"] == ["window: firefox"]


@pytest.mark.parametrize(
    "tool",
    [
        ToolName.WINDOWS_MINIMIZE,
        ToolName.WINDOWS_MAXIMIZE,
        ToolName.WINDOWS_RESTORE,
        ToolName.WINDOWS_CLOSE,
    ],
)
def test_window_management_tools_declare_a_usage_pattern(tool: ToolName) -> None:
    spec = build_default_action_registry().get(tool)

    assert spec is not None
    assert spec.usage_pattern


def test_window_management_tools_are_not_release_verified_yet() -> None:
    """Promotion requires live Fedora KDE Wayland evidence, which this change does not add."""

    from operance.platforms.linux import CURRENT_RELEASE_VERIFIED_TOOLS

    for tool in (
        ToolName.WINDOWS_MINIMIZE,
        ToolName.WINDOWS_MAXIMIZE,
        ToolName.WINDOWS_RESTORE,
        ToolName.WINDOWS_CLOSE,
    ):
        assert tool not in CURRENT_RELEASE_VERIFIED_TOOLS
