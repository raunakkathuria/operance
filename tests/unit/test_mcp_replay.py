from pathlib import Path


def test_mcp_fixture_runner_replays_stateful_calls(tmp_path: Path) -> None:
    fixture_path = tmp_path / "mcp_fixture.jsonl"
    fixture_path.write_text(
        "\n".join(
            [
                '{"method":"tools/call","name":"windows.close","arguments":{"window":"firefox"},"expected_result":{"status":"awaiting_confirmation","tool":"windows.close"}}',
                '{"method":"tools/call","name":"operance.cancel_pending","arguments":{},"expected_result":{"status":"cancelled","tool":"windows.close"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from operance.mcp.replay import run_mcp_fixture

    report = run_mcp_fixture(
        fixture_path,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert report["total"] == 2
    assert report["passed"] == 2
    assert report["failed"] == 0
    assert report["results"][0]["passed"] is True
    assert report["results"][1]["passed"] is True
    assert report["results"][0]["result"]["status"] == "awaiting_confirmation"
    assert report["results"][1]["result"]["status"] == "cancelled"
    assert report["results"][1]["result"]["tool"] == "windows.close"


def test_mcp_fixture_runner_reports_failed_expectation(tmp_path: Path) -> None:
    fixture_path = tmp_path / "mcp_fixture_fail.jsonl"
    fixture_path.write_text(
        '{"method":"tools/call","name":"apps.launch","arguments":{"app":"firefox"},"expected_result":{"status":"failed"}}\n',
        encoding="utf-8",
    )

    from operance.mcp.replay import run_mcp_fixture

    report = run_mcp_fixture(
        fixture_path,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert report["total"] == 1
    assert report["passed"] == 0
    assert report["failed"] == 1
    assert report["results"][0]["passed"] is False
