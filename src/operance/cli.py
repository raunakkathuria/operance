"""Developer CLI for the scaffold."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Sequence

from .audio import build_default_audio_capture_source, build_default_audio_playback_sink
from .corpus import run_default_corpus
from .daemon import OperanceDaemon
from .doctor import build_environment_report
from .installed_smoke import build_installed_smoke_result
from .mcp import MCPServer, run_mcp_fixture
from .mcp.stdio import run_stdio_session
from .planner import (
    build_plan_preview,
    PlannerContextWindow,
    build_planner_payload_schema,
    PlannerRoutingPolicy,
    PlannerServiceClient,
    PlannerServiceConfig,
    parse_planner_payload,
    run_planner_fixture,
)
from .project_info import build_project_identity
from .replay import run_replay_fixture
from .schemas import build_action_plan_schema, build_action_result_schema
from .session import process_transcript, run_interactive_session, run_transcript_file
from .stt import build_default_speech_transcriber
from .support_bundle import write_support_bundle_artifact
from .support_snapshot import build_support_snapshot
from .supported_commands import build_supported_command_catalog
from .tts import build_default_speech_synthesizer
from .tts.assets import (
    find_existing_tts_model_path,
    find_existing_tts_voices_path,
    tts_model_candidate_paths,
    tts_voices_candidate_paths,
)
from .ui import (
    build_setup_snapshot,
    run_setup_app,
    build_tray_snapshot,
    run_setup_action,
    run_setup_actions,
    run_tray_app,
)
from .voice import (
    DEFAULT_CLICK_TO_TALK_MAX_FRAMES,
    build_voice_loop_config_snapshot,
    build_voice_loop_runtime_status_snapshot,
    run_continuous_voice_loop,
    run_live_voice_session,
    run_manual_voice_session,
    run_stt_probe,
    run_tts_probe,
    run_wakeword_calibration,
    run_wakeword_idle_evaluation,
    run_wakeword_probe,
)
from .voice.service import build_voice_loop_service_snapshot
from .wakeword.assets import find_existing_wakeword_model_path, wakeword_model_candidate_paths
from .wakeword import build_default_wakeword_detector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operance developer CLI")
    parser.add_argument("--version", action="store_true", help="Print the current Operance version")
    parser.add_argument("--print-config", action="store_true", help="Print the effective configuration")
    parser.add_argument("--supported-commands", action="store_true", help="Print the current supported command catalog")
    parser.add_argument(
        "--supported-commands-available-only",
        action="store_true",
        help="When printing supported commands, include only commands that are runnable now on this machine",
    )
    parser.add_argument("--audit-log", action="store_true", help="Print recent runtime audit entries")
    parser.add_argument("--audit-limit", type=int, default=20, help="Maximum entries for --audit-log")
    parser.add_argument(
        "--emit-demo-events",
        action="store_true",
        help="Emit a minimal wake + transcript event sequence",
    )
    parser.add_argument(
        "--transcript",
        help="Process a transcript through one CLI session; default developer mode uses simulated adapters unless OPERANCE_DEVELOPER_MODE=0",
    )
    parser.add_argument(
        "--transcript-file",
        help="Process one transcript per non-empty line from a file; default developer mode uses simulated adapters unless OPERANCE_DEVELOPER_MODE=0",
    )
    parser.add_argument("--interactive", action="store_true", help="Read transcripts from stdin until exit or EOF")
    parser.add_argument("--status", action="store_true", help="Print the current runtime status snapshot")
    parser.add_argument(
        "--support-snapshot",
        action="store_true",
        help="Print one aggregated support snapshot for issue reports and setup debugging",
    )
    parser.add_argument(
        "--support-snapshot-raw",
        action="store_true",
        help="Disable default path redaction for --support-snapshot",
    )
    parser.add_argument(
        "--support-snapshot-out",
        help="Write the --support-snapshot JSON payload to a file as well as stdout",
    )
    parser.add_argument(
        "--support-bundle",
        action="store_true",
        help="Write one redacted support bundle archive and print its manifest summary",
    )
    parser.add_argument(
        "--support-bundle-out",
        help="Write the --support-bundle archive to a specific path",
    )
    parser.add_argument("--setup-snapshot", action="store_true", help="Print the projected setup-status snapshot")
    parser.add_argument("--setup-actions", action="store_true", help="Print the projected setup actions")
    parser.add_argument("--setup-app", action="store_true", help="Run the optional PySide6 setup app")
    parser.add_argument("--setup-run-action", action="append", help="Run one setup action by id")
    parser.add_argument("--setup-run-recommended", action="store_true", help="Run the recommended setup actions")
    parser.add_argument("--setup-dry-run", action="store_true", help="Preview setup actions without executing them")
    parser.add_argument("--tray-snapshot", action="store_true", help="Print the projected tray-state snapshot")
    parser.add_argument("--tray-run", action="store_true", help="Run the optional PySide6 tray app")
    parser.add_argument("--mvp-launch", action="store_true", help="Launch the preferred current MVP interaction path")
    parser.add_argument("--voice-asset-paths", action="store_true", help="Print discovered and preferred voice asset paths")
    parser.add_argument("--voice-loop-config", action="store_true", help="Print the effective repo-local voice-loop config")
    parser.add_argument("--voice-loop-service-status", action="store_true", help="Print the combined voice-loop service, config, and runtime status snapshot")
    parser.add_argument("--voice-loop-status", action="store_true", help="Print the latest continuous voice-loop runtime status")
    parser.add_argument("--audio-list-devices", action="store_true", help="List Linux audio input devices")
    parser.add_argument(
        "--audio-capture-frames",
        type=int,
        help="Capture N audio frame metadata samples from the default Linux microphone path",
    )
    parser.add_argument("--audio-device", help="Preferred Linux audio input device name for capture probes")
    parser.add_argument(
        "--wakeword-model",
        help="Path to a custom openWakeWord model file for model-backed wake-word detection, or 'auto' to resolve a discovered external model asset",
    )
    parser.add_argument(
        "--wakeword-probe-frames",
        type=int,
        help="Process N captured audio frames through the current wake-word probe detector",
    )
    parser.add_argument(
        "--wakeword-calibrate-frames",
        type=int,
        help="Measure ambient wake-word confidence over N captured audio frames and print a suggested energy-detector threshold",
    )
    parser.add_argument(
        "--apply-suggested-threshold",
        action="store_true",
        help="Apply the threshold suggested by --wakeword-calibrate-frames to the user-scoped voice-loop config",
    )
    parser.add_argument(
        "--wakeword-eval-frames",
        type=int,
        help="Measure idle false activations over N captured audio frames through the current wake-word detector",
    )
    parser.add_argument(
        "--stt-probe-frames",
        type=int,
        help="Process N captured audio frames through the current speech-to-text probe backend",
    )
    parser.add_argument("--tts-probe-text", help="Synthesize one text utterance through the current TTS probe backend")
    parser.add_argument("--tts-model", help="Path to a Kokoro ONNX model file for the TTS probe")
    parser.add_argument("--tts-voices", help="Path to a Kokoro voices file for the TTS probe")
    parser.add_argument("--tts-output", help="Optional output path for the synthesized TTS probe audio")
    parser.add_argument("--tts-play", action="store_true", help="Play the synthesized TTS probe output through the current Linux playback sink")
    parser.add_argument("--tts-voice", default="af_sarah", help="Voice id for the current TTS probe backend")
    parser.add_argument("--tts-speed", type=float, default=1.0, help="Speech speed for the current TTS probe backend")
    parser.add_argument("--tts-language", default="en-us", help="Language code for the current TTS probe backend")
    parser.add_argument(
        "--voice-session-tts-output-dir",
        help="Optional output directory for synthesized response audio during a bounded voice session",
    )
    parser.add_argument(
        "--voice-session-tts-play",
        action="store_true",
        help="Play synthesized bounded voice-session responses through the current Linux playback sink",
    )
    parser.add_argument(
        "--voice-session-frames",
        type=int,
        help="Run a bounded captured voice session through wake-word, STT, and the daemon",
    )
    parser.add_argument(
        "--click-to-talk",
        action="store_true",
        help="Run a bounded manual voice session with the default click-to-talk capture budget",
    )
    parser.add_argument(
        "--click-to-talk-frames",
        type=int,
        help="Run a bounded manual voice session without wake-word gating",
    )
    parser.add_argument(
        "--voice-self-test",
        action="store_true",
        help="Run one bounded composite voice self-test across capture, wake-word, and optional STT/TTS paths",
    )
    parser.add_argument(
        "--voice-loop",
        action="store_true",
        help="Run a continuous captured voice loop until interrupted or optional stop criteria are met",
    )
    parser.add_argument(
        "--voice-loop-max-frames",
        type=int,
        help="Optional frame limit for --voice-loop",
    )
    parser.add_argument(
        "--voice-loop-max-commands",
        type=int,
        help="Optional completed-command limit for --voice-loop",
    )
    parser.add_argument(
        "--wakeword-threshold",
        type=float,
        default=0.6,
        help="Detection threshold for the current wake-word probe detector",
    )
    parser.add_argument(
        "--use-voice-loop-config",
        action="store_true",
        help="Resolve wake-word threshold and model defaults from the repo-local voice-loop config when explicit CLI values are not provided",
    )
    parser.add_argument("--action-plan-schema", action="store_true", help="Print the ActionPlan JSON schema")
    parser.add_argument("--action-result-schema", action="store_true", help="Print the ActionResult JSON schema")
    parser.add_argument("--doctor", action="store_true", help="Print environment readiness checks")
    parser.add_argument(
        "--installed-smoke",
        action="store_true",
        help="Run installed-package readiness checks and print explicit next steps",
    )
    parser.add_argument(
        "--installed-smoke-systemctl-command",
        default="systemctl",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--replay-file", help="Run a JSONL transcript replay fixture")
    parser.add_argument("--planner-fixture", help="Run a JSONL planner payload regression fixture")
    parser.add_argument("--planner-schema", action="store_true", help="Print the planner payload schema")
    parser.add_argument("--planner-prompt", help="Print the planner prompt messages for a transcript")
    parser.add_argument("--planner-request", help="Build the planner service request payload for a transcript")
    parser.add_argument(
        "--planner-context-entry",
        action="append",
        help="Add one planner context message as role:content for --planner-prompt or --planner-request",
    )
    parser.add_argument("--planner-health", action="store_true", help="Probe local planner endpoint health")
    parser.add_argument("--planner-route", help="Print the fallback routing decision for a transcript")
    parser.add_argument("--planner-confidence", type=float, default=1.0, help="Transcript confidence for --planner-route")
    parser.add_argument(
        "--planner-deterministic-matched",
        action="store_true",
        help="Mark the transcript as already matched deterministically for --planner-route",
    )
    parser.add_argument(
        "--planner-partial",
        action="store_true",
        help="Mark the transcript as partial instead of final for --planner-route",
    )
    parser.add_argument("--planner-transcript", help="Transcript to pair with --planner-payload")
    parser.add_argument("--planner-payload", help="JSON object of schema-constrained planner output")
    parser.add_argument("--run-corpus", action="store_true", help="Run the built-in deterministic demo corpus")
    parser.add_argument("--mcp-list-tools", action="store_true", help="Print MCP tool metadata")
    parser.add_argument("--mcp-list-resources", action="store_true", help="Print MCP resource metadata")
    parser.add_argument("--mcp-call-tool", help="Invoke one MCP tool by name")
    parser.add_argument("--mcp-fixture", help="Run a JSONL MCP fixture through one stateful server session")
    parser.add_argument("--mcp-read-resource", help="Read one MCP resource by URI")
    parser.add_argument("--mcp-stdio", action="store_true", help="Run the MCP stdio transport loop")
    parser.add_argument(
        "--mcp-tool-args",
        default="{}",
        help="JSON object of MCP tool args for --mcp-call-tool",
    )
    parser.add_argument("--data-dir", help="Override OPERANCE_DATA_DIR for this CLI run")
    parser.add_argument("--desktop-dir", help="Override OPERANCE_DESKTOP_DIR for this CLI run")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(argv_list)
    env = _build_cli_env(args)

    if args.apply_suggested_threshold and args.wakeword_calibrate_frames is None:
        parser.error("--apply-suggested-threshold requires --wakeword-calibrate-frames")
    if args.click_to_talk and args.click_to_talk_frames is not None:
        parser.error("--click-to-talk and --click-to-talk-frames cannot be used together")
    if args.support_snapshot_raw and not args.support_snapshot:
        parser.error("--support-snapshot-raw requires --support-snapshot")
    if args.support_snapshot_out and not args.support_snapshot:
        parser.error("--support-snapshot-out requires --support-snapshot")
    if args.support_bundle_out and not args.support_bundle:
        parser.error("--support-bundle-out requires --support-bundle")

    if args.version:
        identity = build_project_identity()
        version_text = f"{identity['name']} {identity['version']}"
        git_commit = identity.get("git_commit")
        if isinstance(git_commit, str) and git_commit:
            version_text = f"{version_text} ({git_commit})"
        print(version_text)
        return 0

    daemon = OperanceDaemon.build_default(env)

    if args.print_config:
        print(json.dumps(daemon.config.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.supported_commands or args.supported_commands_available_only:
        print(
            json.dumps(
                build_supported_command_catalog(
                    build_environment_report(),
                    available_only=args.supported_commands_available_only,
                ),
                sort_keys=True,
            )
        )
        return 0

    if args.audit_log:
        if args.audit_limit < 1:
            parser.error("--audit-limit must be at least 1")
        entries = daemon.audit_store.list_recent(limit=args.audit_limit)
        print(json.dumps({"count": len(entries), "entries": [entry.to_dict() for entry in entries]}, sort_keys=True))
        return 0

    if args.status:
        print(json.dumps(daemon.status_snapshot().to_dict(), sort_keys=True))
        return 0

    if args.support_snapshot:
        payload = build_support_snapshot(
            env=env,
            redact=not args.support_snapshot_raw,
        )
        if args.support_snapshot_out:
            _write_json_file(Path(args.support_snapshot_out), payload)
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.support_bundle:
        payload = write_support_bundle_artifact(
            output_path=Path(args.support_bundle_out) if args.support_bundle_out else None,
            env=env,
            redact=True,
        )
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.setup_snapshot:
        print(json.dumps(build_setup_snapshot().to_dict(), sort_keys=True))
        return 0

    if args.setup_actions:
        snapshot = build_setup_snapshot()
        print(
            json.dumps(
                {
                    "summary_status": snapshot.summary_status,
                    "next_steps": _serialize_setup_next_steps(getattr(snapshot, "next_steps", [])),
                    "blocked_recommendations": _serialize_setup_blocked_recommendations(snapshot.blocked_recommendations),
                    "actions": [action.to_dict() for action in snapshot.actions],
                },
                sort_keys=True,
            )
        )
        return 0

    if args.voice_asset_paths:
        print(json.dumps(_build_voice_asset_paths_payload(env), sort_keys=True))
        return 0

    if args.voice_loop_config:
        print(json.dumps(build_voice_loop_config_snapshot(env=env).to_dict(), sort_keys=True))
        return 0

    if args.voice_loop_service_status:
        print(json.dumps(build_voice_loop_service_snapshot(env=env).to_dict(), sort_keys=True))
        return 0

    if args.voice_loop_status:
        print(json.dumps(build_voice_loop_runtime_status_snapshot(env=env).to_dict(), sort_keys=True))
        return 0

    if args.setup_app:
        try:
            return run_setup_app()
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1

    if args.setup_run_action and args.setup_run_recommended:
        parser.error("--setup-run-action and --setup-run-recommended cannot be used together")

    if args.setup_run_action:
        try:
            results = run_setup_actions(action_ids=args.setup_run_action, dry_run=args.setup_dry_run)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        result_payloads = [result.to_dict() for result in results]
        if len(results) == 1:
            print(json.dumps(result_payloads[0], sort_keys=True))
        else:
            print(json.dumps({"results": result_payloads}, sort_keys=True))
        return 1 if any(payload.get("status") == "failed" for payload in result_payloads) else 0

    if args.setup_run_recommended:
        snapshot = build_setup_snapshot()
        try:
            results = run_setup_actions(recommended_only=True, dry_run=args.setup_dry_run, snapshot=snapshot)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        result_payloads = [result.to_dict() for result in results]
        payload: dict[str, object] = {
            "requested": "recommended",
            "results": result_payloads,
        }
        if not results:
            next_steps = _serialize_setup_next_steps(getattr(snapshot, "next_steps", []))
            if next_steps:
                payload["next_steps"] = next_steps
            if snapshot.blocked_recommendations:
                payload["message"] = "No recommended setup actions are currently runnable."
                payload["blocked_recommendations"] = _serialize_setup_blocked_recommendations(snapshot.blocked_recommendations)
            elif next_steps:
                payload["message"] = "No setup changes are needed right now. Try one of the next steps."
        print(json.dumps(payload, sort_keys=True))
        return 1 if any(result.get("status") == "failed" for result in result_payloads) else 0

    if args.mvp_launch:
        snapshot = build_setup_snapshot()
        if not getattr(snapshot, "ready_for_mvp", False):
            print(json.dumps(_build_mvp_launch_blocked_payload(snapshot), sort_keys=True))
            return 1

        if _setup_step_status(snapshot, "tray_user_service_active") == "ok":
            print(json.dumps(_build_tray_already_running_payload("Tray service is already active. Use the existing tray icon."), sort_keys=True))
            return 0

        if _setup_step_status(snapshot, "tray_ui_available") == "ok":
            try:
                return run_tray_app(env)
            except ValueError as exc:
                if str(exc) == "Operance tray is already running. Use the existing tray icon.":
                    print(json.dumps(_build_tray_already_running_payload(str(exc)), sort_keys=True))
                    return 0
                print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
                return 1

        exit_code, payload = _run_click_to_talk_launch(
            daemon,
            device_name=args.audio_device,
            max_frames=DEFAULT_CLICK_TO_TALK_MAX_FRAMES,
        )
        print(json.dumps(payload, sort_keys=True))
        return exit_code

    if args.tray_snapshot:
        print(
            json.dumps(
                build_tray_snapshot(
                    daemon.status_snapshot(),
                    voice_loop_status=build_voice_loop_runtime_status_snapshot(env=env),
                ).to_dict(),
                sort_keys=True,
            )
        )
        return 0

    if args.tray_run:
        try:
            return run_tray_app(env)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1

    if args.audio_list_devices:
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps({"devices": [device.to_dict() for device in source.list_input_devices()]}, sort_keys=True))
        return 0

    if args.audio_capture_frames is not None:
        if args.audio_capture_frames < 1:
            parser.error("--audio-capture-frames must be at least 1")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        frames = [frame.to_dict() for frame in source.frames(max_frames=args.audio_capture_frames)]
        print(json.dumps({"captured_frames": len(frames), "frames": frames}, sort_keys=True))
        return 0

    if args.wakeword_calibrate_frames is not None:
        if args.wakeword_calibrate_frames < 1:
            parser.error("--wakeword-calibrate-frames must be at least 1")
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        if _arg_present(argv_list, "--wakeword-model"):
            parser.error("--wakeword-model cannot be used with --wakeword-calibrate-frames")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        payload = run_wakeword_calibration(
            source,
            max_frames=args.wakeword_calibrate_frames,
            base_threshold=threshold,
        )
        suggested_threshold = float(payload["suggested_threshold"])
        payload["suggested_voice_loop_config_command"] = _build_voice_loop_threshold_update_command(
            suggested_threshold
        )
        if args.apply_suggested_threshold:
            payload["voice_loop_config_update"] = _apply_voice_loop_threshold_update(
                suggested_threshold
            )
        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=_resolve_wakeword_model_arg(wakeword_model_arg, env),
            )
        )
        print(
            json.dumps(payload, sort_keys=True)
        )
        if args.apply_suggested_threshold and payload["voice_loop_config_update"]["status"] != "ok":
            return 1
        return 0

    if args.wakeword_probe_frames is not None:
        if args.wakeword_probe_frames < 1:
            parser.error("--wakeword-probe-frames must be at least 1")
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        wakeword_model = _resolve_wakeword_model_arg(wakeword_model_arg, env)
        if wakeword_model_arg == "auto" and wakeword_model is None:
            parser.error("--wakeword-model auto requires a discovered wake-word model asset; inspect paths with --voice-asset-paths")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        detector = build_default_wakeword_detector(
            phrase="operance",
            threshold=threshold,
            model_path=wakeword_model,
        )
        payload = run_wakeword_probe(
            source,
            detector,
            max_frames=args.wakeword_probe_frames,
        )
        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=wakeword_model,
            )
        )
        print(
            json.dumps(payload, sort_keys=True)
        )
        return 0

    if args.wakeword_eval_frames is not None:
        if args.wakeword_eval_frames < 1:
            parser.error("--wakeword-eval-frames must be at least 1")
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        wakeword_model = _resolve_wakeword_model_arg(wakeword_model_arg, env)
        if wakeword_model_arg == "auto" and wakeword_model is None:
            parser.error("--wakeword-model auto requires a discovered wake-word model asset; inspect paths with --voice-asset-paths")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        detector = build_default_wakeword_detector(
            phrase="operance",
            threshold=threshold,
            model_path=wakeword_model,
        )
        payload = run_wakeword_idle_evaluation(
            source,
            detector,
            max_frames=args.wakeword_eval_frames,
        )
        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=wakeword_model,
            )
        )
        print(
            json.dumps(payload, sort_keys=True)
        )
        return 0

    if args.stt_probe_frames is not None:
        if args.stt_probe_frames < 1:
            parser.error("--stt-probe-frames must be at least 1")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
            transcriber = build_default_speech_transcriber()
            payload = run_stt_probe(
                source,
                transcriber,
                max_frames=args.stt_probe_frames,
            )
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.tts_probe_text is not None:
        if not args.tts_probe_text.strip():
            parser.error("--tts-probe-text must not be empty")
        tts_model = _resolve_tts_model_arg(args.tts_model, env)
        tts_voices = _resolve_tts_voices_arg(args.tts_voices, env)
        if tts_model is None:
            parser.error("--tts-model is required with --tts-probe-text")
        if tts_voices is None:
            parser.error("--tts-voices is required with --tts-probe-text")
        if args.tts_play and not args.tts_output:
            parser.error("--tts-output is required with --tts-play")
        try:
            synthesizer = build_default_speech_synthesizer(
                model_path=tts_model,
                voices_path=tts_voices,
                voice=args.tts_voice,
                speed=args.tts_speed,
                language=args.tts_language,
            )
            payload = run_tts_probe(
                synthesizer,
                args.tts_probe_text,
                output_path=Path(args.tts_output) if args.tts_output else None,
            )
            if args.tts_play:
                build_default_audio_playback_sink().play_file(Path(args.tts_output))
                payload["played_output"] = True
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.voice_self_test:
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        wakeword_model = _resolve_wakeword_model_arg(wakeword_model_arg, env)
        if wakeword_model_arg == "auto" and wakeword_model is None:
            parser.error("--wakeword-model auto requires a discovered wake-word model asset; inspect paths with --voice-asset-paths")
        tts_model = _resolve_tts_model_arg(args.tts_model, env)
        tts_voices = _resolve_tts_voices_arg(args.tts_voices, env)
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
            detector = build_default_wakeword_detector(
                phrase="operance",
                threshold=threshold,
                model_path=wakeword_model,
            )
            capture_frames = [frame.to_dict() for frame in source.frames(max_frames=2)]
            wakeword_idle_eval = run_wakeword_idle_evaluation(source, detector, max_frames=50)
            if int(wakeword_idle_eval.get("detection_count", 0)) > 0:
                wakeword_idle_eval["status"] = "warn"
                wakeword_idle_eval["message"] = "Idle false activations detected during wake-word evaluation."
            else:
                wakeword_idle_eval["status"] = "ok"
            payload = {
                "capture": {
                    "status": "ok" if capture_frames else "failed",
                    "captured_frames": len(capture_frames),
                    "frames": capture_frames,
                },
                "wakeword_idle_eval": wakeword_idle_eval,
            }
        except ValueError as exc:
            payload = {
                "capture": {"status": "failed", "message": str(exc)},
                "wakeword_idle_eval": {"status": "skipped", "message": "capture setup failed"},
                "stt": {"status": "skipped", "message": "capture setup failed"},
                "tts": {"status": "skipped", "message": "capture setup failed"},
                "summary_status": "failed",
            }
            print(json.dumps(payload, sort_keys=True))
            return 1

        try:
            transcriber = build_default_speech_transcriber()
        except ValueError as exc:
            payload["stt"] = {"status": "skipped", "message": str(exc)}
        else:
            payload["stt"] = {"status": "ok", **run_stt_probe(source, transcriber, max_frames=12)}

        if tts_model is None or tts_voices is None:
            payload["tts"] = _build_missing_tts_assets_payload(env)
        else:
            try:
                synthesizer = build_default_speech_synthesizer(
                    model_path=tts_model,
                    voices_path=tts_voices,
                    voice=args.tts_voice,
                    speed=args.tts_speed,
                    language=args.tts_language,
                )
            except ValueError as exc:
                payload["tts"] = {"status": "skipped", "message": str(exc)}
            else:
                payload["tts"] = {
                    "status": "ok",
                    **run_tts_probe(synthesizer, "Hello from Operance"),
                }

        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=wakeword_model,
            )
        )
        payload["summary_status"] = _voice_self_test_summary_status(payload)
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.voice_session_frames is not None:
        if args.voice_loop:
            parser.error("--voice-loop cannot be used with --voice-session-frames")
        if args.voice_session_frames < 1:
            parser.error("--voice-session-frames must be at least 1")
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        response_synthesizer = None
        response_output_dir = None
        response_playback_sink = None
        wakeword_model = _resolve_wakeword_model_arg(wakeword_model_arg, env)
        tts_model = _resolve_tts_model_arg(args.tts_model, env)
        tts_voices = _resolve_tts_voices_arg(args.tts_voices, env)
        if wakeword_model_arg == "auto" and wakeword_model is None:
            parser.error("--wakeword-model auto requires a discovered wake-word model asset; inspect paths with --voice-asset-paths")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
            detector = build_default_wakeword_detector(
                phrase="operance",
                threshold=threshold,
                model_path=wakeword_model,
            )
            if args.voice_session_tts_play and not args.voice_session_tts_output_dir:
                parser.error("--voice-session-tts-output-dir is required with --voice-session-tts-play")
            if args.voice_session_tts_output_dir:
                if tts_model is None:
                    parser.error("--tts-model is required with --voice-session-tts-output-dir")
                if tts_voices is None:
                    parser.error("--tts-voices is required with --voice-session-tts-output-dir")
                response_synthesizer = build_default_speech_synthesizer(
                    model_path=tts_model,
                    voices_path=tts_voices,
                    voice=args.tts_voice,
                    speed=args.tts_speed,
                    language=args.tts_language,
                )
                response_output_dir = Path(args.voice_session_tts_output_dir)
                if args.voice_session_tts_play:
                    response_playback_sink = build_default_audio_playback_sink()
            payload = run_live_voice_session(
                source,
                detector,
                build_default_speech_transcriber,
                max_frames=args.voice_session_frames,
                env=env,
                response_synthesizer=response_synthesizer,
                response_output_dir=response_output_dir,
                response_playback_sink=response_playback_sink,
            )
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=wakeword_model,
            )
        )
        print(json.dumps(payload, sort_keys=True))
        return 0

    click_to_talk_frames = (
        DEFAULT_CLICK_TO_TALK_MAX_FRAMES if args.click_to_talk else args.click_to_talk_frames
    )
    if click_to_talk_frames is not None:
        if click_to_talk_frames < 1:
            parser.error("--click-to-talk-frames must be at least 1")
        exit_code, payload = _run_click_to_talk_launch(
            daemon,
            device_name=args.audio_device,
            max_frames=click_to_talk_frames,
        )
        print(json.dumps(payload, sort_keys=True))
        return exit_code

    if args.voice_loop:
        if args.voice_loop_max_frames is not None and args.voice_loop_max_frames < 1:
            parser.error("--voice-loop-max-frames must be at least 1")
        if args.voice_loop_max_commands is not None and args.voice_loop_max_commands < 1:
            parser.error("--voice-loop-max-commands must be at least 1")
        threshold, wakeword_model_arg, voice_loop_config = _resolve_wakeword_runtime_settings(args, env, argv_list)
        if not 0.0 < threshold <= 1.0:
            parser.error("--wakeword-threshold must be between 0.0 and 1.0")
        response_synthesizer = None
        response_output_dir = None
        response_playback_sink = None
        wakeword_model = _resolve_wakeword_model_arg(wakeword_model_arg, env)
        tts_model = _resolve_tts_model_arg(args.tts_model, env)
        tts_voices = _resolve_tts_voices_arg(args.tts_voices, env)
        if wakeword_model_arg == "auto" and wakeword_model is None:
            parser.error("--wakeword-model auto requires a discovered wake-word model asset; inspect paths with --voice-asset-paths")
        try:
            source = build_default_audio_capture_source(device_name=args.audio_device)
            detector = build_default_wakeword_detector(
                phrase="operance",
                threshold=threshold,
                model_path=wakeword_model,
            )
            if args.voice_session_tts_play and not args.voice_session_tts_output_dir:
                parser.error("--voice-session-tts-output-dir is required with --voice-session-tts-play")
            if args.voice_session_tts_output_dir:
                if tts_model is None:
                    parser.error("--tts-model is required with --voice-session-tts-output-dir")
                if tts_voices is None:
                    parser.error("--tts-voices is required with --voice-session-tts-output-dir")
                response_synthesizer = build_default_speech_synthesizer(
                    model_path=tts_model,
                    voices_path=tts_voices,
                    voice=args.tts_voice,
                    speed=args.tts_speed,
                    language=args.tts_language,
                )
                response_output_dir = Path(args.voice_session_tts_output_dir)
                if args.voice_session_tts_play:
                    response_playback_sink = build_default_audio_playback_sink()
            payload = run_continuous_voice_loop(
                source,
                detector,
                build_default_speech_transcriber,
                max_frames=args.voice_loop_max_frames,
                stop_after_commands=args.voice_loop_max_commands,
                env=env,
                response_synthesizer=response_synthesizer,
                response_output_dir=response_output_dir,
                response_playback_sink=response_playback_sink,
            )
        except ValueError as exc:
            print(json.dumps({"status": "failed", "message": str(exc)}, sort_keys=True))
            return 1
        payload.update(
            _build_wakeword_runtime_context(
                snapshot=voice_loop_config,
                threshold=threshold,
                wakeword_model=wakeword_model_arg,
                resolved_model_path=wakeword_model,
            )
        )
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.action_plan_schema:
        print(json.dumps(build_action_plan_schema(), sort_keys=True))
        return 0

    if args.action_result_schema:
        print(json.dumps(build_action_result_schema(), sort_keys=True))
        return 0

    if args.doctor:
        print(json.dumps(build_environment_report(), sort_keys=True))
        return 0

    if args.installed_smoke:
        result = build_installed_smoke_result(systemctl_command=args.installed_smoke_systemctl_command)
        print(json.dumps(result.to_dict(), sort_keys=True))
        return 1 if result.status == "failed" else 0

    if args.replay_file:
        print(json.dumps(run_replay_fixture(Path(args.replay_file)), sort_keys=True))
        return 0

    if args.planner_fixture:
        print(json.dumps(run_planner_fixture(Path(args.planner_fixture)), sort_keys=True))
        return 0

    if args.planner_schema:
        print(json.dumps(build_planner_payload_schema(), sort_keys=True))
        return 0

    if args.planner_prompt:
        planner_client = PlannerServiceClient(
            daemon.planner_client.config if daemon.planner_client is not None else _planner_service_config_from_daemon(daemon)
        )
        try:
            context_window = _build_planner_context_window(args.planner_context_entry)
        except ValueError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {"messages": planner_client.build_messages(args.planner_prompt, context_window=context_window)},
                sort_keys=True,
            )
        )
        return 0

    if args.planner_request:
        try:
            context_window = _build_planner_context_window(args.planner_context_entry)
        except ValueError as exc:
            parser.error(str(exc))
        planner_client = PlannerServiceClient(
            daemon.planner_client.config if daemon.planner_client is not None else _planner_service_config_from_daemon(daemon)
        )
        print(json.dumps(planner_client.build_request(args.planner_request, context_window=context_window), sort_keys=True))
        return 0

    if args.planner_health:
        planner_client = PlannerServiceClient(
            daemon.planner_client.config if daemon.planner_client is not None else _planner_service_config_from_daemon(daemon)
        )
        result = planner_client.health()
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "ok" else 1

    if args.planner_route:
        decision = PlannerRoutingPolicy().decide(
            transcript=args.planner_route,
            deterministic_matched=args.planner_deterministic_matched,
            transcript_confidence=args.planner_confidence,
            is_final=not args.planner_partial,
        )
        print(json.dumps({"route": decision.route, "reason": decision.reason}, sort_keys=True))
        return 0

    if args.run_corpus:
        print(json.dumps(run_default_corpus(), sort_keys=True))
        return 0

    if args.mcp_list_tools:
        server = MCPServer(env)
        print(json.dumps({"tools": server.list_tools()}, sort_keys=True))
        server.stop()
        return 0

    if args.mcp_list_resources:
        server = MCPServer(env)
        print(json.dumps({"resources": server.list_resources()}, sort_keys=True))
        server.stop()
        return 0

    if args.mcp_call_tool:
        try:
            tool_args = _parse_tool_args(args.mcp_tool_args)
        except ValueError as exc:
            parser.error(str(exc))

        server = MCPServer(env)
        print(json.dumps(server.call_tool(args.mcp_call_tool, tool_args), sort_keys=True))
        server.stop()
        return 0

    if args.mcp_fixture:
        print(json.dumps(run_mcp_fixture(Path(args.mcp_fixture), env), sort_keys=True))
        return 0

    if args.mcp_read_resource:
        server = MCPServer(env)
        print(json.dumps(server.read_resource(args.mcp_read_resource), sort_keys=True))
        server.stop()
        return 0

    if args.mcp_stdio:
        run_stdio_session(sys.stdin, sys.stdout, env)
        return 0

    if args.planner_payload:
        if not args.planner_transcript:
            parser.error("--planner-transcript is required with --planner-payload")
        try:
            planner_payload = _parse_json_object(args.planner_payload, "Planner payload")
        except ValueError as exc:
            parser.error(str(exc))

        plan = parse_planner_payload(planner_payload, original_text=args.planner_transcript)
        print(
            json.dumps(
                {
                    "preview": build_plan_preview(plan),
                    "plan": plan.to_dict(),
                },
                sort_keys=True,
            )
        )
        return 0

    if args.transcript_file:
        results = run_transcript_file(Path(args.transcript_file))
        print(json.dumps({"total_transcripts": len(results), "results": results}, sort_keys=True))
        return 0

    if args.interactive:
        results = run_interactive_session(sys.stdin)
        print(json.dumps({"total_transcripts": len(results), "results": results}, sort_keys=True))
        return 0

    daemon.start()

    if args.emit_demo_events:
        daemon.emit_wake_detected()
        daemon.emit_transcript("open firefox")

    if args.transcript:
        print(json.dumps(process_transcript(args.transcript), sort_keys=True))

    daemon.stop()
    return 0

def _build_cli_env(args: argparse.Namespace) -> dict[str, str]:
    env: dict[str, str] = {}
    if args.data_dir:
        env["OPERANCE_DATA_DIR"] = args.data_dir
    if args.desktop_dir:
        env["OPERANCE_DESKTOP_DIR"] = args.desktop_dir
    return env


def _planner_service_config_from_daemon(daemon: OperanceDaemon) -> PlannerServiceConfig:
    return PlannerServiceConfig(
        endpoint=daemon.config.planner.endpoint,
        model=daemon.config.planner.model,
        timeout_seconds=daemon.config.planner.timeout_seconds,
        max_retries=daemon.config.planner.max_retries,
    )


def _parse_json_object(raw_json: str, label: str) -> dict[str, object]:
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must decode to a JSON object")
    return parsed


def _parse_tool_args(raw_args: str) -> dict[str, object]:
    return _parse_json_object(raw_args, "MCP tool args")


def _build_planner_context_window(entries: list[str] | None) -> PlannerContextWindow | None:
    if not entries:
        return None

    window = PlannerContextWindow(max_entries=max(4, len(entries)))
    allowed_roles = {"system", "user", "assistant"}
    for raw_entry in entries:
        role, separator, content = raw_entry.partition(":")
        normalized_role = role.strip().lower()
        message = content.strip()
        if not separator or not normalized_role or not message:
            raise ValueError("Planner context entries must use role:content")
        if normalized_role not in allowed_roles:
            raise ValueError("Planner context roles must be one of: assistant, system, user")
        window.add(normalized_role, message)
    return window


def _env_source(env: dict[str, str]) -> dict[str, str]:
    source = dict(os.environ)
    source.update(env)
    return source


def _resolve_wakeword_model_arg(explicit_value: str | None, env: dict[str, str]) -> str | None:
    if explicit_value is None:
        return None
    if explicit_value != "auto":
        return explicit_value
    candidate = find_existing_wakeword_model_path(_env_source(env))
    return None if candidate is None else str(candidate)


def _resolve_tts_model_arg(explicit_value: str | None, env: dict[str, str]) -> str | None:
    if explicit_value:
        return explicit_value
    candidate = find_existing_tts_model_path(_env_source(env))
    return None if candidate is None else str(candidate)


def _resolve_tts_voices_arg(explicit_value: str | None, env: dict[str, str]) -> str | None:
    if explicit_value:
        return explicit_value
    candidate = find_existing_tts_voices_path(_env_source(env))
    return None if candidate is None else str(candidate)


def _arg_present(argv: Sequence[str], flag: str) -> bool:
    return flag in argv


def _resolve_wakeword_runtime_settings(
    args: argparse.Namespace,
    env: dict[str, str],
    argv: Sequence[str],
) -> tuple[float, str | None, object | None]:
    threshold = args.wakeword_threshold
    wakeword_model_arg = args.wakeword_model
    snapshot = None
    if args.use_voice_loop_config:
        snapshot = build_voice_loop_config_snapshot(env=env)
        if not _arg_present(argv, "--wakeword-threshold"):
            threshold = snapshot.effective.wakeword_threshold
        if not _arg_present(argv, "--wakeword-model"):
            wakeword_model_arg = snapshot.effective.wakeword_model
    return threshold, wakeword_model_arg, snapshot


def _build_wakeword_runtime_context(
    *,
    snapshot: object | None,
    threshold: float,
    wakeword_model: str | None,
    resolved_model_path: str | None,
) -> dict[str, object]:
    if snapshot is None:
        return {}
    effective = snapshot.effective
    snapshot_payload = snapshot.to_dict()
    using_voice_loop_config = snapshot_payload.get("selected_args_file") is not None
    return {
        "effective_wakeword_model": wakeword_model,
        "effective_wakeword_model_path": resolved_model_path,
        "effective_wakeword_mode": effective.wakeword_mode,
        "effective_wakeword_threshold": threshold,
        "requested_voice_loop_config": True,
        "using_voice_loop_config": using_voice_loop_config,
        "voice_loop_config": snapshot_payload,
        "voice_loop_config_message": (
            "Using selected voice-loop args file."
            if using_voice_loop_config
            else "Requested voice-loop config, but no args file was found; using defaults."
        ),
        "voice_loop_config_status": "ok" if using_voice_loop_config else "warn",
    }


def _build_voice_loop_threshold_update_command(threshold: float) -> str:
    return f"./scripts/update_voice_loop_user_config.sh --wakeword-threshold {threshold}"


def _apply_voice_loop_threshold_update(threshold: float) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [
            "bash",
            str(repo_root / "scripts" / "update_voice_loop_user_config.sh"),
            "--wakeword-threshold",
            str(threshold),
        ],
        capture_output=True,
        check=False,
        cwd=repo_root,
        text=True,
    )
    return {
        "command": _build_voice_loop_threshold_update_command(threshold),
        "returncode": completed.returncode,
        "status": "ok" if completed.returncode == 0 else "failed",
        "stderr": completed.stderr,
        "stdout": completed.stdout,
    }


def _build_voice_asset_paths_payload(env: dict[str, str]) -> dict[str, object]:
    source = _env_source(env)
    wakeword_existing = find_existing_wakeword_model_path(source)
    tts_model_existing = find_existing_tts_model_path(source)
    tts_voices_existing = find_existing_tts_voices_path(source)
    wakeword_source = _existing_optional_path(source.get("OPERANCE_WAKEWORD_MODEL_SOURCE"))
    tts_model_source = _existing_optional_path(source.get("OPERANCE_TTS_MODEL_SOURCE"))
    tts_voices_source = _existing_optional_path(source.get("OPERANCE_TTS_VOICES_SOURCE"))

    payload: dict[str, object] = {
        "wakeword_model": {
            "status": "ok" if wakeword_existing is not None else "warn",
            "existing_path": None if wakeword_existing is None else str(wakeword_existing),
            "preferred_path": str(wakeword_model_candidate_paths(source)[0]),
            "candidate_paths": [str(path) for path in wakeword_model_candidate_paths(source)],
            "source_env_var": "OPERANCE_WAKEWORD_MODEL_SOURCE",
            "set_source_example": "export OPERANCE_WAKEWORD_MODEL_SOURCE=/path/to/operance.onnx",
            "source_status": "ok" if wakeword_source is not None else "warn",
            "source_path": None if wakeword_source is None else str(wakeword_source),
        },
        "tts_model": {
            "status": "ok" if tts_model_existing is not None else "warn",
            "existing_path": None if tts_model_existing is None else str(tts_model_existing),
            "preferred_path": str(tts_model_candidate_paths(source)[0]),
            "candidate_paths": [str(path) for path in tts_model_candidate_paths(source)],
            "source_env_var": "OPERANCE_TTS_MODEL_SOURCE",
            "set_source_example": "export OPERANCE_TTS_MODEL_SOURCE=/path/to/kokoro.onnx",
            "source_status": "ok" if tts_model_source is not None else "warn",
            "source_path": None if tts_model_source is None else str(tts_model_source),
        },
        "tts_voices": {
            "status": "ok" if tts_voices_existing is not None else "warn",
            "existing_path": None if tts_voices_existing is None else str(tts_voices_existing),
            "preferred_path": str(tts_voices_candidate_paths(source)[0]),
            "candidate_paths": [str(path) for path in tts_voices_candidate_paths(source)],
            "source_env_var": "OPERANCE_TTS_VOICES_SOURCE",
            "set_source_example": "export OPERANCE_TTS_VOICES_SOURCE=/path/to/voices.bin",
            "source_status": "ok" if tts_voices_source is not None else "warn",
            "source_path": None if tts_voices_source is None else str(tts_voices_source),
        },
    }
    install_commands: dict[str, str] = {}
    if wakeword_source is not None:
        install_commands["wakeword_model"] = shlex.join(
            [
                "./scripts/install_wakeword_model_asset.sh",
                "--source",
                str(wakeword_source),
            ]
        )
    if tts_model_source is not None and tts_voices_source is not None:
        install_commands["tts_assets"] = shlex.join(
            [
                "./scripts/install_tts_assets.sh",
                "--model",
                str(tts_model_source),
                "--voices",
                str(tts_voices_source),
            ]
        )
    if install_commands:
        payload["install_commands"] = install_commands
    return payload


def _existing_optional_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None
    candidate = Path(raw_value).expanduser()
    if candidate.exists():
        return candidate
    return None


def _build_missing_tts_assets_payload(env: dict[str, str]) -> dict[str, object]:
    asset_paths = _build_voice_asset_paths_payload(env)
    return {
        "status": "skipped",
        "message": "TTS model assets are not available",
        "recommended_command": "python3 -m operance.cli --voice-asset-paths",
        "asset_paths": {
            "tts_model": asset_paths["tts_model"],
            "tts_voices": asset_paths["tts_voices"],
        },
    }


def _serialize_setup_blocked_recommendations(items: object) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in items if isinstance(items, list) else []:
        if hasattr(item, "to_dict"):
            payload.append(item.to_dict())
        elif isinstance(item, dict):
            payload.append(dict(item))
    return payload


def _write_json_file(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _serialize_setup_next_steps(items: object) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in items if isinstance(items, list) else []:
        if hasattr(item, "to_dict"):
            payload.append(item.to_dict())
        elif isinstance(item, dict):
            payload.append(dict(item))
    return payload


def _setup_step_status(snapshot: object, name: str) -> str | None:
    steps = getattr(snapshot, "steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if hasattr(step, "name") and getattr(step, "name") == name:
            status = getattr(step, "status", None)
            return status if isinstance(status, str) else None
        if isinstance(step, dict) and step.get("name") == name:
            status = step.get("status")
            return status if isinstance(status, str) else None
    return None


def _build_mvp_launch_blocked_payload(snapshot: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "blocked",
        "message": "MVP launch prerequisites are not ready.",
        "summary_status": getattr(snapshot, "summary_status", None),
        "ready_for_local_runtime": bool(getattr(snapshot, "ready_for_local_runtime", False)),
        "ready_for_mvp": bool(getattr(snapshot, "ready_for_mvp", False)),
        "recommended_command": "python3 -m operance.cli --setup-run-recommended --setup-dry-run",
        "supported_commands_command": "python3 -m operance.cli --supported-commands",
        "runnable_commands_command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
    }
    recommended_commands = getattr(snapshot, "recommended_commands", [])
    if isinstance(recommended_commands, list) and recommended_commands:
        payload["recommended_commands"] = list(recommended_commands)
    blocked_recommendations = _serialize_setup_blocked_recommendations(
        getattr(snapshot, "blocked_recommendations", [])
    )
    if blocked_recommendations:
        payload["blocked_recommendations"] = blocked_recommendations
    next_steps = _serialize_setup_next_steps(getattr(snapshot, "next_steps", []))
    if next_steps:
        payload["next_steps"] = next_steps
    return payload


def _build_tray_already_running_payload(message: str) -> dict[str, str]:
    return {
        "status": "already_running",
        "service": "tray",
        "message": message,
        "supported_commands_command": "python3 -m operance.cli --supported-commands",
        "runnable_commands_command": "python3 -m operance.cli --supported-commands --supported-commands-available-only",
    }


def _run_click_to_talk_launch(
    daemon: OperanceDaemon,
    *,
    device_name: str | None,
    max_frames: int,
) -> tuple[int, dict[str, object]]:
    try:
        source = build_default_audio_capture_source(device_name=device_name)
        payload = run_manual_voice_session(
            daemon,
            source,
            build_default_speech_transcriber,
            max_frames=max_frames,
        )
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__
        return (1, {"status": "failed", "message": message})
    return (0, payload)


def _voice_self_test_summary_status(payload: dict[str, object]) -> str:
    capture = payload.get("capture", {})
    wakeword_idle_eval = payload.get("wakeword_idle_eval", {})
    stt = payload.get("stt", {})
    tts = payload.get("tts", {})
    if capture.get("status") != "ok":
        return "failed"
    if wakeword_idle_eval.get("status") not in {"ok", "warn"}:
        return "failed"
    if wakeword_idle_eval.get("status") == "warn":
        return "partial"
    if stt.get("status") == "ok" and tts.get("status") == "ok":
        return "ok"
    return "partial"


if __name__ == "__main__":
    raise SystemExit(main())
