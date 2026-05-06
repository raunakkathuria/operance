from pathlib import Path
import subprocess

import pytest


def test_build_default_audio_playback_sink_uses_linux_backend() -> None:
    from operance.audio import build_default_audio_playback_sink
    from operance.audio.linux_playback import LinuxAudioPlaybackSink

    sink = build_default_audio_playback_sink(system_name="Linux")

    assert isinstance(sink, LinuxAudioPlaybackSink)


def test_linux_audio_playback_sink_plays_file_with_pw_play(tmp_path: Path) -> None:
    from operance.audio.linux_playback import LinuxAudioPlaybackSink

    commands: list[list[str]] = []
    audio_path = tmp_path / "tts.wav"
    audio_path.write_text("fake-audio", encoding="utf-8")

    def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    sink = LinuxAudioPlaybackSink(
        run_command=run_command,
        resolve_executable=lambda name: f"/usr/bin/{name}" if name == "pw-play" else None,
    )

    sink.play_file(audio_path)

    assert commands == [["pw-play", str(audio_path)]]


def test_linux_audio_playback_sink_raises_when_backend_is_missing(tmp_path: Path) -> None:
    from operance.audio.linux_playback import LinuxAudioPlaybackSink

    sink = LinuxAudioPlaybackSink(resolve_executable=lambda name: None)

    with pytest.raises(ValueError, match="unable to find a supported Linux audio playback backend"):
        sink.play_file(tmp_path / "tts.wav")
