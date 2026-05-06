from pathlib import Path


def test_replay_fixture_runner_reports_pass_and_fail_counts(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_text(
        "\n".join(
            [
                '{"transcript":"open firefox","expected_response":"Launched firefox","expected_status":"success"}',
                '{"transcript":"install updates","expected_response":"I did not understand that command.","expected_status":"unmatched"}',
                '{"transcript":"what time is it","expected_response":"wrong","expected_status":"success"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from operance.replay import run_replay_fixture

    report = run_replay_fixture(
        fixture_path,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert report["total"] == 3
    assert report["passed"] == 2
    assert report["failed"] == 1
    assert report["results"][0]["passed"] is True
    assert report["results"][2]["passed"] is False
