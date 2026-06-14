"""Guided command examples for first-run and tray surfaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CommandCoachStep:
    say: str
    expected: str
    category: str

    def to_dict(self) -> dict[str, str]:
        return {
            "say": self.say,
            "expected": self.expected,
            "category": self.category,
        }


COMMAND_COACH_STEPS = (
    CommandCoachStep(
        say="open browser",
        expected="Your default browser opens.",
        category="Open apps and websites",
    ),
    CommandCoachStep(
        say="open google.com",
        expected="Your default browser opens https://google.com.",
        category="Open apps and websites",
    ),
    CommandCoachStep(
        say="search google for linux automation",
        expected="Your default browser opens a Google search.",
        category="Search",
    ),
    CommandCoachStep(
        say="what time is it",
        expected="Operance answers with the current local time.",
        category="Ask",
    ),
    CommandCoachStep(
        say="what is the volume",
        expected="Operance reports the current audio volume.",
        category="Audio",
    ),
)


def build_command_coach() -> dict[str, object]:
    return {
        "title": "Try commands",
        "summary": "Use click-to-talk, say one command, then confirm the expected result.",
        "steps": [step.to_dict() for step in COMMAND_COACH_STEPS],
        "recovery": (
            "If Operance does not understand a command, try one of these examples first. "
            "Use Report an issue if a listed command fails."
        ),
        "tips": [
            "Left-click the tray icon before speaking.",
            "Keep commands short while testing.",
            "Use always-on listening as: Operance, short pause, then the command.",
        ],
    }
