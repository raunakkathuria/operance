from pathlib import Path


def test_planner_fixture_runner_reports_valid_and_invalid_payloads(tmp_path: Path) -> None:
    fixture_path = tmp_path / "planner_fixture.jsonl"
    fixture_path.write_text(
        "\n".join(
            [
                '{"transcript":"open firefox and notify me","planner_payload":{"actions":[{"tool":"apps.launch","args":{"app":"firefox"}},{"tool":"notifications.show","args":{"title":"Opened","message":"Firefox launched"}}]},"expected_valid":true,"expected_tools":["apps.launch","notifications.show"]}',
                '{"transcript":"open firefox","planner_payload":{"actions":[{"tool":"apps.launch","args":{}}]},"expected_valid":false,"expected_tools":["apps.launch"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from operance.planner.replay import run_planner_fixture

    report = run_planner_fixture(fixture_path)

    assert report["total"] == 2
    assert report["passed"] == 2
    assert report["failed"] == 0
    assert report["results"][0]["actual_valid"] is True
    assert report["results"][1]["actual_valid"] is False
