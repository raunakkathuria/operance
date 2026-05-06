"""Deterministic developer corpus for Phase 0A demos."""

from __future__ import annotations

from typing import Mapping

from .daemon import OperanceDaemon
from .models.events import ResponseEvent
from .runtime.metrics import MetricsCollector

DEFAULT_COMMAND_CORPUS = [
    "open firefox",
    "open terminal",
    "what time is it",
    "what is my battery level",
    "set volume to 50 percent",
    "get volume",
    "mute audio",
    "unmute audio",
    "is audio muted",
    "fullscreen window firefox",
    "keep window firefox above",
    "shade window firefox",
    "keep window firefox below",
    "show window firefox on all desktops",
    "what is on the clipboard",
    "copy build complete to clipboard",
    "copy selection",
    "clear clipboard",
    "paste clipboard",
    "type build complete",
    "press enter",
    "press control c",
    "wifi status",
    "turn wi-fi on",
    "show a notification saying build complete",
    "show files modified today",
    "create folder on desktop called projects",
]

PARAPHRASE_COMMAND_CORPUS = [
    "launch firefox",
    "please open terminal",
    "tell me the time",
    "battery status",
    "set the volume to 50 percent",
    "current volume",
    "mute sound",
    "unmute sound",
    "is the audio muted",
    "exit fullscreen for window firefox",
    "stop keeping window firefox above",
    "unshade window firefox",
    "stop keeping window firefox below",
    "show window firefox only on this desktop",
    "read clipboard",
    "copy release ready to clipboard",
    "copy selected text",
    "empty clipboard",
    "paste from clipboard",
    "type release ready",
    "hit escape",
    "press ctrl shift p",
    "what is the wifi status",
    "turn wi fi on",
    "show notification saying build complete",
    "show recent files",
    "make a folder on desktop called projects",
]


def _run_corpus(commands: list[str], env: Mapping[str, str] | None = None) -> dict[str, object]:
    responses: dict[str, str] = {}
    metrics = MetricsCollector()
    matched_commands = 0
    successful_commands = 0

    for transcript in commands:
        daemon = OperanceDaemon.build_default(env)
        observed_responses: list[ResponseEvent] = []
        daemon.event_bus.subscribe(ResponseEvent, observed_responses.append)

        daemon.start()
        daemon.emit_wake_detected("operance")
        daemon.emit_transcript(transcript, is_final=True)
        daemon.stop()

        response = observed_responses[-1]
        responses[transcript] = response.text

        if daemon.metrics.completed_commands:
            metric = daemon.metrics.completed_commands[-1]
            metrics.record(metric)
            if metric.matched:
                matched_commands += 1

        if response.status == "success":
            successful_commands += 1

    total_commands = len(commands)
    success_rate = successful_commands / total_commands if total_commands else 0.0

    return {
        "total_commands": total_commands,
        "matched_commands": matched_commands,
        "successful_commands": successful_commands,
        "success_rate": success_rate,
        "p95_latency_ms": metrics.p95_total_duration_ms(),
        "responses": responses,
    }


def run_default_corpus(env: Mapping[str, str] | None = None) -> dict[str, object]:
    return _run_corpus(DEFAULT_COMMAND_CORPUS, env)


def run_paraphrase_corpus(env: Mapping[str, str] | None = None) -> dict[str, object]:
    return _run_corpus(PARAPHRASE_COMMAND_CORPUS, env)
