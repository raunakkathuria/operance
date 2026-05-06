import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from operance.support_bundle import write_support_bundle_artifact


def _read_bundle_members(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            payload[member.name] = extracted.read().decode("utf-8")
    return payload


def test_write_support_bundle_artifact_writes_expected_archive(monkeypatch, tmp_path: Path) -> None:
    snapshot = {
        "doctor": {"checks": [{"name": "linux_platform", "status": "ok"}]},
        "setup": {"summary_status": "ready"},
    }
    help_text = {
        "title": "Support snapshot",
        "summary": "ready",
        "highlights": ["Doctor warnings: none"],
        "details": "{}",
    }

    class _FakeVoiceLoopRuntimeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "status_file_path": "/home/test/.operance/voice-loop-status.json",
                "status_file_exists": True,
                "status": "ok",
                "message": "fresh",
            }

    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot",
        lambda env=None, redact=False, home_dir=None: snapshot,
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot_help_text",
        lambda value: help_text,
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_voice_loop_runtime_status_snapshot",
        lambda env=None: _FakeVoiceLoopRuntimeSnapshot(),
    )
    monkeypatch.setattr(
        "operance.support_bundle._read_user_service_log",
        lambda unit_name, *, lines=100: (
            f"{unit_name} /home/test/.config/operance/runtime.log",
            None,
        ),
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
    )

    result = write_support_bundle_artifact(
        output_path=tmp_path / "operance-support.tar.gz",
        env={"OPERANCE_DATA_DIR": str(tmp_path)},
        home_dir="/home/test",
    )

    members = _read_bundle_members(tmp_path / "operance-support.tar.gz")
    manifest = json.loads(members["manifest.json"])
    runtime = json.loads(members["voice-loop-runtime.json"])

    assert result["bundle_path"] == str(tmp_path / "operance-support.tar.gz")
    assert result["redacted"] is True
    assert result["warning_count"] == 0
    assert sorted(result["included_files"]) == [
        "logs/operance-tray.service.log",
        "logs/operance-voice-loop.service.log",
        "manifest.json",
        "support-help.json",
        "support-snapshot.json",
        "voice-loop-runtime.json",
    ]
    assert manifest["included_files"] == result["included_files"]
    assert manifest["warning_count"] == 0
    assert manifest["project"] == {
        "name": "operance",
        "version": "0.1.0",
        "version_source": "pyproject",
        "git_commit": "abc1234",
        "git_branch": "main",
        "git_dirty": False,
    }
    assert json.loads(members["support-snapshot.json"]) == snapshot
    assert json.loads(members["support-help.json"]) == help_text
    assert runtime["status_file_path"] == "~/.operance/voice-loop-status.json"
    assert "~/.config/operance/runtime.log" in members["logs/operance-tray.service.log"]


def test_write_support_bundle_artifact_records_log_warnings(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot",
        lambda env=None, redact=False, home_dir=None: {"doctor": {"checks": []}},
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot_help_text",
        lambda snapshot: {"title": "Support snapshot", "summary": "warn", "highlights": [], "details": "{}"},
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_voice_loop_runtime_status_snapshot",
        lambda env=None: type(
            "_Runtime",
            (),
            {"to_dict": lambda self: {"status_file_path": "/tmp/voice-loop-status.json", "status": "warn"}},
        )(),
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "0.1.0",
            "version_source": "pyproject",
            "git_commit": None,
            "git_branch": None,
            "git_dirty": None,
        },
    )

    def _read_log(unit_name: str, *, lines: int = 100) -> tuple[str | None, str | None]:
        if unit_name == "operance-tray.service":
            return None, "journalctl unavailable"
        return "voice-loop ok", None

    monkeypatch.setattr("operance.support_bundle._read_user_service_log", _read_log)

    result = write_support_bundle_artifact(
        output_path=tmp_path / "operance-support.tar.gz",
        env={"OPERANCE_DATA_DIR": str(tmp_path)},
    )

    members = _read_bundle_members(tmp_path / "operance-support.tar.gz")
    manifest = json.loads(members["manifest.json"])

    assert result["warning_count"] == 1
    assert result["warnings"] == ["operance-tray.service: journalctl unavailable"]
    assert "logs/operance-tray.service.log" not in members
    assert members["logs/operance-voice-loop.service.log"] == "voice-loop ok\n"
    assert manifest["project"]["version"] == "0.1.0"
    assert manifest["warnings"] == ["operance-tray.service: journalctl unavailable"]


def test_write_support_bundle_artifact_uses_versioned_default_filename(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot",
        lambda env=None, redact=False, home_dir=None: {"doctor": {"checks": []}},
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_support_snapshot_help_text",
        lambda snapshot: {"title": "Support snapshot", "summary": "ok", "highlights": [], "details": "{}"},
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_voice_loop_runtime_status_snapshot",
        lambda env=None: type("_Runtime", (), {"to_dict": lambda self: {"status": "ok"}})(),
    )
    monkeypatch.setattr(
        "operance.support_bundle.build_project_identity",
        lambda: {
            "name": "operance",
            "version": "1.2.3",
            "version_source": "pyproject",
            "git_commit": "abc1234",
            "git_branch": "main",
            "git_dirty": False,
        },
    )
    monkeypatch.setattr("operance.support_bundle.project_version", lambda: "1.2.3")
    monkeypatch.setattr(
        "operance.support_bundle._read_user_service_log",
        lambda unit_name, *, lines=100: (None, "no journal output"),
    )

    result = write_support_bundle_artifact(
        env={"OPERANCE_DATA_DIR": str(tmp_path)},
        now=datetime(2026, 5, 1, 1, 2, 3, tzinfo=timezone.utc),
    )

    assert result["bundle_path"] == str(
        tmp_path / "support-bundles" / "support-bundle-1.2.3-20260501T010203Z.tar.gz"
    )
