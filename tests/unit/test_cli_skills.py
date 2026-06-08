import json

from operance.cli import main


def test_cli_skills_prints_builtin_skill_catalog_without_daemon(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "operance.cli.OperanceDaemon.build_default",
        lambda env: (_ for _ in ()).throw(AssertionError("daemon should not be built for --skills")),
    )

    exit_code = main(["--skills"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["pack_count"] == 0
    assert payload["safety_contract"]["execution"] == "typed_actions_only"


def test_cli_skill_validate_accepts_safe_pack(tmp_path, capsys) -> None:
    skill_path = tmp_path / "browser.json"
    skill_path.write_text(
        json.dumps(
            {
                "skill_id": "example.browser",
                "name": "Browser",
                "description": "Browser shortcuts.",
                "commands": [
                    {
                        "id": "open_docs",
                        "phrases": ["open project docs"],
                        "actions": [
                            {
                                "tool": "apps.launch",
                                "args": {"app": "https://github.com/raunakkathuria/operance"},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["--skill-validate", str(skill_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["skill_id"] == "example.browser"


def test_cli_skill_validate_rejects_unsafe_pack(tmp_path, capsys) -> None:
    skill_path = tmp_path / "unsafe.json"
    skill_path.write_text(
        json.dumps(
            {
                "skill_id": "example.unsafe",
                "name": "Unsafe",
                "description": "Unsafe raw shell command.",
                "commands": [
                    {
                        "id": "raw_shell",
                        "phrases": ["run raw shell"],
                        "actions": [{"tool": "shell.run", "args": {"command": "echo unsafe"}}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["--skill-validate", str(skill_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert "unknown tool: shell.run" in payload["errors"]


def test_cli_transcript_loads_external_skill_pack_from_environment(tmp_path, monkeypatch, capsys) -> None:
    skill_path = tmp_path / "notify.json"
    skill_path.write_text(
        json.dumps(
            {
                "skill_id": "example.notify",
                "name": "Notify",
                "description": "Notification shortcut.",
                "commands": [
                    {
                        "id": "skill_notify",
                        "phrases": ["skill smoke"],
                        "actions": [
                            {
                                "tool": "notifications.show",
                                "args": {"title": "Skill", "message": "Smoke passed"},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPERANCE_SKILL_PACKS", str(skill_path))

    exit_code = main(["--transcript", "skill smoke"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["response"] == "Notification shown"
