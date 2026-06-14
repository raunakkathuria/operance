from operance.command_coach import build_command_coach


def test_build_command_coach_returns_guided_user_examples() -> None:
    coach = build_command_coach()

    assert coach["title"] == "Try commands"
    assert coach["summary"] == "Use click-to-talk, say one command, then confirm the expected result."
    assert coach["steps"] == [
        {
            "say": "open browser",
            "expected": "Your default browser opens.",
            "category": "Open apps and websites",
        },
        {
            "say": "open google.com",
            "expected": "Your default browser opens https://google.com.",
            "category": "Open apps and websites",
        },
        {
            "say": "search google for linux automation",
            "expected": "Your default browser opens a Google search.",
            "category": "Search",
        },
        {
            "say": "what time is it",
            "expected": "Operance answers with the current local time.",
            "category": "Ask",
        },
        {
            "say": "what is the volume",
            "expected": "Operance reports the current audio volume.",
            "category": "Audio",
        },
    ]
    assert "Report an issue" in coach["recovery"]
    assert "Left-click the tray icon before speaking." in coach["tips"]
