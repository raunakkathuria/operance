"""Speech-to-text contracts and probe backends."""

from .moonshine import MoonshineSpeechTranscriber
from .transcriber import SpeechTranscriber, TranscriptSegment


def build_default_speech_transcriber(*, language: str = "en") -> SpeechTranscriber:
    return MoonshineSpeechTranscriber(language=language)


__all__ = [
    "MoonshineSpeechTranscriber",
    "SpeechTranscriber",
    "TranscriptSegment",
    "build_default_speech_transcriber",
]
