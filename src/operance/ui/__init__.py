"""Optional tray UI surfaces."""

from .setup import (
    SetupAction,
    SetupController,
    SetupRunResult,
    SetupSnapshot,
    SetupStep,
    build_setup_snapshot,
    run_setup_app,
    run_setup_action,
    run_setup_actions,
)
from .tray import (
    TrayConfirmationDialog,
    TrayController,
    TrayInteractionReport,
    TrayNotification,
    TraySnapshot,
    build_tray_snapshot,
    run_tray_app,
    select_tray_notification,
)

__all__ = [
    "SetupSnapshot",
    "SetupStep",
    "SetupAction",
    "SetupController",
    "SetupRunResult",
    "build_setup_snapshot",
    "run_setup_app",
    "run_setup_action",
    "run_setup_actions",
    "TrayConfirmationDialog",
    "TrayController",
    "TrayInteractionReport",
    "TrayNotification",
    "TraySnapshot",
    "build_tray_snapshot",
    "run_tray_app",
    "select_tray_notification",
]
