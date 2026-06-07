import json

import pytest

from operance.intent import DeterministicIntentMatcher
from operance.models.actions import PlanSource, RiskTier, ToolName
from operance.skills import (
    SkillValidationError,
    build_default_skill_library,
    load_skill_pack_from_mapping,
)


def test_builtin_skill_library_loads_safe_typed_command_packs() -> None:
    library = build_default_skill_library()

    payload = library.to_dict()

    assert payload["summary"]["pack_count"] >= 1
    assert payload["summary"]["command_count"] >= 1
    assert "open operance docs" in {
        phrase
        for pack in payload["packs"]
        for command in pack["commands"]
        for phrase in command["phrases"]
    }


def test_skill_pack_rejects_raw_shell_tools() -> None:
    with pytest.raises(SkillValidationError, match="unknown tool: shell.run"):
        load_skill_pack_from_mapping(
            {
                "skill_id": "unsafe.shell",
                "name": "Unsafe shell",
                "description": "Invalid raw shell example.",
                "commands": [
                    {
                        "id": "run_shell",
                        "phrases": ["run shell"],
                        "actions": [{"tool": "shell.run", "args": {"command": "rm -rf /"}}],
                    }
                ],
            }
        )


def test_skill_pack_normalizes_safety_through_registry() -> None:
    pack = load_skill_pack_from_mapping(
        {
            "skill_id": "example.files",
            "name": "File examples",
            "description": "Confirmation-gated file command examples.",
            "commands": [
                {
                    "id": "delete_notes",
                    "phrases": ["delete notes fixture"],
                    "actions": [
                        {
                            "tool": "files.delete_file",
                            "args": {"location": "desktop", "name": "notes.txt"},
                        }
                    ],
                }
            ],
        }
    )

    action = pack.commands[0].actions[0]

    assert action.tool == ToolName.FILES_DELETE_FILE
    assert action.risk_tier == RiskTier.TIER_2
    assert action.requires_confirmation is True


def test_deterministic_matcher_can_match_builtin_skill_phrase() -> None:
    matcher = DeterministicIntentMatcher(skill_library=build_default_skill_library())

    plan = matcher.match("open operance docs")

    assert plan is not None
    assert plan.source == PlanSource.DETERMINISTIC
    assert [(action.tool, action.args) for action in plan.actions] == [
        (ToolName.APPS_LAUNCH, {"app": "https://github.com/raunakkathuria/operance/blob/main/README.md"})
    ]


def test_skill_library_round_trips_as_json_safe_metadata() -> None:
    payload = build_default_skill_library().to_dict()

    encoded = json.dumps(payload, sort_keys=True)

    assert "shell.run" not in encoded
    assert "typed_actions_only" in encoded
