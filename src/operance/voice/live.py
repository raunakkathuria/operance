"""Bounded and continuous live voice-session helpers for captured audio frames."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from ..audio.capture import AudioCaptureSource
from ..audio.playback import AudioPlaybackSink
from ..daemon import OperanceDaemon
from ..models.events import ResponseEvent, RuntimeState
from ..stt import SpeechTranscriber
from ..tts import SpeechSynthesizer
from ..wakeword import WakeWordDetector
from .runtime import VoiceLoopRuntimeStatusWriter

DEFAULT_CLICK_TO_TALK_MAX_FRAMES = 40


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

    return {
        "processed_frames": processed_frames,
        "transcripts": transcripts,
        "response": response,
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
                        continue
                    active_transcriber = build_transcriber()
                    status_writer.update(
                        processed_frames=frame_index,
                        loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                        daemon_state=daemon.state_machine.current_state.value,
                        awaiting_confirmation=True,
                        completed_commands=len(daemon.metrics.completed_commands),
                    )

                segment = active_transcriber.process_frame(frame)
                if segment is None:
                    continue
                _emit_transcript_segment(daemon, segment, frame_index, transcripts)
                status_writer.update(
                    processed_frames=frame_index,
                    last_transcript_text=segment.text,
                    last_transcript_final=segment.is_final,
                    loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                    daemon_state=daemon.state_machine.current_state.value,
                    awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                    completed_commands=len(daemon.metrics.completed_commands),
                )
                if segment.is_final:
                    active_transcriber.close()
                    active_transcriber = None
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
                _emit_transcript_segment(daemon, segment, processed_frames, transcripts)
                status_writer.update(
                    processed_frames=processed_frames,
                    last_transcript_text=segment.text,
                    last_transcript_final=segment.is_final,
                    loop_state=_voice_loop_phase(daemon, active_transcriber=active_transcriber),
                    daemon_state=daemon.state_machine.current_state.value,
                    awaiting_confirmation=daemon.pending_confirmation_plan is not None,
                    completed_commands=len(daemon.metrics.completed_commands),
                )
                if segment.is_final:
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


def _emit_transcript_segment(
    daemon: OperanceDaemon,
    segment,
    frame_index: int,
    transcripts: list[dict[str, object]],
) -> None:
    _append_transcript_segment(segment, frame_index, transcripts)
    daemon.emit_transcript(
        segment.text,
        confidence=segment.confidence,
        is_final=segment.is_final,
    )


def _append_transcript_segment(
    segment,
    frame_index: int,
    transcripts: list[dict[str, object]],
) -> None:
    payload = segment.to_dict()
    payload["frame_index"] = frame_index
    transcripts.append(payload)


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
