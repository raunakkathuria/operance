from types import SimpleNamespace

import pytest


def test_build_default_speech_transcriber_uses_moonshine_backend(monkeypatch) -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import build_default_speech_transcriber
    from operance.stt.moonshine import MoonshineSpeechTranscriber

    class FakeTranscriptEventListener:
        pass

    class FakeTranscriber:
        def __init__(self, *, model_path: str, model_arch: str) -> None:
            self.model_path = model_path
            self.model_arch = model_arch
            self.listener = None
            self.started = 0
            self.audio_batches: list[tuple[list[float], int]] = []

        def add_listener(self, listener) -> None:
            self.listener = listener

        def start(self) -> None:
            self.started += 1

        def add_audio(self, audio_data: list[float], sample_rate: int) -> None:
            self.audio_batches.append((audio_data, sample_rate))
            assert self.listener is not None
            self.listener.on_line_completed(
                SimpleNamespace(line=SimpleNamespace(text="open firefox"))
            )

        def stop(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "operance.stt.moonshine._load_moonshine_api",
        lambda: (
            FakeTranscriptEventListener,
            FakeTranscriber,
            lambda language: (f"models/{language}", "tiny"),
        ),
    )

    transcriber = build_default_speech_transcriber()

    assert isinstance(transcriber, MoonshineSpeechTranscriber)

    segment = transcriber.process_frame(
        AudioFrame(
            sample_rate_hz=16000,
            channels=1,
            sample_count=2,
            pcm_s16le=b"\x00\x00\xff\x7f",
        )
    )

    assert segment is not None
    assert segment.text == "open firefox"
    assert segment.confidence == 1.0
    assert segment.is_final is True
    assert transcriber.backend.model_path == "models/en"
    assert transcriber.backend.model_arch == "tiny"
    assert transcriber.backend.started == 1
    assert transcriber.backend.audio_batches[0][1] == 16000
    assert transcriber.backend.audio_batches[0][0][0] == 0.0
    assert transcriber.backend.audio_batches[0][0][1] == pytest.approx(32767 / 32768)


def test_build_default_speech_transcriber_raises_when_backend_is_missing(monkeypatch) -> None:
    from operance.stt import build_default_speech_transcriber

    def raise_missing() -> object:
        raise ValueError("moonshine-voice is not installed")

    monkeypatch.setattr("operance.stt.moonshine._load_moonshine_api", raise_missing)

    with pytest.raises(ValueError, match="moonshine-voice is not installed"):
        build_default_speech_transcriber()


def test_run_stt_probe_reports_segments_and_flushes() -> None:
    from operance.audio.capture import AudioFrame
    from operance.stt import TranscriptSegment
    from operance.voice.probe import run_stt_probe

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x01\x00" * 4)

    class FakeSpeechTranscriber:
        def __init__(self) -> None:
            self.calls = 0
            self.finished = False
            self.closed = False

        def process_frame(self, frame) -> TranscriptSegment | None:
            self.calls += 1
            if self.calls == 2:
                return TranscriptSegment(text="open fire", confidence=0.41, is_final=False)
            return None

        def finish(self) -> list[TranscriptSegment]:
            self.finished = True
            return [TranscriptSegment(text="open firefox", confidence=0.96, is_final=True)]

        def close(self) -> None:
            self.closed = True

    transcriber = FakeSpeechTranscriber()

    result = run_stt_probe(FakeCaptureSource(), transcriber, max_frames=2)

    assert result["processed_frames"] == 2
    assert result["segments"] == [
        {
            "confidence": 0.41,
            "frame_index": 2,
            "is_final": False,
            "segment_id": result["segments"][0]["segment_id"],
            "text": "open fire",
            "timestamp": result["segments"][0]["timestamp"],
        },
        {
            "confidence": 0.96,
            "frame_index": 2,
            "is_final": True,
            "segment_id": result["segments"][1]["segment_id"],
            "text": "open firefox",
            "timestamp": result["segments"][1]["timestamp"],
        },
    ]
    assert transcriber.finished is True
    assert transcriber.closed is True
