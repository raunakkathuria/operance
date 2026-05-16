"""Minimal tray-state projection and optional PySide6 tray runner."""

from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from dataclasses import dataclass, field
import json
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Lock, Thread
from typing import Any, Callable, Mapping, TextIO

from ..audio import build_default_audio_capture_source
from ..daemon import OperanceDaemon
from ..installed_smoke import (
    InstalledSmokeCheck,
    InstalledSmokeResult,
    build_installed_smoke_result,
)
from ..models.events import RuntimeState
from ..project_info import project_version
from ..status import StatusSnapshot
from ..stt import SpeechTranscriber, build_default_speech_transcriber
from ..support_bundle import write_support_bundle_artifact
from ..support_snapshot import build_support_snapshot, build_support_snapshot_help_text
from ..supported_commands import (
    build_supported_command_catalog,
    build_supported_command_help_text,
)
from .setup import SetupRunResult, run_setup_action
from ..voice import run_manual_voice_session
from ..voice import DEFAULT_CLICK_TO_TALK_MAX_FRAMES
from ..voice.runtime import (
    VoiceLoopRuntimeStatusSnapshot,
    build_voice_loop_runtime_status_snapshot,
)


@dataclass(slots=True, frozen=True)
class TrayConfirmationDialog:
    title: str
    message: str
    details: list[str]
    confirm_label: str
    cancel_label: str

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "message": self.message,
            "details": list(self.details),
            "confirm_label": self.confirm_label,
            "cancel_label": self.cancel_label,
        }


@dataclass(slots=True, frozen=True)
class TrayNotification:
    level: str
    title: str
    message: str
    event_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "event_id": self.event_id,
        }


@dataclass(slots=True, frozen=True)
class TrayInteractionReport:
    title: str
    summary: str
    details: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "summary": self.summary,
            "details": list(self.details),
        }


@dataclass(slots=True, frozen=True)
class TrayInstalledReadinessReport:
    status: str
    title: str
    summary: str
    details: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "details": list(self.details),
        }


@dataclass(slots=True, frozen=True)
class TraySnapshot:
    current_state: str
    tray_state: str
    mic_state: str
    state_label: str
    developer_mode: bool
    click_to_talk_label: str
    voice_loop_status: str | None
    voice_loop_state: str | None
    voice_loop_heartbeat_fresh: bool | None
    voice_loop_message: str | None
    voice_loop_activity: str | None
    voice_loop_last_transcript: str | None
    voice_loop_last_response: str | None
    last_command_transcript: str | None
    last_command_preview: str | None
    last_interaction: TrayInteractionReport | None
    pending_confirmation_prompt: str | None
    confirmation_dialog: TrayConfirmationDialog | None
    notification: TrayNotification | None
    can_start_click_to_talk: bool
    can_confirm: bool
    can_cancel: bool
    can_undo: bool
    can_reset_planner: bool
    can_restart_voice_loop_service: bool
    undo_label: str | None
    tooltip: str

    def to_dict(self) -> dict[str, object]:
        return {
            "current_state": self.current_state,
            "tray_state": self.tray_state,
            "mic_state": self.mic_state,
            "state_label": self.state_label,
            "developer_mode": self.developer_mode,
            "click_to_talk_label": self.click_to_talk_label,
            "voice_loop_status": self.voice_loop_status,
            "voice_loop_state": self.voice_loop_state,
            "voice_loop_heartbeat_fresh": self.voice_loop_heartbeat_fresh,
            "voice_loop_message": self.voice_loop_message,
            "voice_loop_activity": self.voice_loop_activity,
            "voice_loop_last_transcript": self.voice_loop_last_transcript,
            "voice_loop_last_response": self.voice_loop_last_response,
            "last_command_transcript": self.last_command_transcript,
            "last_command_preview": self.last_command_preview,
            "last_interaction": (
                None if self.last_interaction is None else self.last_interaction.to_dict()
            ),
            "pending_confirmation_prompt": self.pending_confirmation_prompt,
            "confirmation_dialog": (
                None if self.confirmation_dialog is None else self.confirmation_dialog.to_dict()
            ),
            "notification": None if self.notification is None else self.notification.to_dict(),
            "can_start_click_to_talk": self.can_start_click_to_talk,
            "can_confirm": self.can_confirm,
            "can_cancel": self.can_cancel,
            "can_undo": self.can_undo,
            "can_reset_planner": self.can_reset_planner,
            "can_restart_voice_loop_service": self.can_restart_voice_loop_service,
            "undo_label": self.undo_label,
            "tooltip": self.tooltip,
        }


