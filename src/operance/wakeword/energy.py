"""Frame-driven wake-word probe detectors."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import struct

from ..audio.capture import AudioFrame
from .detector import WakeWordDetection


@dataclass(slots=True)
class EnergyWakeWordDetector:
    phrase: str = "operance"
    threshold: float = 0.6
    cooldown_frames: int = 6
    activation_frames: int = 2
    _cooldown_remaining: int = field(default=0, init=False, repr=False)
    _activation_streak: int = field(default=0, init=False, repr=False)
    _streak_confidence: float = field(default=0.0, init=False, repr=False)

    def process_frame(self, frame: AudioFrame) -> WakeWordDetection | None:
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            self._reset_streak()
            return None

        if frame.sample_format != "s16le" or not frame.pcm_s16le:
            self._reset_streak()
            return None

        confidence = frame_energy_confidence(frame.pcm_s16le)
        if confidence < self.threshold:
            self._reset_streak()
            return None

        self._activation_streak += 1
        self._streak_confidence = max(self._streak_confidence, confidence)
        if self._activation_streak < self.activation_frames:
            return None

        self._cooldown_remaining = self.cooldown_frames
        detection_confidence = self._streak_confidence
        self._reset_streak()
        return WakeWordDetection(phrase=self.phrase, confidence=detection_confidence)

    def _reset_streak(self) -> None:
        self._activation_streak = 0
        self._streak_confidence = 0.0


def frame_peak_confidence(pcm_s16le: bytes) -> float:
    peak = 0
    for (sample,) in struct.iter_unpack("<h", pcm_s16le):
        magnitude = abs(sample)
        if magnitude > peak:
            peak = magnitude

    if peak == 0:
        return 0.0
    return min(1.0, peak / 32767.0)


def frame_energy_confidence(
    pcm_s16le: bytes,
    *,
    active_sample_floor: float = 0.1,
    rms_scale: float = 4.0,
    active_ratio_scale: float = 2.0,
) -> float:
    magnitudes = [abs(sample) for (sample,) in struct.iter_unpack("<h", pcm_s16le)]
    if not magnitudes:
        return 0.0

    peak = max(magnitudes)
    if peak == 0:
        return 0.0

    peak_confidence = min(1.0, peak / 32767.0)
    rms = math.sqrt(sum(magnitude * magnitude for magnitude in magnitudes) / len(magnitudes))
    rms_confidence = min(1.0, (rms / 32767.0) * rms_scale)
    active_cutoff = 32767.0 * active_sample_floor
    active_ratio = sum(1 for magnitude in magnitudes if magnitude >= active_cutoff) / len(magnitudes)
    sustained_confidence = min(1.0, active_ratio * active_ratio_scale)
    return min(peak_confidence, rms_confidence, sustained_confidence)


def suggest_energy_wakeword_threshold(
    ambient_detector_confidence: float,
    *,
    base_threshold: float = 0.6,
    margin: float = 0.1,
    max_threshold: float = 0.95,
) -> float:
    suggested = max(base_threshold, ambient_detector_confidence + margin)
    return min(max_threshold, round(suggested, 3))
