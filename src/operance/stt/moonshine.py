"""Optional Moonshine-backed speech-to-text probe backend."""

from __future__ import annotations

from collections import deque
import struct
from typing import Any

from ..audio.capture import AudioFrame
from .transcriber import TranscriptSegment


def _load_moonshine_api() -> tuple[type[Any], type[Any], Any]:
    try:
        from moonshine_voice import TranscriptEventListener, Transcriber, get_model_for_language
    except ImportError as exc:
        raise ValueError("moonshine-voice is not installed") from exc

    return TranscriptEventListener, Transcriber, get_model_for_language


def _pcm_s16le_to_float_samples(frame: AudioFrame) -> list[float]:
    sample_bytes = frame.pcm_s16le[: (len(frame.pcm_s16le) // 2) * 2]
    return [sample / 32768.0 for (sample,) in struct.iter_unpack("<h", sample_bytes)]


class MoonshineSpeechTranscriber:
    """Feed PCM frames into Moonshine and emit completed transcript segments."""

    def __init__(self, *, language: str = "en") -> None:
        self.language = language
        self._segments: deque[TranscriptSegment] = deque()
        self._started = False
        self._closed = False

        try:
            transcript_event_listener, transcriber_cls, get_model_for_language = _load_moonshine_api()
            model_path, model_arch = get_model_for_language(language)
            self.backend = transcriber_cls(model_path=model_path, model_arch=model_arch)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"moonshine STT backend failed to initialize: {exc}") from exc

        parent = self

        class _Listener(transcript_event_listener):
            def on_line_completed(self, event) -> None:
                line = getattr(event, "line", None)
                text = getattr(line, "text", "").strip()
                if not text:
                    return
                parent._segments.append(TranscriptSegment(text=text, confidence=1.0, is_final=True))

        self._listener = _Listener()
        self.backend.add_listener(self._listener)

    def process_frame(self, frame: AudioFrame) -> TranscriptSegment | None:
        if self._closed:
            raise ValueError("moonshine STT backend is already closed")
        if frame.sample_format != "s16le" or not frame.pcm_s16le:
            return None

        if not self._started:
            try:
                self.backend.start()
            except Exception as exc:
                raise ValueError(f"moonshine STT backend failed to start: {exc}") from exc
            self._started = True

        audio_data = _pcm_s16le_to_float_samples(frame)
        if not audio_data:
            return None

        try:
            self.backend.add_audio(audio_data, frame.sample_rate_hz)
        except Exception as exc:
            raise ValueError(f"moonshine STT backend failed during transcription: {exc}") from exc
        return self._pop_segment()

    def finish(self) -> list[TranscriptSegment]:
        if self._closed:
            return []
        if self._started:
            try:
                self.backend.stop()
            except Exception as exc:
                raise ValueError(f"moonshine STT backend failed to stop: {exc}") from exc
            self._started = False
        return self._drain_segments()

    def close(self) -> None:
        if self._closed:
            return
        if self._started:
            try:
                self.backend.stop()
            except Exception:
                pass
            self._started = False
        close_backend = getattr(self.backend, "close", None)
        if callable(close_backend):
            try:
                close_backend()
            except Exception:
                pass
        self._closed = True

    def _drain_segments(self) -> list[TranscriptSegment]:
        segments = list(self._segments)
        self._segments.clear()
        return segments

    def _pop_segment(self) -> TranscriptSegment | None:
        if not self._segments:
            return None
        return self._segments.popleft()
