from operance.corpus import DEFAULT_COMMAND_CORPUS, PARAPHRASE_COMMAND_CORPUS, run_default_corpus, run_paraphrase_corpus


def test_run_default_corpus_reports_success_rate_and_p95(tmp_path) -> None:
    result = run_default_corpus(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    assert result["total_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert result["matched_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert result["successful_commands"] == len(DEFAULT_COMMAND_CORPUS)
    assert result["success_rate"] == 1.0
    assert result["p95_latency_ms"] is not None
    assert result["responses"]["open firefox"] == "Launched firefox"


def test_run_paraphrase_corpus_meets_phase_0a_success_target(tmp_path) -> None:
    result = run_paraphrase_corpus(
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        }
    )

    assert result["total_commands"] == len(PARAPHRASE_COMMAND_CORPUS)
    assert result["success_rate"] >= 0.95
    assert result["matched_commands"] >= int(len(PARAPHRASE_COMMAND_CORPUS) * 0.95)
    assert result["responses"]["launch firefox"] == "Launched firefox"
    assert result["responses"]["battery status"] == "Battery is 87%"
