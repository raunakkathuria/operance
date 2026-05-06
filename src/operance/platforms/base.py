"""Platform provider contracts for adapter and environment integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from ..adapters.base import AdapterSet
from ..models.actions import ToolName

if False:  # pragma: no cover
    from ..config import AppConfig


@dataclass(slots=True, frozen=True)
class CheckMetadata:
    name: str
    label: str
    required_for_local_runtime: bool = False
    remediation_command: str | None = None


@dataclass(slots=True, frozen=True)
class PlatformSetupAction:
    action_id: str
    label: str
    command: str
    available: bool
    recommended: bool
    unavailable_reason: str | None = None
    suggested_command: str | None = None


@dataclass(slots=True, frozen=True)
class PlatformSetupBlockedRecommendation:
    label: str
    reason: str
    suggested_command: str


@dataclass(slots=True, frozen=True)
class PlatformSetupNextStep:
    label: str
    command: str


class PlatformProvider(Protocol):
    provider_id: str
    display_name: str
    check_metadata: tuple[CheckMetadata, ...]
    release_verification_target: str
    release_verified_tools: frozenset[ToolName]

    def build_adapters(self, config: "AppConfig") -> AdapterSet: ...

    def build_environment_checks(self) -> list[dict[str, object]]: ...

    def recommended_command_for_check(
        self,
        name: str,
        status: str,
        checks_by_name: Mapping[str, dict[str, object]],
        remediation_commands: Mapping[str, str],
    ) -> str | None: ...

    def build_setup_recommended_commands(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[str]: ...

    def build_setup_blocked_recommendations(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
    ) -> list[PlatformSetupBlockedRecommendation]: ...

    def build_setup_next_steps(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        ready_for_local_runtime: bool,
    ) -> list[PlatformSetupNextStep]: ...

    def build_setup_actions(
        self,
        checks_by_name: Mapping[str, dict[str, object]],
        *,
        recommended_commands: tuple[str, ...],
    ) -> list[PlatformSetupAction]: ...

    def tool_live_runtime_blockers(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> list[str]: ...

    def tool_live_runtime_suggested_command(
        self,
        tool: ToolName,
        steps_by_name: Mapping[str, object],
    ) -> str | None: ...
