"""Bounded and continuous live voice-session helpers for captured audio frames."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
import re

from ..audio.capture import AudioCaptureSource
from ..audio.playback import AudioPlaybackSink
from ..daemon import OperanceDaemon
from ..models.events import ResponseEvent, RuntimeState
from ..spoken_response import build_spoken_response_text
from ..stt import SpeechTranscriber
from ..tts import SpeechSynthesizer
from ..wakeword import WakeWordDetector
from .runtime import VoiceLoopRuntimeStatusWriter

DEFAULT_CLICK_TO_TALK_MAX_FRAMES = 40
DEFAULT_ALWAYS_ON_COMMAND_TIMEOUT_FRAMES = 120
_NO_COMMAND_AFTER_WAKE_RESPONSE = "I heard Operance, but no command followed."

_LIVE_COMMAND_START_RE = re.compile(
    r"\b(?:please\s+)?(?:"
    r"open|launch|start|focus|switch|show|search|what|time|battery|wifi|"
    r"volume|mute|unmute|is|set|quit|close|create|rename|move|delete|"
    r"copy|clear|paste"
    r")\b",
    re.IGNORECASE,
)
_MAX_LEADING_WAKE_RESIDUE_CHARS = 32
_WAKE_ONLY_TRANSCRIPTS = {
    "aprons",
    "appearance",
    "operance",
    "operant",
    "operants",
    "operand",
    "operands",
    "prince",
    "properance",
    "province",
}


def run_live_voice_session(
    capture_source: AudioCaptureSource,
    wakeword_detector: WakeWordDetector,
    build_transcriber: Callable[[], SpeechTranscriber],
    *,
    max_frames: int,
    env: Mapping[str, str] | None = None,
    response_synthesizer: SpeechSynthesizer | None = None,
    response_output_dir: Path | None = None,
    response_playback_sink: AudioPlaybackSink | None = None,
) -> dict[str, object]:
    return _run_voice_capture_loop(
        capture_source,
        wakeword_detector,
        build_transcriber,
        max_frames=max_frames,
        env=env,
        response_synthesizer=response_synthesizer,
        response_output_dir=response_output_dir,
        response_playback_sink=response_playback_sink,
    )


def run_manual_voice_session(
    daemon: OperanceDaemon,
    capture_source: AudioCaptureSource,
    build_transcriber: Callable[[], SpeechTranscriber],
    *,
    max_frames: int,
) -> dict[str, object]:
    started_daemon = False
    entered_manual_listening = False
    transcripts: list[dict[str, object]] = []
    processed_frames = 0
    stopped_reason = "capture_ended"
    response: dict[str, object] | None = None
    transcriber: SpeechTranscriber | None = None

    if not daemon.running:
        daemon.start()
        started_daemon = True

    try:
        if daemon.state_machine.current_state != RuntimeState.AWAITING_CONFIRMATION:
            daemon.begin_manual_listening(source="click_to_talk")
            entered_manual_listening = True

        transcriber = build_transcriber()
        try:
            for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
                processed_frames = frame_index
                segment = transcriber.process_frame(frame)
                if segment is None:
                    continue
                _append_transcript_segment(segment, frame_index, transcripts)
                if not segment.is_final:
                    continue
                daemon.emit_transcript(
                    segment.text,
                    confidence=segment.confidence,
                    is_final=True,
                )
                _complete_voice_response_cycle(daemon)
                response = _manual_response_payload(daemon)
                stopped_reason = "final_transcript"
                break
            else:
                if processed_frames >= max_frames:
                    stopped_reason = "frame_limit"
        except KeyboardInterrupt:
            stopped_reason = "interrupted"

        if response is None:
            for segment in transcriber.finish():
                _append_transcript_segment(segment, processed_frames, transcripts)
                if not segment.is_final:
                    continue
                daemon.emit_transcript(
                    segment.text,
                    confidence=segment.confidence,
                    is_final=True,
                )
                _complete_voice_response_cycle(daemon)
                response = _manual_response_payload(daemon)
                stopped_reason = "final_transcript"
                break

        if response is None:
            daemon.cancel_manual_listening(source="click_to_talk")
            response = {
                "simulated": daemon.config.runtime.developer_mode,
                "status": "no_transcript",
                "text": "I did not catch a command.",
            }
            if stopped_reason == "capture_ended" and processed_frames > 0:
                stopped_reason = "no_final_transcript"
    except Exception:
        if entered_manual_listening:
            daemon.cancel_manual_listening(source="click_to_talk")
        raise
    finally:
        if transcriber is not None:
            transcriber.close()
        if started_daemon:
            daemon.stop()

    spoken_response_text = build_spoken_response_text(response)
    return {
        "processed_frames": processed_frames,
        "transcripts": transcripts,
        "response": response,
        "spoken_response": (
            None
            if spoken_response_text is None
            else {
                "status": "ready",
                "text": spoken_response_text,
            }
        ),
        "completed_commands": len(daemon.metrics.completed_commands),
        "final_state": daemon.state_machine.current_state.value,
        "stopped_reason": stopped_reason,
    }


def run_continuous_voice_loop(
    capture_source: AudioCaptureSource,
    wakeword_detector: WakeWordDetector,
    build_transcriber: Callable[[], SpeechTranscriber],
    *,
    max_frames: int | None = None,
    stop_after_commands: int | None = None,
    env: Mapping[str, str] | None = None,
    response_synthesizer: SpeechSynthesizer | None = None,
    response_output_dir: Path | None = None,
    response_playback_sink: AudioPlaybackSink | None = None,
) -> dict[str, object]:
    return _run_voice_capture_loop(
        capture_source,
        wakeword_detector,
        build_transcriber,
        max_frames=max_frames,
        stop_after_commands=stop_after_commands,
        env=env,
        response_synthesizer=response_synthesizer,
        response_output_dir=response_output_dir,
        response_playback_sink=response_playback_sink,
    )


def _run_voice_capture_loop(
    capture_source: AudioCaptureSource,
    wakeword_detector: WakeWordDetector,
    build_transcriber: Callable[[], SpeechTranscriber],
    *,
    max_frames: int | None,
    stop_after_commands: int | None = None,
    env: Mapping[str, str] | None = None,
    response_synthesizer: SpeechSynthesizer | None = None,
    response_output_dir: Path | None = None,
    response_playback_sink: AudioPlaybackSink | None = None,
) -> dict[str, object]:
    daemon = OperanceDaemon.build_default(env)
    status_writer = VoiceLoopRuntimeStatusWriter(env=env)
    responses: list[dict[str, object]] = []
    spoken_responses: list[dict[str, object]] = []
    wake_detections: list[dict[str, object]] = []
    transcripts: list[dict[str, object]] = []
    active_transcriber: SpeechTranscriber | None = None
    command_listen_started_frame: int | None = None
    processed_frames = 0
    stopped_reason = "capture_ended"

    def collect_response(event: ResponseEvent) -> None:
        payload = {
            "plan_id": event.plan_id,
            "status": event.status,
            "text": event.text,
        }
        responses.append(payload)
        status_writer.update(
            last_response_text=event.text,
            last_response_status=event.status,
            loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
            daemon_state=daemon.state_machine.current_state.value,
            awaiting_confirmation=daemon.pending_confirmation_plan is not None,
            completed_commands=len(daemon.metrics.completed_commands),
        )
        if response_synthesizer is None or response_output_dir is None:
            return

        response_output_dir.mkdir(parents=True, exist_ok=True)
        output_index = len(spoken_responses) + 1
        output_path = response_output_dir / f"response-{output_index:03d}.wav"
        audio = response_synthesizer.synthesize(event.text)
        response_synthesizer.save(audio, output_path)
        spoken_responses.append(
            {
                "duration_seconds": audio.duration_seconds,
                "output_path": str(output_path),
                "plan_id": event.plan_id,
                "sample_count": audio.sample_count,
                "sample_rate_hz": audio.sample_rate_hz,
                "status": event.status,
                "text": audio.text,
                "voice": audio.voice,
            }
        )
        if response_playback_sink is not None:
            response_playback_sink.play_file(output_path)
            spoken_responses[-1]["played_output"] = True

    daemon.event_bus.subscribe(ResponseEvent, collect_response)
    daemon.start()
    status_writer.update(
        loop_state="waiting_for_wake",
        daemon_state=daemon.state_machine.current_state.value,
        awaiting_confirmation=False,
    )
    try:
        try:
            for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
                processed_frames = frame_index
                status_writer.heartbeat(
                    processed_frames=processed_frames,
                    loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                    daemon_state=daemon.state_machine.current_state.value,
                    awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                    completed_commands=len(daemon.metrics.completed_commands),
                )

                if active_transcriber is None:
                    if daemon.state_machine.current_state != RuntimeState.AWAITING_CONFIRMATION:
                        detection = wakeword_detector.process_frame(frame)
                        if detection is None:
                            continue
                        daemon.emit_wake_detected(detection.phrase)
                        detection_payload = detection.to_dict()
                        detection_payload["frame_index"] = frame_index
                        wake_detections.append(detection_payload)
                        active_transcriber = build_transcriber()
                        command_listen_started_frame = frame_index
                        status_writer.update(
                            processed_frames=frame_index,
                            wake_detections=len(wake_detections),
                            last_wake_phrase=detection.phrase,
                            last_wake_confidence=detection.confidence,
                            loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                            daemon_state=daemon.state_machine.current_state.value,
                            awaiting_confirmation=False,
                            completed_commands=len(daemon.metrics.completed_commands),
                        )
                    else:
                        active_transcriber = build_transcriber()
                        command_listen_started_frame = frame_index
                        status_writer.update(
                            processed_frames=frame_index,
                            loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                            daemon_state=daemon.state_machine.current_state.value,
                            awaiting_confirmation=True,
                            completed_commands=len(daemon.metrics.completed_commands),
                        )

                segment = active_transcriber.process_frame(frame)
                if segment is None:
                    if _command_window_expired(command_listen_started_frame, frame_index):
                        handled_final = False
                        for final_segment in active_transcriber.finish():
                            final_segment = _prepare_live_transcript_segment(
                                final_segment,
                                frame_index,
                                transcripts,
                            )
                            handled_final = _handle_live_transcript_segment(
                                daemon,
                                status_writer,
                                final_segment,
                                frame_index,
                                active_transcriber=active_transcriber,
                                completed_commands=len(daemon.metrics.completed_commands),
                            )
                            if final_segment.is_final:
                                if handled_final:
                                    _complete_voice_response_cycle(daemon)
                                    status_writer.update(
                                        processed_frames=frame_index,
                                        loop_state=_voice_loop_phase(daemon, active_transcriber=None),
                                        daemon_state=daemon.state_machine.current_state.value,
                                        awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                                        completed_commands=len(daemon.metrics.completed_commands),
                                    )
                                break
                        if not handled_final:
                            _record_no_command_after_wake(
                                daemon,
                                status_writer,
                                frame_index,
                                completed_commands=len(daemon.metrics.completed_commands),
                            )
                        active_transcriber.close()
                        active_transcriber = None
                        command_listen_started_frame = None
                    continue
                segment = _prepare_live_transcript_segment(segment, frame_index, transcripts)
                handled_final = _handle_live_transcript_segment(
                    daemon,
                    status_writer,
                    segment,
                    frame_index,
                    active_transcriber=active_transcriber,
                    completed_commands=len(daemon.metrics.completed_commands),
                )
                if segment.is_final:
                    active_transcriber.close()
                    active_transcriber = None
                    command_listen_started_frame = None
                    if handled_final:
                        _complete_voice_response_cycle(daemon)
                        status_writer.update(
                            processed_frames=frame_index,
                            loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                            daemon_state=daemon.state_machine.current_state.value,
                            awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                            completed_commands=len(daemon.metrics.completed_commands),
                        )
                    if stop_after_commands is not None and len(daemon.metrics.completed_commands) >= stop_after_commands:
                        stopped_reason = "command_limit"
                        break
            else:
                if max_frames is not None and processed_frames >= max_frames:
                    stopped_reason = "frame_limit"
        except KeyboardInterrupt:
            stopped_reason = "interrupted"

        if active_transcriber is not None:
            for segment in active_transcriber.finish():
                segment = _prepare_live_transcript_segment(segment, processed_frames, transcripts)
                handled_final = _handle_live_transcript_segment(
                    daemon,
                    status_writer,
                    segment,
                    processed_frames,
                    active_transcriber=active_transcriber,
                    completed_commands=len(daemon.metrics.completed_commands),
                )
                if segment.is_final:
                    if handled_final:
                        _complete_voice_response_cycle(daemon)
                        status_writer.update(
                            processed_frames=processed_frames,
                            loop_state=_voice_loop_phase(daemon, active_transcriber=None),
                            daemon_state=daemon.state_machine.current_state.value,
                            awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                            completed_commands=len(daemon.metrics.completed_commands),
                        )
                    if stop_after_commands is not None and len(daemon.metrics.completed_commands) >= stop_after_commands:
                        stopped_reason = "command_limit"
                        break
            active_transcriber.close()
            active_transcriber = None
    finally:
        if active_transcriber is not None:
            active_transcriber.close()
        daemon.stop()
        status_writer.stop(
            processed_frames=processed_frames,
            loop_state="stopped",
            daemon_state=daemon.state_machine.current_state.value,
            awaiting_confirmation=daemon.pending_confirmation_plan is not None,
            completed_commands=len(daemon.metrics.completed_commands),
            stopped_reason=stopped_reason,
        )

    return {
        "processed_frames": processed_frames,
        "wake_detections": wake_detections,
        "transcripts": transcripts,
        "responses": responses,
        "spoken_responses": spoken_responses,
        "completed_commands": len(daemon.metrics.completed_commands),
        "final_state": daemon.state_machine.current_state.value,
        "stopped_reason": stopped_reason,
    }


def _prepare_live_transcript_segment(
    segment,
    frame_index: int,
    transcripts: list[dict[str, object]],
):
    segment = _trim_leading_wake_residue(segment)
    _append_transcript_segment(segment, frame_index, transcripts)
    return segment


def _handle_live_transcript_segment(
    daemon: OperanceDaemon,
    status_writer: VoiceLoopRuntimeStatusWriter,
    segment,
    frame_index: int,
    *,
    active_transcriber: SpeechTranscriber,
    completed_commands: int,
) -> bool:
    if segment.is_final and _is_wake_only_transcript(segment.text):
        _record_no_command_after_wake(
            daemon,
            status_writer,
            frame_index,
            transcript_text=segment.text,
            transcript_final=True,
            completed_commands=completed_commands,
        )
        return False

    daemon.emit_transcript(
        segment.text,
        confidence=segment.confidence,
        is_final=segment.is_final,
    )
    status_writer.update(
        processed_frames=frame_index,
        last_transcript_text=segment.text,
        last_transcript_final=segment.is_final,
        loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
        daemon_state=daemon.state_machine.current_state.value,
        awaiting_confirmation=daemon.pending_confirmation_plan is not None,
        completed_commands=completed_commands,
    )
    return segment.is_final


def _append_transcript_segment(
    segment,
    frame_index: int,
    transcripts: list[dict[str, object]],
) -> None:
    payload = segment.to_dict()
    payload["frame_index"] = frame_index
    transcripts.append(payload)


def _command_window_expired(started_frame: int | None, frame_index: int) -> bool:
    if started_frame is None:
        return False
    return frame_index - started_frame >= DEFAULT_ALWAYS_ON_COMMAND_TIMEOUT_FRAMES


def _record_no_command_after_wake(
    daemon: OperanceDaemon,
    status_writer: VoiceLoopRuntimeStatusWriter,
    frame_index: int,
    *,
    transcript_text: str | None = None,
    transcript_final: bool = False,
    completed_commands: int,
) -> None:
    daemon.cancel_wake_listening(source="voice_loop")
    status_writer.update(
        processed_frames=frame_index,
        last_transcript_text=transcript_text,
        last_transcript_final=transcript_final,
        last_response_text=_NO_COMMAND_AFTER_WAKE_RESPONSE,
        last_response_status="no_command",
        loop_state=_voice_loop_phase(daemon, active_transcriber=None),
        daemon_state=daemon.state_machine.current_state.value,
        awaiting_confirmation=daemon.pending_confirmation_plan is not None,
        completed_commands=completed_commands,
    )


def _trim_leading_wake_residue(segment):
    text = str(segment.text or "").strip()
    if not text:
        return segment

    match = _LIVE_COMMAND_START_RE.search(text)
    if match is None or match.start() == 0:
        return segment
    if match.start() > _MAX_LEADING_WAKE_RESIDUE_CHARS:
        return segment

    prefix = text[: match.start()].strip(" ,.;:-")
    if not prefix or len(prefix.split()) > 4:
        return segment

    cleaned = text[match.start() :].strip(" ,.;:-")
    if not cleaned or cleaned == text:
        return segment
    return replace(segment, text=cleaned)


def _is_wake_only_transcript(text: str) -> bool:
    normalized = re.sub(r"[^a-z]+", "", text.lower())
    return normalized in _WAKE_ONLY_TRANSCRIPTS


def _complete_voice_response_cycle(daemon: OperanceDaemon) -> None:
    if daemon.state_machine.current_state == RuntimeState.RESPONDING:
        daemon.complete_response_cycle()


def _manual_response_payload(daemon: OperanceDaemon) -> dict[str, object]:
    return {
        "simulated": daemon.config.runtime.developer_mode,
        "status": daemon.last_command_status,
        "text": daemon.last_response,
    }


def _voice_loop_phase(
    daemon: OperanceDaemon,
    *,
    active_transcriber: SpeechTranscriber | None,
) -> str:
    if daemon.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION:
        return "awaiting_confirmation"
    if daemon.state_machine.current_state == RuntimeState.RESPONDING:
        return "responding"
    if active_transcriber is not None:
        return "listening_for_command"
    return "waiting_for_wake"
