"""Reusable transcript-session helpers for deterministic demos."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .daemon import OperanceDaemon
from .models.events import ResponseEvent, RuntimeState
from .sources import FileTranscriptSource, IterableTranscriptSource, TranscriptSource


def process_transcript(transcript: str, env: Mapping[str, str] | None = None) -> dict[str, object]:
    daemon = OperanceDaemon.build_default(env)
    daemon.start()
    try:
        response = _process_transcript_with_daemon(daemon, transcript)
    finally:
        daemon.stop()

    return response


def _process_transcript_with_daemon(daemon: OperanceDaemon, transcript: str) -> dict[str, object]:
    responses: list[ResponseEvent] = []
    daemon.event_bus.subscribe(ResponseEvent, responses.append)

    if daemon.state_machine.current_state != RuntimeState.AWAITING_CONFIRMATION:
        daemon.emit_wake_detected("operance")
    daemon.emit_transcript(transcript, is_final=True)
    response = responses[-1]
    daemon.complete_response_cycle()

    return {
        "transcript": transcript,
        "response": response.text,
        "status": response.status,
        "plan_id": response.plan_id,
        "simulated": daemon.config.runtime.developer_mode,
    }


def run_transcript_source(
    source: TranscriptSource,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    daemon = OperanceDaemon.build_default(env)
    daemon.start()
    try:
        return [_process_transcript_with_daemon(daemon, transcript) for transcript in source.read_transcripts()]
    finally:
        daemon.stop()


def run_transcript_file(
    transcript_file: Path,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    return run_transcript_source(FileTranscriptSource(transcript_file), env)


def run_inline_transcripts(
    transcripts: list[str],
    env: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    return run_transcript_source(IterableTranscriptSource(transcripts), env)


def run_interactive_session(
    transcript_stream,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    collected: list[str] = []
    for raw_line in transcript_stream:
        transcript = str(raw_line).strip()
        if not transcript:
            continue
        if transcript.lower() in {"exit", "quit"}:
            break
        collected.append(transcript)

    return run_inline_transcripts(collected, env)
