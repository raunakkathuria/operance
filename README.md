# Operance

Turn intent into action.

Operance lets developers control a Linux desktop with natural language through a tray-first click-to-talk workflow. In the current Fedora KDE Wayland developer alpha, it can open apps and URLs, focus apps, and answer a small verified set of desktop-status commands such as time, battery, Wi-Fi, and audio state.

Under the hood, Operance is a local-first desktop action runtime for Linux desktops, with a shared portable core, per-platform adapters, and an MCP-compatible control surface. Every command flows through typed actions, validation, and policy before execution.

The current MVP interaction path is tray plus click-to-talk through the repo-local `./scripts/run_mvp.sh` launcher. Wake-word and continuous voice-loop paths remain available for diagnostics and later product work, but they are not the default public alpha path.

Platform roadmap:

- Phase 1: Linux/KDE/Wayland
- Phase 2: Windows
- Phase 3: macOS

The implementation stays Linux-first today. The portable core remains shared across platforms, including the voice pipeline orchestration, planner, typed action schema, safety model, and MCP server, while platform providers own host-specific readiness, setup workflow, and release-verification rules and OS-specific execution or input translation stays behind per-platform adapters. That keeps the current delivery scope KISS and YAGNI-compliant without closing off the later Windows and macOS paths.

## Developer Alpha Quickstart

This is the primary supported public-alpha path today:

```bash
./scripts/install_linux_dev.sh --ui --voice
.venv/bin/python -m operance.cli --version
.venv/bin/python -m operance.cli --doctor
.venv/bin/python -m operance.cli --supported-commands --supported-commands-available-only
./scripts/run_mvp.sh
./scripts/run_beta_smoke.sh
```

Try a few live commands from the verified alpha subset:

```bash
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "what time is it"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "what is my battery level"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "wifi status"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "open firefox"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "open localhost:3000"
```

If the MVP path fails or you need to file a bug, collect the current issue artifact with:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

Current assumptions for that path:

- Linux
- KDE Plasma on Wayland
- local source checkout
- optional voice and UI extras installed when you want the tray and click-to-talk path

## Current Public Position

Operance is ready for a **Fedora KDE Wayland developer alpha** for outside developers. It is not yet a broad public desktop release.

- Primary supported path: source checkout with `./scripts/install_linux_dev.sh --ui --voice`, `.venv/bin/python -m operance.cli --doctor`, `./scripts/run_mvp.sh`, and `./scripts/run_beta_smoke.sh`
- Secondary supported path: Fedora RPM install of the `mvp` runtime profile, validated through `./scripts/run_fedora_alpha_gate.sh`
- Default interaction: tray plus click-to-talk
- Wake word and the continuous voice loop remain secondary to click-to-talk for alpha reliability
- The supported Fedora package path now vendors the tray UI and STT runtime dependencies needed for the MVP tray plus click-to-talk path
- Wake-word and TTS assets or backends remain optional and are not part of the packaged alpha support contract

Not yet claimed:

- broad distro or desktop-environment support
- Windows or macOS delivery
- wake-word-first as the default interaction model
- a zero-setup consumer install story

Use [docs/release/public-developer-alpha.md](docs/release/public-developer-alpha.md) for the current public handoff, [docs/release/fedora-alpha-checklist.md](docs/release/fedora-alpha-checklist.md) for the exact Fedora gate, [docs/release/release-plan.md](docs/release/release-plan.md) for the current release sequence, [docs/requirements/linux.md](docs/requirements/linux.md) for Linux setup, packaging, and advanced diagnostics, and [docs/release/public-repo-metadata.md](docs/release/public-repo-metadata.md) for suggested GitHub About metadata.

## How To Contribute

Anyone can contribute right now through one of these paths:

- test Operance on Fedora KDE Wayland and file reproducible issues with a support bundle
- improve onboarding, troubleshooting, and public-alpha docs
- add tests and bug fixes that make tray plus click-to-talk more reliable
- harden packaging, setup, doctor, and release-gate workflows

This is still a founder-maintained alpha. Small, focused fixes and high-quality issue reports are more useful than broad rewrites.

Start with [CONTRIBUTING.md](CONTRIBUTING.md). If you are reporting a problem instead of sending a patch, attach the output artifact from `.venv/bin/python -m operance.cli --support-bundle` whenever possible.

