"""Wake-word contracts and probe detectors."""

from .energy import EnergyWakeWordDetector
from .detector import WakeWordDetection, WakeWordDetector
from .openwakeword import OpenWakeWordDetector


def build_default_wakeword_detector(
    *,
    phrase: str = "operance",
    threshold: float = 0.6,
    cooldown_frames: int = 6,
    model_path: str | None = None,
) -> WakeWordDetector:
    if model_path:
        return OpenWakeWordDetector(
            model_path=model_path,
            phrase=phrase,
            threshold=threshold,
            cooldown_frames=cooldown_frames,
        )
    return EnergyWakeWordDetector(
        phrase=phrase,
        threshold=threshold,
        cooldown_frames=cooldown_frames,
    )


__all__ = [
    "EnergyWakeWordDetector",
    "OpenWakeWordDetector",
    "WakeWordDetection",
    "WakeWordDetector",
    "build_default_wakeword_detector",
]