@dataclass(slots=True)
class TrayController:
    daemon: OperanceDaemon
    env: Mapping[str, str] | None = None
    include_voice_loop_status: bool = False
    click_to_talk_frame_limit: int = DEFAULT_CLICK_TO_TALK_MAX_FRAMES
    _click_to_talk_active: bool = field(default=False, init=False, repr=False)
    _click_to_talk_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _last_click_to_talk_transcript: str | None = field(default=None, init=False, repr=False)
    _last_click_to_talk_response: str | None = field(default=None, init=False, repr=False)
    _last_click_to_talk_result: dict[str, object] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _last_click_to_talk_error: str | None = field(default=None, init=False, repr=False)

    def click_to_talk_active(self) -> bool:
        with self._click_to_talk_lock:
            return self._click_to_talk_active

    def snapshot(self) -> TraySnapshot:
        voice_loop_status = None
        if self.include_voice_loop_status:
            voice_loop_status = build_voice_loop_runtime_status_snapshot(env=self.env)
        return build_tray_snapshot(
            self.daemon.status_snapshot(),
            voice_loop_status=voice_loop_status,
            click_to_talk_active=self.click_to_talk_active(),
            developer_mode=self.daemon.config.runtime.developer_mode,
            fallback_last_transcript=self._last_click_to_talk_transcript,
            fallback_last_response=self._last_click_to_talk_response,
            last_click_to_talk_result=self._last_click_to_talk_result,
            last_click_to_talk_error=self._last_click_to_talk_error,
        )

    def confirm_pending(self) -> TraySnapshot:
        self._clear_click_to_talk_history()
        if self.daemon.pending_confirmation_plan is None:
            return self.snapshot()
        self.daemon.emit_transcript("confirm", confidence=1.0, is_final=True)
        if self.daemon.state_machine.current_state == RuntimeState.RESPONDING:
            self.daemon.complete_response_cycle()
        return self.snapshot()

    def cancel_pending(self) -> TraySnapshot:
        self._clear_click_to_talk_history()
        if self.daemon.pending_confirmation_plan is None:
            return self.snapshot()
        self.daemon.emit_transcript("cancel", confidence=1.0, is_final=True)
        if self.daemon.state_machine.current_state == RuntimeState.RESPONDING:
            self.daemon.complete_response_cycle()
        return self.snapshot()

    def undo_last_action(self) -> TraySnapshot:
        self._clear_click_to_talk_history()
        self.daemon.undo_last_action()
        return self.snapshot()

    def reset_planner_runtime(self) -> TraySnapshot:
        self._clear_click_to_talk_history()
        self.daemon.reset_planner_runtime()
        return self.snapshot()

    def restart_voice_loop_service(self) -> SetupRunResult:
        return run_setup_action("restart_voice_loop_service")

    def installed_readiness_report(self) -> TrayInstalledReadinessReport:
        return build_installed_readiness_report(build_installed_smoke_result(env=self.env))

    def start_click_to_talk(
        self,
        *,
        capture_source=None,
        build_transcriber: Callable[[], SpeechTranscriber] | None = None,
        max_frames: int | None = None,
        device_name: str | None = None,
    ) -> dict[str, object]:
        with self._click_to_talk_lock:
            if self._click_to_talk_active:
                raise ValueError("click-to-talk session is already active")
            self._click_to_talk_active = True

        try:
            self._clear_click_to_talk_history()
            source = (
                capture_source
                if capture_source is not None
                else build_default_audio_capture_source(device_name=device_name)
            )
            transcriber_builder = (
                build_default_speech_transcriber if build_transcriber is None else build_transcriber
            )
            result = run_manual_voice_session(
                self.daemon,
                source,
                transcriber_builder,
                max_frames=self.click_to_talk_frame_limit if max_frames is None else max_frames,
            )
            self._remember_click_to_talk_result(result)
            return result
        except Exception as exc:
            self._remember_click_to_talk_error(_format_click_to_talk_error(exc))
            raise
        finally:
            with self._click_to_talk_lock:
                self._click_to_talk_active = False

    def _remember_click_to_talk_result(self, result: dict[str, object]) -> None:
        self._last_click_to_talk_error = None
        self._last_click_to_talk_result = result
        response = result.get("response")
        if not isinstance(response, dict):
            self._clear_click_to_talk_history()
            return
        if response.get("status") != "no_transcript":
            self._clear_click_to_talk_preview_fallback()
            return

        transcripts = result.get("transcripts")
        last_transcript = None
        if isinstance(transcripts, list) and transcripts:
            last_item = transcripts[-1]
            if isinstance(last_item, dict):
                transcript_text = last_item.get("text")
                if isinstance(transcript_text, str) and transcript_text:
                    last_transcript = transcript_text

        response_text = response.get("text")
        self._last_click_to_talk_transcript = last_transcript
        self._last_click_to_talk_response = (
            response_text if isinstance(response_text, str) and response_text else None
        )

    def _remember_click_to_talk_error(self, message: str) -> None:
        self._last_click_to_talk_result = None
        self._last_click_to_talk_error = message
        self._last_click_to_talk_transcript = None
        self._last_click_to_talk_response = message

    def _clear_click_to_talk_preview_fallback(self) -> None:
        self._last_click_to_talk_transcript = None
        self._last_click_to_talk_response = None

    def _clear_click_to_talk_history(self) -> None:
        self._clear_click_to_talk_preview_fallback()
        self._last_click_to_talk_result = None
        self._last_click_to_talk_error = None


