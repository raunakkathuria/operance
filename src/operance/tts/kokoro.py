"""Optional Kokoro-backed speech synthesis probe backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .synthesizer import SynthesizedAudio


def _load_kokoro_api() -> tuple[type[Any], Any]:
    try:
        from kokoro_onnx import Kokoro
        import soundfile
    except ImportError as exc:
        raise ValueError("kokoro-onnx or soundfile is not installed") from exc

    return Kokoro, soundfile


class KokoroSpeechSynthesizer:
    """Synthesize bounded probe audio through a local Kokoro ONNX model."""

    def __init__(
        self,
        *,
        model_path: str,
        voices_path: str,
        voice: str = "af_sarah",
        speed: float = 1.0,
        language: str = "en-us",
    ) -> None:
        self.model_path = model_path
        self.voices_path = voices_path
        self.voice = voice
        self.speed = speed
        self.language = language

        try:
            kokoro_cls, soundfile_module = _load_kokoro_api()
            self.backend = kokoro_cls(model_path=model_path, voices_path=voices_path)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"kokoro TTS backend failed to initialize: {exc}") from exc

        self._soundfile = soundfile_module

    def synthesize(self, text: str) -> SynthesizedAudio:
        try:
            samples, sample_rate_hz = self.backend.create(
                text,
                voice=self.voice,
                speed=self.speed,
                lang=self.language,
            )
        except Exception as exc:
            raise ValueError(f"kokoro TTS backend failed during synthesis: {exc}") from exc

        return SynthesizedAudio(
            text=text,
            voice=self.voice,
            sample_rate_hz=int(sample_rate_hz),
            samples=list(samples),
        )

    def save(self, audio: SynthesizedAudio, path: Path) -> None:
        try:
            self._soundfile.write(str(path), audio.samples, audio.sample_rate_hz)
        except Exception as exc:
            raise ValueError(f"kokoro TTS backend failed to save audio: {exc}") from exc
