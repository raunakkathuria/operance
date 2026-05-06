import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_demo.sh"
REPLAY_FIXTURE = REPO_ROOT / "demo" / "phase0a_replay.jsonl"
CONFIRMATION_FIXTURE = REPO_ROOT / "demo" / "phase0a_confirmation.txt"


def _run_demo_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_demo_replay_fixture_passes(tmp_path: Path) -> None:
    from operance.replay import run_replay_fixture

    report = run_replay_fixture(
        REPLAY_FIXTURE,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert report["total"] == 5
    assert report["passed"] == 5
    assert report["failed"] == 0


def test_demo_confirmation_fixture_confirms_pending_command(tmp_path: Path) -> None:
    from operance.session import run_transcript_file

    results = run_transcript_file(
        CONFIRMATION_FIXTURE,
        {
            "OPERANCE_DATA_DIR": str(tmp_path / "data"),
            "OPERANCE_DESKTOP_DIR": str(tmp_path / "Desktop"),
        },
    )

    assert [result["status"] for result in results] == ["awaiting_confirmation", "success"]
    assert [result["response"] for result in results] == [
        "Command requires confirmation.",
        "Closed window Firefox",
    ]


def test_demo_script_dry_run_prints_repeatable_steps() -> None:
    result = _run_demo_script(
        "--dry-run",
        "--python",
        ".venv/bin/python",
        "--workdir",
        "/tmp/operance-demo",
    )

    assert result.stdout.splitlines() == [
        "== Operance deterministic demo ==",
        "Workspace: /tmp/operance-demo",
        "Python: .venv/bin/python",
        "",
        "== Status snapshot ==",
        "+ .venv/bin/python -m operance.cli --status",
        "",
        "== Launch command ==",
        '+ .venv/bin/python -m operance.cli --transcript "open firefox"',
        "",
        "== Confirmation session ==",
        "+ .venv/bin/python -m operance.cli --transcript-file demo/phase0a_confirmation.txt",
        "",
        "== Replay summary ==",
        "+ .venv/bin/python -m operance.cli --replay-file demo/phase0a_replay.jsonl",
        "",
        "== Corpus summary ==",
        "+ .venv/bin/python -m operance.cli --run-corpus",
    ]
    assert result.stderr == ""