def build_tray_snapshot(
    status: StatusSnapshot,
    *,
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None = None,
    click_to_talk_active: bool = False,
    developer_mode: bool = False,
    fallback_last_transcript: str | None = None,
    fallback_last_response: str | None = None,
    last_click_to_talk_result: dict[str, object] | None = None,
    last_click_to_talk_error: str | None = None,
) -> TraySnapshot:
    tray_state, state_label = _resolve_tray_state(
        status,
        click_to_talk_active=click_to_talk_active,
    )
    mic_state = _resolve_mic_state(
        status.current_state,
        click_to_talk_active=click_to_talk_active,
    )
    click_to_talk_label, can_start_click_to_talk = _resolve_click_to_talk_action(
        status,
        click_to_talk_active=click_to_talk_active,
    )
    voice_loop_activity = _resolve_voice_loop_activity(voice_loop_status)
    voice_loop_last_response = None if voice_loop_status is None else voice_loop_status.last_response_text
    if fallback_last_transcript is not None or fallback_last_response is not None:
        last_command_transcript = fallback_last_transcript
        last_command_preview = fallback_last_response
    else:
        last_command_transcript = status.last_transcript
        last_command_preview = status.last_response
    pending_confirmation_prompt = status.pending_plan_preview if status.pending_confirmation else None
    confirmation_dialog = _build_confirmation_dialog(status)
    notification = _build_notification(status, voice_loop_status=voice_loop_status)
    last_interaction = _build_last_interaction_report(
        status,
        last_click_to_talk_result=last_click_to_talk_result,
        last_click_to_talk_error=last_click_to_talk_error,
    )
    usage_hint = _resolve_tray_usage_hint(
        status,
        can_start_click_to_talk=can_start_click_to_talk,
        last_command_transcript=last_command_transcript,
        last_command_preview=last_command_preview,
        voice_loop_status=voice_loop_status,
    )
    display_state_label = f"{state_label} (simulated)" if developer_mode else state_label
    tooltip_parts = [f"Operance: {display_state_label}"]
    if developer_mode:
        tooltip_parts.append("Developer mode uses simulated adapters")
    if usage_hint:
        tooltip_parts.append(usage_hint)
    elif voice_loop_activity:
        tooltip_parts.append(voice_loop_activity)
    if pending_confirmation_prompt:
        tooltip_parts.append(pending_confirmation_prompt)
    elif last_command_transcript:
        tooltip_parts.append(f"Heard: {last_command_transcript}")
        if last_command_preview and last_command_preview != last_command_transcript:
            tooltip_parts.append(last_command_preview)
    elif last_command_preview:
        tooltip_parts.append(last_command_preview)

    return TraySnapshot(
        current_state=status.current_state.value,
        tray_state=tray_state,
        mic_state=mic_state,
        state_label=display_state_label,
        developer_mode=developer_mode,
        click_to_talk_label=click_to_talk_label,
        voice_loop_status=None if voice_loop_status is None else voice_loop_status.status,
        voice_loop_state=None if voice_loop_status is None else voice_loop_status.loop_state,
        voice_loop_heartbeat_fresh=(
            None if voice_loop_status is None else voice_loop_status.heartbeat_fresh
        ),
        voice_loop_message=None if voice_loop_status is None else voice_loop_status.message,
        voice_loop_activity=voice_loop_activity,
        voice_loop_last_transcript=(
            None if voice_loop_status is None else voice_loop_status.last_transcript_text
        ),
        voice_loop_last_response=voice_loop_last_response,
        last_command_transcript=last_command_transcript,
        last_command_preview=last_command_preview,
        last_interaction=last_interaction,
        pending_confirmation_prompt=pending_confirmation_prompt,
        confirmation_dialog=confirmation_dialog,
        notification=notification,
        can_start_click_to_talk=can_start_click_to_talk,
        can_confirm=status.pending_confirmation,
        can_cancel=status.pending_confirmation,
        can_undo=status.undo_available,
        can_reset_planner=(
            status.planner_consecutive_failures > 0 or status.last_planner_error is not None
        ),
        can_restart_voice_loop_service=_can_restart_voice_loop_service(voice_loop_status),
        undo_label=status.last_undo_tool,
        tooltip=" | ".join(tooltip_parts),
    )


def select_tray_notification(
    previous_snapshot: TraySnapshot | None,
    current_snapshot: TraySnapshot,
) -> TrayNotification | None:
    notification = current_snapshot.notification
    if notification is None:
        return None

    if previous_snapshot is not None and previous_snapshot.notification is not None:
        if previous_snapshot.notification.event_id == notification.event_id:
            return None

    return notification


def build_startup_notification(snapshot: TraySnapshot) -> TrayNotification | None:
    if snapshot.notification is not None:
        return None
    if snapshot.tray_state != "idle" or not snapshot.can_start_click_to_talk:
        return None
    if snapshot.pending_confirmation_prompt is not None:
        return None
    if snapshot.last_command_transcript is not None or snapshot.last_command_preview is not None:
        return None
    return TrayNotification(
        level="info",
        title="Operance is ready",
        message="Left-click the tray icon to talk. Right-click for supported commands.",
        event_id="startup:click_to_talk",
    )


def build_click_to_talk_started_notification() -> TrayNotification:
    return TrayNotification(
        level="info",
        title="Listening",
        message="Speak a command now. Operance will stop listening automatically.",
        event_id="click_to_talk:started",
    )


def build_installed_readiness_report(
    result: InstalledSmokeResult,
) -> TrayInstalledReadinessReport:
    if result.status == "ok":
        summary = "Installed package is ready for tray click-to-talk."
    elif result.status == "warn":
        summary = "Installed package is usable, but one or more checks need attention."
    else:
        summary = "Installed package is not ready for the supported tray path."

    details: list[str] = []
    attention_checks = [check for check in result.checks if check.status != "ok"]
    if attention_checks:
        details.append("Checks needing attention:")
        details.extend(_format_installed_readiness_check(check) for check in attention_checks)
    elif result.status == "ok":
        details.append("All installed package checks passed.")
    else:
        details.append("No individual check failures were reported.")

    if result.next_steps:
        details.append("Next steps:")
        details.extend(f"- {step}" for step in result.next_steps)

    if result.manual_checks:
        details.append("Manual click-to-talk checks:")
        details.extend(f"- {check}" for check in result.manual_checks)

    return TrayInstalledReadinessReport(
        status=result.status,
        title="Installed package readiness",
        summary=summary,
        details=details,
    )


def build_installed_readiness_notification(
    report: TrayInstalledReadinessReport,
) -> TrayNotification | None:
    if report.status == "ok":
        return None
    return TrayNotification(
        level="warning" if report.status == "warn" else "error",
        title="Installed package needs attention",
        message=report.summary,
        event_id=f"installed_readiness:{report.status}:{report.summary}",
    )


