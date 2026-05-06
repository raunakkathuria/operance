"""Voice probe helpers that consume captured audio frames."""

from __future__ import annotations

from pathlib import Path

from ..audio.capture import AudioCaptureSource
from ..stt import SpeechTranscriber
from ..tts import SpeechSynthesizer
from ..wakeword.energy import frame_energy_confidence, frame_peak_confidence, suggest_energy_wakeword_threshold
from ..wakeword import WakeWordDetector


def run_wakeword_probe(
    capture_source: AudioCaptureSource,
    detector: WakeWordDetector,
    *,
    max_frames: int,
) -> dict[str, object]:
    detections: list[dict[str, object]] = []
    processed_frames = 0

    for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
        processed_frames = frame_index
        detection = detector.process_frame(frame)
        if detection is None:
            continue

        payload = detection.to_dict()
        payload["frame_index"] = frame_index
        detections.append(payload)

    return {
        "processed_frames": processed_frames,
        "detections": detections,
    }


def run_wakeword_idle_evaluation(
    capture_source: AudioCaptureSource,
    detector: WakeWordDetector,
    *,
    max_frames: int,
) -> dict[str, object]:
    detections: list[dict[str, object]] = []
    processed_frames = 0
    max_detection_confidence = 0.0

    for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
        processed_frames = frame_index
        detection = detector.process_frame(frame)
        if detection is None:
            continue

        payload = detection.to_dict()
        payload["frame_index"] = frame_index
        detections.append(payload)
        confidence = float(payload.get("confidence", 0.0))
        if confidence > max_detection_confidence:
            max_detection_confidence = confidence

    false_activation_rate = round(len(detections) / processed_frames, 3) if processed_frames else 0.0
    result: dict[str, object] = {
        "processed_frames": processed_frames,
        "detection_count": len(detections),
        "idle_false_activation_rate": false_activation_rate,
        "detections": detections,
    }
    activation_frames = getattr(detector, "activation_frames", None)
    if isinstance(activation_frames, int) and activation_frames > 1:
        result["activation_frames"] = activation_frames
    threshold = getattr(detector, "threshold", None)
    if isinstance(threshold, int | float):
        rounded_threshold = round(float(threshold), 3)
        result["current_threshold"] = rounded_threshold
        if detections:
            rounded_max_confidence = round(max_detection_confidence, 3)
            suggested_threshold = suggest_energy_wakeword_threshold(
                rounded_max_confidence,
                base_threshold=rounded_threshold,
            )
            result["max_detection_confidence"] = rounded_max_confidence
            result["suggested_threshold"] = suggested_threshold
            result["suggested_voice_loop_config_command"] = (
                "./scripts/update_voice_loop_user_config.sh "
                f"--wakeword-threshold {suggested_threshold}"
            )
    return result


def run_wakeword_calibration(
    capture_source: AudioCaptureSource,
    *,
    max_frames: int,
    base_threshold: float = 0.6,
) -> dict[str, object]:
    processed_frames = 0
    ambient_detector_confidence = 0.0
    ambient_peak_confidence = 0.0

    for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
        processed_frames = frame_index
        if frame.sample_format != "s16le" or not frame.pcm_s16le:
            continue

        detector_confidence = frame_energy_confidence(frame.pcm_s16le)
        if detector_confidence > ambient_detector_confidence:
            ambient_detector_confidence = detector_confidence
        peak_confidence = frame_peak_confidence(frame.pcm_s16le)
        if peak_confidence > ambient_peak_confidence:
            ambient_peak_confidence = peak_confidence

    rounded_ambient_detector = round(ambient_detector_confidence, 3)
    rounded_ambient_peak = round(ambient_peak_confidence, 3)
    return {
        "ambient_detector_confidence": rounded_ambient_detector,
        "processed_frames": processed_frames,
        "ambient_peak_confidence": rounded_ambient_peak,
        "base_threshold": round(base_threshold, 3),
        "suggested_threshold": suggest_energy_wakeword_threshold(
            rounded_ambient_detector,
            base_threshold=base_threshold,
        ),
    }


def run_stt_probe(
    capture_source: AudioCaptureSource,
    transcriber: SpeechTranscriber,
    *,
    max_frames: int,
) -> dict[str, object]:
    segments: list[dict[str, object]] = []
    processed_frames = 0

    try:
        for frame_index, frame in enumerate(capture_source.frames(max_frames=max_frames), start=1):
            processed_frames = frame_index
            segment = transcriber.process_frame(frame)
            if segment is None:
                continue

            payload = segment.to_dict()
            payload["frame_index"] = frame_index
            segments.append(payload)

        for segment in transcriber.finish():
            payload = segment.to_dict()
            payload["frame_index"] = processed_frames
            segments.append(payload)
    finally:
        transcriber.close()

    return {
        "processed_frames": processed_frames,
        "segments": segments,
    }


def run_tts_probe(
    synthesizer: SpeechSynthesizer,
    text: str,
    *,
    output_path: Path | None = None,
) -> dict[str, object]:
    audio = synthesizer.synthesize(text)
    if output_path is not None:
        synthesizer.save(audio, output_path)

    return {
        "duration_seconds": audio.duration_seconds,
        "output_path": str(output_path) if output_path is not None else None,
        "sample_count": audio.sample_count,
        "sample_rate_hz": audio.sample_rate_hz,
        "text": audio.text,
        "voice": audio.voice,
    }
