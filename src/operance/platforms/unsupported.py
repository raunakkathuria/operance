"""Fallback platform provider for unsupported hosts."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass

from ..adapters.base import AdapterSet
from ..adapters.mock import build_mock_adapter_set
from ..models.actions import ToolName
from .base import (
    CheckMetadata,
    PlatformSetupAction,
    PlatformSetupBlockedRecommendation,
    PlatformSetupNextStep,
)


@dataclass(slots=True, frozen=True)
class UnsupportedPlatformProvider:
    provider_id: str = "unsupported_platform"
    display_name: str = "Unsupported platform"
    check_metadata: tuple[CheckMetadata, ...] = (
        CheckMetadata(
            name="linux_platform",
            label="Linux platform",
            required_for_local_runtime=True,
        ),
        CheckMetadata(
            name="kde_wayland_target",
            label="KDE Wayland session",
            required_for_local_runtime=True,
        ),
    )
    release_verification_target: str = "unsupported_platform"
    release_verified_tools: frozenset[ToolName] = frozenset()

    def build_adapters(self, config) -> AdapterSet:
        return build_mock_adapter_set(desktop_dir=config.paths.desktop_dir)

    def build_environment_checks(self) -> list[dict[str, object]]:
        session_type = os.environ.get("XDG_SESSION_TYPE")
        desktop_session = os.environ.get("XDG_CURRENT_DESKTOP")
        return [
            {
                "name": "linux_platform",
                "status": "warn",
                "detail": platform.system(),
            },
            {
                "name": "kde_wayland_target",
                "status": "warn",
                "detail": {
                    "session_type": session_type,
                    "desktop_session": desktop_session,
                },
            },
        ]

    def recommended_command_for_check(
        self,
        name: str,
        status: str,
        checks_by_name: dict[str, dict[str, object]],
        remediation_commands: dict[str, str],
    ) -> str | None:
        return remediation_commands.get(name)

    def build_setup_recommended_commands(
        self,
        checks_by_name: dict[str, dict[str, object]],
    ) -> list[str]:
        return []

    def build_setup_blocked_recommendations(
        self,
        checks_by_name: dict[str, dict[str, object]],
    ) -> list[PlatformSetupBlockedRecommendation]:
        return []

    def build_setup_next_steps(
        self,
        checks_by_name: dict[str, dict[str, object]],
        *,
        ready_for_local_runtime: bool,
    ) -> list[PlatformSetupNextStep]:
        return []

    def build_setup_actions(
        self,
        checks_by_name: dict[str, dict[str, object]],
        *,
        recommended_commands: tuple[str, ...],
    ) -> list[PlatformSetupAction]:
        return []

    def tool_live_runtime_blockers(
        self,
        tool: ToolName,
        steps_by_name: dict[str, object],
    ) -> list[str]:
        step = steps_by_name.get("linux_platform")
        if step is not None:
            return [getattr(step, "label", "Linux platform")]
        return ["Linux platform"]

    def tool_live_runtime_suggested_command(
        self,
        tool: ToolName,
        steps_by_name: dict[str, object],
    ) -> str | None:
        return None