This repository already contains the Phase 0A foundation plus the later planner, MCP, Linux-adapter, tray, voice, and release-tooling slices needed for the current developer alpha. Keep `README.md` for the public stop line and use [CHANGELOG.md](CHANGELOG.md) when you need the feature-by-feature implementation history.

## Current status

Operance already has a coherent Linux-first developer-alpha path: a typed and validated runtime, tray plus click-to-talk MVP flow, and Fedora packaging or support tooling. For the current public alpha, the supported command surface is intentionally narrower than the full implemented runtime. Use [CHANGELOG.md](CHANGELOG.md) for the feature-by-feature implementation history.

What works now:

- Core runtime: typed action models, deterministic intent matching, validator and policy enforcement, local audit logging, planner fallback, and MCP-compatible control surfaces.
- Verified alpha command subset on Fedora KDE Wayland: `open <app name>` or URL targets, `focus <app name>`, `what time is it`, `what is my battery level`, `wifi status`, `what is the volume`, and `is audio muted`.
- Voice and tray MVP: tray app, bounded click-to-talk, confirmation flows, last-interaction reporting, optional wake-word, STT, and TTS probe paths, plus repo-local background voice-loop support.
- Diagnostics and support: doctor, setup actions, runnable-command catalog, runtime status resources, support snapshot, support bundle, audit inspection, and beta-smoke scripts.
- Packaging and release gates: reproducible Linux bootstrap, source-checkout install or uninstall helpers, repo-local systemd helpers, Debian or RPM scaffolds, installed-package smoke, and the Fedora developer-alpha gate.

What is intentionally not implemented yet:

This is still a developer alpha. The main remaining gaps are bundling, broader platform coverage, and deeper Linux coverage, not the absence of a basic runnable product path. Broader implemented commands remain out of the supported alpha subset until they are live-verified and graduate into `--supported-commands --supported-commands-available-only`.

- A supported native package path that bundles the optional UI and voice Python backends out of the box
- A bundled Operance wake-word model and tuned default wake-word behavior
- Richer STT and TTS beyond the current optional bounded paths
- Broader KDE execution coverage and later Windows or macOS adapters
- Richer tray UI and planner recovery beyond the current bounded implementation

## Development and Diagnostics

README intentionally stays narrow for the public developer alpha. Use these docs for the deeper reference material instead of treating the README as a command inventory:

- [docs/requirements/linux.md](docs/requirements/linux.md) for Linux setup, packaging, systemd, planner, and optional voice diagnostics
- [docs/release/public-developer-alpha.md](docs/release/public-developer-alpha.md) for the outside-developer handoff
- [docs/release/fedora-alpha-checklist.md](docs/release/fedora-alpha-checklist.md) for the Fedora release gate
- [CONTRIBUTING.md](CONTRIBUTING.md) for contributor workflow and verification expectations

## Open-source baseline

The local core in this repository is released under the [MIT License](LICENSE).
That open-source boundary covers the local daemon, typed action and safety
runtime, desktop adapters, local voice loop, MCP server, and repo-local setup
tooling. Optional hosted relay, sync, or managed inference layers remain outside
the current runnable scope of this repo.

The repo now also includes a baseline public-project trust surface:

- [CONTRIBUTING.md](CONTRIBUTING.md) for workflow and verification expectations
- [SECURITY.md](SECURITY.md) for vulnerability reporting expectations
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for contributor behavior
- [docs/architecture/overview.md](docs/architecture/overview.md) for the
  portable-core versus platform-adapter boundary
- [docs/architecture/adapter-authoring.md](docs/architecture/adapter-authoring.md)
  for the current provider and adapter extension contract
- [docs/release/fedora-alpha-checklist.md](docs/release/fedora-alpha-checklist.md)
  for the current Fedora KDE alpha release gate and stop line
- [docs/requirements/linux.md](docs/requirements/linux.md) for Linux machine
  setup and live integration status
- `.github/workflows/ci.yml`, which runs the full test suite, minimal CLI smoke
  checks, and packaging or release dry-run smoke checks on pushes and pull
  requests

## Development

Use this section as the detailed reference, not the first-run path. The normal loop for a new machine is: bootstrap, run `--doctor`, run `./scripts/run_mvp.sh`, and then use the lower-level commands below only when you are debugging a specific subsystem.

