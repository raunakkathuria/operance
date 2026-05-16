"""Platform provider registry."""

from __future__ import annotations

import platform

from .base import CheckMetadata, PlatformProvider
from .linux import LinuxKdeWaylandPlatformProvider
from .macos import MacOSDesktopPlatformProvider
from .unsupported import UnsupportedPlatformProvider
from .windows import WindowsDesktopPlatformProvider

_LINUX_PROVIDER = LinuxKdeWaylandPlatformProvider()
_WINDOWS_PROVIDER = WindowsDesktopPlatformProvider()
_MACOS_PROVIDER = MacOSDesktopPlatformProvider()
_UNSUPPORTED_PROVIDER = UnsupportedPlatformProvider()
_PROVIDERS_BY_ID = {
    _LINUX_PROVIDER.provider_id: _LINUX_PROVIDER,
    _WINDOWS_PROVIDER.provider_id: _WINDOWS_PROVIDER,
    _MACOS_PROVIDER.provider_id: _MACOS_PROVIDER,
    _UNSUPPORTED_PROVIDER.provider_id: _UNSUPPORTED_PROVIDER,
}


def get_platform_provider(
    *,
    system_name: str | None = None,
    provider_id: str | None = None,
) -> PlatformProvider:
    if provider_id is not None and provider_id in _PROVIDERS_BY_ID:
        return _PROVIDERS_BY_ID[provider_id]

    current_system = system_name or platform.system()
    if current_system == "Linux":
        return _LINUX_PROVIDER
    if current_system == "Windows":
        return _WINDOWS_PROVIDER
    if current_system == "Darwin":
        return _MACOS_PROVIDER
    return _UNSUPPORTED_PROVIDER


__all__ = [
    "CheckMetadata",
    "PlatformProvider",
    "get_platform_provider",
]