def _format_installed_readiness_check(check: InstalledSmokeCheck) -> str:
    detail = check.detail
    if isinstance(detail, dict):
        detail_text = ", ".join(f"{key}={value}" for key, value in detail.items())
    else:
        detail_text = str(detail)
    if check.suggested_command:
        return f"- {check.status}: {check.name}: {detail_text}; next: {check.suggested_command}"
    return f"- {check.status}: {check.name}: {detail_text}"


def run_tray_app(env: Mapping[str, str] | None = None) -> int:
    QApplication, QAction, QIcon, QMenu, QMessageBox, QStyle, QSystemTrayIcon, QTimer = _load_pyside6_api()

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    if not QSystemTrayIcon.isSystemTrayAvailable():
        raise ValueError("system tray is not available")

    daemon = OperanceDaemon.build_default(env)
    daemon.start()
    try:
        tray_lock = _acquire_tray_instance_lock(daemon.config.paths.data_dir / "tray.lock")
    except ValueError:
        daemon.stop()
        raise
    controller = TrayController(daemon, env=env, include_voice_loop_status=True)

    tray = QSystemTrayIcon()
    menu = QMenu()
    state_action = QAction("", menu)
    state_action.setEnabled(False)
    click_to_talk_action = QAction("Click to talk", menu)
    supported_commands_action = QAction("Show supported commands", menu)
    installed_readiness_action = QAction("Show installed readiness", menu)
    support_snapshot_action = QAction("Show support snapshot", menu)
    save_support_snapshot_action = QAction("Save support snapshot", menu)
    save_support_bundle_action = QAction("Save support bundle", menu)
    last_interaction_action = QAction("Show last interaction", menu)
    voice_loop_action = QAction("", menu)
    voice_loop_action.setEnabled(False)
    transcript_action = QAction("", menu)
    transcript_action.setEnabled(False)
    preview_action = QAction("", menu)
    preview_action.setEnabled(False)
    pending_action = QAction("", menu)
    pending_action.setEnabled(False)
    confirm_action = QAction("Confirm pending command", menu)
    cancel_action = QAction("Cancel pending command", menu)
    undo_action = QAction("Undo last action", menu)
    restart_voice_loop_action = QAction("Restart voice-loop service", menu)
    reset_planner_action = QAction("Reset planner runtime", menu)
    quit_action = QAction("Quit Operance", menu)

    menu.addAction(state_action)
    menu.addAction(click_to_talk_action)
    menu.addAction(supported_commands_action)
    menu.addAction(installed_readiness_action)
    menu.addAction(support_snapshot_action)
    menu.addAction(save_support_snapshot_action)
    menu.addAction(save_support_bundle_action)
    menu.addAction(last_interaction_action)
    menu.addAction(voice_loop_action)
    menu.addAction(transcript_action)
    menu.addAction(preview_action)
    menu.addAction(pending_action)
    menu.addSeparator()
    menu.addAction(confirm_action)
    menu.addAction(cancel_action)
    menu.addAction(undo_action)
    menu.addAction(restart_voice_loop_action)
    menu.addAction(reset_planner_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    last_snapshot: TraySnapshot | None = None
    click_to_talk_results: SimpleQueue[tuple[str, object]] = SimpleQueue()

    def refresh() -> TraySnapshot:
        nonlocal last_snapshot
        snapshot = controller.snapshot()
        state_action.setText(f"State: {snapshot.state_label}")
        click_to_talk_action.setText(snapshot.click_to_talk_label)
        click_to_talk_action.setEnabled(snapshot.can_start_click_to_talk)
        last_interaction_action.setEnabled(snapshot.last_interaction is not None)
        voice_loop_action.setText(
            f"Voice loop: {snapshot.voice_loop_activity or snapshot.voice_loop_message or 'No runtime status'}"
        )
        transcript_action.setText(
            f"Heard: {snapshot.last_command_transcript or 'No recent transcript'}"
        )
        preview_action.setText(
            f"Last: {snapshot.last_command_preview or 'No recent response'}"
        )
        pending_action.setText(
            f"Pending: {snapshot.pending_confirmation_prompt or 'No pending confirmation'}"
        )
        confirm_action.setEnabled(snapshot.can_confirm)
        cancel_action.setEnabled(snapshot.can_cancel)
        undo_action.setEnabled(snapshot.can_undo)
        restart_voice_loop_action.setEnabled(snapshot.can_restart_voice_loop_service)
        reset_planner_action.setEnabled(snapshot.can_reset_planner)
        undo_action.setText(
            "Undo last action" if snapshot.undo_label is None else f"Undo {snapshot.undo_label}"
        )
        tray.setToolTip(snapshot.tooltip)
        tray.setIcon(_build_tray_icon(app, QStyle, snapshot.tray_state, QIcon))
        notification = select_tray_notification(last_snapshot, snapshot)
        if notification is not None:
            tray.showMessage(
                notification.title,
                notification.message,
                _resolve_notification_icon(QSystemTrayIcon, notification.level),
            )
        _drain_click_to_talk_results(
            tray,
            QSystemTrayIcon,
            snapshot,
            click_to_talk_results,
        )
        last_snapshot = snapshot
        return snapshot

    def run_action(action) -> None:
        snapshot = action()
        refresh()
        message = snapshot.last_command_preview
        if message and snapshot.notification is None:
            tray.showMessage("Operance", message)

    def confirm_pending() -> None:
        snapshot = controller.snapshot()
        dialog = snapshot.confirmation_dialog
        if dialog is None:
            run_action(controller.confirm_pending)
            return
        choice = _show_confirmation_dialog(QMessageBox, dialog)
        if choice == "confirm":
            run_action(controller.confirm_pending)
        elif choice == "cancel":
            run_action(controller.cancel_pending)

    def restart_voice_loop_service() -> None:
        try:
            result = controller.restart_voice_loop_service()
        except ValueError as exc:
            refresh()
            tray.showMessage(
                "Voice loop needs attention",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "warning"),
            )
            return
        refresh()
        tray.showMessage(
            "Operance" if result.status == "success" else "Voice loop restart failed",
            _setup_result_message(result),
            _resolve_notification_icon(
                QSystemTrayIcon,
                "info" if result.status == "success" else "error",
            ),
        )

    def click_to_talk_worker() -> None:
        try:
            result = controller.start_click_to_talk()
        except Exception as exc:
            click_to_talk_results.put(("error", _format_click_to_talk_error(exc)))
            return
        click_to_talk_results.put(("result", result))

    def start_click_to_talk() -> None:
        click_to_talk_action.setEnabled(False)
        click_to_talk_action.setText("Listening...")
        Thread(target=click_to_talk_worker, daemon=True).start()
        refresh()
        notification = build_click_to_talk_started_notification()
        tray.showMessage(
            notification.title,
            notification.message,
            _resolve_notification_icon(QSystemTrayIcon, notification.level),
        )

    def show_supported_commands() -> None:
        try:
            help_text = build_supported_command_help_text(build_supported_command_catalog())
        except Exception as exc:
            tray.showMessage(
                "Supported commands unavailable",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "warning"),
            )
            return
        examples = help_text.get("examples")
        details = help_text.get("details")
        _show_information_dialog(
            QMessageBox,
            title=str(help_text["title"]),
            summary=str(help_text["summary"]),
            informative_text=(
                "Try: " + "; ".join(str(example) for example in examples)
                if isinstance(examples, list) and examples
                else None
            ),
            details=details if isinstance(details, str) and details else None,
        )

    def show_installed_readiness() -> None:
        try:
            report = controller.installed_readiness_report()
        except Exception as exc:
            tray.showMessage(
                "Installed readiness unavailable",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "warning"),
            )
            return
        _show_information_dialog(
            QMessageBox,
            title=report.title,
            summary=report.summary,
            informative_text=f"Status: {report.status}",
            details="\n".join(report.details) if report.details else None,
        )

    def show_support_snapshot() -> None:
        try:
            help_text = build_support_snapshot_help_text(
                build_support_snapshot(
                    env=dict(env or {}),
                    redact=True,
                )
            )
        except Exception as exc:
            tray.showMessage(
                "Support snapshot unavailable",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "warning"),
            )
            return
        highlights = help_text.get("highlights")
        details = help_text.get("details")
        _show_information_dialog(
            QMessageBox,
            title=str(help_text["title"]),
            summary=str(help_text["summary"]),
            informative_text=(
                "\n".join(str(item) for item in highlights)
                if isinstance(highlights, list) and highlights
                else None
            ),
            details=details if isinstance(details, str) and details else None,
        )

    def save_support_snapshot() -> None:
        try:
            artifact_path = _save_support_snapshot_artifact(
                data_dir=daemon.config.paths.data_dir,
                env=env,
            )
        except Exception as exc:
            tray.showMessage(
                "Support snapshot save failed",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "error"),
            )
            return
        tray.showMessage(
            "Support snapshot saved",
            str(artifact_path),
            _resolve_notification_icon(QSystemTrayIcon, "info"),
        )

    def save_support_bundle() -> None:
        try:
            artifact_path = _save_support_bundle_artifact(
                data_dir=daemon.config.paths.data_dir,
                env=env,
            )
        except Exception as exc:
            tray.showMessage(
                "Support bundle save failed",
                str(exc),
                _resolve_notification_icon(QSystemTrayIcon, "error"),
            )
            return
        tray.showMessage(
            "Support bundle saved",
            str(artifact_path),
            _resolve_notification_icon(QSystemTrayIcon, "info"),
        )

    def show_last_interaction() -> None:
        report = controller.snapshot().last_interaction
        if report is None:
            tray.showMessage(
                "No recent interaction",
                "Use click-to-talk or a tray action first.",
                _resolve_notification_icon(QSystemTrayIcon, "info"),
            )
            return
        _show_information_dialog(
            QMessageBox,
            title=report.title,
            summary=report.summary,
            informative_text="\n".join(report.details) if report.details else None,
        )

    def quit_tray() -> None:
        timer.stop()
        tray.hide()
        daemon.stop()
        app.quit()

    def on_tray_activated(reason) -> None:
        if _should_start_click_to_talk_from_activation(reason, QSystemTrayIcon):
            start_click_to_talk()

    tray.activated.connect(on_tray_activated)
    click_to_talk_action.triggered.connect(start_click_to_talk)
    supported_commands_action.triggered.connect(show_supported_commands)
    installed_readiness_action.triggered.connect(show_installed_readiness)
    support_snapshot_action.triggered.connect(show_support_snapshot)
    save_support_snapshot_action.triggered.connect(save_support_snapshot)
    save_support_bundle_action.triggered.connect(save_support_bundle)
    last_interaction_action.triggered.connect(show_last_interaction)
    confirm_action.triggered.connect(confirm_pending)
    cancel_action.triggered.connect(lambda: run_action(controller.cancel_pending))
    undo_action.triggered.connect(lambda: run_action(controller.undo_last_action))
    restart_voice_loop_action.triggered.connect(restart_voice_loop_service)
    reset_planner_action.triggered.connect(lambda: run_action(controller.reset_planner_runtime))
    quit_action.triggered.connect(quit_tray)

    timer = QTimer()
    timer.timeout.connect(refresh)
    timer.start(500)

    initial_snapshot = refresh()
    tray.show()
    startup_notification = build_startup_notification(initial_snapshot)
    if startup_notification is not None:
        tray.showMessage(
            startup_notification.title,
            startup_notification.message,
            _resolve_notification_icon(QSystemTrayIcon, startup_notification.level),
        )
    if not daemon.config.runtime.developer_mode:
        try:
            installed_notification = build_installed_readiness_notification(
                controller.installed_readiness_report()
            )
        except Exception:
            installed_notification = None
        if installed_notification is not None:
            tray.showMessage(
                installed_notification.title,
                installed_notification.message,
                _resolve_notification_icon(QSystemTrayIcon, installed_notification.level),
            )

    try:
        app.exec()
    finally:
        if timer.isActive():
            timer.stop()
        tray.hide()
        _release_tray_instance_lock(tray_lock)
        daemon.stop()

    return 0


