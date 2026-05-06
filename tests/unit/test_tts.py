from pathlib import Path

import pytest


def test_build_default_speech_synthesizer_uses_kokoro_backend(monkeypatch, tmp_path: Path) -> None:
    from operance.tts import build_default_speech_synthesizer
    from operance.tts.kokoro import KokoroSpeechSynthesizer

    writes: list[tuple[str, object, int]] = []

    class FakeKokoro:
        def __init__(self, model_path: str, voices_path: str) -> None:
            self.model_path = model_path
            self.voices_path = voices_path
            self.calls: list[tuple[str, str, float, str]] = []

        def create(self, text: str, *, voice: str, speed: float, lang: str):
            self.calls.append((text, voice, speed, lang))
            return ([0.0, 0.5, -0.5], 24000)

    class FakeSoundFile:
        @staticmethod
        def write(path: str, samples: object, sample_rate_hz: int) -> None:
            writes.append((path, samples, sample_rate_hz))

    monkeypatch.setattr(
        "operance.tts.kokoro._load_kokoro_api",
        lambda: (FakeKokoro, FakeSoundFile),
    )

    synthesizer = build_default_speech_synthesizer(
        model_path="models/kokoro-v1.0.onnx",
        voices_path="models/voices-v1.0.bin",
        voice="af_sarah",
        speed=1.1,
        language="en-us",
    )

    assert isinstance(synthesizer, KokoroSpeechSynthesizer)

    audio = synthesizer.synthesize("Hello from Operance")
    output_path = tmp_path / "audio.wav"
    synthesizer.save(audio, output_path)

    assert audio.voice == "af_sarah"
    assert audio.sample_rate_hz == 24000
    assert audio.sample_count == 3
    assert audio.duration_seconds == pytest.approx(3 / 24000)
    assert synthesizer.backend.model_path == "models/kokoro-v1.0.onnx"
    assert synthesizer.backend.voices_path == "models/voices-v1.0.bin"
    assert synthesizer.backend.calls == [("Hello from Operance", "af_sarah", 1.1, "en-us")]
    assert writes == [(str(output_path), [0.0, 0.5, -0.5], 24000)]


def test_build_default_speech_synthesizer_raises_when_backend_is_missing(monkeypatch) -> None:
    from operance.tts import build_default_speech_synthesizer

    def raise_missing() -> object:
        raise ValueError("kokoro-onnx or soundfile is not installed")

    monkeypatch.setattr("operance.tts.kokoro._load_kokoro_api", raise_missing)

    with pytest.raises(ValueError, match="kokoro-onnx or soundfile is not installed"):
        build_default_speech_synthesizer(
            model_path="model.onnx",
            voices_path="voices.bin",
        )


def test_run_tts_probe_reports_metadata_and_output_path(tmp_path: Path) -> None:
    from operance.tts import SynthesizedAudio
    from operance.voice.probe import run_tts_probe

    class FakeSpeechSynthesizer:
        def __init__(self) -> None:
            self.saved: list[tuple[SynthesizedAudio, Path]] = []

        def synthesize(self, text: str) -> SynthesizedAudio:
            return SynthesizedAudio(
                text=text,
                voice="af_sarah",
                sample_rate_hz=24000,
                samples=[0.0, 0.25, -0.25, 0.5],
            )

        def save(self, audio: SynthesizedAudio, path: Path) -> None:
            self.saved.append((audio, path))

    synthesizer = FakeSpeechSynthesizer()
    output_path = tmp_path / "tts.wav"

    result = run_tts_probe(
        synthesizer,
        "Hello from Operance",
        output_path=output_path,
    )

    assert result == {
        "duration_seconds": pytest.approx(4 / 24000),
        "output_path": str(output_path),
        "sample_count": 4,
        "sample_rate_hz": 24000,
        "text": "Hello from Operance",
        "voice": "af_sarah",
    }
    assert synthesizer.saved[0][1] == output_path


def test_tts_asset_discovery_ignores_unrelated_paths(tmp_path: Path, monkeypatch) -> None:
    from operance.tts.assets import find_existing_tts_model_path, find_existing_tts_voices_path

    monkeypatch.chdir(tmp_path)
    home_dir = tmp_path / "home"
    unrelated_tts_dir = home_dir / ".config" / "archived-app" / "tts"
    unrelated_tts_dir.mkdir(parents=True)
    unrelated_model_path = unrelated_tts_dir / "kokoro.onnx"
    unrelated_voices_path = unrelated_tts_dir / "voices.bin"
    unrelated_model_path.write_bytes(b"model")
    unrelated_voices_path.write_bytes(b"voices")

    env = {"HOME": str(home_dir)}

    assert find_existing_tts_model_path(env) is None
    assert find_existing_tts_voices_path(env) is None
