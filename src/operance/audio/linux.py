"""Linux microphone discovery and frame capture helpers."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import BinaryIO, Callable, Protocol

from .capture import AudioFrame, AudioInputDevice


RunCommand = Callable[[list[str]], subprocess.CompletedProcess[str]]
ResolveExecutable = Callable[[str], str | None]


class CaptureProcess(Protocol):
    stdout: BinaryIO | None

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


OpenProcess = Callable[[list[str]], CaptureProcess]


def _default_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _default_resolve_executable(name: str) -> str | None:
    return shutil.which(name)


def _default_open_process(command: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


def _require_success(
    result: subprocess.CompletedProcess[str],
    *,
    command_label: str,
) -> subprocess.CompletedProcess[str]:
    if result.returncode == 0:
        return result

    detail = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
    raise ValueError(f"{command_label} failed: {detail}")


@dataclass(slots=True)
class LinuxAudioCaptureSource:
    device_name: str | None = None
    sample_rate_hz: int = 16000
    channels: int = 1
    frame_samples: int = 1600
    bytes_per_sample: int = 2
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable
    open_process: OpenProcess = _default_open_process

    def list_input_devices(self) -> list[AudioInputDevice]:
        if self.resolve_executable("pactl") is not None:
            try:
                default_source = self._default_source_name()
                result = _require_success(
                    self.run_command(["pactl", "list", "short", "sources"]),
                    command_label="pactl list short sources",
                )
                devices = _parse_pactl_sources(result.stdout, default_source)
                if devices:
                    return devices
            except ValueError:
                pass

        return [
            AudioInputDevice(
                device_id="default",
                name=self.device_name or "default",
                is_default=True,
                backend=self._capture_backend(),
            )
        ]

    def frames(self, *, max_frames: int | None = None) -> Iterable[AudioFrame]:
        if max_frames is not None and max_frames <= 0:
            return []

        command = self._capture_command()
        process = self.open_process(command)
        if process.stdout is None:
            raise ValueError("audio capture process did not expose stdout")

        bytes_per_frame = self.frame_samples * self.channels * self.bytes_per_sample
        yielded = 0

        try:
            while max_frames is None or yielded < max_frames:
                chunk = process.stdout.read(bytes_per_frame)
                if not chunk:
                    break

                sample_count = len(chunk) // (self.channels * self.bytes_per_sample)
                if sample_count <= 0:
                    continue

                yield AudioFrame(
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    sample_count=sample_count,
                    sample_format="s16le",
                    source=self.device_name or "microphone",
                    pcm_s16le=chunk,
                )
                yielded += 1
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)

    def _default_source_name(self) -> str | None:
        result = self.run_command(["pactl", "get-default-source"])
        if result.returncode != 0:
            return None

        value = result.stdout.strip()
        return value or None

    def _capture_command(self) -> list[str]:
        backend = self._capture_backend()
        if backend == "pw-record":
            command = [
                "pw-record",
                "--rate",
                str(self.sample_rate_hz),
                "--channels",
                str(self.channels),
                "--format",
                "s16",
                "-",
            ]
            if self.device_name:
                command[1:1] = ["--target", self.device_name]
            return command

        command = [
            "parecord",
            "--rate",
            str(self.sample_rate_hz),
            "--channels",
            str(self.channels),
            "--format",
            "s16le",
            "--raw",
            "-",
        ]
        if self.device_name:
            command.insert(1, f"--device={self.device_name}")
        return command

    def _capture_backend(self) -> str:
        if self.resolve_executable("pw-record") is not None:
            return "pw-record"
        if self.resolve_executable("parecord") is not None:
            return "parecord"
        raise ValueError("unable to find a supported Linux audio capture backend")


def _parse_pactl_sources(raw_output: str, default_source: str | None) -> list[AudioInputDevice]:
    devices: list[AudioInputDevice] = []

    for line in raw_output.splitlines():
        if not line.strip():
            continue

        fields = line.split("\t")
        if len(fields) < 2:
            continue

        device_id = fields[0].strip()
        name = fields[1].strip()
        if not device_id or not name or name.endswith(".monitor"):
            continue

        devices.append(
            AudioInputDevice(
                device_id=device_id,
                name=name,
                is_default=name == default_source,
                backend="pactl",
            )
        )

    if devices and not any(device.is_default for device in devices):
        first = devices[0]
        devices[0] = AudioInputDevice(
            device_id=first.device_id,
            name=first.name,
            is_default=True,
            backend=first.backend,
        )

    return devices