def _build_confirmation_dialog(status: StatusSnapshot) -> TrayConfirmationDialog | None:
    if not status.pending_confirmation or status.pending_plan_preview is None:
        return None

    details: list[str] = []
    if status.pending_original_text:
        details.append(f"Original command: {status.pending_original_text}")
    if status.pending_source:
        details.append(f"Source: {status.pending_source}")
    if status.pending_risk_tier is not None:
        details.append(f"Risk tier: {status.pending_risk_tier}")
    if status.pending_affected_resources:
        details.append(f"Affected: {', '.join(status.pending_affected_resources)}")
    if status.pending_rollback_hint:
        details.append(f"Rollback: {status.pending_rollback_hint}")
    if status.pending_timeout_behavior:
        details.append(f"Timeout: {status.pending_timeout_behavior}")

    return TrayConfirmationDialog(
        title="Confirm pending command",
        message=status.pending_plan_preview,
        details=details,
        confirm_label="Confirm",
        cancel_label="Cancel",
    )


def _build_last_interaction_report(
    status: StatusSnapshot,
    *,
    last_click_to_talk_result: dict[str, object] | None,
    last_click_to_talk_error: str | None,
) -> TrayInteractionReport | None:
    if last_click_to_talk_error:
        return TrayInteractionReport(
            title="Last click-to-talk error",
            summary=last_click_to_talk_error,
            details=["Source: click-to-talk"],
        )

    report = _build_click_to_talk_interaction_report(last_click_to_talk_result)
    if report is not None:
        return report

    if status.last_response is None and status.last_transcript is None:
        return None

    details: list[str] = []
    if status.last_transcript:
        details.append(f"Heard: {status.last_transcript}")
    if status.last_command_status:
        details.append(f"Status: {status.last_command_status}")

    summary = status.last_response if status.last_response is not None else status.last_transcript
    if summary is None:
        return None
    return TrayInteractionReport(
        title="Last interaction",
        summary=summary,
        details=details,
    )


