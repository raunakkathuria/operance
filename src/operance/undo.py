"""In-memory undo registration for reversible actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .models.base import new_id


UndoFn = Callable[[], str]


@dataclass(slots=True)
class UndoManager:
    _callbacks: dict[str, UndoFn] = field(default_factory=dict)

    def register(self, callback: UndoFn) -> str:
        token = new_id()
        self._callbacks[token] = callback
        return token

    def undo(self, token: str) -> str:
        callback = self._callbacks.pop(token)
        return callback()
