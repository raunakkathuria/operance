from datetime import UTC, datetime, timedelta


def test_planner_context_window_drops_expired_entries() -> None:
    from operance.planner.context import PlannerContextWindow

    started_at = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    window = PlannerContextWindow(ttl_seconds=30, max_entries=4)
    window.add("user", "open firefox", now=started_at)
    window.add("assistant", "Planned action: launch firefox.", now=started_at + timedelta(seconds=10))

    messages = window.active_messages(now=started_at + timedelta(seconds=39))

    assert messages == [{"role": "assistant", "content": "Planned action: launch firefox."}]


def test_planner_context_window_keeps_only_most_recent_entries() -> None:
    from operance.planner.context import PlannerContextWindow

    started_at = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    window = PlannerContextWindow(ttl_seconds=300, max_entries=2)
    window.add("user", "open firefox", now=started_at)
    window.add("assistant", "Planned action: launch firefox.", now=started_at + timedelta(seconds=1))
    window.add("user", "also notify me", now=started_at + timedelta(seconds=2))

    messages = window.active_messages(now=started_at + timedelta(seconds=3))

    assert messages == [
        {"role": "assistant", "content": "Planned action: launch firefox."},
        {"role": "user", "content": "also notify me"},
    ]
