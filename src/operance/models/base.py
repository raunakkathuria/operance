"""Serialization helpers for dataclass-based models."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


def serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            field.name: serialize_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


class SerializableModel:
    """Mixin for compact JSON-ready dict rendering."""

    def to_dict(self) -> dict[str, Any]:
        return {
            field.name: serialize_value(getattr(self, field.name))
            for field in fields(self)
        }
