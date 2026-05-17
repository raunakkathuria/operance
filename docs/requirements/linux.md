# Linux Development Requirements

Status: Working reference
Type: Linux setup and handoff checklist
Audience: Founder, contributors, future Linux test machines

---

## 1. Purpose

This document is the focused Linux reference for running and validating Operance on the target platform.

It consolidates the Linux-specific requirements that are otherwise spread across:

- [README.md](../../README.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [SECURITY.md](../../SECURITY.md)
- [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)
- [overview.md](../architecture/overview.md)
- [fedora-checklist.md](../release/fedora-checklist.md)
- [tech.md](./tech.md)
- [linux.py](../../src/operance/platforms/linux.py)
- [CHANGELOG.md](../../CHANGELOG.md)

Use this document when preparing a real Linux machine for desktop-integration work.
Use [CONTRIBUTING.md](../../CONTRIBUTING.md) for repo workflow expectations and
[overview.md](../architecture/overview.md) for the portable-core versus adapter
boundary before widening Linux-specific code. Use [SECURITY.md](../../SECURITY.md)
for vulnerability reporting expectations and [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)
for contributor behavior on public issues or pull requests.
Use [fedora-checklist.md](../release/fedora-checklist.md) when you
need the current Fedora release stop line instead of the broader Linux setup inventory.

Linux is Phase 1 of the product roadmap. Windows is planned as Phase 2 and macOS as Phase 3, but those later phases should reuse the shared portable core instead of widening current Linux delivery scope. Public positioning should stay Linux-first with a cross-platform roadmap, not a simultaneous three-platform launch claim.

Current architecture note:

- the Linux host surface now hangs off the `linux_kde_wayland` platform provider in `src/operance/platforms/linux.py`
- that provider owns Linux-specific adapter construction, doctor checks, setup-step metadata, setup actions, service discovery, Wayland probes, and live command availability or verification rules
- `src/operance/doctor.py` now assembles common checks and delegates platform checks through the provider instead of carrying Linux host probes itself
- Linux-specific input transport details like `wtype` key sequences now also stay in `src/operance/adapters/linux.py` instead of shared key-definition modules
- the Linux execution path itself remains in `src/operance/adapters/linux.py`
- new OS work should start by adding a provider and adapters, not by adding more Linux branching to shared core modules

### Current public developer release state

The current public support contract is:

- Fedora KDE Plasma on Wayland
- source checkout as the primary supported path
- installed RPM as a secondary `mvp` runtime validation path
- tray plus click-to-talk as the default interaction model
- wake word and the continuous voice loop as secondary diagnostics, not the primary release workflow
- the supported Fedora RPM path vendors the tray UI and STT runtime dependencies needed for click-to-talk
- first installed-package diagnostic: `operance --installed-smoke`
- wake-word and TTS assets or backends remain optional and outside the packaged support contract

Current supported command subset on that target:

- `open <app name>` and URL-like launch targets such as `open localhost:3000`
- `focus <app name>`
- `what time is it`
- `what is my battery level`
- `wifi status`
- `what is the volume`
- `is audio muted`

If you want the fastest iteration loop, use the source checkout. Treat the RPM path as the packaged public handoff and run a human tray plus microphone smoke after the automated gate passes.

Use [public-handoff.md](../release/public-handoff.md) for the outside-developer handoff and [fedora-checklist.md](../release/fedora-checklist.md) for the exact release gate.

### Fast developer release bring-up

For the shortest current source-checkout path on the target Linux stack:

```bash
./scripts/install_linux_dev.sh --ui --voice
.venv/bin/python -m operance.cli --version
.venv/bin/python -m operance.cli --about
./scripts/run_mvp.sh
./scripts/run_checkout_smoke.sh
./scripts/run_fedora_gate.sh --reset-user-services --dry-run
./scripts/run_release_readiness_gate.sh --dry-run
```

If that path still fails and you need one issue artifact:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

### Try a few commands

Use developer-mode mocks first when you only want to validate parsing and responses. These commands are simulated and do not touch the real desktop; the transcript payload now returns `"simulated": true` in this mode. The `--supported-commands --supported-commands-available-only` view is intentionally conservative: it shows only commands that are both environment-ready and release-verified for the current Fedora KDE release target.

```bash
.venv/bin/python -m operance.cli --supported-commands --supported-commands-available-only
.venv/bin/python -m operance.cli --transcript "wifi status"
.venv/bin/python -m operance.cli --transcript "what is the volume"
```

Use the live Linux adapters when you want real desktop effects on the current machine. These runs should return `"simulated": false`:

```bash
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --doctor
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "what time is it"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "what is my battery level"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "wifi status"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "what is the volume"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "is audio muted"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "open firefox"
OPERANCE_DEVELOPER_MODE=0 .venv/bin/python -m operance.cli --transcript "open localhost:3000"
```

---

## 2. Target environment

Current target platform:

- Linux
- KDE Plasma 6
- Wayland session
- systemd user session
- D-Bus user session
- PipeWire audio stack

Secondary validation targets:

- Fedora Kinoite
- Fedora KDE
- Bluefin KDE
- Kubuntu

The project is **not** targeting GNOME-first, X11-first, or non-Linux desktop environments in v1.

### Recommended distro direction for a new machine

For a fresh Linux development machine, prefer a **mutable Fedora KDE Plasma Desktop install** first.

Why:

- it matches the project’s KDE/Wayland target directly
- it keeps local Python, editable installs, and package iteration straightforward
- it avoids introducing Atomic Desktop workflow constraints before the repo needs them

Use **Fedora Kinoite** only if you explicitly want an immutable/Atomic Desktop validation target in addition to the main development setup.

---

## 3. Minimum development requirements

At minimum, the Linux machine should provide:

- Python 3.12+
- a working virtual environment flow
- `git`
- a KDE Plasma Wayland session
- PipeWire
- systemd user services
- D-Bus session services

Recommended developer tooling:

- `uv` for environment and dependency management
- `pytest`
- `ruff`
- `black`
- `mypy`

The repo now includes a reproducible bootstrap script for a checked-out source tree:

```bash
./scripts/install_linux_dev.sh
./scripts/install_linux_dev.sh --ui --voice
./scripts/install_linux_dev.sh --dry-run --venv .envs/operance
```

The repo now also includes a source-checkout local install orchestrator that composes the bootstrap and tray-service install steps:

```bash
./scripts/install_local_linux_app.sh
./scripts/install_local_linux_app.sh --voice --dry-run
./scripts/install_local_linux_app.sh --voice-loop --dry-run
```

The matching uninstall orchestrator removes that source-checkout service setup and can optionally delete the local virtual environment:

```bash
./scripts/uninstall_local_linux_app.sh --dry-run
./scripts/uninstall_local_linux_app.sh --remove-venv --dry-run
./scripts/uninstall_local_linux_app.sh --voice-loop --dry-run
```

Current repo setup also remains compatible with the standard venv flow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

Install the optional voice backends when you want to exercise the model-backed wake-word path, the STT probe, the TTS probe, or the bounded live voice session:

```bash
python3 -m pip install -e ".[dev,voice]"
```

Install the optional UI backend when you want to run the tray app:

```bash
python3 -m pip install -e ".[dev,ui]"
```

For the current MVP, the preferred developer bring-up path is the repo-local `./scripts/run_mvp.sh` launcher, which prefers the tray and falls back to one bounded click-to-talk run when the tray backend is unavailable. Treat wake-word and the continuous voice loop as secondary diagnostics until the launch path is stable.

Run the checked-in deterministic demo when you want a repeatable mock-backed walkthrough of the current command loop:

```bash
./scripts/run_demo.sh
./scripts/run_demo.sh --dry-run
```

Render or install the repo-local tray user service scaffold when you want a systemd-managed tray process from a source checkout:

```bash
./scripts/install_systemd_user_service.sh --dry-run
./scripts/install_systemd_user_service.sh --skip-systemctl
```

Remove the repo-local tray user service scaffold when you want to roll back that source-checkout service setup:

```bash
./scripts/uninstall_systemd_user_service.sh --dry-run
./scripts/uninstall_systemd_user_service.sh --skip-systemctl
```

Render or install the repo-local continuous voice-loop user service scaffold when you want the checked-out tree to run the new loop through systemd:

```bash
./scripts/install_voice_loop_user_service.sh --dry-run
./scripts/install_voice_loop_user_service.sh --skip-systemctl
```

Remove the repo-local continuous voice-loop user service scaffold when you want to roll back that loop-specific service setup:

```bash
./scripts/uninstall_voice_loop_user_service.sh --dry-run
./scripts/uninstall_voice_loop_user_service.sh --skip-systemctl
```

Tail recent logs for the repo-local tray or voice-loop user service when diagnosing source-checkout startup or session issues:

```bash
./scripts/tail_systemd_user_service_logs.sh --dry-run
./scripts/tail_systemd_user_service_logs.sh --lines 100 --follow
./scripts/tail_systemd_user_service_logs.sh --voice-loop --lines 100
```

Enable, disable, or otherwise control the repo-local tray or voice-loop user services from the checked-out tree:

```bash
./scripts/control_systemd_user_services.sh status --dry-run
./scripts/control_systemd_user_services.sh enable --voice-loop --dry-run
./scripts/control_systemd_user_services.sh restart --voice-loop --dry-run
./scripts/control_systemd_user_services.sh restart --all --dry-run
```

Render the shared packaged desktop plus tray and voice-loop systemd assets when preparing package scaffolds from the current source tree:

```bash
./scripts/render_packaged_assets.sh --dry-run
./scripts/render_packaged_assets.sh --output-dir dist/packaged-assets
```

The packaged voice-loop scaffold now runs through `/usr/lib/operance/voice-loop-launcher`, which prefers optional one-token-per-line args from `~/.config/operance/voice-loop.args` and falls back to `/etc/operance/voice-loop.args` before starting `operance --voice-loop`. The package scaffolds also ship `/etc/operance/voice-loop.args.example` as a starting point for that file.

The repo now also includes `scripts/update_voice_loop_user_config.sh` for idempotently setting `--wakeword-threshold` or `--wakeword-model auto` in `~/.config/operance/voice-loop.args` without hand-editing the file.
The calibration CLI can now also reuse that same updater directly with `python3 -m operance.cli --wakeword-calibrate-frames N --apply-suggested-threshold`, returning structured success or failure details instead of forcing a manual copy/paste of the suggested command.
The repo now also includes `scripts/install_wakeword_model_asset.sh` and `scripts/install_tts_assets.sh` for copying external wake-word or Kokoro model files into the same user-scoped discovery tree without inventing ad hoc target paths.
The CLI now also exposes `python3 -m operance.cli --voice-asset-paths`, which prints the discovered and preferred wake-word plus TTS asset locations and is now used as the recommended remediation when setup sees missing asset files.
That same CLI payload now also includes env-provided source paths and ready-to-run asset install commands when those source files exist, so voice asset staging can be inspected from one surface instead of correlating doctor, setup, and shell scripts by hand.
That same payload now also includes the exact source env var names plus shell export examples for each asset type, so missing-source warnings can be resolved directly from the printed JSON.
When `OPERANCE_WAKEWORD_MODEL_SOURCE`, `OPERANCE_TTS_MODEL_SOURCE`, and `OPERANCE_TTS_VOICES_SOURCE` point at existing files, doctor and setup now surface those source paths too, and the setup action list can run the matching asset-install helpers without requiring a manual shell command rewrite.
The composite `voice-self-test` now also returns concrete TTS asset path guidance when Kokoro files are missing, and `--wakeword-model auto` failures now point back at `--voice-asset-paths` instead of stopping at a bare missing-asset error.
When those source env vars are set and the corresponding user-scoped assets are still missing, the setup recommendation list now also promotes the matching install helpers, so `--setup-run-recommended` can close the asset gap without a separate manual action selection step.
When no runnable recommended setup actions remain because required external voice asset sources are still missing, the setup snapshot and `--setup-run-recommended` output now surface blocked recommendations with the exact next diagnostic command instead of returning an unexplained empty list.
Individual setup actions now also expose per-action unavailable reasons and next-step commands where possible, so `python3 -m operance.cli --setup-actions` can explain blocked work without forcing you to infer it from raw booleans.
When setup does execute runnable actions, `python3 -m operance.cli --setup-run-action ...` and `python3 -m operance.cli --setup-run-recommended` now return a nonzero shell exit status if any executed action fails, so shell automation can treat those commands like normal setup primitives instead of reparsing the JSON output first.
The setup snapshot now also exposes a distinct `ready_for_mvp` flag, and its coarse `summary_status` now flips to `ready` once the current machine can actually run the click-to-talk MVP path instead of waiting on packaging or optional later-phase voice extras.
When the host is ready for the current MVP path, the setup snapshot and `--setup-actions` output now also surface explicit next-step commands like `./scripts/run_mvp.sh`, `./scripts/run_click_to_talk.sh`, and `./scripts/run_tray_app.sh`, keeping “try the product” separate from remediation commands.
When `--setup-run-recommended` has nothing left to change but the machine is ready to try Operance, it now returns those next-step commands instead of ending at an empty success payload.
That same `./scripts/run_mvp.sh` path now also reports `already_running` when the tray user service is already active, and the tray app itself now rejects a second instance through a local lock file, so Linux bring-up no longer creates duplicate tray icons when a background service is already present.
The CLI now also exposes `python3 -m operance.cli --voice-loop-config`, which prints the effective repo-local voice-loop args file, parsed wake-word settings, loop limits, passthrough args, any resolved `--wakeword-model auto` asset path, and an explicit status/message pair describing whether a real args file was actually selected before you start the background loop.
The continuous loop now also writes a repo-local runtime heartbeat file, and the CLI plus doctor/setup surfaces expose it through `python3 -m operance.cli --voice-loop-status`, `voice_loop_runtime_status_available`, and `voice_loop_runtime_heartbeat_fresh`.
Those doctor and setup surfaces now only escalate stale runtime heartbeats when an active `operance-voice-loop.service` should actually be updating them; inactive or uninstalled service states keep the last repo-local snapshot visible without treating it like a current runtime failure.
The CLI now also exposes `python3 -m operance.cli --voice-loop-service-status`, which collapses service install and enable state, the selected repo-local config, the latest runtime heartbeat, and the next recommended remediation into one service-level snapshot.
When the voice-loop service is installed and active but that heartbeat goes stale, the setup projection now escalates it into a restart recommendation through `./scripts/control_systemd_user_services.sh restart --voice-loop` instead of leaving the stale heartbeat as inspection-only metadata.
The tray snapshot and optional PySide6 tray app now also project that same repo-local heartbeat file, so the tray surface can show background voice-loop activity and surface stale-heartbeat warnings without opening `--doctor` or `--setup-actions`.
That same tray menu now also exposes `Show supported commands` plus `Show support snapshot`, so developers can inspect command coverage and one aggregated machine-diagnostics payload without dropping back to raw CLI output.
That same tray menu now also exposes `Save support snapshot`, which writes the same redacted diagnostics payload to `data_dir/support-snapshots/` for issue reports without requiring terminal copy-paste.
That same tray menu now also exposes `Save support bundle`, which writes the preferred redacted `tar.gz` issue-report artifact to `data_dir/support-bundles/` without requiring a separate shell command.
Those tray-saved support snapshot and support-bundle artifacts now also include the current Operance version in their generated filenames, so files collected from multiple builds do not collapse into ambiguous timestamp-only names.
When that heartbeat is stale, the same tray surface now also marks restart availability and the tray app can invoke the shared voice-loop service restart path directly instead of requiring a separate setup or shell step.
The MCP control surface now also exposes that same restart path through `operance.restart_voice_loop_service`, so non-CLI clients can trigger the repo-local voice-loop service restart without inventing a separate systemd control integration.
The tray snapshot now also carries the voice loop’s last transcript and last response from that same repo-local status file, so the tray preview can reflect recent background-loop activity even when the tray app’s own daemon session has not executed a local command.
The tray snapshot now also carries the tray daemon session’s own last heard transcript separately from its last response, so voice-testing developers can tell whether a mistake came from STT or execution without leaving the tray surface; no-transcript click-to-talk attempts now also persist in that same tray state instead of disappearing after a transient notification.
The tray snapshot now also includes one structured last-interaction report for the tray session itself, so successful click-to-talk runs and backend failures can both be inspected from one projected state instead of depending on tooltip text or transient notifications.
That same tray menu now also exposes `Show last interaction`, so developers can open that structured click-to-talk result or backend failure report from the product surface instead of dropping back to raw snapshot JSON.
Click-to-talk completion notifications now also include both `Heard: ...` and the resulting response text when a final transcript exists, so successful voice runs are debuggable from the bubble itself instead of requiring the tray dialog for basic inspection.
For the packaged click-to-talk MVP path, a missing continuous voice-loop runtime status file is informational in the tray and must not suppress the click-to-talk result notification. Stale or invalid continuous-loop status still surfaces as a voice-loop warning when that background loop has written status before.
Click-to-talk startup failures now also fail closed across both the tray and CLI surfaces, so microphone or STT backend errors return the daemon to `IDLE` and remain visible as structured error output instead of leaving the session stuck in `LISTENING`.
When the tray is otherwise idle, its tooltip now prefers the MVP hint `Left-click to talk` over the background loop’s benign `waiting_for_wake` activity text, so the first-run Linux interaction path stays explicit even when the optional voice loop is healthy.
The tray app now also shows that same guidance once at startup with an `Operance is ready` info bubble that adds `Right-click for supported commands.`, and the tray menu now exposes a shared supported-command help view so developers can discover runnable commands from the product surface instead of dropping back to raw CLI JSON first.
Deterministic `open ...`, `launch ...`, `focus ...`, and `switch to ...` app commands now also accept simple app names beyond the original Firefox and Terminal examples, while still leaving chained phrases like `open firefox and notify me` to the planner path instead of over-matching them as one app launch.
Those same deterministic app commands now also accept the more voice-like variants `please open ...`, `open app ...`, `focus app ...`, and `switch to app ...`, which reduces filler-word brittleness in the current MVP path without widening the execution surface itself.
That same supported-command catalog and tray help now also render generic app patterns like `open <app name>` and `quit <app name>` instead of implying those commands are limited to the example app names used in the underlying registry metadata.
The tray menu now also exposes `Show installed readiness`, which runs the same installed-package diagnostic as `operance --installed-smoke` and renders check failures, warnings, next-step commands, and manual click-to-talk checks from the product surface.
That same repo-local config can now also be applied to wake-word probes, idle evaluation, composite voice self-test, and direct `operance.cli --voice-loop` or `--voice-session-frames` runs with `--use-voice-loop-config`, and those outputs now distinguish between config that was requested versus config that was actually applied, so diagnostics no longer label a missing args file as an active config source.
When `~/.config/operance/voice-loop.args` is already present, the structured setup actions now automatically use that same config for wake-word probe, calibration, idle evaluation, and voice self-test commands instead of pointing setup users at default-threshold diagnostics.
Doctor and setup now also expose one explicit `voice_loop_wakeword_customized` check that warns when the loop is still on raw defaults and points back at `python3 -m operance.cli --voice-loop-config` for the effective threshold, mode, and selected args file.
That same setup warning now also adapts its recommended command: seed `voice-loop.args` first when no user config exists, otherwise jump straight to the one-step `--apply-suggested-threshold` calibration flow against the existing config.
The MCP server now also mirrors that repo-local voice-loop config through `operance://runtime/voice-loop-config`, so non-CLI clients can inspect the selected args file and effective wake-word settings through the same control surface they already use for runtime status and confirmation state.
The MCP server now also mirrors the latest voice-loop heartbeat through `operance://runtime/voice-loop-status`, so non-CLI clients can inspect the continuous loop’s most recent counters and activity without reading the repo-local status file directly.
The MCP server now also mirrors the combined voice-loop service snapshot through `operance://runtime/voice-loop-service`, so non-CLI clients can inspect install state, config, runtime health, and the next recommended service action from one resource instead of joining separate reads.

Seed a user-scoped voice-loop config from the packaged or repo example file:

```bash
./scripts/install_voice_loop_user_config.sh --dry-run
./scripts/install_voice_loop_user_config.sh --force --dry-run
python3 -m operance.cli --voice-loop-config
python3 -m operance.cli --voice-loop-service-status
python3 -m operance.cli --voice-loop-status
python3 -m operance.cli --voice-self-test --use-voice-loop-config
python3 -m operance.cli --wakeword-eval-frames 50 --use-voice-loop-config
```

Render the Debian package staging tree when preparing the current tray and voice-loop service scaffold:

```bash
./scripts/build_deb_package.sh --dry-run
./scripts/build_deb_package.sh --skip-build --staging-dir dist/deb/operance
```

Render the RPM package staging tree when preparing the current tray and voice-loop service scaffold:

```bash
./scripts/build_rpm_package.sh --dry-run
./scripts/build_rpm_package.sh --skip-build --spec-dir dist/rpm
```

Render both package scaffolds in one pass when you want one staging root for local packaging work:

```bash
./scripts/build_package_scaffolds.sh --dry-run
./scripts/build_package_scaffolds.sh --root-dir dist/packages
```

Build package artifacts through the current helper scripts when the required host tooling is available:

```bash
./scripts/build_package_artifacts.sh --dry-run
./scripts/build_package_artifacts.sh --deb --root-dir dist/package-artifacts
```

Install the package-build tooling required by those helpers when `dpkg-deb` or `rpmbuild` is still missing:

```bash
./scripts/install_packaging_tools.sh --dry-run
./scripts/install_packaging_tools.sh --rpm --dry-run
```

The RPM helper now copies the built artifact back into `dist/package-artifacts/rpm/`, so the documented install path no longer depends on the internal rpmbuild output tree. That copy step now tolerates Fedora-style internal filenames like `operance-0.1.0-1.fc43.noarch.rpm` while still writing the documented normalized output path. The Fedora release gate helpers now also fail fast with `./scripts/install_packaging_tools.sh --rpm` when `rpmbuild` is missing, so packaging-host blockers are surfaced before the longer gate steps start.

The current Fedora `mvp` package installs `/usr/bin/operance`, the packaged Python source tree, and the tray UI plus STT Python runtime needed for the click-to-talk path under `/usr/lib/operance`. The packaged command defaults to live Linux adapters (`OPERANCE_DEVELOPER_MODE=0`) and `OPERANCE_ENVIRONMENT=production`, so installed-package transcript and tray commands should affect the desktop instead of returning developer-mode simulated success. Wake-word and TTS assets remain optional and outside the packaged support contract.

For the Fedora package path, use the `mvp` bundled-runtime profile:

```bash
./scripts/build_package_artifacts.sh --rpm --bundle-profile mvp --bundle-python .venv/bin/python
./scripts/build_rpm_package.sh --bundle-profile mvp --bundle-python .venv/bin/python
```

That profile vendors the current tray UI and STT runtime Python dependencies into the RPM payload from the local virtualenv, so the artifact carries the packaged tray-plus-click-to-talk runtime checks. Wake-word and TTS assets or backends remain optional and outside the packaged support contract.

After installing the RPM, verify that the package is using live adapters before testing tray voice commands:

```bash
operance --print-config
operance --installed-smoke
python3 scripts/check_installed_mvp_runtime.py --command operance --check-tray-service
```

`operance --print-config` should report `"developer_mode": false`. `operance --about` reports whether the command is a packaged install or source checkout plus package profile, build commit, tag when available, build time, and install root. `operance --installed-smoke` summarizes installed package readiness, warns when the tray service is not active, fails when packaged build identity or runtime dependencies are missing, and catches stale repo-local user units shadowing the packaged service. `preset: disabled` in `systemctl --user status` is normal Fedora preset metadata; verify `Loaded`, `Active`, and the `ExecStart` path instead. `./scripts/run_installed_desktop_smoke.sh` starts/enables the packaged tray user service before checking status, so `Active: inactive (dead)` is a smoke failure.
The packaged tray shows the same diagnostic from `Show installed readiness`, so users can inspect readiness and next steps after install without finding the CLI command first.

Install a built native package artifact through the matching distro package manager:

```bash
./scripts/install_package_artifact.sh --package dist/package-artifacts/deb/operance_0.1.0_all.deb --installer apt --dry-run
./scripts/install_package_artifact.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --dry-run
./scripts/install_package_artifact.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --replace-existing --dry-run
./scripts/install_package_artifact.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --replace-existing --reset-user-services --dry-run
```

Use `--replace-existing` when installing a rebuilt local Fedora RPM that has the same package version as the already installed package. The helper detects whether the RPM package name is installed, removes it when present, and then installs the provided artifact, which prevents `dnf install` from silently leaving an older same-version payload in place.
Use `--reset-user-services` when moving from source-checkout services to the packaged runtime. It stops, disables, and removes only user-scoped Operance systemd units under the current user's systemd config before install, then reloads the user manager so packaged units can be selected.

Run the installed-package smoke when you want one install-to-run proof for a native artifact:

```bash
./scripts/run_installed_package_smoke.sh --dry-run
./scripts/run_installed_package_smoke.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --require-mvp-runtime --dry-run
./scripts/run_installed_package_smoke.sh --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm --installer dnf --require-mvp-runtime --reset-user-services --dry-run
```

This smoke runs the same package-local diagnostic users can run with `operance --installed-smoke`. When `--require-mvp-runtime` is enabled, it also forwards `--check-tray-service` to `scripts/check_installed_mvp_runtime.py`, so stale source-checkout tray units fail the package smoke instead of silently shadowing the installed runtime.

Run the Fedora-first release gate when you want one source-checkout command that builds the RPM artifact and then smokes the installed package:

```bash
./scripts/run_fedora_release_smoke.sh --dry-run
./scripts/run_fedora_release_smoke.sh --reset-user-services --dry-run
./scripts/run_fedora_release_smoke.sh --support-bundle-out /tmp/operance-release-support.tar.gz --dry-run
```

Run the full Fedora gate from the same checkout when you want one command that covers tests, source-checkout smoke, and package-backed release smoke:

```bash
./scripts/run_fedora_gate.sh --dry-run
./scripts/run_fedora_gate.sh --reset-user-services --dry-run
./scripts/run_fedora_gate.sh --support-bundle-out /tmp/operance-release-support.tar.gz --dry-run
```

The setup surface now also exposes `run_release_readiness_gate`, `run_installed_desktop_smoke`, `run_fedora_gate`, `run_fedora_release_smoke`, and `run_installed_rpm_package_smoke` with reset-aware Fedora commands when the current machine has the right checkout and RPM build or install prerequisites, so the same package handoff path stays discoverable from `python3 -m operance.cli --setup-actions`. When Fedora prerequisites are present, setup next steps now surface the release-readiness gate and installed desktop smoke directly.
That same setup surface now also exposes `install_deb_packaging_tools` and `install_rpm_packaging_tools` when the corresponding package-build CLI is missing but the host can install it, so Fedora bring-up no longer stops at a passive `rpmbuild` warning.

Run the release-readiness gate when validating a larger release batch:

```bash
./scripts/run_release_readiness_gate.sh --dry-run
./scripts/run_release_readiness_gate.sh
./scripts/run_release_readiness_gate.sh --run-package-gate
```

The default release-readiness gate runs the package portion as a dry-run so it stays usable during normal development. Use `--run-package-gate` before a release candidate or when explicitly validating a full installed RPM path on the target Fedora KDE Wayland machine. The full package gate keeps the RPM installed so the installed desktop smoke and manual tray click-to-talk checks run against the same package payload.

Run the installed desktop smoke after installing the RPM in the active KDE session:

```bash
./scripts/run_installed_desktop_smoke.sh --dry-run
./scripts/run_installed_desktop_smoke.sh
```

This helper validates the installed runtime and prints the manual click-to-talk commands that still require microphone access and a real tray session.

Remove an installed native package through the matching distro package manager:

```bash
./scripts/uninstall_native_package.sh --installer apt --dry-run
./scripts/uninstall_native_package.sh --installer dnf --package-name operance --dry-run
```

---

## 4. Linux desktop/service dependencies

These are the Linux-side capabilities the project expects to integrate with as implementation moves from portable core work to real desktop control:

- KDE / KWin services for desktop actions
- D-Bus for desktop and system APIs
- NetworkManager for network control
- UPower for power and battery status
- freedesktop notifications
- `xdg-open` / desktop files for app launching
- PipeWire for microphone capture and audio routing
- `pw-play`, `paplay`, or `aplay` for optional spoken-output playback
- systemd user service support for daemon lifecycle

Package names vary by distribution. Treat the list above as the capability checklist, not a distro-specific install command.

---

## 5. Python and runtime stack on Linux

The current stack decision for Linux is:

- Python 3.12+ for the control plane
- SQLite for local audit/state metadata
- PySide6 for tray/setup/confirmation UI
- `PySide6.QtDBus` for UI-facing D-Bus integration
- adapter-based D-Bus integration for the headless daemon
- a local OpenAI-compatible chat-completions server for planner inference
- openWakeWord for wake-word detection
- Moonshine via `moonshine-voice` for local STT
- Kokoro for local TTS

Important architecture rule:

- portable core logic stays platform-neutral
- platform-specific readiness and verified-command rules stay behind platform providers
- Linux-specific behavior must remain behind adapters

---

## 6. What the repo can verify today

The current doctor check can verify these basics:

- Python 3.12+
- active virtualenv
- Linux platform
- KDE Wayland target session

Run it with:

```bash
python3 -m operance.cli --doctor
```

Today the doctor is a readiness check, not a full installer or dependency probe.
The bootstrap script above creates the local Python environment and runs the doctor check, but distro package installation is still documented rather than automated.
The repo-local systemd helpers currently target the tray and voice-loop processes from a source checkout; they do not replace later packaging or first-run setup work.

It now also reports whether the current machine exposes the command-line surfaces used by the first real Linux adapter slice:

- `xdg-open` for app launch fallback
- `notify-send` for notifications
- `gdbus` for desktop-service-backed notification and UPower calls
- `nmcli` for Wi-Fi control
- `wpctl` or `pactl` for audio control
- `pw-record` or `parecord` for microphone frame capture
- `pw-play`, `paplay`, or `aplay` for optional TTS playback
- `systemctl` for repo-local user-service installation and removal plus current user-unit inspection
- `dpkg-deb`, `rpmbuild`, and `tar` for the current package scaffold and artifact build path
- `apt` and `dnf` for the current native-package install and uninstall helpers
- whether the current `operance-tray.service` unit is currently available from either a repo-local or packaged user-unit path
- whether the current `operance-tray.service` unit is currently enabled and active in the user session
- whether the current `operance-voice-loop.service` unit is currently available from either a repo-local or packaged user-unit path
- whether the current `operance-voice-loop.service` unit is currently enabled and active in the user session
- `PySide6` in the current Python environment for the optional tray app
- `openwakeword` in the current Python environment for the optional custom-model wake-word backend
- an external `operance.onnx` wake-word model file in `OPERANCE_WAKEWORD_MODEL`, `.operance/wakeword/operance.onnx`, `~/.config/operance/wakeword/operance.onnx`, or `/etc/operance/wakeword/operance.onnx` when you want to use `--wakeword-model auto`
- `moonshine-voice` in the current Python environment for the optional STT probe and bounded live voice session
- `kokoro-onnx` plus `soundfile` in the current Python environment for the optional TTS probe
- `upower` or battery sysfs for battery status

The CLI now also exposes `python3 -m operance.cli --supported-commands`, which projects the typed command catalog with example transcripts, current live blockers from doctor/setup state, and release-verification status. Use that when a developer needs to answer both “what can I say?” and “why is this command not live on this machine?” from one surface. When a tester only needs the current launch-safe subset, `python3 -m operance.cli --supported-commands --supported-commands-available-only` filters the catalog down to commands that are both live on the current machine and release-verified for the Fedora KDE developer target. That filtered view is now also the preferred next-step path from setup, and the repo-local MVP wrapper can print it through `./scripts/run_mvp.sh --supported-commands --supported-commands-available-only`, so developers can reach the same conservative discovery path from the main bring-up flow instead of remembering a separate raw CLI flag.
That same text-input surface now also covers a small allowlist of developer-oriented modifier chords like `Ctrl+C`, `Ctrl+L`, `Ctrl+R`, `Ctrl+T`, `Ctrl+W`, and `Ctrl+Shift+P` on the existing `keys.press` path instead of stopping at only bare keys like Enter or Escape.
The CLI now also exposes `python3 -m operance.cli --version`, which prints the current Operance version plus source or packaged build identity. Use `python3 -m operance.cli --about` when you need the full machine-readable identity payload, including install mode, package profile, build commit, tag when available, build time, and install root.
The CLI now also exposes `python3 -m operance.cli --support-snapshot`, which aggregates doctor, setup, the full supported-command catalog, the release-verified runnable subset, and voice-loop state into one JSON payload for issue reports and remote debugging. Home-directory paths are redacted by default so the payload is safer to paste into public issues, `--support-snapshot-raw` opts back into exact paths when maintainers need them, and `--support-snapshot-out <path>` can persist that same JSON to a file without changing stdout behavior.
That same support snapshot now also includes build identity metadata, including the Operance version plus git branch, commit, and dirty-state details when those checkout details are available, so Linux bug reports can be matched to an exact source tree instead of relying on free-form prose.
That same support snapshot now also carries a bounded tail of recent audit-log entries, so Linux issue reports include recent runtime turns alongside environment and setup state instead of requiring a second `--audit-log` dump.
That same file-output path is now also available through `./scripts/run_mvp.sh --support-snapshot --support-snapshot-out <path>`, so the repo-local MVP launcher can collect one redacted issue-report artifact without bypassing the wrapper.
The CLI now also exposes `python3 -m operance.cli --support-bundle`, which writes one redacted `tar.gz` support bundle under `data_dir/support-bundles/` by default. That archive packages the aggregated support snapshot, support-summary help text, current voice-loop runtime snapshot, and any available `operance-tray.service` or `operance-voice-loop.service` journal excerpts into one issue-report artifact instead of forcing developers to attach several separate files.
That same bundle manifest now also carries the current build identity, so maintainers can see the reported version and checkout state before unpacking the internal snapshot files.
When Operance chooses that bundle path itself, the generated archive filename now also includes the current version as well as the timestamp, so Linux issue-report artifacts stay sortable once multiple builds are in circulation.
That same bundle path can also be written to an explicit location through `python3 -m operance.cli --support-bundle --support-bundle-out <path>`, and missing service logs are recorded as bundle warnings instead of failing the whole archive.
That same archive path is now also available through `./scripts/run_mvp.sh --support-bundle --support-bundle-out <path>`, so the repo-local MVP launcher can collect the preferred redacted issue-report artifact without dropping back to the lower-level CLI.
The contributor-facing bug-report flow now points at that support bundle first, with the raw `--support-snapshot` JSON kept as the inline fallback when a maintainer specifically wants machine-readable details pasted directly into an issue.

To run the current command-backed Linux adapters instead of the mock developer adapters:

```bash
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "what time is it"
OPERANCE_DEVELOPER_MODE=0 python3 -m operance.cli --transcript "what is my battery level"
```

To probe the current Linux microphone and bounded or continuous voice paths:

```bash
python3 -m operance.cli --audio-list-devices
python3 -m operance.cli --audio-capture-frames 3
python3 -m operance.cli --wakeword-probe-frames 3
python3 -m operance.cli --wakeword-calibrate-frames 20
python3 -m operance.cli --wakeword-eval-frames 50
python3 -m operance.cli --voice-self-test
python3 -m operance.cli --click-to-talk
./scripts/run_click_to_talk.sh
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --wakeword-probe-frames 3 --wakeword-model auto
python3 -m operance.cli --stt-probe-frames 10
python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin --tts-output /tmp/operance-hello.wav
python3 -m operance.cli --tts-probe-text "Hello from Operance" --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin --tts-output /tmp/operance-hello.wav --tts-play
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --voice-session-frames 40 --wakeword-model auto
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx --voice-session-tts-output-dir /tmp/operance-spoken --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin
python3 -m operance.cli --voice-session-frames 40 --wakeword-model /path/to/operance.onnx --voice-session-tts-output-dir /tmp/operance-spoken --voice-session-tts-play --tts-model /path/to/kokoro.onnx --tts-voices /path/to/voices.bin
python3 -m operance.cli --voice-loop --wakeword-model /path/to/operance.onnx
python3 -m operance.cli --voice-loop --wakeword-model auto
python3 -m operance.cli --voice-loop --voice-loop-max-commands 2 --wakeword-model /path/to/operance.onnx
./scripts/run_voice_loop.sh --args-file .operance/voice-loop.args
./scripts/run_voice_loop.sh -- --wakeword-model /path/to/operance.onnx
./scripts/run_voice_loop.sh -- --voice-loop-max-commands 2 --wakeword-model /path/to/operance.onnx
```

An optional repo-local `.operance/voice-loop.args` file is read first, then `~/.config/operance/voice-loop.args` is used as a fallback, with one CLI token per line and blank lines or `#` comments ignored. Use those files to keep model paths or loop limits out of the systemd unit itself.

To inspect or run the current tray surface:

```bash
python3 -m operance.cli --tray-snapshot
python3 -m operance.cli --tray-run
./scripts/run_tray_app.sh
```

To inspect the projected setup-status snapshot for future first-run UI work:

```bash
python3 -m operance.cli --setup-snapshot
python3 -m operance.cli --setup-actions
python3 -m operance.cli --setup-app
python3 -m operance.cli --setup-run-action install_ui_backend --setup-dry-run
python3 -m operance.cli --setup-run-action install_voice_loop_service --setup-dry-run
python3 -m operance.cli --setup-run-action install_voice_loop_user_config --setup-dry-run
python3 -m operance.cli --setup-run-action enable_voice_loop_service --setup-dry-run
python3 -m operance.cli --setup-run-action probe_planner_health --setup-dry-run
python3 -m operance.cli --setup-run-action build_rpm_package_artifact --setup-dry-run
python3 -m operance.cli --setup-run-recommended --setup-dry-run
```

The recommended setup runner now collapses overlapping repo-local setup steps when one command already subsumes the others. For example, a missing tray service plus missing optional voice backends now resolves to one `install_local_linux_app.sh --voice` recommendation instead of separate local-app, UI, and voice commands. Planner readiness is now projected separately: when planner fallback is enabled but the configured endpoint is unhealthy, the same setup surface adds a dedicated `python3 -m operance.cli --planner-health` recommendation instead of pretending that bootstrap or service setup will fix the planner path.

When the current machine already satisfies the base runtime checks and exposes an STT backend, the setup action surface now also exposes a dedicated `install_voice_loop_service` action for `operance-voice-loop.service`. The same setup surface now also reports whether `voice-loop.args` is already available from user or system config and exposes `install_voice_loop_user_config` for seeding `~/.config/operance/voice-loop.args`. Once the host is already voice-capable, the default recommended command set now also promotes those missing voice-loop service or config steps automatically instead of leaving them as manual side actions. When tray or voice-loop services already exist but are disabled or inactive, the same projected setup surface now switches those steps to `enable` or `restart` remediation through `control_systemd_user_services.sh` instead of pointing back at reinstall commands. Packaging-capable machines now also get projected package scaffold and per-format package build actions, and once the default package artifact paths exist the same setup surface exposes matching native package install and uninstall actions. That same setup surface now also projects bounded voice-diagnostic actions for audio device listing, microphone capture, wake-word probing, threshold calibration for the built-in energy detector, idle false-activation evaluation, a model-backed wake-word probe when an external asset is discoverable, STT probing, TTS probing, and one composite `voice-self-test` summary action.
When `voice-loop.args` is already present but still reflects the raw fallback wake-word defaults, the same recommended command set now also promotes the one-step `--apply-suggested-threshold` calibration flow plus idle false-activation evaluation with `--use-voice-loop-config`, so setup can guide the next tuning step instead of only reporting the warning.
When the current machine already satisfies the wake-word backend plus asset checks, that same setup action surface now also exposes `configure_voice_loop_wakeword_model`, which seeds `--wakeword-model auto` into the user-scoped voice-loop args file instead of forcing a manual edit before the background loop can reuse the discovered external model asset.

For TTS assets, the current runtime now looks in this order:

- `OPERANCE_TTS_MODEL` / `OPERANCE_TTS_VOICES`
- `.operance/tts/kokoro.onnx` and `.operance/tts/voices.bin` in the current checkout
- `~/.config/operance/tts/kokoro.onnx` and `~/.config/operance/tts/voices.bin`
- `/etc/operance/tts/kokoro.onnx` and `/etc/operance/tts/voices.bin`

To run the checked-in deterministic demo assets against mock adapters:

```bash
./scripts/run_demo.sh
```

---

## 7. Current Linux handoff checklist

Before starting Linux-specific implementation work, the machine should satisfy all of the following:

- boot into a KDE Plasma Wayland session
- report `Linux` as the current platform
- have Python 3.12+ available
- support `.venv` creation and local editable installs
- have PipeWire active
- have a working D-Bus user session
- use systemd user services
- expose NetworkManager, UPower, and notification services
- have `xdg-open` available
- expose `pactl` for input discovery and `pw-record` or `parecord` for capture probes
- expose `wl-copy` and `wl-paste` for clipboard integration
- expose `wtype` for active-window text injection on Wayland, and only advertise those commands as live when the compositor actually accepts the virtual keyboard protocol
- surface missing `wl-copy`, `wl-paste`, and `wtype` in setup and onboarding flows, not only in doctor output
- distinguish missing Wayland tooling from “running outside the active Wayland user session” by checking socket accessibility in doctor and setup output
- distinguish “`wtype` is installed” from “the current compositor will accept injected key events” by probing the backend in doctor and setup output
- when `apt` or `dnf` is present, surface the exact install command for `wl-clipboard` or `wtype` in setup output instead of only generic remediation text
- provide a repo-local `./scripts/install_wayland_input_tools.sh` helper so setup can point at one runnable command for installing `wl-clipboard`, `wtype`, or both

Recommended validation sequence:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m operance.cli --doctor
```

---

## 8. What is still deferred even on Linux

Having the right Linux machine does **not** mean all Linux-target features are already implemented.

Still deferred in the repo at the moment:

- a fully bundled installed always-on voice runtime beyond the current continuous CLI loop plus the repo-local and package-scaffold service paths
- a bundled Operance wake-word model asset and tuned defaults beyond the current optional custom-model openWakeWord path
- richer speech-to-text beyond the current optional Moonshine-backed bounded session
- richer or fully bundled text-to-speech beyond the current optional Kokoro probe and bounded response-playback path
- broader KDE desktop execution coverage beyond the current implemented action slice
- richer tray UI beyond the current minimal status surface

The current repository contains a broader implemented Linux runtime beyond the supported verified command subset above, including voice probes, planner tooling, tray surfaces, and additional KDE action paths. Those broader surfaces remain implementation inventory, not part of the supported support contract, until they are live-verified and graduate into `--supported-commands --supported-commands-available-only`.

Broader implemented Linux-backed paths that are not all release-verified yet:

- app focus prefers a KWin scripting bridge over the session bus
- app launch reuses the existing executable, desktop-file, and `xdg-open` fallback path, and now also normalizes localhost dev-server targets like `localhost:3000` to `http://localhost:3000` before live launch
- spoken dev-server phrases like `browse to localhost 3000` and `open url localhost port 3000` now normalize into that same launch path, which keeps the developer MVP usable without requiring literal punctuation in every voice transcript
- explicit URL phrases like `browse to docs.python.org/3` and `open url github.com/openai/openai-python` now also normalize bare hostnames to `https://...`, so developer docs and repository browsing work without widening the generic app-launch path
- app quit reuses the same KWin window-close path and now executes after an in-session confirmation reply
- window listing and window switching prefer KWin `WindowsRunner` over the session bus
- window minimization, maximization, fullscreen on or off, keep-above or keep-below on or off, shade on or off, all-desktops on or off, and restore prefer a KWin scripting bridge over the session bus
- window close uses the same KWin scripting path and now executes after an in-session confirmation reply
- desktop folder deletion and desktop file deletion use the existing file adapter path and now execute after an in-session confirmation reply
- desktop entry rename and move use the existing file adapter path, now execute after confirmation, and can be undone in-session
- desktop file and folder open requests now use the same file adapter path, with live Linux execution through `xdg-open`
- recent-file open requests now resolve against the current file adapter’s recent-file list for the desktop root before opening the matched file through the same `xdg-open` path
- microphone discovery and frame capture now use `pactl` plus `pw-record` or `parecord`, with a default-device fallback when the discovery backend cannot reach the current session audio server
- wake-word probing now consumes captured PCM frames through a simple sustained-energy detector with a short activation streak, which validates the frame-driven Linux voice path without claiming model-backed inference yet
- the same built-in wake-word path can now also sample ambient microphone input and suggest a tighter threshold for noisy rooms based on detector confidence, while still reporting raw ambient peak reference without pretending to calibrate the optional model-backed backend
- the same built-in wake-word path can now also report idle false activations over a bounded captured frame sample, which gives the repo an honest local surface for the plan’s wake-word false-activation checkpoint without claiming a full long-run evaluation harness yet
- that bounded idle evaluation now also reports the current threshold, required activation streak, peak false-activation confidence, and a ready-to-run voice-loop config update command when false activations are observed
- wake-word probing can also use a custom openWakeWord model file when `openwakeword` is installed and `--wakeword-model` is provided, and `--wakeword-model auto` now resolves the same external asset from the standard Linux search paths without the repo shipping a default Operance model asset yet
- the CLI can now also run a bounded `voice-self-test` that combines capture, wake-word idle evaluation, and optional STT/TTS probes into one `ok` or `partial` summary for Linux handoff work, and it now marks idle false activations as a real warning instead of treating wake-word as healthy by default
- wake-word calibration now also returns a ready-to-run `update_voice_loop_user_config.sh --wakeword-threshold ...` command so the suggested threshold can be applied to the user-scoped background-loop config without manually editing `voice-loop.args`
- STT probing now consumes captured PCM frames through an optional Moonshine-backed transcriber when `moonshine-voice` is installed, which validates the next voice stage without claiming daemon-integrated live transcription yet
- a bounded manual click-to-talk session can now feed captured microphone audio straight through STT into the daemon without wake-word gating, which is the preferred MVP invocation path for local developer bring-up
- a bounded live voice session can now chain wake-word detection, optional Moonshine-backed STT, and daemon transcript handling through one captured frame session, including confirmation follow-ups without a second wake word
- a continuous live voice loop can now keep listening across multiple commands on one capture stream, with optional command or frame stop criteria for regression and an interrupt-safe summary on exit
- the repo now also includes `scripts/run_voice_loop.sh`, a thin launcher for the continuous voice loop from the checked-out tree, and it can now load extra CLI tokens from repo-local or user-scoped args files
- that continuous loop now also writes a repo-local runtime status heartbeat, and the CLI plus doctor/setup surfaces can inspect its latest counters, last transcript or response, and heartbeat freshness
- the repo now also includes repo-local systemd user-service install and removal helpers for the continuous voice loop
- the repo-local voice-loop config and optional voice-asset discovery now use only `operance` locations and filenames, so setup, doctor, and runtime tooling stay aligned on one path contract
- doctor, setup, and the local install scripts now also detect legacy pre-rename tray or voice-loop units plus old user config, recommend one dedicated `./scripts/migrate_legacy_install.sh` path, and block fresh `operance` service installation until that migration runs so rename cleanup happens deliberately instead of producing duplicate user services
- the setup next-step surface now points at one-command support-bundle collection, and `./scripts/run_mvp.sh` exposes the same bundle path, so Linux bring-up can jump straight into one redacted issue-report artifact when something still fails after doctor or setup checks
- the setup action surface now also exposes both `Collect support bundle` and `Collect support snapshot`, so the setup app and structured action API can execute the preferred archive path directly while keeping the raw JSON fallback available for inline issue reports
- packaging-ready Fedora hosts now also see the right release path in setup next steps, surfacing either `./scripts/run_fedora_release_smoke.sh` or the installed-RPM smoke command when the default RPM artifact already exists instead of leaving that release gate buried only in the action catalog
- once the current checkout is also running from a ready Python environment, that same setup next-step surface now prefers `./scripts/run_fedora_gate.sh`, so Fedora developer validation becomes one explicit command instead of a manual chain of `pytest`, source-checkout smoke, and release smoke steps
- the repo now also includes `./scripts/run_checkout_smoke.sh`, which runs `--version`, `--doctor`, `--setup-actions`, the runnable-only supported-command subset, and `--support-bundle` in one fail-fast sequence for Linux contributor bring-up and issue reproduction
- the runtime snapshot can now be projected into a tray-state model, and an optional PySide6 tray app can expose state, pending confirmation, a real confirmation dialog for gated actions, failure notifications, and undo actions from the same daemon session
- that same tray app now also exposes a one-shot click-to-talk action on both the tray menu and primary tray activation, running a bounded manual voice session against the tray daemon itself so last-command preview, confirmation replies, and undo stay in the same session
- that same tray-state model now also includes repo-local voice-loop runtime state, activity, and heartbeat warnings, so background-loop health is visible from the same tray surface instead of being limited to doctor or setup output
- when that repo-local heartbeat is stale, the tray surface now also exposes a direct restart path for `operance-voice-loop.service` instead of limiting the remediation to setup output
- MCP now also exposes the same repo-local voice-loop restart control through `operance.restart_voice_loop_service`, keeping service remediation on the existing validated control surface instead of forcing clients to shell out separately
- the tray now also exposes the background voice loop’s last transcript and last response from the repo-local runtime status file without letting those background replies overwrite the tray session’s own last-command preview
- that tray confirmation dialog now also exposes an explicit Cancel action inside the dialog itself, matching the plan’s confirmation UX requirement instead of forcing cancellation back through the tray menu
- tray notifications now also surface planner-fallback failures as a distinct warning instead of collapsing them into the same generic unmatched notification as normal command misses
- the tray session and long-lived MCP sessions can now also clear planner cooldown and recent planner-error state without restarting the daemon when the local planner endpoint recovers
- pending confirmation views in that tray dialog and in MCP confirmation resources now also expose plan source and risk tier metadata before execution
- pending confirmation snapshots and MCP confirmation resources now also expose the configured confirmation timeout plus a human-readable timeout explanation, and late confirmation replies now expire closed instead of executing stale plans
- audio volume, mute control, and mute-status inspection use `wpctl` or `pactl`, with very high volume changes now routed through confirmation first
- notifications prefer `org.freedesktop.Notifications` over the session bus
- battery status prefers UPower over the system bus
- clipboard read, copy, and clear now use `wl-paste` and `wl-copy`, with clipboard mutations undoable in-session
- copying the active selection into the clipboard now also uses the same `wtype` plus clipboard path, with undo restoring the previous clipboard contents instead of claiming to undo the active app selection
- clipboard paste into the active window and direct text typing now use `wtype`, so the current Linux runtime can inject text into the focused Wayland window without adding broader input automation yet
- supported key presses such as Enter and Escape now also use that same `wtype` path, which keeps submit and navigation actions on the same narrow Wayland text-input backend instead of growing a separate macro layer
- setup snapshots and setup actions now also surface missing Wayland clipboard or text-input backends as blocked recommendations, so onboarding does not pretend those runtime paths are ready when `wl-copy`, `wl-paste`, or `wtype` are absent
- that same text-input surface now also probes real compositor support, so KWin sessions that reject the virtual keyboard protocol block text injection up front and point back to doctor output instead of pretending the backend is usable just because `wtype` is installed
- Wi-Fi status, Wi-Fi toggling, current-Wi-Fi disconnect, and saved-network connection use NetworkManager through `nmcli`, with disconnect, disable, and saved-network connection routed through confirmation first
- planner fallback can call a local chat-completions endpoint when `OPERANCE_PLANNER_ENABLED=1` and the transcript is final, unmatched, and above the configured confidence threshold
- planner prompt generation now includes per-tool required-arg hints, confirmation and risk hints, plus example transcripts, so the local planner sees a much tighter tool contract before Linux execution ever begins
- planner transport calls now support bounded retries, and the CLI can probe the sibling `/v1/models` or `/health` surfaces before relying on the local endpoint for live fallback
- planner fallback now also enters a bounded cooldown after repeated planner failures, and the live runtime plus MCP planner snapshots expose the current failure count and remaining cooldown time for Linux-side debugging
- the CLI can now print the exact planner prompt messages for a transcript before the request wrapper is built, which makes prompt regressions easier to inspect on a Linux dev machine
- the CLI can also inject explicit short-lived planner context entries into those prompt or request inspections, which makes local planner debugging possible without waiting for a live daemon session to populate the context window
- those adapter paths still retain command and sysfs fallbacks when the preferred desktop service is unavailable or times out
- confirmation state is still session-local; the current tray app provides a minimal GUI confirmation surface, but broader cross-session confirmation UX is still deferred
- MCP-based confirmation resolution is available only within the same long-lived MCP session, not across separate one-shot CLI invocations
- pending confirmation state now also exposes a plain-language action preview plus source and risk metadata for future UI and MCP clients
- live MCP runtime resources now expose session status and pending confirmation details for future external clients
- the same runtime status surface now also exposes the last plan source, last routing reason, last planner error, and the active short-lived planner context window, which is useful when debugging live planner fallback on a Linux desktop session
- MCP clients can now also read a dedicated `operance://runtime/planner` resource for that planner-focused runtime snapshot instead of parsing the broader session status payload
- MCP clients can now also read `operance://runtime/voice-loop-status` for the latest repo-local continuous-loop heartbeat and activity counters instead of shelling out to `operance.cli --voice-loop-status`
- pending confirmation inspection now also includes structured action metadata, the original triggering transcript, affected resources, and rollback hints for future UI and MCP clients
- the local SQLite audit log now also preserves plan source, routing reason, and planner error metadata, including unmatched planner-failure turns, so Linux-side debugging is not limited to live session state
- the CLI and MCP surfaces can now also read recent audit entries directly through `operance.cli --audit-log` and `operance://runtime/audit`, which removes the need to inspect the SQLite file by hand for normal debugging
- the MCP tool catalog now also exposes per-tool result schemas, allowed side-effect metadata, example transcripts, and undo summaries or non-undo reasons, so Linux-side clients can inspect approved outcomes, likely invocation shapes, impact, and rollback behavior without reverse-engineering responses
- desktop-scoped file actions now reject path-like entry names before execution, which closes a missing safety check in the earlier desktop file slice
- the developer CLI can now replay session-scoped MCP fixtures locally, which is useful for confirming gated desktop actions without wiring a separate MCP client first
- undo availability is now exposed through runtime status and MCP session resources, and stateful MCP sessions can revert the last reversible action directly
- MCP fixture replay can now serve as a lightweight regression surface for session-scoped Linux action flows by asserting expected result subsets
- the optional PySide6 setup app now surfaces both the projected environment checks and the executable setup actions, supports dry-run previews, and shows per-action result details, which brings the current first-run UI closer to the setup-wizard milestone without claiming a fully polished installer flow yet
- the low-level microphone, wake-word, and STT probe commands remain available independently, while the new continuous CLI loop now drives the daemon end to end without claiming a separate background-managed voice service yet
- the repo still does not ship a default custom wake-word model for `operance`, so model-backed wake detection still depends on an external asset even though `--wakeword-model auto` can now resolve that asset from the standard search paths

---

## 9. Recommended reference order

When setting up the Linux machine, refer to documents in this order:

1. [README.md](../../README.md)
2. [CONTRIBUTING.md](../../CONTRIBUTING.md)
3. [overview.md](../architecture/overview.md)
4. [linux.md](./linux.md)
5. [CHANGELOG.md](../../CHANGELOG.md)
6. [tech.md](./tech.md)

Use `README.md` for current runnable behavior, `CONTRIBUTING.md` for
contributor workflow expectations, `overview.md` for module and platform
boundaries, `linux.md` for Linux setup and integration status, `CHANGELOG.md`
for completed slices, and `tech.md` for stack decisions.
