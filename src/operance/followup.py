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
    interpretation: str | None = None


@dataclass(frozen=True, slots=True)
class FollowupRequest:
    action_kind: str
    destination_location: str | None = None


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
        tool="operance.followup_copy",
        description="Copy an item from the previous file discovery or metadata result to a known folder.",
        example_transcripts=(
            "copy it to documents",
            "copy the first one to downloads",
        ),
        usage_pattern="copy it to documents | copy the first one to downloads",
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
    request = _followup_request(normalized)
    if request is None:
        return None
    action_kind = request.action_kind

    if context is None or not context.references:
        return FollowupMatch(
            response=(
                "I do not know what that refers to. Try list files in downloads or show open windows first.",
                "unmatched",
            ),
            interpretation="Follow-up needs a previous file or window result.",
        )

    references = _references_for_action(context.references, action_kind)
    if not references:
        return FollowupMatch(
            response=(
                f"The previous result from {context.source_transcript!r} cannot be used with {transcript!r}. "
                "Use file follow-ups after file results, or window follow-ups after window results.",
                "unmatched",
            ),
            interpretation=f"No {action_kind} target in previous result.",
        )

    index = _reference_index(normalized, len(references))
    if index is None:
        if len(references) == 1:
            index = 0
        else:
            example_suffix = ""
            if request.destination_location is not None:
                example_suffix = f" to {request.destination_location}"
            return FollowupMatch(
                response=(
                    f"I found {len(references)} previous results from {context.source_transcript!r}. "
                    f"Say {action_kind} the first one{example_suffix} "
                    f"or {action_kind} the last one{example_suffix}.",
                    "unmatched",
                ),
                interpretation="Follow-up needs a specific previous result.",
            )

    reference = references[index]
    args = dict(reference.args)
    if action_kind == "copy":
        args["destination_location"] = request.destination_location
    return FollowupMatch(
        plan=ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=transcript,
            actions=[TypedAction(tool=reference.tool, args=args)],
        ),
        interpretation=_reference_interpretation(action_kind, reference, request.destination_location),
    )


def _followup_request(normalized: str) -> FollowupRequest | None:
    if re.fullmatch(r"open (it|that|this|the (first|second|third|last) (one|result|item)|first result|second result|third result|last result)", normalized):
        return FollowupRequest("open")
    copy_match = re.fullmatch(
        r"copy (it|that|this|the (first|second|third|last) (one|result|item)|first result|second result|third result|last result) to (?P<destination>desktop|downloads|documents|home)",
        normalized,
    )
    if copy_match:
        return FollowupRequest("copy", copy_match.group("destination"))
    if re.fullmatch(r"switch to (it|that|this|the (first|second|third|last) (one|window|result)|first window|second window|third window|last window)", normalized):
        return FollowupRequest("switch to")
    return None


def _references_for_action(
    references: tuple[FollowupReference, ...],
    action_kind: str,
) -> tuple[FollowupReference, ...]:
    if action_kind == "open":
        return tuple(reference for reference in references if reference.tool == ToolName.FILES_OPEN)
    if action_kind == "copy":
        return tuple(
            FollowupReference(
                kind=reference.kind,
                label=reference.label,
                tool=ToolName.FILES_COPY,
                args=dict(reference.args),
            )
            for reference in references
            if reference.tool == ToolName.FILES_OPEN
        )
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


def _reference_interpretation(
    action_kind: str,
    reference: FollowupReference,
    destination_location: str | None = None,
) -> str:
    if action_kind == "open" and reference.kind == "file":
        location = reference.args.get("location")
        if isinstance(location, str) and location:
            return f"Open {location} item: {reference.label}"
        return f"Open previous item: {reference.label}"
    if action_kind == "copy" and reference.kind == "file":
        location = reference.args.get("location")
        if isinstance(location, str) and location and destination_location:
            return f"Copy {location} item {reference.label} to {destination_location}"
        return f"Copy previous item: {reference.label}"
    if action_kind == "switch to" and reference.kind == "window":
        return f"Switch to window: {reference.label}"
    return f"{action_kind.capitalize()} previous result: {reference.label}"
