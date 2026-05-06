"""Audio capture and playback contracts."""

from __future__ import annotations

import platform

from .capture import AudioCaptureSource, AudioFrame, AudioInputDevice
from .linux import LinuxAudioCaptureSource
from .linux_playback import LinuxAudioPlaybackSink
from .playback import AudioPlaybackSink


def build_default_audio_capture_source(
    *,
    device_name: str | None = None,
    system_name: str | None = None,
) -> AudioCaptureSource:
    current_system = system_name or platform.system()
    if current_system == "Linux":
        return LinuxAudioCaptureSource(device_name=device_name)
    raise ValueError(f"unsupported audio capture platform: {current_system}")


def build_default_audio_playback_sink(
    *,
    system_name: str | None = None,
) -> AudioPlaybackSink:
    current_system = system_name or platform.system()
    if current_system == "Linux":
        return LinuxAudioPlaybackSink()
    raise ValueError(f"unsupported audio playback platform: {current_system}")


__all__ = [
    "AudioCaptureSource",
    "AudioPlaybackSink",
    "AudioFrame",
    "AudioInputDevice",
    "LinuxAudioCaptureSource",
    "LinuxAudioPlaybackSink",
    "build_default_audio_capture_source",
    "build_default_audio_playback_sink",
]
