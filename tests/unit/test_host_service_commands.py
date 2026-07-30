from __future__ import annotations

from pathlib import Path

import pytest

from operance.platforms import get_platform_provider, list_platform_providers
from operance.platforms.base import HOST_SERVICE_TRAY, HOST_SERVICE_VOICE_LOOP


SCAFFOLD_SYSTEM_NAMES = ("Windows", "Darwin", "FreeBSD")


def test_linux_provider_owns_tray_service_state_command() -> None:
    provider = get_platform_provider(system_name="Linux")

    command = provider.host_service_state_command(HOST_SERVICE_TRAY)

    assert command is not None
    assert command[0] == "systemctl"
    assert "operance-tray.service" in command


@pytest.mark.parametrize(
    ("action", "expects_now"),
    [("enable", True), ("disable", True), ("start", False), ("stop", False)],
)
def test_linux_provider_owns_voice_loop_control_command(action: str, expects_now: bool) -> None:
    provider = get_platform_provider(system_name="Linux")

    command = provider.host_service_control_command(HOST_SERVICE_VOICE_LOOP, action=action)

    assert command is not None
    assert command[:3] == ("systemctl", "--user", action)
    assert ("--now" in command) is expects_now
    assert command[-1] == "operance-voice-loop.service"


def test_linux_provider_owns_service_log_targets() -> None:
    provider = get_platform_provider(system_name="Linux")

    targets = provider.host_service_log_targets(lines=25)

    assert [target.name for target in targets] == [
        "operance-tray.service",
        "operance-voice-loop.service",
    ]
    for target in targets:
        assert target.command[0] == "journalctl"
        assert "25" in target.command


def test_linux_provider_owns_voice_loop_config_update_command() -> None:
    provider = get_platform_provider(system_name="Linux")

    command = provider.voice_loop_config_update_command(
        wakeword_threshold=0.75,
        repo_root=Path("/repo"),
    )

    assert command is not None
    assert command[0] == "bash"
    assert command[1] == "/repo/scripts/update_voice_loop_user_config.sh"
    assert command[-2:] == ("--wakeword-threshold", "0.75")


def test_unknown_service_name_has_no_command() -> None:
    provider = get_platform_provider(system_name="Linux")

    assert provider.host_service_state_command("not_a_service") is None
    assert provider.host_service_control_command("not_a_service", action="start") is None


@pytest.mark.parametrize("system_name", SCAFFOLD_SYSTEM_NAMES)
def test_scaffold_providers_declare_no_host_service_commands(system_name: str) -> None:
    provider = get_platform_provider(system_name=system_name)

    assert provider.host_service_state_command(HOST_SERVICE_TRAY) is None
    assert provider.host_service_control_command(HOST_SERVICE_VOICE_LOOP, action="start") is None
    assert provider.host_service_log_targets(lines=10) == ()
    assert (
        provider.voice_loop_config_update_command(
            wakeword_threshold=0.5,
            repo_root=Path("/repo"),
        )
        is None
    )


def test_every_provider_implements_the_host_service_contract() -> None:
    required = (
        "host_service_state_command",
        "host_service_control_command",
        "host_service_log_targets",
        "voice_loop_config_update_command",
    )

    missing = [
        f"{provider.provider_id}.{name}"
        for provider in list_platform_providers()
        for name in required
        if not callable(getattr(provider, name, None))
    ]

    assert missing == []
