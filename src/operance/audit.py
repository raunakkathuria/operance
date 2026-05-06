"""SQLite-backed local audit log."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .models.base import SerializableModel, new_id, utc_now


@dataclass(slots=True, frozen=True)
class AuditEntry(SerializableModel):
    entry_id: str = field(default_factory=new_id)
    timestamp: object = field(default_factory=utc_now)
    transcript: str = ""
    status: str = ""
    tool: str | None = None
    response_text: str | None = None
    plan_source: str | None = None
    routing_reason: str | None = None
    planner_error: str | None = None


@dataclass(slots=True)
class AuditStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tool TEXT,
                    response_text TEXT,
                    plan_source TEXT,
                    routing_reason TEXT,
                    planner_error TEXT
                )
                """
            )
            _ensure_column(connection, "audit_entries", "plan_source", "TEXT")
            _ensure_column(connection, "audit_entries", "routing_reason", "TEXT")
            _ensure_column(connection, "audit_entries", "planner_error", "TEXT")
            connection.commit()

    def append(self, entry: AuditEntry) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO audit_entries (
                    entry_id, timestamp, transcript, status, tool, response_text, plan_source, routing_reason, planner_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.entry_id,
                    str(entry.timestamp),
                    entry.transcript,
                    entry.status,
                    entry.tool,
                    entry.response_text,
                    entry.plan_source,
                    entry.routing_reason,
                    entry.planner_error,
                ),
            )
            connection.commit()

    def list_entries(self) -> list[AuditEntry]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT entry_id, timestamp, transcript, status, tool, response_text, plan_source, routing_reason, planner_error
                FROM audit_entries
                ORDER BY rowid ASC
                """
            ).fetchall()

        return [
            AuditEntry(
                entry_id=row[0],
                timestamp=row[1],
                transcript=row[2],
                status=row[3],
                tool=row[4],
                response_text=row[5],
                plan_source=row[6],
                routing_reason=row[7],
                planner_error=row[8],
            )
            for row in rows
        ]

    def list_recent(self, *, limit: int = 20) -> list[AuditEntry]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT entry_id, timestamp, transcript, status, tool, response_text, plan_source, routing_reason, planner_error
                FROM audit_entries
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            AuditEntry(
                entry_id=row[0],
                timestamp=row[1],
                transcript=row[2],
                status=row[3],
                tool=row[4],
                response_text=row[5],
                plan_source=row[6],
                routing_reason=row[7],
                planner_error=row[8],
            )
            for row in rows
        ]


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    existing_columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name in existing_columns:
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