Bootstrap a reproducible local development environment:

```bash
./scripts/install_linux_dev.sh
./scripts/install_linux_dev.sh --ui --voice
```

Run the source-checkout local install orchestrator:

```bash
./scripts/install_local_linux_app.sh
./scripts/install_local_linux_app.sh --voice --dry-run
./scripts/install_local_linux_app.sh --voice-loop --dry-run
```

Roll back the source-checkout local install orchestrator:

```bash
./scripts/uninstall_local_linux_app.sh --dry-run
./scripts/uninstall_local_linux_app.sh --remove-venv --dry-run
./scripts/uninstall_local_linux_app.sh --voice-loop --dry-run
```

Inspect the projected setup-status snapshot:

```bash
python3 -m operance.cli --setup-snapshot
python3 -m operance.cli --setup-actions
python3 -m operance.cli --setup-app
python3 -m operance.cli --setup-run-action install_ui_backend --setup-dry-run
python3 -m operance.cli --setup-run-action install_voice_loop_service --setup-dry-run
python3 -m operance.cli --setup-run-action install_voice_loop_user_config --setup-dry-run
python3 -m operance.cli --setup-run-action inspect_voice_loop_config --setup-dry-run
python3 -m operance.cli --setup-run-action enable_voice_loop_service --setup-dry-run
python3 -m operance.cli --setup-run-action probe_planner_health --setup-dry-run
python3 -m operance.cli --setup-run-action build_rpm_package_artifact --setup-dry-run
python3 -m operance.cli --setup-run-recommended --setup-dry-run
python3 -m operance.cli --voice-loop-config
python3 -m operance.cli --voice-loop-service-status
python3 -m operance.cli --voice-loop-status
python3 -m operance.cli --voice-self-test --use-voice-loop-config
python3 -m operance.cli --wakeword-eval-frames 50 --use-voice-loop-config
```

The manual venv flow remains supported:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

Install the optional voice backends for the wake-word, STT, and TTS probe paths:

```bash
python3 -m pip install -e ".[dev,voice]"
```

Run the optional bounded TTS probe when you have local Kokoro model assets:

```bash
python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin --tts-output /tmp/operance-hello.wav
python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin --tts-output /tmp/operance-hello.wav --tts-play
```

If you keep those assets in one of the discovered default locations, the CLI and setup surface can now use them without repeating the flags:

```bash
export OPERANCE_TTS_MODEL=/path/to/kokoro.onnx
export OPERANCE_TTS_VOICES=/path/to/voices.bin
python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-output /tmp/operance-hello.wav --tts-play
```

For wake-word models, keep the external `operance.onnx` file in one of the discovered locations or point `OPERANCE_WAKEWORD_MODEL` at it, then opt into that discovered asset with `--wakeword-model auto`:

```bash
export OPERANCE_WAKEWORD_MODEL=/path/to/operance.onnx
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model auto
python3 -m operance.cli --voice-session-frames 40 --wakeword-model auto
python3 -m operance.cli --voice-loop --wakeword-model auto
```

Run a bounded live voice session that also saves synthesized response audio:

```bash
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx --voice-session-tts-output-dir /tmp/operance-spoken --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx --voice-session-tts-output-dir /tmp/operance-spoken --voice-session-tts-play --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin
```

Run the continuous live voice loop, optionally with finite stop criteria for local smoke tests:

```bash
python3 -m operance.cli --voice-loop --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --voice-loop --voice-loop-max-commands 2 --wakeword-model /path/to/operance.onnx
./scripts/run_voice_loop.sh -- --wakeword-model /path/to/operance.onnx
./scripts/run_voice_loop.sh --args-file .operance/voice-loop.args
./scripts/run_voice_loop.sh -- --voice-loop-max-commands 2 --wakeword-model /path/to/operance.onnx
```

An optional repo-local `.operance/voice-loop.args` file is read first, then `~/.config/operance/voice-loop.args` is used as a fallback, with one CLI token per line and blank lines or `#` comments ignored. The repo-local `operance-voice-loop.service` unit now relies on that launcher search order instead of hardwiring one args file path in the unit itself.

Install the optional tray UI backend:

```bash
python3 -m pip install -e ".[dev,ui]"
```

Run the checked-in deterministic local demo:

```bash
./scripts/run_demo.sh
./scripts/run_demo.sh --dry-run
```

Install the repo-local tray user service scaffold:

```bash
./scripts/install_systemd_user_service.sh --dry-run
./scripts/install_systemd_user_service.sh --skip-systemctl
```

Remove the repo-local tray user service scaffold:

```bash
./scripts/uninstall_systemd_user_service.sh --dry-run
./scripts/uninstall_systemd_user_service.sh --skip-systemctl
```

Tail recent logs for the repo-local tray or voice-loop user service:

```bash
./scripts/tail_systemd_user_service_logs.sh --dry-run
./scripts/tail_systemd_user_service_logs.sh --lines 100 --follow
./scripts/tail_systemd_user_service_logs.sh --voice-loop --lines 100
```

Enable, disable, or otherwise control the repo-local tray or voice-loop user services:

```bash
./scripts/control_systemd_user_services.sh status --dry-run
./scripts/control_systemd_user_services.sh enable --voice-loop --dry-run
./scripts/control_systemd_user_services.sh restart --voice-loop --dry-run
./scripts/control_systemd_user_services.sh restart --all --dry-run
```

Install or remove the repo-local continuous voice-loop user service:

```bash
./scripts/install_voice_loop_user_service.sh --dry-run
./scripts/install_voice_loop_user_service.sh --skip-systemctl
./scripts/uninstall_voice_loop_user_service.sh --dry-run
./scripts/uninstall_voice_loop_user_service.sh --skip-systemctl
```

Render the shared packaged desktop and systemd assets:

```bash
./scripts/render_packaged_assets.sh --dry-run
./scripts/render_packaged_assets.sh --output-dir dist/packaged-assets
```

The packaged voice-loop scaffold now uses `/usr/lib/operance/voice-loop-launcher`, which prefers optional one-token-per-line args from `~/.config/operance/voice-loop.args` and falls back to `/etc/operance/voice-loop.args` before starting `operance --voice-loop`. The package scaffolds also ship `/etc/operance/voice-loop.args.example` as a starting point for that file.

Seed a user-scoped voice-loop config from the packaged or repo example file:

```bash
./scripts/install_voice_loop_user_config.sh --dry-run
./scripts/install_voice_loop_user_config.sh --force --dry-run
```

Update the user-scoped voice-loop config with a calibrated threshold or discovered wake-word model token:

```bash
./scripts/update_voice_loop_user_config.sh --wakeword-threshold 0.72 --dry-run
./scripts/update_voice_loop_user_config.sh --wakeword-model auto --dry-run
```

Stage external voice assets into the discovered user-scoped config paths:

```bash
python3 -m operance.cli --voice-asset-paths
./scripts/install_wakeword_model_asset.sh --source /path/to/operance.onnx --dry-run
./scripts/install_tts_assets.sh --model /path/to/kokoro.onnx --voices /path/to/voices.bin --dry-run
```

If you want the setup surface to run those install helpers directly, export source paths first:

```bash
export OPERANCE_WAKEWORD_MODEL_SOURCE=/path/to/operance.onnx
export OPERANCE_TTS_MODEL_SOURCE=/path/to/kokoro.onnx
export OPERANCE_TTS_VOICES_SOURCE=/path/to/voices.bin
python3 -m operance.cli --setup-actions
```

Render the Debian package staging tree:

```bash
./scripts/build_deb_package.sh --dry-run
./scripts/build_deb_package.sh --skip-build --staging-dir dist/deb/operance
```

Render the RPM package staging tree:

```bash
./scripts/build_rpm_package.sh --dry-run
./scripts/build_rpm_package.sh --skip-build --spec-dir dist/rpm
```

Render both package scaffolds in one pass:

```bash
./scripts/build_package_scaffolds.sh --dry-run
./scripts/build_package_scaffolds.sh --root-dir dist/packages
```

Build package artifacts through the existing helper scripts:

```bash
./scripts/build_package_artifacts.sh --dry-run
./scripts/build_package_artifacts.sh --rpm --root-dir dist/package-artifacts
```

Install the native package build tools used by those helpers:

