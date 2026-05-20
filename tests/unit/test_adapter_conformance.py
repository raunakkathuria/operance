from pathlib import Path

from operance.adapters.base import AdapterSet
from operance.adapters.conformance import (
    ADAPTER_TOOL_CONTRACTS,
    adapter_capability_matrix,
    validate_adapter_set,
)
from operance.adapters.mock import build_mock_adapter_set
from operance.models.actions import ToolName
from operance.registry import build_default_action_registry


def test_adapter_contracts_cover_registered_tools() -> None:
    registry = build_default_action_registry()

    assert set(ADAPTER_TOOL_CONTRACTS) == {spec.name for spec in registry.list_specs()}


def test_mock_adapter_set_conforms_to_all_tool_contracts(tmp_path: Path) -> None:
    adapters = build_mock_adapter_set(desktop_dir=tmp_path)

    report = validate_adapter_set(adapters)

    assert report.status == "ok"
    assert report.to_dict()["summary"] == {
        "checked_tools": len(ADAPTER_TOOL_CONTRACTS),
        "failed_tools": 0,
    }


def test_adapter_conformance_reports_missing_adapter() -> None:
    report = validate_adapter_set(AdapterSet(), tools={ToolName.APPS_LAUNCH})

    assert report.status == "failed"
    assert report.to_dict()["checks"] == [
        {
            "tool": "apps.launch",
            "adapter": "apps",
            "required_methods": ["launch"],
            "status": "failed",
            "message": "missing adapter: apps",
        }
    ]


def test_adapter_conformance_reports_missing_method() -> None:
    class _IncompleteAppsAdapter:
        def launch(self, app: str) -> str:
            return f"Launched {app}"

    report = validate_adapter_set(
        AdapterSet(apps=_IncompleteAppsAdapter()),
        tools={ToolName.APPS_QUIT},
    )

    assert report.status == "failed"
    assert report.to_dict()["checks"] == [
        {
            "tool": "apps.quit",
            "adapter": "apps",
            "required_methods": ["quit"],
            "status": "failed",
            "message": "missing methods: quit",
        }
    ]


def test_adapter_capability_matrix_groups_tools_by_adapter() -> None:
    matrix = adapter_capability_matrix()

    assert matrix["apps"] == ["apps.focus", "apps.launch", "apps.quit"]
    assert "audio.set_volume" in matrix["audio"]
    assert "clipboard.copy_selection" in matrix["text_input"]
