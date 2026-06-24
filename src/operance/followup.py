"""Contextual follow-up command matching."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .models.actions import ActionPlan, PlanSource, ToolName, TypedAction


@dataclass(frozen=True, slots=True)
class FollowupCommandSpec:
    tool: str
    description: str
    example_transcripts: tuple[str, ...]
    usage_pattern: str


@dataclass(frozen=True, slots=True)
class FollowupReference:
    kind: str
    label: str
    tool: ToolName
    args: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FollowupContext:
    source_transcript: str
    references: tuple[FollowupReference, ...]


@dataclass(frozen=True, slots=True)
class FollowupMatch:
    plan: ActionPlan | None = None
    response: tuple[str, str] | None = None


FOLLOWUP_COMMAND_SPECS: tuple[FollowupCommandSpec, ...] = (
    FollowupCommandSpec(
        tool="operance.followup_open",
        description="Open an item from the previous file discovery or metadata result.",
        example_transcripts=(
            "open it",
            "open the first one",
            "open the last result",
        ),
        usage_pattern="open it | open the first one | open the last result",
    ),
    FollowupCommandSpec(
        tool="operance.followup_switch",
        description="Switch to a window from the previous window discovery result.",
        example_transcripts=(
            "switch to it",
            "switch to the first window",
            "switch to the last window",
        ),
        usage_pattern="switch to it | switch to the first window | switch to the last window",
    ),
)


def match_followup_command(
    transcript: str,
    context: FollowupContext | None,
) -> FollowupMatch | None:
    normalized = _normalize(transcript)
    action_kind = _followup_action_kind(normalized)
    if action_kind is None:
        return None

    if context is None or not context.references:
        return FollowupMatch(response=("I do not have an actionable previous result.", "unmatched"))

    references = _references_for_action(context.references, action_kind)
    if not references:
        return FollowupMatch(response=(f"I cannot {action_kind} the previous result.", "unmatched"))

    index = _reference_index(normalized, len(references))
    if index is None:
        if len(references) == 1:
            index = 0
        else:
            return FollowupMatch(
                response=(
                    f"I found multiple previous results. Say {action_kind} the first one.",
                    "unmatched",
                )
            )

    reference = references[index]
    return FollowupMatch(
        plan=ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=transcript,
            actions=[TypedAction(tool=reference.tool, args=dict(reference.args))],
        )
    )


def _followup_action_kind(normalized: str) -> str | None:
    if re.fullmatch(r"open (it|that|this|the (first|second|third|last) (one|result|item)|first result|second result|third result|last result)", normalized):
        return "open"
    if re.fullmatch(r"switch to (it|that|this|the (first|second|third|last) (one|window|result)|first window|second window|third window|last window)", normalized):
        return "switch to"
    return None


def _references_for_action(
    references: tuple[FollowupReference, ...],
    action_kind: str,
) -> tuple[FollowupReference, ...]:
    if action_kind == "open":
        return tuple(reference for reference in references if reference.tool == ToolName.FILES_OPEN)
    if action_kind == "switch to":
        return tuple(reference for reference in references if reference.tool == ToolName.WINDOWS_SWITCH)
    return ()


def _reference_index(normalized: str, reference_count: int) -> int | None:
    ordinals = {
        "first": 0,
        "second": 1,
        "third": 2,
        "last": reference_count - 1,
    }
    for word, index in ordinals.items():
        if word in normalized:
            if 0 <= index < reference_count:
                return index
            return None
    return None


def _normalize(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(normalized.split())
