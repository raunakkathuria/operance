from __future__ import annotations

from operance.models.actions import ToolName


def test_get_platform_provider_returns_linux_provider_for_linux_host() -> None:
    from operance.platforms import get_platform_provider

    provider = get_platform_provider(system_name="Linux")

    assert provider.provider_id == "linux_kde_wayland"


def test_get_platform_provider_returns_windows_provider_for_windows_host() -> None:
    from operance.platforms import get_platform_provider

    provider = get_platform_provider(system_name="Windows")

    assert provider.provider_id == "windows_desktop"
    assert provider.release_verification_target == "windows_desktop_unverified"
    assert provider.release_verified_tools == frozenset()
    assert provider.tool_live_runtime_blockers(ToolName.APPS_LAUNCH, {}) == [
        "Windows desktop adapter"
    ]


def test_get_platform_provider_returns_macos_provider_for_darwin_host() -> None:
    from operance.platforms import get_platform_provider

    provider = get_platform_provider(system_name="Darwin")

    assert provider.provider_id == "macos_desktop"
    assert provider.release_verification_target == "macos_desktop_unverified"
    assert provider.release_verified_tools == frozenset()
    assert provider.tool_live_runtime_blockers(ToolName.APPS_LAUNCH, {}) == [
        "macOS desktop adapter"
    ]


def test_build_setup_snapshot_uses_platform_provider_check_metadata(monkeypatch) -> None:
    from operance.platforms.base import CheckMetadata
    from operance.ui.setup import build_setup_snapshot

    class _FakeProvider:
        provider_id = "fake_platform"
        release_verification_target = "fake_release"
        release_verified_tools = frozenset()
        check_metadata = (
            CheckMetadata(
                name="fake_runtime",
                label="Fake runtime",
                required_for_local_runtime=True,
                remediation_command="run fake setup",
            ),
        )

        def recommended_command_for_check(
            self,
            name: str,
            status: str,
            checks_by_name: dict[str, dict[str, object]],
            remediation_commands: dict[str, str],
        ) -> str | None:
            return "run provider setup"

        def build_setup_recommended_commands(
            self,
            checks_by_name: dict[str, dict[str, object]],
        ) -> list[str]:
            return []

        def build_setup_blocked_recommendations(
            self,
            checks_by_name: dict[str, dict[str, object]],
        ) -> list[object]:
            return []

        def build_setup_next_steps(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            ready_for_local_runtime: bool,
        ) -> list[object]:
            return []

        def build_setup_actions(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            recommended_commands: tuple[str, ...],
        ) -> list[object]:
            return []

        def tool_live_runtime_blockers(self, tool: ToolName, steps_by_name: dict[str, object]) -> list[str]:
            return []

    monkeypatch.setattr(
        "operance.ui.setup.get_platform_provider",
        lambda system_name=None, provider_id=None: _FakeProvider(),
    )

    snapshot = build_setup_snapshot(
        {
            "platform": "TestOS",
            "platform_provider": "fake_platform",
            "python_version": "3.14.0",
            "checks": [
                {
                    "name": "fake_runtime",
                    "status": "warn",
                    "detail": "missing fake runtime",
                }
            ],
        }
    )

    steps = {step["name"]: step for step in snapshot.to_dict()["steps"]}

    assert steps["fake_runtime"] == {
        "name": "fake_runtime",
        "label": "Fake runtime",
        "status": "warn",
        "detail": "missing fake runtime",
        "required": True,
        "recommended_command": "run provider setup",
    }


def test_build_setup_snapshot_allows_provider_remediation_override(monkeypatch) -> None:
    from operance.platforms.base import CheckMetadata
    from operance.ui.setup import build_setup_snapshot

    class _FakeProvider:
        provider_id = "fake_platform"
        release_verification_target = "fake_release"
        release_verified_tools = frozenset()
        check_metadata = (
            CheckMetadata(
                name="tray_user_service_installed",
                label="Tray user service installed",
                remediation_command="provider install tray",
            ),
        )

        def recommended_command_for_check(
            self,
            name: str,
            status: str,
            checks_by_name: dict[str, dict[str, object]],
            remediation_commands: dict[str, str],
        ) -> str | None:
            return remediation_commands.get(name)

        def build_setup_recommended_commands(self, checks_by_name: dict[str, dict[str, object]]) -> list[str]:
            return []

        def build_setup_blocked_recommendations(self, checks_by_name: dict[str, dict[str, object]]) -> list[object]:
            return []

        def build_setup_next_steps(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            ready_for_local_runtime: bool,
        ) -> list[object]:
            return []

        def build_setup_actions(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            recommended_commands: tuple[str, ...],
        ) -> list[object]:
            return []

        def tool_live_runtime_blockers(self, tool: ToolName, steps_by_name: dict[str, object]) -> list[str]:
            return []

    monkeypatch.setattr(
        "operance.ui.setup.get_platform_provider",
        lambda system_name=None, provider_id=None: _FakeProvider(),
    )

    snapshot = build_setup_snapshot(
        {
            "platform": "TestOS",
            "platform_provider": "fake_platform",
            "python_version": "3.14.0",
            "checks": [
                {
                    "name": "tray_user_service_installed",
                    "status": "warn",
                    "detail": "missing tray service",
                }
            ],
        }
    )

    steps = {step["name"]: step for step in snapshot.to_dict()["steps"]}

    assert steps["tray_user_service_installed"]["recommended_command"] == "provider install tray"


