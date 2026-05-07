"""Repo-local voice-loop config inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

from ..wakeword.assets import find_existing_wakeword_model_path


@dataclass(slots=True, frozen=True)
class EffectiveVoiceLoopConfig:
    wakeword_threshold: float
    wakeword_threshold_source: str
    wakeword_model: str | None
    wakeword_model_source: str
    wakeword_mode: str
    wakeword_auto_model_path: str | None
    voice_loop_max_frames: int | None
    voice_loop_max_frames_source: str
    voice_loop_max_commands: int | None
    voice_loop_max_commands_source: str
    passthrough_args: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "passthrough_args": list(self.passthrough_args),
            "voice_loop_max_commands": self.voice_loop_max_commands,
            "voice_loop_max_commands_source": self.voice_loop_max_commands_source,
            "voice_loop_max_frames": self.voice_loop_max_frames,
            "voice_loop_max_frames_source": self.voice_loop_max_frames_source,
            "wakeword_auto_model_path": self.wakeword_auto_model_path,
            "wakeword_mode": self.wakeword_mode,
            "wakeword_model": self.wakeword_model,
            "wakeword_model_source": self.wakeword_model_source,
            "wakeword_threshold": self.wakeword_threshold,
            "wakeword_threshold_source": self.wakeword_threshold_source,
        }


@dataclass(slots=True, frozen=True)
class VoiceLoopConfigSnapshot:
    launcher_mode: str
    explicit_args_file: str | None
    search_paths: list[str]
    selected_args_file: str | None
    configured_args: list[str]
    effective: EffectiveVoiceLoopConfig

    @property
    def config_available(self) -> bool:
        return self.selected_args_file is not None

    @property
    def status(self) -> str:
        return "ok" if self.config_available else "warn"

    @property
    def message(self) -> str:
        if self.config_available:
            return "Using selected voice-loop args file."
        return "No voice-loop args file found; using launcher defaults."

    def to_dict(self) -> dict[str, object]:
        return {
            "config_available": self.config_available,
            "configured_args": list(self.configured_args),
            "effective": self.effective.to_dict(),
            "explicit_args_file": self.explicit_args_file,
            "launcher_mode": self.launcher_mode,
            "message": self.message,
            "search_paths": list(self.search_paths),
            "selected_args_file": self.selected_args_file,
            "status": self.status,
        }


def build_voice_loop_config_snapshot(
    *,
    env: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    explicit_args_file: Path | None = None,
) -> VoiceLoopConfigSnapshot:
    root = Path.cwd() if repo_root is None else repo_root
    search_paths = _repo_local_voice_loop_args_candidate_paths(env=env, repo_root=root)
    explicit_path = explicit_args_file.expanduser() if explicit_args_file is not None else None
    selected_args_path = _select_voice_loop_args_path(search_paths, explicit_args_file=explicit_path)
    configured_args = _read_voice_loop_args(selected_args_path)

    return VoiceLoopConfigSnapshot(
        launcher_mode="repo_local",
        explicit_args_file=str(explicit_path) if explicit_path is not None else None,
        search_paths=[str(path) for path in search_paths],
        selected_args_file=str(selected_args_path) if selected_args_path is not None else None,
        configured_args=configured_args,
        effective=_resolve_effective_voice_loop_config(configured_args, env=env),
    )


def _repo_local_voice_loop_args_candidate_paths(
    *,
    env: Mapping[str, str] | None,
    repo_root: Path,
) -> list[Path]:
    source = dict(os.environ)
    source.update(env or {})
    if env is not None and "HOME" in env:
        home_path = Path(env["HOME"]).expanduser()
    else:
        home_path = Path(source.get("HOME", str(Path.home()))).expanduser()

    if env is not None and "XDG_CONFIG_HOME" in env:
        config_home = Path(env["XDG_CONFIG_HOME"]).expanduser()
    elif env is not None and "HOME" in env:
        config_home = home_path / ".config"
    else:
        config_home = Path(source.get("XDG_CONFIG_HOME", str(home_path / ".config"))).expanduser()

    paths = [
        repo_root / ".operance" / "voice-loop.args",
        config_home / "operance" / "voice-loop.args",
    ]
    return paths


def _select_voice_loop_args_path(
    candidate_paths: list[Path],
    *,
    explicit_args_file: Path | None,
) -> Path | None:
    if explicit_args_file is not None:
        return explicit_args_file if explicit_args_file.exists() else None
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    return None


def _read_voice_loop_args(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []

    args: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        args.append(stripped)
    return args


def _resolve_effective_voice_loop_config(
    configured_args: list[str],
    *,
    env: Mapping[str, str] | None,
) -> EffectiveVoiceLoopConfig:
    wakeword_threshold = 0.6
    wakeword_threshold_source = "default"
    wakeword_model: str | None = None
    wakeword_model_source = "default"
    voice_loop_max_frames: int | None = None
    voice_loop_max_frames_source = "default"
    voice_loop_max_commands: int | None = None
    voice_loop_max_commands_source = "default"
    passthrough_args: list[str] = []

    index = 0
    while index < len(configured_args):
        token = configured_args[index]
        if token == "--wakeword-threshold" and index + 1 < len(configured_args):
            try:
                wakeword_threshold = float(configured_args[index + 1])
                wakeword_threshold_source = "args_file"
                index += 2
                continue
            except ValueError:
                pass
        if token == "--wakeword-model" and index + 1 < len(configured_args):
            wakeword_model = configured_args[index + 1]
            wakeword_model_source = "args_file"
            index += 2
            continue
        if token == "--voice-loop-max-frames" and index + 1 < len(configured_args):
            try:
                voice_loop_max_frames = int(configured_args[index + 1])
                voice_loop_max_frames_source = "args_file"
                index += 2
                continue
            except ValueError:
                pass
        if token == "--voice-loop-max-commands" and index + 1 < len(configured_args):
            try:
                voice_loop_max_commands = int(configured_args[index + 1])
                voice_loop_max_commands_source = "args_file"
                index += 2
                continue
            except ValueError:
                pass
        passthrough_args.append(token)
        index += 1

    auto_model_path = None
    wakeword_mode = "energy_fallback"
    if wakeword_model == "auto":
        wakeword_mode = "auto_model"
        auto_model = find_existing_wakeword_model_path(env)
        auto_model_path = str(auto_model) if auto_model is not None else None
    elif wakeword_model:
        wakeword_mode = "custom_model"

    return EffectiveVoiceLoopConfig(
        wakeword_threshold=wakeword_threshold,
        wakeword_threshold_source=wakeword_threshold_source,
        wakeword_model=wakeword_model,
        wakeword_model_source=wakeword_model_source,
        wakeword_mode=wakeword_mode,
        wakeword_auto_model_path=auto_model_path,
        voice_loop_max_frames=voice_loop_max_frames,
        voice_loop_max_frames_source=voice_loop_max_frames_source,
        voice_loop_max_commands=voice_loop_max_commands,
        voice_loop_max_commands_source=voice_loop_max_commands_source,
        passthrough_args=passthrough_args,
    )
