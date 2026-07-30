from __future__ import annotations

import pytest

from operance.adapters import build_default_adapter_set
from operance.adapters.blocked import BlockedAdapter, build_blocked_adapter_set
from operance.adapters.conformance import validate_adapter_set
from operance.config import AppConfig
from operance.executor import ActionExecutor
from operance.models.actions import (
    ActionPlan,
    PlanSource,
    RiskTier,
    ToolName,
    TypedAction,
)


def _live_config() -> AppConfig:
    return AppConfig.from_env({"OPERANCE_DEVELOPER_MODE": "0"})


def _plan(tool: ToolName, args: dict[str, object]) -> ActionPlan:
    return ActionPlan(
        source=PlanSource.PLANNER,
        original_text=f"test {tool.value}",
        actions=[TypedAction(tool=tool, args=args, risk_tier=RiskTier.TIER_0)],
    )


@pytest.mark.parametrize(
    ("system_name", "expected_fragment"),
    [
        ("Windows", "Windows desktop adapter is not implemented yet"),
        ("Darwin", "macOS desktop adapter is not implemented yet"),
        ("FreeBSD", "This platform has no Operance desktop adapter"),
    ],
)
def test_scaffold_platforms_block_execution_instead_of_reporting_success(
    system_name: str,
    expected_fragment: str,
) -> None:
    adapters = build_default_adapter_set(_live_config(), system_name=system_name)

    result = ActionExecutor(adapters=adapters).execute(
        _plan(ToolName.APPS_LAUNCH, {"app": "firefox"})
    )

    assert result.status == "failed"
    assert expected_fragment in result.results[0].message


def test_blocked_file_tool_reports_platform_blocker_not_a_missing_entry() -> None:
    adapters = build_default_adapter_set(_live_config(), system_name="Windows")

    result = ActionExecutor(adapters=adapters).execute(
        _plan(ToolName.FILES_DELETE_FOLDER, {"location": "desktop", "name": "reports"})
    )

    assert result.status == "failed"
    assert "Windows desktop adapter is not implemented yet" in result.results[0].message


def test_blocked_adapter_set_still_satisfies_adapter_conformance_surface() -> None:
    adapters = build_blocked_adapter_set(blocker="blocked for test")

    report = validate_adapter_set(adapters)

    assert report.status == "ok"


def test_blocked_adapter_raises_blocker_on_call_and_on_desktop_dir() -> None:
    adapter = BlockedAdapter("blocked for test")

    with pytest.raises(ValueError, match="blocked for test"):
        adapter.launch("firefox")

    with pytest.raises(ValueError, match="blocked for test"):
        _ = adapter.desktop_dir


def test_blocked_adapter_does_not_answer_dunder_lookups() -> None:
    adapter = BlockedAdapter("blocked for test")

    with pytest.raises(AttributeError):
        _ = adapter.__deepcopy__


def test_developer_mode_still_uses_simulated_adapters() -> None:
    config = AppConfig.from_env({"OPERANCE_DEVELOPER_MODE": "1"})

    adapters = build_default_adapter_set(config, system_name="Windows")

    result = ActionExecutor(adapters=adapters).execute(
        _plan(ToolName.APPS_LAUNCH, {"app": "firefox"})
    )

    assert result.status == "success"


def test_linux_provider_still_builds_native_adapters() -> None:
    adapters = build_default_adapter_set(_live_config(), system_name="Linux")

    assert type(adapters.apps).__name__ == "LinuxAppsAdapter"
