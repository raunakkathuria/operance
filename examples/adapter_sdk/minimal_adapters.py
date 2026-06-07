"""Minimal adapter example for a new desktop backend.

Run with:

    python3 -m examples.adapter_sdk.minimal_adapters

This intentionally implements only two safe tool surfaces. Real OS backends
should keep native API calls inside adapter methods like these.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from operance.adapters.base import AdapterSet
from operance.adapters.conformance import validate_adapter_set
from operance.executor import ActionExecutor
from operance.models.actions import ActionPlan, PlanSource, ToolName, TypedAction


@dataclass(slots=True)
class ExampleAppsAdapter:
    launched: list[str] = field(default_factory=list)

    def launch(self, app: str) -> str:
        self.launched.append(app)
        return f"Example backend launched {app}"

    def focus(self, app: str) -> str:
        return f"Example backend focused {app}"

    def quit(self, app: str) -> str:
        return f"Example backend quit {app}"


@dataclass(slots=True)
class ExampleNotificationsAdapter:
    shown: list[tuple[str, str]] = field(default_factory=list)

    def show(self, title: str, message: str) -> str:
        self.shown.append((title, message))
        return "Example backend showed notification"


def build_example_adapter_set() -> AdapterSet:
    return AdapterSet(
        apps=ExampleAppsAdapter(),
        notifications=ExampleNotificationsAdapter(),
    )


def validate_example_adapter_set() -> dict[str, object]:
    report = validate_adapter_set(
        build_example_adapter_set(),
        tools={ToolName.APPS_LAUNCH, ToolName.APPS_FOCUS, ToolName.APPS_QUIT, ToolName.NOTIFICATIONS_SHOW},
    )
    return report.to_dict()


def run_example_plan() -> dict[str, object]:
    plan = ActionPlan(
        source=PlanSource.DETERMINISTIC,
        original_text="open browser and notify me",
        actions=[
            TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": "browser"}),
            TypedAction(tool=ToolName.NOTIFICATIONS_SHOW, args={"title": "Operance", "message": "Browser opened"}),
        ],
    )
    result = ActionExecutor(build_example_adapter_set()).execute(plan)
    return result.to_dict()


def main() -> int:
    print(validate_example_adapter_set())
    print(run_example_plan())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
