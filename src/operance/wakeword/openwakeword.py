"""Optional openWakeWord-backed wake-word detector."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..audio.capture import AudioFrame
from .detector import WakeWordDetection


def _load_openwakeword_api() -> tuple[Any, type[Any]]:
    try:
        import numpy
        from openwakeword.model import Model
    except ImportError as exc:
        raise ValueError("openwakeword is not installed") from exc

    return numpy, Model


@dataclass(slots=True)
class OpenWakeWordDetector:
    model_path: str
    phrase: str = "operance"
    threshold: float = 0.5
    cooldown_frames: int = 6
    _cooldown_remaining: int = field(default=0, init=False, repr=False)
    _model_name: str = field(default="", init=False, repr=False)
    _numpy: Any = field(default=None, init=False, repr=False)
    backend: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        model_file = Path(self.model_path).expanduser()
        if not model_file.is_file():
            raise ValueError(f"wake-word model not found: {model_file}")

        self.model_path = str(model_file)
        self._model_name = model_file.stem

        try:
            self._numpy, model_cls = _load_openwakeword_api()
            self.backend = model_cls(wakeword_models=[self.model_path])
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"openwakeword backend failed to initialize: {exc}") from exc

    def process_frame(self, frame: AudioFrame) -> WakeWordDetection | None:
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            return None

        if frame.sample_format != "s16le" or not frame.pcm_s16le:
            return None

        try:
            samples = self._numpy.frombuffer(frame.pcm_s16le, dtype=self._numpy.int16)
            predictions = self.backend.predict(samples)
        except Exception as exc:
            raise ValueError(f"openwakeword prediction failed: {exc}") from exc

        confidence = _extract_prediction_score(predictions, self.phrase, self._model_name)
        if confidence < self.threshold:
            return None

        self._cooldown_remaining = self.cooldown_frames
        return WakeWordDetection(phrase=self.phrase, confidence=confidence)


def _extract_prediction_score(predictions: object, phrase: str, model_name: str) -> float:
    if not isinstance(predictions, dict) or not predictions:
        return 0.0

    for key in (phrase, model_name):
        if key in predictions:
            return float(predictions[key])

    if len(predictions) == 1:
        return float(next(iter(predictions.values())))

    return max(float(value) for value in predictions.values())
