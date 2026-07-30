from __future__ import annotations

import pytest

from operance.adapters.conformance import ADAPTER_TOOL_CONTRACTS
from operance.adapters.mock import build_mock_adapter_set
from operance.confirmation import _affected_resources
from operance.executor import ActionExecutor
from operance.models.actions import (
    ActionPlan,
    PlanSource,
    RiskTier,
    ToolName,
    TypedAction,
)
from operance.planner import build_plan_preview
from operance.registry import build_default_action_registry


def _registered_tools() -> list[ToolName]:
    return [spec.name for spec in build_default_action_registry().list_specs()]


def test_every_registered_tool_has_an_adapter_contract() -> None:
    missing = [tool.value for tool in _registered_tools() if tool not in ADAPTER_TOOL_CONTRACTS]

    assert missing == []


def test_every_registered_tool_is_executable(tmp_path) -> None:
    """Each tool must be reachable in the executor, by declared call or explicit branch."""

    executor = ActionExecutor(adapters=build_mock_adapter_set(desktop_dir=tmp_path))
    registry = build_default_action_registry()
    unreachable: list[str] = []

    for tool in _registered_tools():
        contract = ADAPTER_TOOL_CONTRACTS.get(tool)
        if contract is not None and contract.call is not None:
            continue
        spec = registry.get(tool)
        assert spec is not None
        args = {name: _placeholder_arg(name) for name in spec.required_args}
        plan = ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=f"coverage {tool.value}",
            actions=[TypedAction(tool=tool, args=args, risk_tier=RiskTier.TIER_0)],
        )
        result = executor.execute(plan)
        message = result.results[0].message or ""
        if f"unsupported tool: {tool.value}" in message:
            unreachable.append(tool.value)

    assert unreachable == []


@pytest.mark.parametrize("tool", _registered_tools(), ids=lambda tool: tool.value)
def test_every_registered_tool_has_preview_text(tool: ToolName) -> None:
    spec = build_default_action_registry().get(tool)
    assert spec is not None
    args = {name: _placeholder_arg(name) for name in spec.required_args}
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text=f"preview {tool.value}",
        actions=[TypedAction(tool=tool, args=args, risk_tier=RiskTier.TIER_0)],
    )

    preview = build_plan_preview(plan)

    assert preview
    assert preview.strip() != ""


def test_confirmation_gated_tools_declare_affected_resources() -> None:
    """A confirmation prompt without affected resources gives the user nothing to judge."""

    registry = build_default_action_registry()
    missing: list[str] = []

    for tool in _registered_tools():
        spec = registry.get(tool)
        assert spec is not None
        if not spec.requires_confirmation:
            continue
        args = {name: _placeholder_arg(name) for name in spec.required_args}
        if not _affected_resources(tool, args):
            missing.append(tool.value)

    assert missing == []


def test_declared_adapter_calls_name_methods_that_exist(tmp_path) -> None:
    adapters = build_mock_adapter_set(desktop_dir=tmp_path)
    broken: list[str] = []

    for tool, contract in ADAPTER_TOOL_CONTRACTS.items():
        if contract.call is None:
            continue
        adapter = getattr(adapters, contract.adapter, None)
        if adapter is None or not callable(getattr(adapter, contract.call.method, None)):
            broken.append(f"{tool.value} -> {contract.adapter}.{contract.call.method}")

    assert broken == []


def test_declared_adapter_calls_only_use_known_coercions() -> None:
    from operance.executor import _ARG_COERCIONS

    unknown = [
        f"{tool.value}:{name}:{kind}"
        for tool, contract in ADAPTER_TOOL_CONTRACTS.items()
        if contract.call is not None
        for name, kind in contract.call.args
        if kind not in _ARG_COERCIONS
    ]

    assert unknown == []


def test_declared_adapter_call_args_are_declared_required_args() -> None:
    registry = build_default_action_registry()
    mismatched: list[str] = []

    for tool, contract in ADAPTER_TOOL_CONTRACTS.items():
        if contract.call is None:
            continue
        spec = registry.get(tool)
        if spec is None:
            continue
        for name, _kind in contract.call.args:
            if name not in spec.required_args:
                mismatched.append(f"{tool.value}:{name}")

    assert mismatched == []


def _placeholder_arg(name: str) -> object:
    if name in {"enabled", "muted"}:
        return True
    if name == "percent":
        return 50
    if name == "location":
        return "desktop"
    if name == "kind":
        return "file"
    if name == "destination_folder":
        return "documents"
    return "placeholder"
