"""Minimal platform-provider example.

This example is not registered as a real provider. It shows where host
readiness, blocked-tool explanations, and release-verification policy belong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from operance.adapters.base import AdapterSet
from operance.models.actions import ToolName
from operance.platforms.base import (
    CheckMetadata,
    PlatformSetupAction,
    PlatformSetupBlockedRecommendation,
    PlatformSetupNextStep,
)

from .minimal_adapters import build_example_adapter_set


EXAMPLE_CHECK_METADATA = (
    CheckMetadata("example_platform", "Example platform", required_for_local_runtime=True),
    CheckMetadata("example_desktop_adapter", "Example desktop adapter", required_for_local_runtime=True),
)


@dataclass(slots=True, frozen=True)
class ExampleDesktopPlatformProvider:
    provider_id: str = "example_desktop"
    display_name: str = "Example desktop"
    check_metadata: tuple[CheckMetadata, ...] = EXAMPLE_CHECK_METADATA
    release_verification_target: str = "example_desktop_unverified"
    release_verified_tools: frozenset[ToolName] = frozenset()

    def build_adapters(self, config) -> AdapterSet:
        return build_example_adapter_set()

    def build_environment_checks(self) -> list[dict[str, object]]:
        return [
            {"name": "example_platform", "status": "ok", "detail": "example"},
            {
                "name": "example_desktop_adapter",
                "status": "warn",
                "detail": "Example provider is documentation-only and not a live backend.",
            },
        ]

    def recommended_command_for_check(
        self,
        name: str,
        status: str,
        checks_by_name: Mapping[str, dict[str, object]],
        remediation_commands: Mapping[str, str],
    ) -> str | None:
        return remediation_commands.get(name)

    def build_setup_recommended_commands(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[str]:
        return []

    def build_setup_blocked_recommendations(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[PlatformSetupBlockedRecommendation]:
        return [
            PlatformSetupBlockedRecommendation(
                label="Implement native example desktop adapters",
                reason="The example provider is not registered and must not claim live support.",
                suggested_command="Read docs/architecture/adapter-authoring.md",
            )
        ]

    def build_setup_next_steps(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        ready_for_local_runtime: bool,
    ) -> list[PlatformSetupNextStep]:
        return [
            PlatformSetupNextStep(
                label="Run adapter conformance for selected tools",
                command="python3 -m operance.cli --adapter-conformance",
            )
        ]

    def build_setup_actions(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        recommended_commands: tuple[str, ...],
    ) -> list[PlatformSetupAction]:
        return []

    def tool_live_runtime_blockers(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> list[str]:
        return ["Example provider is documentation-only"]

    def tool_live_runtime_suggested_command(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> str | None:
        return "Read examples/adapter_sdk/minimal_adapters.py"