```bash
./scripts/install_packaging_tools.sh --dry-run
./scripts/install_packaging_tools.sh --rpm --dry-run
```

The RPM helper now copies the built artifact back into `dist/package-artifacts/rpm/`, so the install helper can consume the documented path directly instead of reaching into the rpmbuild staging tree. That copy step now tolerates Fedora-style internal filenames like `operance-0.1.0-1.fc43.noarch.rpm` while still writing the documented normalized output path. The Fedora release and alpha gate helpers now also fail fast with `./scripts/install_packaging_tools.sh --rpm` when `rpmbuild` is missing, so packaging-host blockers are surfaced before the longer gate steps start.

The current Fedora `mvp` package installs `/usr/bin/operance`, the packaged Python source tree, and the tray UI plus STT Python runtime needed for the alpha click-to-talk path under `/usr/lib/operance`. The packaged command defaults to live Linux adapters (`OPERANCE_DEVELOPER_MODE=0`), so `operance --transcript "open firefox"` and tray click-to-talk should affect the desktop instead of returning simulated success. Wake-word and TTS assets remain optional and outside the packaged alpha contract.

Install a built native package artifact:

```bash
./scripts/install_package_artifact.sh --package dist/package-artifacts/deb/operance_0.1.0_all.deb --installer apt --dry-run
./scripts/install_package_artifact.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --dry-run
./scripts/install_package_artifact.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --replace-existing --dry-run
```

Use `--replace-existing` when testing a rebuilt Fedora RPM with the same package version. The helper removes the installed package when present and then installs the provided artifact, otherwise it keeps the normal first-install path.

Smoke-test an installed native package, optionally installing the artifact first:

```bash
./scripts/run_installed_beta_smoke.sh --dry-run
./scripts/run_installed_beta_smoke.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --require-mvp-runtime --dry-run
```

Run the full Fedora-first release gate from a checkout:

```bash
./scripts/run_fedora_release_smoke.sh --dry-run
./scripts/run_fedora_release_smoke.sh --support-bundle-out /tmp/operance-release-support.tar.gz --dry-run
```

Run the full Fedora developer-alpha gate from a checkout:

```bash
./scripts/run_fedora_alpha_gate.sh --dry-run
./scripts/run_fedora_alpha_gate.sh --support-bundle-out /tmp/operance-release-support.tar.gz --dry-run
```

Remove an installed native package:

```bash
./scripts/uninstall_native_package.sh --installer apt --dry-run
./scripts/uninstall_native_package.sh --installer dnf --package-name operance --dry-run
```

Use real Linux desktop adapters instead of mocks:

```bash
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --doctor
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "what is my battery level"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "open firefox"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "open localhost:3000"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "browse to localhost 3000"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "browse to docs.python.org/3"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "open file on desktop called notes.txt"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "open recent file called notes.txt"
```

Probe the Linux microphone and bounded voice-session paths:

```bash
python3 -m operance.cli --audio-list-devices
python3 -m operance.cli --audio-capture-frames 3
python3 -m operance.cli --wakeword-probe-frames 3
python3 -m operance.cli --wakeword-calibrate-frames 20
python3 -m operance.cli --wakeword-eval-frames 50
python3 -m operance.cli --voice-self-test
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --stt-probe-frames 10
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx
```

Enable planner fallback against a local chat-completions endpoint:

```bash
OPERANCE_PLANNER_ENABLED=1 python3 -m operance.cli --print-config
```

Inspect or run the tray surface:

```bash
python3 -m operance.cli --tray-snapshot
python3 -m operance.cli --tray-run
./scripts/run_tray_app.sh
```

## Workflow rules

- Use TDD for implementation work: add or update a failing test first, implement the smallest change that makes it pass, then refactor only if needed.
- Apply `KISS`: choose the simplest implementation that satisfies the current runnable requirement.
- Apply `YAGNI`: do not add future-phase abstractions, knobs, or integrations before the current milestone requires them.
- Apply `DRY`: remove duplication where it clarifies the current slice, but do not introduce abstractions that make small feature work harder to follow.
- Treat documentation updates as part of the same change, not follow-up work.
- Create a git commit at the end of each completed implementation step, not just at phase or milestone boundaries.
- Use descriptive commit messages that state the concrete behavior or surface added in that step.
- Keep future-phase work out of the current milestone unless the current tests require it.

