from pathlib import Path


def test_run_transcript_file_source_processes_each_non_empty_line(tmp_path: Path) -> None:
    transcript_file = tmp_path / "transcripts.txt"
    transcript_file.write_text("open firefox\n\ninstall updates\nwhat time is it\n", encoding="utf-8")

    from operance.session import run_transcript_file

    results = run_transcript_file(
        transcript_file,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["transcript"] for result in results] == [
        "open firefox",
        "install updates",
        "what time is it",
    ]
    assert results[0]["response"] == "Launched firefox"
    assert results[0]["status"] == "success"
    assert results[0]["simulated"] is True
    assert results[1]["response"] == "I did not understand that command."
    assert results[1]["status"] == "unmatched"
    assert results[1]["simulated"] is True
    assert results[2]["response"] == "It is 09:41"
    assert results[2]["status"] == "success"
    assert results[2]["simulated"] is True


def test_run_transcript_file_raises_for_missing_file(tmp_path: Path) -> None:
    from operance.session import run_transcript_file

    missing_path = tmp_path / "missing.txt"

    try:
        run_transcript_file(missing_path, {})
    except FileNotFoundError as exc:
        assert str(missing_path) in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_run_inline_transcripts_reuses_single_daemon_session(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["open firefox", "what time is it"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["response"] for result in results] == ["Launched firefox", "It is 09:41"]
    assert all(result["simulated"] is True for result in results)


def test_run_interactive_session_stops_on_exit_command(tmp_path: Path) -> None:
    from operance.session import run_interactive_session

    results = run_interactive_session(
        iter(["open firefox", "what time is it", "exit", "open terminal"]),
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["transcript"] for result in results] == ["open firefox", "what time is it"]
    assert [result["response"] for result in results] == ["Launched firefox", "It is 09:41"]
    assert all(result["simulated"] is True for result in results)


def test_run_inline_transcripts_can_confirm_pending_command(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["close window firefox", "confirm"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == ["Command requires confirmation.", "Closed window Firefox"]
    assert all(result["simulated"] is True for result in results)


def test_run_inline_transcripts_can_cancel_pending_command(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["delete folder on desktop called projects", "cancel"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "cancelled"]
    assert [result["response"] for result in results] == ["Command requires confirmation.", "Cancelled pending command."]
    assert all(result["simulated"] is True for result in results)


def test_run_inline_transcripts_can_confirm_desktop_entry_rename(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    (desktop_dir / "projects").mkdir()

    results = run_inline_transcripts(
        ["rename folder on desktop from projects to archive", "confirm"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(desktop_dir),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == [
        "Command requires confirmation.",
        "Renamed desktop entry projects to archive",
    ]


def test_run_inline_transcripts_can_confirm_desktop_entry_move(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    (desktop_dir / "projects").mkdir()
    (desktop_dir / "archive").mkdir()

    results = run_inline_transcripts(
        ["move folder on desktop called projects to archive", "confirm"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(desktop_dir),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == [
        "Command requires confirmation.",
        "Moved desktop entry projects to archive",
    ]


def test_run_inline_transcripts_can_confirm_wifi_disable(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["turn wifi off", "confirm"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == ["Command requires confirmation.", "Wi-Fi turned off"]


def test_run_inline_transcripts_can_confirm_known_wifi_connection(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["connect to wifi home", "confirm"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == ["Command requires confirmation.", "Connected to Wi-Fi home"]


def test_run_inline_transcripts_can_cancel_high_volume_change(tmp_path: Path) -> None:
    from operance.session import run_inline_transcripts

    results = run_inline_transcripts(
        ["set volume to 90 percent", "cancel"],
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "cancelled"]
    assert [result["response"] for result in results] == ["Command requires confirmation.", "Cancelled pending command."]
