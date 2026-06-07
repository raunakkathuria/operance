from __future__ import annotations

from examples.adapter_sdk.minimal_adapters import (
    build_example_adapter_set,
    run_example_plan,
    validate_example_adapter_set,
)
from examples.adapter_sdk.minimal_provider import ExampleDesktopPlatformProvider
from operance.adapters.conformance import validate_adapter_set
from operance.models.actions import ToolName


def test_minimal_adapter_example_conforms_for_selected_tools() -> None:
    report = validate_example_adapter_set()

    assert report["status"] == "ok"
    assert report["summary"] == {"checked_tools": 4, "failed_tools": 0}


def test_minimal_adapter_example_executes_typed_plan() -> None:
    result = run_example_plan()

    assert result["status"] == "success"
    assert [item["tool"] for item in result["results"]] == [
        "apps.launch",
        "notifications.show",
    ]
    assert result["results"][0]["message"] == "Example backend launched browser"
    assert result["results"][1]["message"] == "Example backend showed notification"


def test_minimal_provider_example_keeps_live_tools_blocked() -> None:
    provider = ExampleDesktopPlatformProvider()

    assert provider.release_verified_tools == frozenset()
    assert provider.tool_live_runtime_blockers(ToolName.APPS_LAUNCH, {}) == [
        "Example provider is documentation-only"
    ]
    assert provider.build_setup_blocked_recommendations({})[0].suggested_command == (
        "Read docs/architecture/adapter-authoring.md"
    )


def test_minimal_provider_example_builds_conformant_selected_adapter_set(tmp_path) -> None:
    provider = ExampleDesktopPlatformProvider()
    adapters = provider.build_adapters(config=None)

    report = validate_adapter_set(
        adapters,
        tools={ToolName.APPS_LAUNCH, ToolName.NOTIFICATIONS_SHOW},
    )

    assert report.status == "ok"
    assert build_example_adapter_set().apps is not None
