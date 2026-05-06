def test_energy_wakeword_detector_detects_loud_frame_after_activation_streak() -> None:
    from operance.audio.capture import AudioFrame
    from operance.wakeword import EnergyWakeWordDetector

    detector = EnergyWakeWordDetector(phrase="operance", threshold=0.5)
    frame = AudioFrame(
        sample_rate_hz=16000,
        channels=1,
        sample_count=4,
        pcm_s16le=b"\xff\x7f" * 4,
    )

    first = detector.process_frame(frame)
    detection = detector.process_frame(frame)

    assert first is None
    assert detection is not None
    assert detection.phrase == "operance"
    assert detection.confidence == 1.0


def test_energy_wakeword_detector_ignores_single_clipped_spike_frame() -> None:
    import struct

    from operance.audio.capture import AudioFrame
    from operance.wakeword import EnergyWakeWordDetector

    detector = EnergyWakeWordDetector(phrase="operance", threshold=0.5, activation_frames=1)
    pcm_s16le = struct.pack("<1600h", 32767, *([0] * 1599))
    frame = AudioFrame(
        sample_rate_hz=16000,
        channels=1,
        sample_count=1600,
        pcm_s16le=pcm_s16le,
    )

    detection = detector.process_frame(frame)

    assert detection is None


def test_energy_wakeword_detector_respects_cooldown() -> None:
    from operance.audio.capture import AudioFrame
    from operance.wakeword import EnergyWakeWordDetector

    detector = EnergyWakeWordDetector(phrase="operance", threshold=0.5, cooldown_frames=2)
    loud_frame = AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\xff\x7f" * 4)

    first = detector.process_frame(loud_frame)
    second = detector.process_frame(loud_frame)
    third = detector.process_frame(loud_frame)
    fourth = detector.process_frame(loud_frame)
    fifth = detector.process_frame(loud_frame)
    sixth = detector.process_frame(loud_frame)

    assert first is None
    assert second is not None
    assert third is None
    assert fourth is None
    assert fifth is None
    assert sixth is not None


def test_run_wakeword_probe_reports_detected_frames() -> None:
    from operance.audio.capture import AudioFrame
    from operance.voice.probe import run_wakeword_probe
    from operance.wakeword import EnergyWakeWordDetector

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\xff\x7f" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\xff\x7f" * 4)

    result = run_wakeword_probe(
        FakeCaptureSource(),
        EnergyWakeWordDetector(phrase="operance", threshold=0.5),
        max_frames=3,
    )

    assert result["processed_frames"] == 3
    assert len(result["detections"]) == 1
    assert result["detections"][0]["frame_index"] == 3
    assert result["detections"][0]["phrase"] == "operance"


def test_suggest_energy_wakeword_threshold_respects_floor_and_margin() -> None:
    from operance.wakeword.energy import suggest_energy_wakeword_threshold

    assert suggest_energy_wakeword_threshold(0.31) == 0.6
    assert suggest_energy_wakeword_threshold(0.73) == 0.83


def test_suggest_energy_wakeword_threshold_caps_high_ambient_noise() -> None:
    from operance.wakeword.energy import suggest_energy_wakeword_threshold

    assert suggest_energy_wakeword_threshold(0.92) == 0.95


def test_run_wakeword_calibration_reports_detector_confidence_and_peak_reference() -> None:
    import struct

    from operance.audio.capture import AudioFrame
    from operance.voice.probe import run_wakeword_calibration

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield AudioFrame(
                sample_rate_hz=16000,
                channels=1,
                sample_count=4,
                pcm_s16le=struct.pack("<hhhh", 0, 1000, -2000, 5000),
            )
            yield AudioFrame(
                sample_rate_hz=16000,
                channels=1,
                sample_count=4,
                pcm_s16le=struct.pack("<hhhh", 0, 8000, -16000, 26000),
            )

    result = run_wakeword_calibration(FakeCaptureSource(), max_frames=2)

    assert result == {
        "ambient_detector_confidence": 0.793,
        "ambient_peak_confidence": 0.793,
        "base_threshold": 0.6,
        "processed_frames": 2,
        "suggested_threshold": 0.893,
    }