def _build_click_to_talk_interaction_report(
    result: dict[str, object] | None,
) -> TrayInteractionReport | None:
    if result is None:
        return None

    response = result.get("response")
    if not isinstance(response, dict):
        return None

    summary = response.get("text")
    if not isinstance(summary, str) or not summary:
        return None

    details: list[str] = []
    transcript = _resolve_last_click_to_talk_transcript(result)
    if transcript is None:
        details.append("Heard: No final transcript")
    else:
        details.append(f"Heard: {transcript}")

    result_status = response.get("status")
    if isinstance(result_status, str) and result_status:
        details.append(f"Result: {result_status}")

    if response.get("simulated") is True:
        details.append("Mode: simulated")

    processed_frames = result.get("processed_frames")
    if isinstance(processed_frames, int) and processed_frames >= 0:
        details.append(f"Processed frames: {processed_frames}")

    stopped_reason = result.get("stopped_reason")
    if isinstance(stopped_reason, str) and stopped_reason:
        details.append(f"Stopped: {stopped_reason}")

    final_state = result.get("final_state")
    if isinstance(final_state, str) and final_state:
        details.append(f"Final state: {final_state}")

    return TrayInteractionReport(
        title="Last click-to-talk interaction",
        summary=summary,
        details=details,
    )


def _resolve_last_click_to_talk_transcript(result: dict[str, object]) -> str | None:
    transcripts = result.get("transcripts")
    if not isinstance(transcripts, list):
        return None

    for item in reversed(transcripts):
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text:
            return text
    return None


def _build_notification(
    status: StatusSnapshot,
    *,
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None = None,
) -> TrayNotification | None:
    if status.current_state == RuntimeState.ERROR:
        message = status.last_response or "Runtime entered the error state."
        return TrayNotification(
            level="error",
            title="Runtime error",
            message=message,
            event_id=f"runtime_error:{message}",
        )

    if status.last_response is not None and status.last_command_status is not None:
        if status.last_command_status == "failed":
            return TrayNotification(
                level="error",
                title="Command failed",
                message=status.last_response,
                event_id=f"failed:{status.last_response}",
            )
        if status.last_command_status == "denied":
            return TrayNotification(
                level="error",
                title="Command denied",
                message=status.last_response,
                event_id=f"denied:{status.last_response}",
            )
        if status.last_command_status == "unmatched":
            if status.last_routing_reason == "planner_failed" and status.last_planner_error:
                return TrayNotification(
                    level="warning",
                    title="Planner fallback failed",
                    message=status.last_planner_error,
                    event_id=f"planner_failed:{status.last_planner_error}",
                )
            return TrayNotification(
                level="warning",
                title="Command not understood",
                message=status.last_response,
                event_id=f"unmatched:{status.last_response}",
            )

    if _voice_loop_needs_attention(voice_loop_status):
        return TrayNotification(
            level="warning",
            title="Voice loop needs attention",
            message=str(voice_loop_status.message),
            event_id=f"voice_loop:{voice_loop_status.loop_state}:{voice_loop_status.message}",
        )

    return None


