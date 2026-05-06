from io import BytesIO
import subprocess


def test_audio_input_device_serializes_to_dict() -> None:
    from operance.audio.capture import AudioInputDevice

    device = AudioInputDevice(device_id="42", name="alsa_input.usb-mic", is_default=True, backend="pactl")

    payload = device.to_dict()

    assert payload == {
        "device_id": "42",
        "name": "alsa_input.usb-mic",
        "is_default": True,
        "backend": "pactl",
    }


def test_linux_audio_capture_source_lists_input_devices_from_pactl() -> None:
    from operance.audio.linux import LinuxAudioCaptureSource

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command == ["pactl", "get-default-source"]:
            return subprocess.CompletedProcess(command, 0, stdout="alsa_input.usb-mic\n", stderr="")
        if command == ["pactl", "list", "short", "sources"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    "42\talsa_input.usb-mic\tPipeWire\ts16le 1ch 16000Hz\tRUNNING\n"
                    "99\talsa_output.pci.monitor\tPipeWire\ts16le 2ch 48000Hz\tIDLE\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    source = LinuxAudioCaptureSource(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "pactl" else None,
    )

    devices = source.list_input_devices()

    assert [device.to_dict() for device in devices] == [
        {
            "device_id": "42",
            "name": "alsa_input.usb-mic",
            "is_default": True,
            "backend": "pactl",
        }
    ]
    assert commands == [
        ["pactl", "get-default-source"],
        ["pactl", "list", "short", "sources"],
    ]


def test_linux_audio_capture_source_falls_back_to_default_device_when_pactl_is_unavailable() -> None:
    from operance.audio.linux import LinuxAudioCaptureSource

    commands: list[list[str]] = []

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="connection refused")

    source = LinuxAudioCaptureSource(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name in {"pactl", "pw-record"} else None,
    )

    devices = source.list_input_devices()

    assert [device.to_dict() for device in devices] == [
        {
            "device_id": "default",
            "name": "default",
            "is_default": True,
            "backend": "pw-record",
        }
    ]
    assert commands == [
        ["pactl", "get-default-source"],
        ["pactl", "list", "short", "sources"],
    ]


def test_linux_audio_capture_source_yields_frame_metadata_from_pw_record() -> None:
    from operance.audio.linux import LinuxAudioCaptureSource

    commands: list[list[str]] = []

    class FakeProcess:
        def __init__(self, payload: bytes) -> None:
            self.stdout = BytesIO(payload)
            self._returncode: int | None = None

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self._returncode = 0
            return 0

        def kill(self) -> None:
            self._returncode = -9

    def open_process(command: list[str]) -> FakeProcess:
        commands.append(command)
        return FakeProcess(b"\x00" * 6400)

    source = LinuxAudioCaptureSource(
        open_process=open_process,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "pw-record" else None,
        device_name="alsa_input.usb-mic",
    )

    frames = list(source.frames(max_frames=2))

    assert commands == [[
        "pw-record",
        "--target",
        "alsa_input.usb-mic",
        "--rate",
        "16000",
        "--channels",
        "1",
        "--format",
        "s16",
        "-",
    ]]
    assert [frame.sample_count for frame in frames] == [1600, 1600]
    assert [frame.channels for frame in frames] == [1, 1]
    assert [frame.sample_rate_hz for frame in frames] == [16000, 16000]
    assert [frame.sample_format for frame in frames] == ["s16le", "s16le"]
    assert [frame.source for frame in frames] == ["alsa_input.usb-mic", "alsa_input.usb-mic"]
    assert [len(frame.pcm_s16le) for frame in frames] == [3200, 3200]
