"""Speech-synthesis contracts and probe backends."""

from .kokoro import KokoroSpeechSynthesizer
from .synthesizer import SpeechSynthesizer, SynthesizedAudio


def build_default_speech_synthesizer(
    *,
    model_path: str,
    voices_path: str,
    voice: str = "af_sarah",
    speed: float = 1.0,
    language: str = "en-us",
) -> SpeechSynthesizer:
    return KokoroSpeechSynthesizer(
        model_path=model_path,
        voices_path=voices_path,
        voice=voice,
        speed=speed,
        language=language,
    )


__all__ = [
    "KokoroSpeechSynthesizer",
    "SpeechSynthesizer",
    "SynthesizedAudio",
    "build_default_speech_synthesizer",
]
