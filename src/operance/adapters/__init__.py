"""Adapter protocols and backend builders for desktop-facing integrations."""

from __future__ import annotations

import platform
from typing import TYPE_CHECKING

from ..platforms import get_platform_provider
from .base import (
    AdapterSet,
    AppsAdapter,
    AudioAdapter,
    ClipboardAdapter,
    FilesAdapter,
    NetworkAdapter,
    NotificationsAdapter,
    PowerAdapter,
    TimeAdapter,
    WindowsAdapter,
)
from .conformance import (
    ADAPTER_TOOL_CONTRACTS,
    AdapterConformanceReport,
    AdapterToolContract,
    adapter_capability_matrix,
    validate_adapter_set,
)
from .linux import build_linux_adapter_set
from .mock import build_mock_adapter_set

if TYPE_CHECKING:
    from ..config import AppConfig


def build_default_adapter_set(config: "AppConfig", *, system_name: str | None = None) -> AdapterSet:
    current_system = system_name or platform.system()
    if config.runtime.developer_mode:
        return build_mock_adapter_set(desktop_dir=config.paths.desktop_dir)
    provider = get_platform_provider(system_name=current_system)
    return provider.build_adapters(config)

__all__ = [
    "AdapterSet",
    "ADAPTER_TOOL_CONTRACTS",
    "AdapterConformanceReport",
    "AdapterToolContract",
    "AppsAdapter",
    "AudioAdapter",
    "ClipboardAdapter",
    "FilesAdapter",
    "NetworkAdapter",
    "NotificationsAdapter",
    "PowerAdapter",
    "TimeAdapter",
    "WindowsAdapter",
    "build_default_adapter_set",
    "build_linux_adapter_set",
    "build_mock_adapter_set",
    "adapter_capability_matrix",
    "validate_adapter_set",
]
