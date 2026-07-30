from __future__ import annotations

import json
from pathlib import Path

import pytest

from operance.skills import (
    SkillValidationError,
    build_skill_library_from_paths,
)


def _pack(skill_id: str, phrase: str, *, platforms: list[str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "skill_id": skill_id,
        "name": f"pack {skill_id}",
        "description": "test pack",
        "commands": [
            {
                "id": "open_docs",
                "phrases": [phrase],
                "actions": [{"tool": "apps.launch", "args": {"app": "firefox"}}],
            }
        ],
    }
    if platforms is not None:
        payload["platforms"] = platforms
    return payload


def _write(directory: Path, name: str, payload: dict[str, object]) -> None:
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def test_pack_declaring_other_platforms_does_not_match(tmp_path: Path) -> None:
    _write(tmp_path, "linux_only.json", _pack("pack.linux", "open docs", platforms=["linux"]))

    library = build_skill_library_from_paths([tmp_path], system_name="Windows")

    assert library.match("open docs") is None
    assert [pack.skill_id for pack in library.packs if library.pack_applies(pack)] == []


def test_pack_declaring_current_platform_matches(tmp_path: Path) -> None:
    _write(tmp_path, "linux_only.json", _pack("pack.linux", "open docs", platforms=["linux"]))

    library = build_skill_library_from_paths([tmp_path], system_name="Linux")

    matched = library.match("open docs")
    assert matched is not None
    assert matched.command_id == "open_docs"


def test_pack_without_platforms_matches_every_host(tmp_path: Path) -> None:
    _write(tmp_path, "any.json", _pack("pack.any", "open docs"))

    for system_name in ("Linux", "Windows", "Darwin", "FreeBSD"):
        library = build_skill_library_from_paths([tmp_path], system_name=system_name)
        assert library.match("open docs") is not None, system_name


def test_cross_pack_phrase_collision_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "a_first.json", _pack("pack.a", "open docs"))
    _write(tmp_path, "b_second.json", _pack("pack.b", "open docs"))

    library = build_skill_library_from_paths([tmp_path], system_name="Linux")

    assert any("pack.a" in warning and "pack.b" in warning for warning in library.warnings)
    assert library.to_dict()["status"] == "warn"
    assert library.to_dict()["warnings"] == list(library.warnings)


def test_malformed_pack_is_skipped_with_a_warning(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
    _write(tmp_path, "good.json", _pack("pack.good", "open docs"))

    library = build_skill_library_from_paths([tmp_path], system_name="Linux")

    assert library.match("open docs") is not None
    assert [pack.skill_id for pack in library.packs] == ["pack.good"]
    assert any("broken.json" in warning for warning in library.warnings)


def test_missing_pack_path_is_skipped_with_a_warning(tmp_path: Path) -> None:
    library = build_skill_library_from_paths([tmp_path / "absent.json"], system_name="Linux")

    assert library.packs == ()
    assert any("absent.json" in warning for warning in library.warnings)


def test_strict_loading_still_raises_for_validation_use(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(SkillValidationError):
        build_skill_library_from_paths([tmp_path], strict=True, system_name="Linux")


def test_daemon_starts_when_a_skill_pack_is_malformed(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon

    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_SKILL_PACKS": str(tmp_path),
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    assert daemon.intent_matcher.skill_library.warnings != ()


def test_inactive_packs_are_reported_but_not_counted_as_available(tmp_path: Path) -> None:
    _write(tmp_path, "linux_only.json", _pack("pack.linux", "open docs", platforms=["linux"]))

    payload = build_skill_library_from_paths([tmp_path], system_name="Windows").to_dict()

    assert payload["summary"]["pack_count"] == 0
    assert payload["summary"]["inactive_pack_count"] == 1
    assert payload["summary"]["platform_family"] == "windows"
    assert payload["packs"][0]["active"] is False
