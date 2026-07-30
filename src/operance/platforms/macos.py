"""macOS platform provider scaffold."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..adapters.base import AdapterSet
from ..adapters.blocked import build_blocked_adapter_set
from ..models.actions import ToolName
from .base import (
    CheckMetadata,
    HostServiceLogTarget,
    PlatformSetupAction,
    PlatformSetupBlockedRecommendation,
    PlatformSetupNextStep,
)


MACOS_ADAPTER_BLOCKER = (
    "macOS desktop adapter is not implemented yet, so live desktop commands "
    "are blocked on this platform."
)

MACOS_CHECK_METADATA = (
    CheckMetadata("macos_platform", "macOS platform", required_for_local_runtime=True),
    CheckMetadata(
        "macos_desktop_adapter",
        "macOS desktop adapter",
        required_for_local_runtime=True,
    ),
)


@dataclass(slots=True, frozen=True)
class MacOSDesktopPlatformProvider:
    provider_id: str = "macos_desktop"
    display_name: str = "macOS desktop"
    check_metadata: tuple[CheckMetadata, ...] = MACOS_CHECK_METADATA
    release_verification_target: str = "macos_desktop_unverified"
    release_verified_tools: frozenset[ToolName] = frozenset()

    def build_adapters(self, config) -> AdapterSet:
        return build_blocked_adapter_set(blocker=MACOS_ADAPTER_BLOCKER)

    def build_environment_checks(self) -> list[dict[str, object]]:
        system_name = platform.system()
        return [
            {
                "name": "macos_platform",
                "status": "ok" if system_name == "Darwin" else "warn",
                "detail": system_name,
            },
            {
                "name": "macos_desktop_adapter",
                "status": "warn",
                "detail": "macOS desktop adapter is not implemented yet.",
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
        return []

    def build_setup_next_steps(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        ready_for_local_runtime: bool,
    ) -> list[PlatformSetupNextStep]:
        return []

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
        return ["macOS desktop adapter"]

    def tool_live_runtime_suggested_command(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> str | None:
        return None

    def host_service_state_command(self, service: str) -> tuple[str, ...] | None:
        return None

    def host_service_control_command(
        self,
        service: str,
        *,
        action: str,
    ) -> tuple[str, ...] | None:
        return None

    def host_service_log_targets(self, *, lines: int) -> tuple[HostServiceLogTarget, ...]:
        return ()

    def voice_loop_config_update_command(
        self,
        *,
        wakeword_threshold: float,
        repo_root: Path,
    ) -> tuple[str, ...] | None:
        return None