def test_run_wakeword_idle_evaluation_reports_false_activation_rate() -> None:
    from operance.audio.capture import AudioFrame
    from operance.voice.probe import run_wakeword_idle_evaluation
    from operance.wakeword import EnergyWakeWordDetector

    class FakeCaptureSource:
        def frames(self, *, max_frames: int | None = None):
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\xff\x7f" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\xff\x7f" * 4)
            yield AudioFrame(sample_rate_hz=16000, channels=1, sample_count=4, pcm_s16le=b"\x00\x00" * 4)

    result = run_wakeword_idle_evaluation(
        FakeCaptureSource(),
        EnergyWakeWordDetector(phrase="operance", threshold=0.5),
        max_frames=4,
    )

    assert result == {
        "activation_frames": 2,
        "current_threshold": 0.5,
        "detection_count": 1,
        "detections": [
            {
                "confidence": 1.0,
                "detection_id": result["detections"][0]["detection_id"],
                "frame_index": 3,
                "phrase": "operance",
                "timestamp": result["detections"][0]["timestamp"],
            }
        ],
        "idle_false_activation_rate": 0.25,
        "max_detection_confidence": 1.0,
        "processed_frames": 4,
        "suggested_threshold": 0.95,
        "suggested_voice_loop_config_command": "./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.95",
    }


def test_build_default_wakeword_detector_falls_back_to_energy_without_model_path() -> None:
    from operance.wakeword import EnergyWakeWordDetector, build_default_wakeword_detector

    detector = build_default_wakeword_detector(phrase="operance", threshold=0.5)

    assert isinstance(detector, EnergyWakeWordDetector)


def test_find_existing_wakeword_model_path_ignores_unrelated_path(tmp_path, monkeypatch) -> None:
    from operance.wakeword.assets import find_existing_wakeword_model_path

    monkeypatch.chdir(tmp_path)
    home_dir = tmp_path / "home"
    unrelated_model_dir = home_dir / ".config" / "archived-app" / "wakeword"
    unrelated_model_dir.mkdir(parents=True)
    unrelated_model_path = unrelated_model_dir / "operance.onnx"
    unrelated_model_path.write_bytes(b"model")

    assert find_existing_wakeword_model_path({"HOME": str(home_dir)}) is None


def test_build_default_wakeword_detector_uses_openwakeword_with_model_path(tmp_path, monkeypatch) -> None:
    from operance.audio.capture import AudioFrame
    from operance.wakeword import OpenWakeWordDetector, build_default_wakeword_detector

    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    class FakeNumpy:
        int16 = "int16"

        @staticmethod
        def frombuffer(payload: bytes, dtype: object) -> tuple[bytes, object]:
            return (payload, dtype)

    class FakeModel:
        def __init__(self, *, wakeword_models: list[str]) -> None:
            self.wakeword_models = wakeword_models
            self.frames: list[object] = []

        def predict(self, frame) -> dict[str, float]:
            self.frames.append(frame)
            return {"operance": 0.91}

    monkeypatch.setattr(
        "operance.wakeword.openwakeword._load_openwakeword_api",
        lambda: (FakeNumpy, FakeModel),
    )

    detector = build_default_wakeword_detector(
        phrase="operance",
        threshold=0.5,
        model_path=str(model_path),
    )

    assert isinstance(detector, OpenWakeWordDetector)

    detection = detector.process_frame(
        AudioFrame(
            sample_rate_hz=16000,
            channels=1,
            sample_count=4,
            pcm_s16le=b"\x01\x00\x02\x00\x03\x00\x04\x00",
        )
    )

    assert detection is not None
    assert detection.phrase == "operance"
    assert detection.confidence == 0.91
    assert detector.backend.wakeword_models == [str(model_path)]
    assert detector.backend.frames == [(b"\x01\x00\x02\x00\x03\x00\x04\x00", "int16")]


def test_build_default_wakeword_detector_raises_when_openwakeword_is_missing(tmp_path, monkeypatch) -> None:
    from operance.wakeword import build_default_wakeword_detector

    model_path = tmp_path / "operance.onnx"
    model_path.write_bytes(b"model")

    monkeypatch.setattr(
        "operance.wakeword.openwakeword._load_openwakeword_api",
        lambda: (_ for _ in ()).throw(ValueError("openwakeword is not installed")),
    )

    try:
        build_default_wakeword_detector(model_path=str(model_path))
    except ValueError as exc:
        assert str(exc) == "openwakeword is not installed"
    else:
        raise AssertionError("expected ValueError")
