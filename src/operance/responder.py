"""Text response formatting for deterministic command handling."""

from __future__ import annotations

from dataclasses import dataclass

from .models.actions import ActionResult

UNMATCHED_RESPONSE = "I did not understand that command."


@dataclass(slots=True)
class ResponseBuilder:
    def from_action_result(self, result: ActionResult) -> tuple[str, str]:
        if not result.results:
            return ("Request completed.", result.status)
        return (result.results[0].message, result.status)

    def unmatched(self) -> tuple[str, str]:
        return (UNMATCHED_RESPONSE, "unmatched")

    def validation_failed(self) -> tuple[str, str]:
        return ("Command validation failed.", "denied")

    def confirmation_required(self) -> tuple[str, str]:
        return ("Command requires confirmation.", "awaiting_confirmation")

    def confirmation_cancelled(self) -> tuple[str, str]:
        return ("Cancelled pending command.", "cancelled")

    def confirmation_expired(self) -> tuple[str, str]:
        return ("Pending command expired.", "expired")

    def confirmation_still_pending(self) -> tuple[str, str]:
        return ("Please confirm or cancel the pending command.", "awaiting_confirmation")
