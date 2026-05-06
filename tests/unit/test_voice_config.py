from __future__ import annotations

from pathlib import Path


def test_build_voice_loop_config_snapshot_defaults_without_args_file(tmp_path: Path) -> None:
    from operance.voice.config import build_voice_loop_config_snapshot

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    snapshot = build_voice_loop_config_snapshot(
        env={"HOME": str(home_dir)},
        repo_root=repo_root,
    )

    assert snapshot.to_dict() == {
        "config_available": False,
        "configured_args": [],
        "effective": {
            "passthrough_args": [],
            "voice_loop_max_commands": None,
            "voice_loop_max_commands_source": "default",
            "voice_loop_max_frames": None,
            "voice_loop_max_frames_source": "default",
            "wakeword_auto_model_path": None,
            "wakeword_mode": "energy_fallback",
            "wakeword_model": None,
            "wakeword_model_source": "default",
            "wakeword_threshold": 0.6,
            "wakeword_threshold_source": "default",
        },
        "explicit_args_file": None,
        "launcher_mode": "repo_local",
        "message": "No voice-loop args file found; using launcher defaults.",
        "search_paths": [
            str(repo_root / ".operance" / "voice-loop.args"),
            str(home_dir / ".config" / "operance" / "voice-loop.args"),
        ],
        "selected_args_file": None,
        "status": "warn",
    }


def test_build_voice_loop_config_snapshot_prefers_repo_args_file_and_parses_known_flags(tmp_path: Path) -> None:
    from operance.voice.config import build_voice_loop_config_snapshot

    repo_root = tmp_path / "repo"
    repo_args_dir = repo_root / ".operance"
    repo_args_dir.mkdir(parents=True)
    repo_args_path = repo_args_dir / "voice-loop.args"
    repo_args_path.write_text(
        "\n".join(
            [
                "--wakeword-threshold",
                "0.95",
                "--wakeword-model",
                "auto",
                "--voice-loop-max-commands",
                "3",
                "--voice-session-tts-play",
                "",
            ]
        ),
        encoding="utf-8",
    )
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    snapshot = build_voice_loop_config_snapshot(
        env={"HOME": str(home_dir)},
        repo_root=repo_root,
    )

    assert snapshot.to_dict() == {
        "config_available": True,
        "configured_args": [
            "--wakeword-threshold",
            "0.95",
            "--wakeword-model",
            "auto",
            "--voice-loop-max-commands",
            "3",
            "--voice-session-tts-play",
        ],
        "effective": {
            "passthrough_args": ["--voice-session-tts-play"],
            "voice_loop_max_commands": 3,
            "voice_loop_max_commands_source": "args_file",
            "voice_loop_max_frames": None,
            "voice_loop_max_frames_source": "default",
            "wakeword_auto_model_path": None,
            "wakeword_mode": "auto_model",
            "wakeword_model": "auto",
            "wakeword_model_source": "args_file",
            "wakeword_threshold": 0.95,
            "wakeword_threshold_source": "args_file",
        },
        "explicit_args_file": None,
        "launcher_mode": "repo_local",
        "message": "Using selected voice-loop args file.",
        "search_paths": [
            str(repo_args_path),
            str(home_dir / ".config" / "operance" / "voice-loop.args"),
        ],
        "selected_args_file": str(repo_args_path),
        "status": "ok",
    }


def test_build_voice_loop_config_snapshot_supports_explicit_args_file(tmp_path: Path) -> None:
    from operance.voice.config import build_voice_loop_config_snapshot

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    explicit_args_path = tmp_path / "explicit.args"
    explicit_args_path.write_text("--voice-loop-max-frames\n12\n", encoding="utf-8")

    snapshot = build_voice_loop_config_snapshot(
        env={"HOME": str(home_dir)},
        repo_root=repo_root,
        explicit_args_file=explicit_args_path,
    )

    assert snapshot.to_dict()["selected_args_file"] == str(explicit_args_path)
    assert snapshot.to_dict()["effective"]["voice_loop_max_frames"] == 12
    assert snapshot.to_dict()["effective"]["voice_loop_max_frames_source"] == "args_file"


def test_build_voice_loop_config_snapshot_ignores_unrelated_config(tmp_path: Path) -> None:
    from operance.voice.config import build_voice_loop_config_snapshot

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    home_dir = tmp_path / "home"
    unrelated_config_dir = home_dir / ".config" / "archived-app"
    unrelated_config_dir.mkdir(parents=True)
    unrelated_args_path = unrelated_config_dir / "voice-loop.args"
    unrelated_args_path.write_text("--wakeword-threshold\n0.844\n", encoding="utf-8")

    snapshot = build_voice_loop_config_snapshot(
        env={"HOME": str(home_dir)},
        repo_root=repo_root,
    )

    assert snapshot.to_dict() == {
        "config_available": False,
        "configured_args": [],
        "effective": {
            "passthrough_args": [],
            "voice_loop_max_commands": None,
            "voice_loop_max_commands_source": "default",
            "voice_loop_max_frames": None,
            "voice_loop_max_frames_source": "default",
            "wakeword_auto_model_path": None,
            "wakeword_mode": "energy_fallback",
            "wakeword_model": None,
            "wakeword_model_source": "default",
            "wakeword_threshold": 0.6,
            "wakeword_threshold_source": "default",
        },
        "explicit_args_file": None,
        "launcher_mode": "repo_local",
        "message": "No voice-loop args file found; using launcher defaults.",
        "search_paths": [
            str(repo_root / ".operance" / "voice-loop.args"),
            str(home_dir / ".config" / "operance" / "voice-loop.args"),
        ],
        "selected_args_file": None,
        "status": "warn",
    }
