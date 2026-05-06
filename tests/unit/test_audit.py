from pathlib import Path
import sqlite3


def test_audit_store_round_trips_entries(tmp_path: Path) -> None:
    from operance.audit import AuditEntry, AuditStore

    store = AuditStore(tmp_path / "audit.sqlite3")
    entry = AuditEntry(
        transcript="set volume to 50 percent",
        status="success",
        tool="audio.set_volume",
        response_text="Volume set to 50%",
        plan_source="deterministic",
        routing_reason="deterministic_match",
    )

    store.append(entry)
    entries = store.list_entries()

    assert len(entries) == 1
    assert entries[0].transcript == "set volume to 50 percent"
    assert entries[0].status == "success"
    assert entries[0].tool == "audio.set_volume"
    assert entries[0].plan_source == "deterministic"
    assert entries[0].routing_reason == "deterministic_match"
    assert entries[0].planner_error is None


def test_daemon_writes_audit_entry_for_successful_command(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("set volume to 50 percent", is_final=True)
    daemon.stop()

    entries = daemon.audit_store.list_entries()
    assert len(entries) == 1
    assert entries[0].status == "success"
    assert entries[0].tool == "audio.set_volume"
    assert entries[0].transcript == "set volume to 50 percent"
    assert entries[0].plan_source == "deterministic"
    assert entries[0].routing_reason == "deterministic_match"
    assert entries[0].planner_error is None


def test_daemon_writes_audit_entry_for_denied_command(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon
    from operance.models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction

    class InvalidMatcher:
        def match(self, text: str) -> ActionPlan | None:
            return ActionPlan(
                source=PlanSource.DETERMINISTIC,
                original_text=text,
                actions=[TypedAction(tool=ToolName.APPS_LAUNCH, args={}, risk_tier=RiskTier.TIER_0)],
            )

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )
    daemon.intent_matcher = InvalidMatcher()

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("open firefox", is_final=True)
    daemon.stop()

    entries = daemon.audit_store.list_entries()
    assert len(entries) == 1
    assert entries[0].status == "denied"
    assert entries[0].transcript == "open firefox"
    assert entries[0].tool == "apps.launch"
    assert entries[0].plan_source == "deterministic"
    assert entries[0].routing_reason == "deterministic_match"


def test_daemon_writes_audit_entry_for_planner_failure(tmp_path: Path) -> None:
    from operance.daemon import OperanceDaemon

    class FailingPlannerClient:
        def plan(self, transcript: str, **_: object) -> dict[str, object]:
            raise ValueError(f"planner failed for {transcript}")

    daemon = OperanceDaemon.build_default(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
            "OPERANCE_PLANNER_ENABLED": "1",
        }
    )
    daemon.planner_client = FailingPlannerClient()

    daemon.start()
    daemon.emit_wake_detected("operance")
    daemon.emit_transcript("let me know when this is done", is_final=True)
    daemon.stop()

    entries = daemon.audit_store.list_entries()
    assert len(entries) == 1
    assert entries[0].status == "unmatched"
    assert entries[0].transcript == "let me know when this is done"
    assert entries[0].plan_source is None
    assert entries[0].routing_reason == "planner_failed"
    assert entries[0].planner_error == "planner failed for let me know when this is done"


def test_audit_store_migrates_existing_schema_with_planner_fields(tmp_path: Path) -> None:
    from operance.audit import AuditEntry, AuditStore

    db_path = tmp_path / "audit.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE audit_entries (
                entry_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                transcript TEXT NOT NULL,
                status TEXT NOT NULL,
                tool TEXT,
                response_text TEXT
            )
            """
        )
        connection.commit()

    store = AuditStore(db_path)
    store.append(
        AuditEntry(
            transcript="open firefox",
            status="success",
            tool="apps.launch",
            response_text="Launched firefox",
            plan_source="deterministic",
            routing_reason="deterministic_match",
        )
    )

    entries = store.list_entries()

    assert len(entries) == 1
    assert entries[0].plan_source == "deterministic"
    assert entries[0].routing_reason == "deterministic_match"
    assert entries[0].planner_error is None