def _resolve_tray_state(
    status: StatusSnapshot,
    *,
    click_to_talk_active: bool = False,
) -> tuple[str, str]:
    if click_to_talk_active and status.current_state == RuntimeState.IDLE:
        return ("listening", "Listening")
    if status.pending_confirmation or status.current_state == RuntimeState.AWAITING_CONFIRMATION:
        return ("attention", "Confirmation needed")
    if status.current_state == RuntimeState.WAKE_DETECTED:
        return ("listening", "Wake word detected")
    if status.current_state == RuntimeState.LISTENING:
        return ("listening", "Listening")
    if status.current_state == RuntimeState.TRANSCRIBING:
        return ("listening", "Transcribing")
    if status.current_state == RuntimeState.UNDERSTANDING:
        return ("busy", "Understanding")
    if status.current_state == RuntimeState.EXECUTING:
        return ("busy", "Executing")
    if status.current_state == RuntimeState.RESPONDING:
        return ("busy", "Responding")
    if status.current_state == RuntimeState.COOLDOWN:
        return ("busy", "Cooldown")
    if status.current_state == RuntimeState.ERROR:
        return ("error", "Error")
    return ("idle", "Idle")


def _resolve_click_to_talk_action(
    status: StatusSnapshot,
    *,
    click_to_talk_active: bool,
) -> tuple[str, bool]:
    if click_to_talk_active:
        return ("Listening...", False)
    if status.current_state in {
        RuntimeState.WAKE_DETECTED,
        RuntimeState.LISTENING,
        RuntimeState.TRANSCRIBING,
        RuntimeState.UNDERSTANDING,
        RuntimeState.EXECUTING,
        RuntimeState.RESPONDING,
        RuntimeState.COOLDOWN,
    }:
        if status.current_state in {RuntimeState.WAKE_DETECTED, RuntimeState.LISTENING}:
            return ("Listening...", False)
        if status.current_state == RuntimeState.TRANSCRIBING:
            return ("Transcribing...", False)
        return ("Processing...", False)
    if status.pending_confirmation or status.current_state == RuntimeState.AWAITING_CONFIRMATION:
        return ("Reply to pending command", True)
    return ("Click to talk", True)


def _resolve_mic_state(state: RuntimeState, *, click_to_talk_active: bool = False) -> str:
    if click_to_talk_active:
        return "listening"
    if state == RuntimeState.WAKE_DETECTED:
        return "wake_detected"
    if state in {RuntimeState.LISTENING, RuntimeState.TRANSCRIBING}:
        return "listening"
    return "inactive"


def _resolve_voice_loop_activity(
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None,
) -> str | None:
    if voice_loop_status is None:
        return None
    if voice_loop_status.loop_state == "waiting_for_wake":
        return "Waiting for wake word"
    if voice_loop_status.loop_state == "listening_for_command":
        return "Listening for command"
    if voice_loop_status.loop_state == "awaiting_confirmation":
        return "Awaiting confirmation"
    if voice_loop_status.loop_state == "responding":
        return "Responding"
    if voice_loop_status.loop_state == "starting":
        return "Starting"
    if voice_loop_status.loop_state == "stopped":
        return "Stopped"
    if voice_loop_status.loop_state == "missing":
        return "Runtime status missing"
    if voice_loop_status.loop_state == "invalid":
        return "Runtime status invalid"
    return voice_loop_status.loop_state.replace("_", " ").capitalize()


def _resolve_tray_usage_hint(
    status: StatusSnapshot,
    *,
    can_start_click_to_talk: bool,
    last_command_transcript: str | None,
    last_command_preview: str | None,
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None,
) -> str | None:
    if not can_start_click_to_talk or status.current_state != RuntimeState.IDLE:
        return None
    if status.pending_confirmation:
        return None
    if last_command_transcript is not None or last_command_preview is not None:
        return None
    if voice_loop_status is not None and _voice_loop_needs_attention(voice_loop_status):
        return None
    return "Left-click to talk"


def _can_restart_voice_loop_service(
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None,
) -> bool:
    if voice_loop_status is None or voice_loop_status.loop_state == "missing":
        return False
    return not voice_loop_status.heartbeat_fresh


def _voice_loop_needs_attention(
    voice_loop_status: VoiceLoopRuntimeStatusSnapshot | None,
) -> bool:
    if voice_loop_status is None:
        return False
    if voice_loop_status.loop_state == "missing":
        return False
    return voice_loop_status.status == "warn" and bool(voice_loop_status.message)


def _setup_result_message(result: SetupRunResult) -> str:
    if result.status == "success":
        return "Restarted voice-loop user service."
    stderr = (result.stderr or "").strip()
    if stderr:
        return stderr
    stdout = (result.stdout or "").strip()
    if stdout:
        return stdout
    return f"{result.label} failed."


