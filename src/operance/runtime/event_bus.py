"""In-memory event bus for early wiring and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")


class EventBusProtocol(Protocol):
    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Register a handler for matching event types."""

    def subscribe_all(self, handler: Callable[[object], None]) -> None:
        """Register a handler for all events."""

    def publish(self, event: object) -> None:
        """Dispatch an event synchronously."""


@dataclass(slots=True)
class InMemoryEventBus:
    _typed_subscribers: dict[type[object], list[Callable[[object], None]]] = field(default_factory=dict)
    _global_subscribers: list[Callable[[object], None]] = field(default_factory=list)

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        self._typed_subscribers.setdefault(event_type, []).append(handler)  # type: ignore[arg-type]

    def subscribe_all(self, handler: Callable[[object], None]) -> None:
        self._global_subscribers.append(handler)

    def publish(self, event: object) -> None:
        for subscribed_type, handlers in self._typed_subscribers.items():
            if isinstance(event, subscribed_type):
                for handler in handlers:
                    handler(event)

        for handler in self._global_subscribers:
            handler(event)
