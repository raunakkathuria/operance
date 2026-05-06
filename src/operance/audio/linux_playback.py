"""Linux audio playback helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Callable


RunCommand = Callable[[list[str]], subprocess.CompletedProcess[str]]
ResolveExecutable = Callable[[str], str | None]


def _default_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _default_resolve_executable(name: str) -> str | None:
    return shutil.which(name)


@dataclass(slots=True)
class LinuxAudioPlaybackSink:
    run_command: RunCommand = _default_run_command
    resolve_executable: ResolveExecutable = _default_resolve_executable

    def play_file(self, path: Path) -> None:
        command = self._play_command(path)
        result = self.run_command(command)
        if result.returncode == 0:
            return

        detail = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
        raise ValueError(f"Linux audio playback failed: {detail}")

    def _play_command(self, path: Path) -> list[str]:
        if self.resolve_executable("pw-play") is not None:
            return ["pw-play", str(path)]
        if self.resolve_executable("paplay") is not None:
            return ["paplay", str(path)]
        if self.resolve_executable("aplay") is not None:
            return ["aplay", str(path)]
        raise ValueError("unable to find a supported Linux audio playback backend")