def _drain_click_to_talk_results(
    tray,
    qsystemtrayicon,
    snapshot: TraySnapshot,
    result_queue: SimpleQueue[tuple[str, object]],
) -> None:
    while True:
        try:
            kind, payload = result_queue.get_nowait()
        except Empty:
            return

        if kind == "error":
            tray.showMessage(
                "Click-to-talk failed",
                str(payload),
                _resolve_notification_icon(qsystemtrayicon, "error"),
            )
            continue

        if not isinstance(payload, dict):
            continue
        report = _build_click_to_talk_interaction_report(payload)
        if report is None:
            continue
        response = payload.get("response")
        if not isinstance(response, dict):
            continue
        status = response.get("status")
        if snapshot.notification is None or status == "no_transcript":
            tray.showMessage(
                "Operance",
                _format_click_to_talk_notification_message(report),
                _resolve_notification_icon(qsystemtrayicon, _result_level(str(status))),
            )


def _result_level(status: str) -> str:
    if status in {"failed", "denied"}:
        return "error"
    if status in {"unmatched", "no_transcript"}:
        return "warning"
    return "info"


def _format_click_to_talk_notification_message(report: TrayInteractionReport) -> str:
    heard_line = next(
        (
            detail
            for detail in report.details
            if detail.startswith("Heard: ") and detail != "Heard: No final transcript"
        ),
        None,
    )
    if heard_line is None:
        return report.summary

    heard_text = heard_line.removeprefix("Heard: ").strip()
    summary = report.summary
    if "Mode: simulated" in report.details:
        summary = f"Simulated: {summary}"
    if not heard_text or heard_text == report.summary:
        return summary
    return f"{heard_line}\n{summary}"


def _should_start_click_to_talk_from_activation(reason: object, qsystemtrayicon: Any) -> bool:
    activation_reason = getattr(qsystemtrayicon, "ActivationReason", None)
    if activation_reason is None:
        return False
    return reason in {
        getattr(activation_reason, "Trigger", None),
        getattr(activation_reason, "DoubleClick", None),
    }


def _format_click_to_talk_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def _acquire_tray_instance_lock(lock_path: Path) -> TextIO:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise ValueError("Operance tray is already running. Use the existing tray icon.") from exc
    return handle


def _release_tray_instance_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _build_tray_icon(app: Any, qstyle: Any, tray_state: str, qicon: Any | None = None):
    if qicon is not None:
        icon = qicon.fromTheme("operance")
        if not icon.isNull():
            return icon

        for icon_path in _operance_icon_candidates():
            if icon_path.exists():
                icon = qicon(str(icon_path))
                if not icon.isNull():
                    return icon

    style = app.style()
    if tray_state == "attention":
        return style.standardIcon(qstyle.StandardPixmap.SP_MessageBoxWarning)
    if tray_state == "error":
        return style.standardIcon(qstyle.StandardPixmap.SP_MessageBoxCritical)
    if tray_state in {"busy", "listening"}:
        return style.standardIcon(qstyle.StandardPixmap.SP_BrowserReload)
    return style.standardIcon(qstyle.StandardPixmap.SP_ComputerIcon)


def _operance_icon_candidates() -> tuple[Path, ...]:
    return (
        Path("/usr/share/icons/hicolor/scalable/apps/operance.svg"),
        Path(__file__).resolve().parents[3] / "assets" / "icons" / "operance.svg",
    )


def _resolve_notification_icon(qsystemtrayicon: Any, level: str):
    if level == "error":
        return qsystemtrayicon.MessageIcon.Critical
    if level == "warning":
        return qsystemtrayicon.MessageIcon.Warning
    return qsystemtrayicon.MessageIcon.Information


def _show_confirmation_dialog(qmessagebox: Any, dialog: TrayConfirmationDialog) -> str | None:
    box = qmessagebox()
    box.setWindowTitle(dialog.title)
    box.setText(dialog.message)
    if dialog.details:
        box.setInformativeText("\n".join(dialog.details))
    box.setIcon(qmessagebox.Icon.Warning)
    confirm_button = box.addButton(dialog.confirm_label, qmessagebox.ButtonRole.AcceptRole)
    cancel_button = box.addButton(dialog.cancel_label, qmessagebox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() == confirm_button:
        return "confirm"
    if box.clickedButton() == cancel_button:
        return "cancel"
    return None


def _show_information_dialog(
    qmessagebox: Any,
    *,
    title: str,
    summary: str,
    informative_text: str | None = None,
    details: str | None = None,
) -> None:
    dialog = qmessagebox()
    information_icon = getattr(getattr(qmessagebox, "Icon", None), "Information", None)
    if information_icon is None:
        information_icon = getattr(qmessagebox, "Information")
    dialog.setIcon(information_icon)
    dialog.setWindowTitle(title)
    dialog.setText(summary)
    if informative_text:
        dialog.setInformativeText(informative_text)
    if details:
        dialog.setDetailedText(details)
    dialog.exec()


def _save_support_snapshot_artifact(
    *,
    data_dir: Path,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> Path:
    timestamp = now if now is not None else datetime.now(timezone.utc)
    output_dir = data_dir / "support-snapshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"support-snapshot-{project_version()}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    snapshot = build_support_snapshot(env=dict(env or {}), redact=True)
    output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _save_support_bundle_artifact(
    *,
    data_dir: Path,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> Path:
    timestamp = now if now is not None else datetime.now(timezone.utc)
    output_dir = data_dir / "support-bundles"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"support-bundle-{project_version()}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.tar.gz"
    write_support_bundle_artifact(
        output_path=output_path,
        env=dict(env or {}),
        redact=True,
        now=timestamp,
    )
    return output_path


def _load_pyside6_api() -> tuple[type[Any], type[Any], type[Any], type[Any], type[Any], type[Any], type[Any], type[Any]]:
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QAction, QIcon
        from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon
    except ImportError as exc:
        raise ValueError("PySide6 is not installed") from exc

    return QApplication, QAction, QIcon, QMenu, QMessageBox, QStyle, QSystemTrayIcon, QTimer