## Documentation sync

- `LICENSE` defines the current local-core open-source license.
- `CONTRIBUTING.md` defines contributor workflow and verification expectations.
- `docs/architecture/overview.md` defines the portable-core versus adapter boundary.
- `README.md` should describe only what is actually runnable in the repository right now.
- `docs/requirements/linux.md` is the focused reference for preparing a real Linux/KDE machine for integration work and tracking live Linux integration status.
- `CHANGELOG.md` tracks completed implementation slices in commit order.
- `docs/requirements/plan.md` remains the long-form specification for scope and milestone boundaries, not the day-to-day status board.
- Any change to runtime behavior, interfaces, commands, or workflow rules must update the relevant docs in the same slice before commit.
- The pre-commit checklist for each step is: failing test first, implementation, docs update, `.venv/bin/python -m pytest`, commit.

## CLI

Most developers only need `--version`, `--doctor`, `--supported-commands --supported-commands-available-only`, `--transcript`, `--mvp-launch`, and `--support-bundle`. In the current developer alpha, `--supported-commands --supported-commands-available-only` is intentionally conservative: it prints only the commands that are both environment-ready and release-verified for the Fedora KDE Wayland target. The rest of this section is the lower-level CLI reference surface.

Print the effective config:

```bash
python3 -m operance.cli --print-config
```

Emit a tiny developer-mode event sequence:

```bash
python3 -m operance.cli --emit-demo-events
```

Process a transcript end to end and print the final response payload:

```bash
python3 -m operance.cli --transcript "open firefox"
```

In default developer mode, `--transcript` runs against simulated adapters and the payload includes `"simulated": true`. Set `OPERANCE_DEVELOPER_MODE=0` when you want the real Linux adapters instead.

Installed packages are different: the packaged `/usr/bin/operance` entrypoint defaults to live adapters. Verify this before testing tray commands:

```bash
operance --print-config
python3 scripts/check_installed_mvp_runtime.py --command operance
```

`operance --print-config` should report `"developer_mode": false`; the installed MVP runtime check fails if the packaged command is still in developer-mode simulation.

Run the built-in deterministic corpus and print a summary:

```bash
python3 -m operance.cli --run-corpus
```

Process one transcript per non-empty line from a file:

```bash
python3 -m operance.cli --transcript-file transcripts.txt
```

Run an interactive typed session until `exit` or EOF:

```bash
python3 -m operance.cli --interactive
```

Print a structured runtime status snapshot:

```bash
python3 -m operance.cli --status
```

Print the projected tray-state snapshot:

```bash
python3 -m operance.cli --tray-snapshot
```

Print recent runtime audit entries:

```bash
python3 -m operance.cli --audit-log
python3 -m operance.cli --audit-log --audit-limit 10
```

Run the optional PySide6 tray app:

```bash
python3 -m operance.cli --tray-run
```

Preferred MVP path: use the one-command repo-local launcher, or fall back to the explicit tray and click-to-talk wrappers:

```bash
./scripts/run_mvp.sh
./scripts/run_tray_app.sh
./scripts/run_click_to_talk.sh
```

List available Linux audio input devices:

```bash
python3 -m operance.cli --audio-list-devices
```

Capture a few Linux microphone frame metadata samples:

```bash
python3 -m operance.cli --audio-capture-frames 3
```

Process a few captured Linux microphone frames through the current wake-word probe detector:

```bash
python3 -m operance.cli --wakeword-probe-frames 3
```

Calibrate the current energy-based wake-word threshold against ambient microphone input:

```bash
python3 -m operance.cli --wakeword-calibrate-frames 20
python3 -m operance.cli --wakeword-calibrate-frames 20 --wakeword-threshold 0.65
```

Calibration now reports both `ambient_detector_confidence` and `ambient_peak_confidence`, because the fallback wake-word path now gates on sustained frame energy instead of a single-sample peak.

Measure idle false activations for the current wake-word detector settings:

```bash
python3 -m operance.cli --wakeword-eval-frames 50
python3 -m operance.cli --wakeword-eval-frames 50 --wakeword-model auto
```

Run one composite voice self-test across capture, wake-word idle evaluation, and optional STT/TTS:

