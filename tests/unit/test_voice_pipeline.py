from pathlib import Path

import pytest

from operance.models.events import RuntimeState


def test_audio_frame_serializes_to_dict() -> None:
    from operance.audio.capture import AudioFrame

    frame = AudioFrame(
        sample_rate_hz=16000,
        channels=1,
        sample_count=512,
        source="mock-mic",
        pcm_s16le=b"\x01\x02" * 512,
    )

    payload = frame.to_dict()

    assert payload["sample_rate_hz"] == 16000
    assert payload["channels"] == 1
    assert payload["sample_count"] == 512
    assert payload["source"] == "mock-mic"
    assert payload["sample_format"] == "s16le"
    assert payload["byte_count"] == 1024
    assert "pcm_s16le" not in payload


def test_scripted_voice_session_runs_wake_and_final_transcript(tmp_path: Path) -> None:
    from operance.voice.scripted import ScriptedVoiceStep, run_scripted_voice_session

    result = run_scripted_voice_session(
        [
            ScriptedVoiceStep.wake("operance"),
            ScriptedVoiceStep.final_transcript("open firefox", confidence=0.98),
        ],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert result["responses"] == ["Launched firefox"]
    assert result["completed_commands"] == 1
    assert result["final_state"] == "RESPONDING"


def test_scripted_voice_session_handles_partial_then_final_transcript(tmp_path: Path) -> None:
    from operance.voice.scripted import ScriptedVoiceStep, run_scripted_voice_session

    result = run_scripted_voice_session(
        [
            ScriptedVoiceStep.wake("operance"),
            ScriptedVoiceStep.partial_transcript("open fire", confidence=0.42),
            ScriptedVoiceStep.final_transcript("open firefox", confidence=0.94),
        ],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert result["responses"] == ["Launched firefox"]
    assert result["completed_commands"] == 1
    assert result["final_state"] == RuntimeState.RESPONDING.value


def test_live_voice_session_runs_wake_stt_and_daemon_command(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.voice import run_live_voice_session
    from operance.wakeword import WakeWordDetection

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls == 2:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0
            self.closed = False

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            self.closed = True

    created_transcribers: list[FakeSpeechTranscriber] = []

    def build_transcriber() -> FakeSpeechTranscriber:
        transcriber = FakeSpeechTranscriber()
        created_transcribers.append(transcriber)
        return transcriber

    result = run_live_voice_session(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        build_transcriber,
        max_frames=4,
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert result["processed_frames"] == 4
    assert result["wake_detections"] == [
        {
            "confidence": 0.88,
            "detection_id": result["wake_detections"][0]["detection_id"],
            "frame_index": 2,
            "phrase": "operance",
            "timestamp": result["wake_detections"][0]["timestamp"],
        }
    ]
    assert result["transcripts"] == [
        {
            "confidence": 0.93,
            "frame_index": 4,
            "is_final": True,
            "segment_id": result["transcripts"][0]["segment_id"],
            "text": "open firefox",
            "timestamp": result["transcripts"][0]["timestamp"],
        }
    ]
    assert result["responses"] == [
        {
            "plan_id": result["responses"][0]["plan_id"],
            "status": "success",
            "text": "Launched firefox",
        }
    ]
    assert result["completed_commands"] == 1
    assert result["final_state"] == RuntimeState.IDLE.value
    assert len(created_transcribers) == 1
    assert created_transcribers[0].closed is True


def test_live_voice_session_can_confirm_pending_command_without_second_wake(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.voice import run_live_voice_session
    from operance.wakeword import WakeWordDetection

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 6
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls == 2:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self, final_text: str, confidence: float) -> None:
            self.final_text = final_text
            self.confidence = confidence
            self.calls = 0
            self.closed = False

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text=self.final_text, confidence=self.confidence, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            self.closed = True

    planned_transcribers = [
        FakeSpeechTranscriber("close window firefox", 0.91),
        FakeSpeechTranscriber("confirm", 0.98),
    ]

    def build_transcriber() -> FakeSpeechTranscriber:
        return planned_transcribers.pop(0)

    result = run_live_voice_session(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        build_transcriber,
        max_frames=6,
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert len(result["wake_detections"]) == 1
    assert [item["text"] for item in result["transcripts"]] == ["close window firefox", "confirm"]
    assert [item["status"] for item in result["responses"]] == ["awaiting_confirmation", "success"]
    assert [item["text"] for item in result["responses"]] == [
        "Command requires confirmation.",
        "Closed window Firefox",
    ]
    assert result["completed_commands"] == 2
    assert result["final_state"] == RuntimeState.IDLE.value


def test_manual_voice_session_runs_final_transcript_against_existing_daemon(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.stt import TranscriptSegment
    from operance.voice import run_manual_voice_session

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0
            self.closed = False

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            self.closed = True

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    transcriber = FakeSpeechTranscriber()

    result = run_manual_voice_session(
        daemon,
        FakeCaptureSource(),
        lambda: transcriber,
        max_frames=4,
    )

    assert result["processed_frames"] == 2
    assert result["transcripts"] == [
        {
            "confidence": 0.93,
            "frame_index": 2,
            "is_final": True,
            "segment_id": result["transcripts"][0]["segment_id"],
            "text": "open firefox",
            "timestamp": result["transcripts"][0]["timestamp"],
        }
    ]
    assert result["response"] == {
        "simulated": True,
        "status": "success",
        "text": "Launched firefox",
    }
    assert result["completed_commands"] == 1
    assert result["final_state"] == RuntimeState.IDLE.value
    assert transcriber.closed is True


def test_manual_voice_session_can_confirm_pending_command_without_wake(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.stt import TranscriptSegment
    from operance.voice import run_manual_voice_session

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="confirm", confidence=0.98, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("close window firefox", is_final=True)

    result = run_manual_voice_session(
        daemon,
        FakeCaptureSource(),
        FakeSpeechTranscriber,
        max_frames=4,
    )

    assert result["response"] == {
        "simulated": True,
        "status": "success",
        "text": "Closed window Firefox",
    }
    assert result["completed_commands"] == 2
    assert result["final_state"] == RuntimeState.IDLE.value


def test_manual_voice_session_returns_no_transcript_and_restores_idle(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.voice import run_manual_voice_session

    class SilentCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class SilentSpeechTranscriber:
        def process_frame(self, frame) -> None:
            return None

        def finish(self) -> list[object]:
            return []

        def close(self) -> None:
            return None

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()

    result = run_manual_voice_session(
        daemon,
        SilentCaptureSource(),
        SilentSpeechTranscriber,
        max_frames=4,
    )

    assert result["response"] == {
        "simulated": True,
        "status": "no_transcript",
        "text": "I did not catch a command.",
    }
    assert result["completed_commands"] == 0
    assert result["final_state"] == RuntimeState.IDLE.value


def test_manual_voice_session_restores_idle_when_transcriber_init_fails(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.daemon import OperanceDaemon
    from operance.models.events import RuntimeState
    from operance.voice import run_manual_voice_session

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 2
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.start()

    with pytest.raises(ValueError, match="moonshine-voice is not installed"):
        run_manual_voice_session(
            daemon,
            FakeCaptureSource(),
            lambda: (_ for _ in ()).throw(ValueError("moonshine-voice is not installed")),
            max_frames=2,
        )

    assert daemon.state_machine.current_state == RuntimeState.IDLE


def test_live_voice_session_can_synthesize_saved_response_audio(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.tts import SynthesizedAudio
    from operance.voice import run_live_voice_session
    from operance.wakeword import WakeWordDetection

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls == 2:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    class FakeSpeechSynthesizer:
        def __init__(self) -> None:
            self.saved_paths: list[Path] = []

        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.25, -0.25],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text(audio.text, encoding="utf-8")
            self.saved_paths.append(path)

    synthesizer = FakeSpeechSynthesizer()
    output_dir = tmp_path / "spoken-responses"
    result = run_live_voice_session(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        lambda: FakeSpeechTranscriber(),
        max_frames=4,
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
        response_synthesizer=synthesizer,
        response_output_dir=output_dir,
    )

    assert result["spoken_responses"] == [
        {
            "duration_seconds": 3 / 24000,
            "output_path": str(output_dir / "response-001.wav"),
            "plan_id": result["spoken_responses"][0]["plan_id"],
            "sample_count": 3,
            "sample_rate_hz": 24000,
            "status": "success",
            "text": "Launched firefox",
            "voice": "af_sarah",
        }
    ]
    assert synthesizer.saved_paths == [output_dir / "response-001.wav"]
    assert (output_dir / "response-001.wav").read_text(encoding="utf-8") == "Launched firefox"


def test_live_voice_session_can_play_synthesized_response_audio(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.tts import SynthesizedAudio
    from operance.voice import run_live_voice_session
    from operance.wakeword import WakeWordDetection

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls == 2:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    class FakeSpeechSynthesizer:
        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.25, -0.25],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            path.write_text(audio.text, encoding="utf-8")

    class FakePlaybackSink:
        def __init__(self) -> None:
            self.played_paths: list[Path] = []

        def play_file(self, path: Path) -> None:
            self.played_paths.append(path)

    playback_sink = FakePlaybackSink()
    output_dir = tmp_path / "spoken-responses"
    result = run_live_voice_session(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        lambda: FakeSpeechTranscriber(),
        max_frames=4,
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
        response_synthesizer=FakeSpeechSynthesizer(),
        response_output_dir=output_dir,
        response_playback_sink=playback_sink,
    )

    assert playback_sink.played_paths == [output_dir / "response-001.wav"]
    assert result["spoken_responses"][0]["played_output"] is True


def test_continuous_voice_loop_stops_after_completed_command_limit(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.voice import run_continuous_voice_loop
    from operance.wakeword import WakeWordDetection

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 10
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls in {2, 6}:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self, text: str) -> None:
            self.text = text
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text=self.text, confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    planned_transcribers = [
        FakeSpeechTranscriber("open firefox"),
        FakeSpeechTranscriber("what is the volume"),
    ]

    result = run_continuous_voice_loop(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        lambda: planned_transcribers.pop(0),
        stop_after_commands=2,
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [item["text"] for item in result["responses"]] == [
        "Launched firefox",
        "Volume is 30%",
    ]
    assert result["completed_commands"] == 2
    assert result["stopped_reason"] == "command_limit"
    assert result["final_state"] == RuntimeState.IDLE.value


def test_continuous_voice_loop_writes_runtime_status_file(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.voice import build_voice_loop_runtime_status_snapshot, run_continuous_voice_loop
    from operance.wakeword import WakeWordDetection

    env = {
        "OPERANCE_DATA_DIR": str(tmp_path / "data"),
        "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
    }

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            frame_total = max_frames if max_frames is not None else 4
            for _ in range(frame_total):
                yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    class FakeWakeWordDetector:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> WakeWordDetection | None:
            self.calls += 1
            if self.calls == 2:
                return WakeWordDetection(phrase="operance", confidence=0.88)
            return None

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open firefox", confidence=0.93, is_final=True)
            return None

        def finish(self) -> list[TranscriptSegment]:
            return []

        def close(self) -> None:
            return None

    result = run_continuous_voice_loop(
        FakeCaptureSource(),
        FakeWakeWordDetector(),
        lambda: FakeSpeechTranscriber(),
        stop_after_commands=1,
        env=env,
    )
    snapshot = build_voice_loop_runtime_status_snapshot(env=env)

    assert result["completed_commands"] == 1
    assert snapshot.status_file_exists is True
    assert snapshot.status == "ok"
    assert snapshot.loop_state == "stopped"
    assert snapshot.processed_frames == result["processed_frames"]
    assert snapshot.wake_detections == 1
    assert snapshot.completed_commands == 1
    assert snapshot.last_wake_phrase == "operance"
    assert snapshot.last_transcript_text == "open firefox"
    assert snapshot.last_response_text == "Launched firefox"
    assert snapshot.last_response_status == "success"
    assert snapshot.stopped_reason == "command_limit"


def test_continuous_voice_loop_reports_interrupts(tmp_path: Path) -> None:
    from operance.audio.capture import AudioFrame
    from operance.voice import run_continuous_voice_loop

    class InterruptedCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)
            raise KeyboardInterrupt

    class SilentWakeWordDetector:
        def process_frame(self, frame):
            return None

    result = run_continuous_voice_loop(
        InterruptedCaptureSource(),
        SilentWakeWordDetector(),
        lambda: (_ for _ in ()).throw(AssertionError("transcriber should not be built")),
        env={
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert result["processed_frames"] == 1
    assert result["completed_commands"] == 0
    assert result["stopped_reason"] == "interrupted"
    assert result["final_state"] == RuntimeState.IDLE.value
