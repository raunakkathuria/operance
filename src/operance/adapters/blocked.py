"""Adapter set for platforms without a native adapter implementation."""

from __future__ import annotations

from typing import Callable

from .base import AdapterSet


class BlockedAdapter:
    """Refuses every adapter call with one explicit platform blocker message.

    Platform providers without a native adapter use this instead of the mock
    adapters, so live desktop commands fail with the real blocker instead of
    reporting simulated success. Method lookup still succeeds so adapter
    conformance can report the contract surface; calling the method is what
    raises.
    """

    __slots__ = ("blocker",)

    def __init__(self, blocker: str) -> None:
        self.blocker = blocker

    def __getattr__(self, name: str) -> Callable[..., object]:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name == "desktop_dir":
            raise ValueError(self.blocker)
        blocker = self.blocker

        def blocked_call(*args: object, **kwargs: object) -> object:
            raise ValueError(blocker)

        blocked_call.__name__ = name
        return blocked_call


def build_blocked_adapter_set(*, blocker: str) -> AdapterSet:
    adapter = BlockedAdapter(blocker)
    return AdapterSet(
        apps=adapter,
        windows=adapter,
        time=adapter,
        power=adapter,
        audio=adapter,
        clipboard=adapter,
        text_input=adapter,
        network=adapter,
        notifications=adapter,
        files=adapter,
    )