```bash
python3 -m operance.cli --voice-self-test
python3 -m operance.cli --voice-self-test --wakeword-model auto
```

Process a few captured Linux microphone frames through a custom openWakeWord model:

```bash
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model auto
```

Process a few captured Linux microphone frames through the optional STT probe backend:

```bash
python3 -m operance.cli --stt-probe-frames 10
```

Run a bounded live voice session through wake-word detection, optional STT, and the daemon:

```bash
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --voice-session-frames 40 --wakeword-model auto
```

Run the continuous live voice loop until interrupted or optional stop criteria are met:

```bash
python3 -m operance.cli --voice-loop --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --voice-loop --wakeword-model auto
python3 -m operance.cli --voice-loop --voice-loop-max-commands 2 --wakeword-model /path/to/operance.onnx
```

The repo does not currently ship a default `operance` wake-word model file, so model-backed wake detection still requires an external asset; `--wakeword-model auto` only resolves that asset from `OPERANCE_WAKEWORD_MODEL`, `.operance/wakeword/operance.onnx`, `~/.config/operance/wakeword/operance.onnx`, or `/etc/operance/wakeword/operance.onnx`.

Print the `ActionPlan` JSON schema:

```bash
python3 -m operance.cli --action-plan-schema
```

Print the `ActionResult` JSON schema:

```bash
python3 -m operance.cli --action-result-schema
```

Print environment readiness checks:

```bash
python3 -m operance.cli --doctor
```

Run a replay fixture in JSONL format:

```bash
python3 -m operance.cli --replay-file fixture.jsonl
```

Run a planner payload regression fixture:

```bash
python3 -m operance.cli --planner-fixture planner_fixture.jsonl
```

Print the planner payload schema:

```bash
python3 -m operance.cli --planner-schema
```

Print the planner prompt messages for a transcript:

```bash
python3 -m operance.cli --planner-prompt "open firefox"
python3 -m operance.cli --planner-prompt "also notify me" --planner-context-entry "assistant:Planned action: launch firefox."
```

Build the planner service request payload for a transcript:

```bash
python3 -m operance.cli --planner-request "open firefox"
python3 -m operance.cli --planner-request "also notify me" --planner-context-entry "user:open firefox" --planner-context-entry "assistant:Planned action: launch firefox."
```

Probe the local planner endpoint health:

```bash
python3 -m operance.cli --planner-health
```

Print the planner fallback routing decision for a transcript:

```bash
python3 -m operance.cli --planner-route "open browser and notify me" --planner-confidence 0.88
```

Print the current MCP tool metadata:

```bash
python3 -m operance.cli --mcp-list-tools
```

Print the current MCP resource metadata:

```bash
python3 -m operance.cli --mcp-list-resources
```

Invoke an MCP tool through the validated runtime:

```bash
python3 -m operance.cli --mcp-call-tool apps.launch --mcp-tool-args '{"app":"firefox"}'
```

`--mcp-call-tool` creates a fresh server for each invocation, so confirmation follow-ups must use a stateful MCP session instead of separate CLI calls.

Read one MCP resource directly:

```bash
python3 -m operance.cli --mcp-read-resource operance://tools/catalog
```

Run a stateful MCP fixture through one shared server session:

```bash
python3 -m operance.cli --mcp-fixture mcp_fixture.jsonl
```

Fixture records may also include `expected_result` to assert a recursive subset of the returned MCP result.

Render a planner payload into a typed plan preview:

```bash
python3 -m operance.cli --planner-transcript "open firefox and notify me" --planner-payload '{"actions":[{"tool":"apps.launch","args":{"app":"firefox"}},{"tool":"notifications.show","args":{"title":"Opened","message":"Firefox launched"}}]}'
```

Run the MCP stdio transport loop on stdin/stdout:

```bash
python3 -m operance.cli --mcp-stdio
```

Within one MCP stdio or fixture-driven session, clients can inspect `operance://runtime/undo` and call `operance.undo_last_action` after a reversible action succeeds.

Within one MCP stdio session, clients can call `operance.confirm_pending` or `operance.cancel_pending` after a gated tool call returns `awaiting_confirmation`.

Developer mode uses mock adapters by default and keeps file-side effects inside the repo-local `.operance/Desktop` path unless `OPERANCE_DESKTOP_DIR` is overridden.
