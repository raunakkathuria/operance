"""Shared TTS asset discovery helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def tts_model_candidate_paths(env: Mapping[str, str] | None = None) -> list[Path]:
    source = _env_source(env)
    home_path = Path(source.get("HOME", str(Path.home()))).expanduser()
    config_home = Path(source.get("XDG_CONFIG_HOME", str(home_path / ".config"))).expanduser()
    paths: list[Path] = []
    if source.get("OPERANCE_TTS_MODEL"):
        paths.append(Path(source["OPERANCE_TTS_MODEL"]).expanduser())
    paths.extend(
        [
            Path.cwd() / ".operance" / "tts" / "kokoro.onnx",
            config_home / "operance" / "tts" / "kokoro.onnx",
            Path("/etc/operance/tts/kokoro.onnx"),
        ]
    )
    return _dedupe_paths(paths)


def tts_voices_candidate_paths(env: Mapping[str, str] | None = None) -> list[Path]:
    source = _env_source(env)
    home_path = Path(source.get("HOME", str(Path.home()))).expanduser()
    config_home = Path(source.get("XDG_CONFIG_HOME", str(home_path / ".config"))).expanduser()
    paths: list[Path] = []
    if source.get("OPERANCE_TTS_VOICES"):
        paths.append(Path(source["OPERANCE_TTS_VOICES"]).expanduser())
    paths.extend(
        [
            Path.cwd() / ".operance" / "tts" / "voices.bin",
            config_home / "operance" / "tts" / "voices.bin",
            Path("/etc/operance/tts/voices.bin"),
        ]
    )
    return _dedupe_paths(paths)


def find_existing_tts_model_path(env: Mapping[str, str] | None = None) -> Path | None:
    return _find_existing_path(tts_model_candidate_paths(env))


def find_existing_tts_voices_path(env: Mapping[str, str] | None = None) -> Path | None:
    return _find_existing_path(tts_voices_candidate_paths(env))


def preferred_tts_model_path(env: Mapping[str, str] | None = None) -> Path:
    return _preferred_path(tts_model_candidate_paths(env))


def preferred_tts_voices_path(env: Mapping[str, str] | None = None) -> Path:
    return _preferred_path(tts_voices_candidate_paths(env))


def _env_source(env: Mapping[str, str] | None) -> dict[str, str]:
    source = dict(os.environ)
    source.update(env or {})
    return source


def _find_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _preferred_path(paths: list[Path]) -> Path:
    existing = _find_existing_path(paths)
    if existing is not None:
        return existing
    return paths[0]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped
