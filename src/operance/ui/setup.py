"""Structured setup status projection for future first-run UI flows."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
import subprocess
from typing import Any

from ..doctor import build_environment_report
from ..platforms import get_platform_provider
from ..platforms.base import (
    PlatformSetupAction,
    PlatformSetupBlockedRecommendation,
    PlatformSetupNextStep,
)

_CHECK_LABELS = {
    "python_3_12_plus": "Python 3.12+",
    "virtualenv_active": "Virtual environment",
    "linux_platform": "Linux platform",
    "kde_wayland_target": "KDE Wayland session",
    "wayland_session_accessible": "Wayland session access",
    "xdg_open_available": "xdg-open",
    "notify_send_available": "notify-send",
    "gdbus_available": "gdbus",
    "networkmanager_cli_available": "NetworkManager CLI",
    "audio_cli_available": "Audio control CLI",
    "audio_capture_cli_available": "Audio capture CLI",
    "audio_playback_cli_available": "Audio playback CLI",
    "clipboard_cli_available": "Wayland clipboard CLI",
    "text_input_cli_available": "Wayland text input CLI",
    "deb_packaging_cli_available": "Debian packaging CLI",
    "rpm_packaging_cli_available": "RPM packaging CLI",
    "archive_packaging_cli_available": "Archive CLI",
    "deb_package_installer_available": "Debian package installer",
    "rpm_package_installer_available": "RPM package installer",
    "systemctl_user_available": "systemctl --user",
    "tray_user_service_installed": "Tray user service installed",
    "tray_user_service_enabled": "Tray user service enabled",
    "tray_user_service_active": "Tray user service active",
    "voice_loop_user_service_installed": "Voice-loop user service installed",
    "voice_loop_user_service_enabled": "Voice-loop user service enabled",
    "voice_loop_user_service_active": "Voice-loop user service active",
    "voice_loop_user_config_available": "Voice-loop user config",
    "voice_loop_runtime_status_available": "Voice-loop runtime status",
    "voice_loop_runtime_heartbeat_fresh": "Voice-loop runtime heartbeat",
    "voice_loop_wakeword_customized": "Voice-loop wake-word config",
    "tray_ui_available": "Tray UI backend",
    "wakeword_backend_available": "Wake-word backend",
    "wakeword_model_asset_available": "Wake-word model asset",
    "wakeword_model_source_available": "Wake-word model source",
    "stt_backend_available": "Speech-to-text backend",
    "tts_backend_available": "Text-to-speech backend",
    "tts_model_asset_available": "TTS model asset",
    "tts_model_source_available": "TTS model source",
    "tts_voices_asset_available": "TTS voices asset",
    "tts_voices_source_available": "TTS voices source",
    "planner_runtime_enabled": "Planner runtime enabled",
    "planner_endpoint_healthy": "Planner endpoint health",
    "power_status_available": "Power status surface",
}

_REQUIRED_RUNTIME_CHECKS = {
    "python_3_12_plus",
    "virtualenv_active",
    "linux_platform",
    "kde_wayland_target",
    "xdg_open_available",
    "gdbus_available",
    "networkmanager_cli_available",
    "audio_cli_available",
    "audio_capture_cli_available",
    "systemctl_user_available",
    "power_status_available",
}

_STEP_ORDER = [
    "python_3_12_plus",
    "virtualenv_active",
    "linux_platform",
    "kde_wayland_target",
    "wayland_session_accessible",
    "xdg_open_available",
    "notify_send_available",
    "gdbus_available",
    "networkmanager_cli_available",
    "audio_cli_available",
    "audio_capture_cli_available",
    "audio_playback_cli_available",
    "clipboard_cli_available",
    "text_input_cli_available",
    "systemctl_user_available",
    "power_status_available",
    "tray_user_service_installed",
    "tray_user_service_enabled",
    "tray_user_service_active",
    "voice_loop_user_service_installed",
    "voice_loop_user_service_enabled",
    "voice_loop_user_service_active",
    "voice_loop_user_config_available",
    "voice_loop_runtime_status_available",
    "voice_loop_runtime_heartbeat_fresh",
    "voice_loop_wakeword_customized",
    "tray_ui_available",
    "wakeword_backend_available",
    "wakeword_model_asset_available",
    "wakeword_model_source_available",
    "stt_backend_available",
    "tts_backend_available",
    "tts_model_asset_available",
    "tts_model_source_available",
    "tts_voices_asset_available",
    "tts_voices_source_available",
    "planner_runtime_enabled",
    "planner_endpoint_healthy",
    "deb_packaging_cli_available",
    "rpm_packaging_cli_available",
    "archive_packaging_cli_available",
    "deb_package_installer_available",
    "rpm_package_installer_available",
]

_REMEDIATION_COMMANDS = {
    "virtualenv_active": "./scripts/install_linux_dev.sh",
    "tray_user_service_installed": "./scripts/install_local_linux_app.sh",
    "tray_user_service_enabled": "./scripts/control_systemd_user_services.sh enable",
    "tray_user_service_active": "./scripts/control_systemd_user_services.sh restart",
    "voice_loop_user_service_installed": "./scripts/install_voice_loop_user_service.sh",
    "voice_loop_user_service_enabled": "./scripts/control_systemd_user_services.sh enable --voice-loop",
    "voice_loop_user_service_active": "./scripts/control_systemd_user_services.sh restart --voice-loop",
    "voice_loop_user_config_available": "./scripts/install_voice_loop_user_config.sh",
    "voice_loop_runtime_status_available": "python3 -m operance.cli --voice-loop-status",
    "voice_loop_runtime_heartbeat_fresh": "python3 -m operance.cli --voice-loop-status",
    "voice_loop_wakeword_customized": "python3 -m operance.cli --voice-loop-config",
    "deb_packaging_cli_available": "./scripts/install_packaging_tools.sh --deb",
    "rpm_packaging_cli_available": "./scripts/install_packaging_tools.sh --rpm",
    "wayland_session_accessible": "python3 -m operance.cli --doctor",
    "tray_ui_available": 'python3 -m pip install -e ".[dev,ui]"',
    "wakeword_backend_available": 'python3 -m pip install -e ".[dev,voice]"',
    "wakeword_model_asset_available": "python3 -m operance.cli --voice-asset-paths",
    "stt_backend_available": 'python3 -m pip install -e ".[dev,voice]"',
    "tts_backend_available": 'python3 -m pip install -e ".[dev,voice]"',
    "tts_model_asset_available": "python3 -m operance.cli --voice-asset-paths",
    "tts_voices_asset_available": "python3 -m operance.cli --voice-asset-paths",
    "planner_endpoint_healthy": "python3 -m operance.cli --planner-health",
}

@dataclass(slots=True, frozen=True)
class SetupStep:
    name: str
    label: str
    status: str
    detail: Any
    required: bool
    recommended_command: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "required": self.required,
            "recommended_command": self.recommended_command,
        }


@dataclass(slots=True, frozen=True)
class SetupAction:
    action_id: str
    label: str
    command: str
    available: bool
    recommended: bool
    unavailable_reason: str | None = None
    suggested_command: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "action_id": self.action_id,
            "label": self.label,
            "command": self.command,
            "available": self.available,
            "recommended": self.recommended,
        }
        if self.unavailable_reason is not None:
            payload["unavailable_reason"] = self.unavailable_reason
        if self.suggested_command is not None:
            payload["suggested_command"] = self.suggested_command
        return payload


@dataclass(slots=True, frozen=True)
class SetupBlockedRecommendation:
    label: str
    reason: str
    suggested_command: str

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "reason": self.reason,
            "suggested_command": self.suggested_command,
        }


@dataclass(slots=True, frozen=True)
class SetupNextStep:
    label: str
    command: str

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "command": self.command,
        }


@dataclass(slots=True, frozen=True)
class SetupSnapshot:
    summary_status: str
    ready_for_local_runtime: bool
    ready_for_mvp: bool
    ready_for_voice: bool
    ready_for_packaging: bool
    available_package_formats: list[str]
    next_steps: list[SetupNextStep]
    recommended_commands: list[str]
    blocked_recommendations: list[SetupBlockedRecommendation]
    actions: list[SetupAction]
    steps: list[SetupStep]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary_status": self.summary_status,
            "ready_for_local_runtime": self.ready_for_local_runtime,
            "ready_for_mvp": self.ready_for_mvp,
            "ready_for_voice": self.ready_for_voice,
            "ready_for_packaging": self.ready_for_packaging,
            "available_package_formats": list(self.available_package_formats),
            "next_steps": [item.to_dict() for item in self.next_steps],
            "recommended_commands": list(self.recommended_commands),
            "blocked_recommendations": [item.to_dict() for item in self.blocked_recommendations],
            "actions": [action.to_dict() for action in self.actions],
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True, frozen=True)
class SetupRunResult:
    action_id: str
    label: str
    command: str
    status: str
    returncode: int | None
    stdout: str | None
    stderr: str | None
    dry_run: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "command": self.command,
            "status": self.status,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "dry_run": self.dry_run,
        }


@dataclass(slots=True)
class SetupController:
    def snapshot(self) -> SetupSnapshot:
        return build_setup_snapshot()

    def run_action(self, action_id: str, *, dry_run: bool = False) -> SetupRunResult:
        return run_setup_action(action_id, dry_run=dry_run)

    def run_recommended(self, *, dry_run: bool = False) -> list[SetupRunResult]:
        return run_setup_actions(recommended_only=True, dry_run=dry_run)


def build_setup_snapshot(report: dict[str, object] | None = None) -> SetupSnapshot:
    setup_report = build_environment_report() if report is None else report
    provider = get_platform_provider(
        system_name=str(setup_report.get("platform") or ""),
        provider_id=(
            str(setup_report["platform_provider"])
            if isinstance(setup_report.get("platform_provider"), str)
            else None
        ),
    )
    raw_checks = setup_report.get("checks", [])
    checks_by_name = {
        check["name"]: check
        for check in raw_checks
        if isinstance(check, dict) and "name" in check and "status" in check
    }
    labels = dict(_CHECK_LABELS)
    remediation_commands = dict(_REMEDIATION_COMMANDS)
    required_runtime_checks = set(_REQUIRED_RUNTIME_CHECKS)
    step_order = list(_STEP_ORDER)
    for metadata in provider.check_metadata:
        labels[metadata.name] = metadata.label
        if metadata.remediation_command is not None:
            remediation_commands[metadata.name] = metadata.remediation_command
        if metadata.required_for_local_runtime:
            required_runtime_checks.add(metadata.name)
        if metadata.name not in step_order:
            step_order.append(metadata.name)
    for name in checks_by_name:
        if name not in step_order:
            step_order.append(name)

    steps: list[SetupStep] = []
    for name in step_order:
        check = checks_by_name.get(name)
        if check is None:
            continue

        current_status = str(check["status"])
        steps.append(
            SetupStep(
                name=name,
                label=labels.get(name, name.replace("_", " ")),
                status=current_status,
                detail=check.get("detail"),
                required=name in required_runtime_checks,
                recommended_command=(
                    provider.recommended_command_for_check(
                        name,
                        current_status,
                        checks_by_name,
                        remediation_commands,
                    )
                    if current_status != "ok"
                    else None
                ),
            )
        )

    ready_for_local_runtime = all(
        str(checks_by_name.get(name, {}).get("status")) == "ok" for name in required_runtime_checks
    )
    ready_for_mvp = ready_for_local_runtime and (
        str(checks_by_name.get("stt_backend_available", {}).get("status")) == "ok"
    )
    ready_for_voice = ready_for_local_runtime and all(
        str(checks_by_name.get(name, {}).get("status")) == "ok"
        for name in (
            "wakeword_backend_available",
            "stt_backend_available",
            "tts_backend_available",
            "audio_playback_cli_available",
        )
    )

    available_package_formats: list[str] = []
    if str(checks_by_name.get("deb_packaging_cli_available", {}).get("status")) == "ok":
        available_package_formats.append("deb")
    if str(checks_by_name.get("rpm_packaging_cli_available", {}).get("status")) == "ok":
        available_package_formats.append("rpm")
    ready_for_packaging = (
        str(checks_by_name.get("archive_packaging_cli_available", {}).get("status")) == "ok"
        and bool(available_package_formats)
    )
    planner_ready = (
        str(checks_by_name.get("planner_runtime_enabled", {}).get("status")) != "ok"
        or str(checks_by_name.get("planner_endpoint_healthy", {}).get("status")) == "ok"
    )

    if not ready_for_local_runtime:
        summary_status = "needs_attention"
    elif ready_for_mvp and planner_ready:
        summary_status = "ready"
    else:
        summary_status = "partial"

    recommended_commands = provider.build_setup_recommended_commands(checks_by_name)
    blocked_recommendations = [
        _setup_blocked_recommendation_from_platform(item)
        for item in provider.build_setup_blocked_recommendations(checks_by_name)
    ]
    next_steps = [
        _setup_next_step_from_platform(item)
        for item in provider.build_setup_next_steps(
            checks_by_name,
            ready_for_local_runtime=ready_for_local_runtime,
        )
    ]
    actions = [
        _setup_action_from_platform(item)
        for item in provider.build_setup_actions(
            checks_by_name,
            recommended_commands=tuple(recommended_commands),
        )
    ]

    return SetupSnapshot(
        summary_status=summary_status,
        ready_for_local_runtime=ready_for_local_runtime,
        ready_for_mvp=ready_for_mvp,
        ready_for_voice=ready_for_voice,
        ready_for_packaging=ready_for_packaging,
        available_package_formats=available_package_formats,
        next_steps=next_steps,
        recommended_commands=recommended_commands,
        blocked_recommendations=blocked_recommendations,
        actions=actions,
        steps=steps,
    )


def _setup_action_from_platform(action: PlatformSetupAction) -> SetupAction:
    return SetupAction(
        action_id=action.action_id,
        label=action.label,
        command=action.command,
        available=action.available,
        recommended=action.recommended,
        unavailable_reason=action.unavailable_reason,
        suggested_command=action.suggested_command,
    )


def _setup_blocked_recommendation_from_platform(
    recommendation: PlatformSetupBlockedRecommendation,
) -> SetupBlockedRecommendation:
    return SetupBlockedRecommendation(
        label=recommendation.label,
        reason=recommendation.reason,
        suggested_command=recommendation.suggested_command,
    )


def _setup_next_step_from_platform(step: PlatformSetupNextStep) -> SetupNextStep:
    return SetupNextStep(
        label=step.label,
        command=step.command,
    )


def run_setup_action(
    action_id: str,
    *,
    snapshot: SetupSnapshot | None = None,
    dry_run: bool = False,
) -> SetupRunResult:
    current_snapshot = build_setup_snapshot() if snapshot is None else snapshot
    action = _find_setup_action(current_snapshot, action_id)
    if action is None:
        raise ValueError(f"unknown setup action: {action_id}")
    if not action.available:
        reason_suffix = f" ({action.unavailable_reason})" if action.unavailable_reason is not None else ""
        raise ValueError(f"setup action is not available: {action_id}{reason_suffix}")

    if dry_run:
        return SetupRunResult(
            action_id=action.action_id,
            label=action.label,
            command=action.command,
            status="planned",
            returncode=None,
            stdout=None,
            stderr=None,
            dry_run=True,
        )

    completed = subprocess.run(
        _command_argv(action.command),
        capture_output=True,
        check=False,
        text=True,
    )
    return SetupRunResult(
        action_id=action.action_id,
        label=action.label,
        command=action.command,
        status="success" if completed.returncode == 0 else "failed",
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        dry_run=False,
    )


def run_setup_actions(
    *,
    action_ids: list[str] | None = None,
    recommended_only: bool = False,
    snapshot: SetupSnapshot | None = None,
    dry_run: bool = False,
) -> list[SetupRunResult]:
    current_snapshot = build_setup_snapshot() if snapshot is None else snapshot

    if recommended_only:
        selected_ids = [action.action_id for action in current_snapshot.actions if action.recommended]
    elif action_ids is not None:
        selected_ids = list(action_ids)
    else:
        raise ValueError("no setup actions requested")

    return [
        run_setup_action(action_id, snapshot=current_snapshot, dry_run=dry_run)
        for action_id in selected_ids
    ]


def _find_setup_action(snapshot: SetupSnapshot, action_id: str) -> SetupAction | None:
    for action in snapshot.actions:
        if action.action_id == action_id:
            return action
    return None


def _command_argv(command: str) -> list[str]:
    args = shlex.split(command)
    if args and args[0].startswith("./scripts/") and args[0].endswith(".sh"):
        return ["bash", *args]
    return args


def run_setup_app() -> int:
    (
        QApplication,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        Qt,
        QVBoxLayout,
        QWidget,
    ) = _load_setup_pyside6_api()

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    controller = SetupController()
    window = QWidget()
    window.setWindowTitle("Operance Setup")
    layout = QVBoxLayout(window)

    summary_label = QLabel()
    summary_label.setWordWrap(True)
    steps_list = QListWidget()
    step_details_label = QLabel()
    step_details_label.setWordWrap(True)
    actions_list = QListWidget()
    action_details_label = QLabel()
    action_details_label.setWordWrap(True)
    run_selected_button = QPushButton("Run selected action")
    dry_run_selected_button = QPushButton("Dry-run selected action")
    run_recommended_button = QPushButton("Run recommended actions")
    dry_run_recommended_button = QPushButton("Dry-run recommended actions")
    refresh_button = QPushButton("Refresh")
    close_button = QPushButton("Close")

    layout.addWidget(summary_label)
    layout.addWidget(steps_list)
    layout.addWidget(step_details_label)
    layout.addWidget(actions_list)
    layout.addWidget(action_details_label)
    layout.addWidget(run_selected_button)
    layout.addWidget(dry_run_selected_button)
    layout.addWidget(run_recommended_button)
    layout.addWidget(dry_run_recommended_button)
    layout.addWidget(refresh_button)
    layout.addWidget(close_button)

    current_snapshot: SetupSnapshot | None = None

    def refresh() -> None:
        nonlocal current_snapshot
        current_snapshot = controller.snapshot()
        summary_label.setText(_build_setup_summary(current_snapshot))
        steps_list.clear()
        for step in current_snapshot.steps:
            item = QListWidgetItem(_format_setup_step_line(step))
            item.setData(Qt.ItemDataRole.UserRole, step.name)
            steps_list.addItem(item)
        actions_list.clear()
        for action in current_snapshot.actions:
            item = QListWidgetItem(_format_setup_action_line(action))
            item.setData(Qt.ItemDataRole.UserRole, action.action_id)
            if not action.available:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            actions_list.addItem(item)
        if steps_list.count() > 0:
            steps_list.setCurrentRow(0)
        else:
            step_details_label.setText("No setup checks available.")
        if actions_list.count() > 0:
            actions_list.setCurrentRow(0)
        else:
            action_details_label.setText("No setup actions available.")
        run_recommended_button.setEnabled(any(action.recommended for action in current_snapshot.actions))
        dry_run_recommended_button.setEnabled(
            any(action.recommended for action in current_snapshot.actions)
        )
        _refresh_selected_step_details()
        _refresh_selected_details()

    def _selected_step_name() -> str | None:
        current_item = steps_list.currentItem()
        if current_item is None:
            return None
        return current_item.data(Qt.ItemDataRole.UserRole)

    def _refresh_selected_step_details() -> None:
        if current_snapshot is None:
            step_details_label.setText("No setup snapshot available.")
            return
        step_name = _selected_step_name()
        if step_name is None:
            step_details_label.setText("Select a setup check to inspect it.")
            return
        step = next((item for item in current_snapshot.steps if item.name == step_name), None)
        if step is None:
            step_details_label.setText("Selected setup check is not available.")
            return
        step_details_label.setText(_build_setup_step_details(step))

    def _selected_action_id() -> str | None:
        current_item = actions_list.currentItem()
        if current_item is None:
            return None
        return current_item.data(Qt.ItemDataRole.UserRole)

    def _refresh_selected_details() -> None:
        if current_snapshot is None:
            action_details_label.setText("No setup snapshot available.")
            run_selected_button.setEnabled(False)
            dry_run_selected_button.setEnabled(False)
            return
        action_id = _selected_action_id()
        if action_id is None:
            action_details_label.setText("Select a setup action to inspect it.")
            run_selected_button.setEnabled(False)
            dry_run_selected_button.setEnabled(False)
            return
        action = _find_setup_action(current_snapshot, action_id)
        if action is None:
            action_details_label.setText("Selected setup action is not available.")
            run_selected_button.setEnabled(False)
            dry_run_selected_button.setEnabled(False)
            return
        action_details_label.setText(_build_setup_action_details(action))
        run_selected_button.setEnabled(action.available)
        dry_run_selected_button.setEnabled(action.available)

    def run_selected_action(*, dry_run: bool = False) -> None:
        if current_snapshot is None:
            return
        action_id = _selected_action_id()
        if action_id is None:
            return
        action = _find_setup_action(current_snapshot, action_id)
        if action is None:
            return
        if not dry_run and not _show_setup_run_confirmation(QMessageBox, [action.command]):
            return
        result = controller.run_action(action_id, dry_run=dry_run)
        refresh()
        _show_setup_run_results(QMessageBox, [result])

    def run_recommended_actions(*, dry_run: bool = False) -> None:
        if current_snapshot is None:
            return
        commands = [action.command for action in current_snapshot.actions if action.recommended]
        if not commands:
            message = "No recommended setup actions are currently runnable."
            if current_snapshot.blocked_recommendations:
                message = "\n\n".join(
                    [
                        message,
                        *[
                            f"{item.label}: {item.reason}\nSuggested command: {item.suggested_command}"
                            for item in current_snapshot.blocked_recommendations
                        ],
                    ]
                )
            _show_setup_information(QMessageBox, message)
            return
        if not dry_run and not _show_setup_run_confirmation(QMessageBox, commands):
            return
        results = controller.run_recommended(dry_run=dry_run)
        refresh()
        _show_setup_run_results(QMessageBox, results)

    steps_list.currentItemChanged.connect(lambda current, previous: _refresh_selected_step_details())
    actions_list.currentItemChanged.connect(lambda current, previous: _refresh_selected_details())
    run_selected_button.clicked.connect(lambda: run_selected_action(dry_run=False))
    dry_run_selected_button.clicked.connect(lambda: run_selected_action(dry_run=True))
    run_recommended_button.clicked.connect(lambda: run_recommended_actions(dry_run=False))
    dry_run_recommended_button.clicked.connect(lambda: run_recommended_actions(dry_run=True))
    refresh_button.clicked.connect(refresh)
    close_button.clicked.connect(window.close)

    refresh()
    window.resize(720, 520)
    window.show()
    app.exec()
    return 0


def _build_setup_summary(snapshot: SetupSnapshot) -> str:
    summary = (
        f"Setup status: {snapshot.summary_status}. "
        f"Local runtime ready: {'yes' if snapshot.ready_for_local_runtime else 'no'}. "
        f"MVP ready: {'yes' if snapshot.ready_for_mvp else 'no'}. "
        f"Voice ready: {'yes' if snapshot.ready_for_voice else 'no'}. "
        f"Packaging ready: {'yes' if snapshot.ready_for_packaging else 'no'}."
    )
    if snapshot.next_steps:
        summary = (
            f"{summary} "
            f"Next: {'; '.join(step.label for step in snapshot.next_steps)}."
        )
    return summary


def _format_setup_step_line(step: SetupStep) -> str:
    suffix = " [required]" if step.required else ""
    return f"[{step.status}] {step.label}{suffix}"


def _format_setup_action_line(action: SetupAction) -> str:
    prefix = "[recommended] " if action.recommended else ""
    suffix = "" if action.available else " (unavailable)"
    return f"{prefix}{action.label}{suffix}"


def _build_setup_step_details(step: SetupStep) -> str:
    lines = [
        f"Check: {step.label}",
        f"Status: {step.status}",
        f"Required: {'yes' if step.required else 'no'}",
    ]
    if step.recommended_command is not None:
        lines.append(f"Recommended command: {step.recommended_command}")
    lines.append(f"Detail: {step.detail}")
    return "\n".join(lines)


def _build_setup_action_details(action: SetupAction) -> str:
    lines = [
        f"Action: {action.label}",
        f"Command: {action.command}",
        f"Recommended: {'yes' if action.recommended else 'no'}",
        f"Available: {'yes' if action.available else 'no'}",
    ]
    if action.unavailable_reason is not None:
        lines.append(f"Unavailable reason: {action.unavailable_reason}")
    if action.suggested_command is not None:
        lines.append(f"Suggested command: {action.suggested_command}")
    return "\n".join(lines)


def _build_setup_run_results_text(results: list[SetupRunResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"{result.label}: {result.status}")
        lines.append(f"  Command: {result.command}")
        if result.returncode is not None:
            lines.append(f"  Return code: {result.returncode}")
    return "\n".join(lines)


def _build_setup_run_results_detail(result: SetupRunResult) -> str:
    lines = [
        f"Action: {result.label}",
        f"Status: {result.status}",
        f"Command: {result.command}",
    ]
    if result.returncode is not None:
        lines.append(f"Return code: {result.returncode}")
    if result.stdout:
        lines.append(f"Stdout: {result.stdout}")
    if result.stderr:
        lines.append(f"Stderr: {result.stderr}")
    return "\n".join(lines)


def _show_setup_run_confirmation(qmessagebox: Any, commands: list[str]) -> bool:
    box = qmessagebox()
    box.setWindowTitle("Run setup action")
    box.setText("Run the selected setup command(s)?")
    box.setInformativeText("\n".join(commands))
    box.setIcon(qmessagebox.Icon.Warning)
    confirm_button = box.addButton("Run", qmessagebox.ButtonRole.AcceptRole)
    box.addButton("Cancel", qmessagebox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() == confirm_button


def _show_setup_run_results(qmessagebox: Any, results: list[SetupRunResult]) -> None:
    failed = [result for result in results if result.status not in {"success", "planned"}]
    box = qmessagebox()
    box.setWindowTitle("Operance Setup")
    all_planned = all(result.status == "planned" for result in results)
    if all_planned:
        box.setText("Setup actions planned.")
    else:
        box.setText("Setup actions completed." if not failed else "One or more setup actions failed.")
    box.setInformativeText(_build_setup_run_results_text(results))
    if hasattr(box, "setDetailedText"):
        box.setDetailedText("\n\n".join(_build_setup_run_results_detail(result) for result in results))
    box.setIcon(qmessagebox.Icon.Information if not failed else qmessagebox.Icon.Critical)
    box.exec()


def _show_setup_information(qmessagebox: Any, message: str) -> None:
    box = qmessagebox()
    box.setWindowTitle("Operance Setup")
    box.setText(message)
    box.setIcon(qmessagebox.Icon.Information)
    box.exec()


def _load_setup_pyside6_api() -> tuple[type[Any], type[Any], type[Any], type[Any], type[Any], type[Any], Any, type[Any], type[Any]]:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise ValueError("PySide6 is not installed") from exc

    return QApplication, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, Qt, QVBoxLayout, QWidget
