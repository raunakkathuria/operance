from operance.runtime.metrics import CommandMetrics, MetricsCollector


def test_metrics_collector_records_command_metrics() -> None:
    collector = MetricsCollector()

    collector.record(
        CommandMetrics(
            transcript="open firefox",
            matched=True,
            total_duration_ms=12.0,
            planning_duration_ms=4.0,
            execution_duration_ms=5.0,
            response_duration_ms=3.0,
        )
    )

    assert len(collector.completed_commands) == 1
    assert collector.completed_commands[0].transcript == "open firefox"
    assert collector.completed_commands[0].matched is True


def test_metrics_collector_computes_p95_total_duration() -> None:
    collector = MetricsCollector()

    for duration in [10.0, 15.0, 22.0, 30.0, 50.0]:
        collector.record(
            CommandMetrics(
                transcript="test",
                matched=True,
                total_duration_ms=duration,
                planning_duration_ms=duration / 2,
                execution_duration_ms=duration / 4,
                response_duration_ms=duration / 4,
            )
        )

    assert collector.p95_total_duration_ms() == 50.0