def test_build_setup_snapshot_uses_platform_provider_setup_surfaces(monkeypatch) -> None:
    from operance.platforms.base import (
        CheckMetadata,
        PlatformSetupAction,
        PlatformSetupBlockedRecommendation,
        PlatformSetupNextStep,
    )
    from operance.ui.setup import build_setup_snapshot

    class _FakeProvider:
        provider_id = "fake_platform"
        release_verification_target = "fake_release"
        release_verified_tools = frozenset()
        check_metadata = (
            CheckMetadata(
                name="linux_platform",
                label="Linux platform",
                required_for_local_runtime=True,
            ),
        )

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
            return ["provider recommended command"]

        def build_setup_blocked_recommendations(
            self,
            checks_by_name: dict[str, dict[str, object]],
        ) -> list[PlatformSetupBlockedRecommendation]:
            return [
                PlatformSetupBlockedRecommendation(
                    label="Provider blocked recommendation",
                    reason="Blocked by provider condition.",
                    suggested_command="provider suggested command",
                )
            ]

        def build_setup_next_steps(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            ready_for_local_runtime: bool,
        ) -> list[PlatformSetupNextStep]:
            return [
                PlatformSetupNextStep(
                    label="Provider next step",
                    command="provider next command",
                )
            ]

        def build_setup_actions(
            self,
            checks_by_name: dict[str, dict[str, object]],
            *,
            recommended_commands: tuple[str, ...],
        ) -> list[PlatformSetupAction]:
            return [
                PlatformSetupAction(
                    action_id="provider_action",
                    label="Provider action",
                    command="provider action command",
                    available=True,
                    recommended=recommended_commands == ("provider recommended command",),
                )
            ]

        def tool_live_runtime_blockers(self, tool: ToolName, steps_by_name: dict[str, object]) -> list[str]:
            return []

    monkeypatch.setattr(
        "operance.ui.setup.get_platform_provider",
        lambda system_name=None, provider_id=None: _FakeProvider(),
    )

    snapshot = build_setup_snapshot(
        {
            "platform": "TestOS",
            "platform_provider": "fake_platform",
            "python_version": "3.14.0",
            "checks": [
                {
                    "name": "linux_platform",
                    "status": "ok",
                    "detail": "Linux",
                }
            ],
        }
    )
    payload = snapshot.to_dict()

    assert payload["recommended_commands"] == ["provider recommended command"]
    assert payload["blocked_recommendations"] == [
        {
            "label": "Provider blocked recommendation",
            "reason": "Blocked by provider condition.",
            "suggested_command": "provider suggested command",
        }
    ]
    assert payload["next_steps"] == [
        {
            "label": "Provider next step",
            "command": "provider next command",
        }
    ]
    assert payload["actions"] == [
        {
            "action_id": "provider_action",
            "label": "Provider action",
            "command": "provider action command",
            "available": True,
            "recommended": True,
        }
    ]


def test_supported_command_catalog_uses_platform_provider_runtime_rules(monkeypatch) -> None:
    from operance.supported_commands import build_supported_command_catalog

    class _FakeProvider:
        provider_id = "fake_platform"
        release_verification_target = "fake_release"
        release_verified_tools = frozenset({ToolName.TIME_NOW})

        def tool_live_runtime_blockers(self, tool: ToolName, steps_by_name: dict[str, object]) -> list[str]:
            if tool == ToolName.TIME_NOW:
                return []
            return ["Fake runtime blocker"]

        def tool_live_runtime_suggested_command(
            self,
            tool: ToolName,
            steps_by_name: dict[str, object],
        ) -> str | None:
            return None

    monkeypatch.setattr(
        "operance.supported_commands.get_platform_provider",
        lambda system_name=None, provider_id=None: _FakeProvider(),
    )
    monkeypatch.setattr(
        "operance.supported_commands._build_setup_snapshot",
        lambda report=None: type(
            "_Snapshot",
            (),
            {"steps": []},
        )(),
    )

    catalog = build_supported_command_catalog(
        {
            "platform": "TestOS",
            "platform_provider": "fake_platform",
            "python_version": "3.14.0",
            "checks": [],
        },
        available_only=True,
    )

    commands = {
        command["tool"]: command
        for domain in catalog["domains"]
        for command in domain["commands"]
    }

    assert commands["time.now"]["release_verification_target"] == "fake_release"
    assert commands["time.now"]["live_runtime_status"] == "available"
    assert "apps.launch" not in commands
