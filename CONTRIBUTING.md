# Contributing to Operance

Operance is a Linux-first desktop action runtime with a portable core and
per-platform execution adapters. This repository is the open-source local core.
Keep contributions inside that boundary unless a change is explicitly about a
future hosted layer or packaging surface.

## Scope

The open-source local core in this repo includes:

- the local daemon and runtime loop
- action models, validators, policy, and executor
- desktop adapters
- the local voice loop
- the MCP server and local control surfaces
- repo-local setup and packaging helpers

Linux and KDE/Wayland are the current delivery target. Windows and macOS are
roadmap phases behind the same portable core, not parallel implementation
targets today.

## Current public handoff focus

The current public position is:

- Fedora KDE Plasma on Wayland
- source checkout as the primary supported path
- installed RPM as the secondary `mvp` runtime path
- tray plus click-to-talk as the default interaction model

This is still a founder-maintained developer release. Small, focused pull requests are much easier to review and land than large rewrites or broad refactors.

The highest-value contributions right now are:

- packaging or installer work that moves the native Fedora path closer to tray plus click-to-talk out of the box
- Linux runtime fixes that improve the current MVP path instead of widening the command surface for its own sake
- doctor, setup, support-bundle, and release-gate improvements that make outside-developer support cheaper
- docs, issue triage, and reproducible bug reports that reduce onboarding friction

Lower priority right now:

- broad new cross-platform abstractions before Linux needs them
- wake-word-first product changes that reduce launch reliability
- speculative command breadth that does not materially improve the current MVP

## Ways anyone can contribute

You do not need to land a large code feature to help. Useful contribution shapes include:

- testing the current Fedora KDE supported path and reporting reproducible failures
- improving docs, release notes, quickstarts, and troubleshooting guidance
- adding or tightening tests around setup, packaging, doctor, support bundles, or the typed runtime
- fixing focused Linux runtime, tray, or click-to-talk defects
- improving issue reports by attaching support bundles, exact commands, and machine details

If you want to propose a larger feature, open an issue first and keep the initial patch on the smallest runnable slice.

Read [docs/release/public-handoff.md](docs/release/public-handoff.md) before proposing work that broadens the public surface, and [docs/release/fedora-checklist.md](docs/release/fedora-checklist.md) before changing the current release gate.

## Architecture boundary

Use these boundaries consistently:

- portable core logic belongs under `src/operance/`
- platform-specific readiness, verification, setup metadata, setup actions, and release-gate guidance belong under `src/operance/platforms/`
- platform-specific execution stays behind `src/operance/adapters/`
- do not leak Linux-only APIs into planner, policy, validator, executor, or
  typed action models
- future Windows and macOS work should add adapters, not fork the runtime model

Read [docs/architecture/overview.md](docs/architecture/overview.md) before
changing module boundaries, and read
[docs/architecture/adapter-authoring.md](docs/architecture/adapter-authoring.md)
before adding another OS backend.

Also read:

- [SECURITY.md](SECURITY.md) before reporting vulnerabilities
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating in issues, pull
  requests, or review threads

## Development setup

Bootstrap the local development environment with:

```bash
./scripts/install_linux_dev.sh
```

Or use the manual flow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Optional extras:

```bash
python3 -m pip install -e ".[dev,ui]"
python3 -m pip install -e ".[dev,voice]"
```

## Workflow expectations

Follow the repo workflow in `AGENTS.md` and keep changes small:

- use TDD for non-trivial implementation work
- make the smallest viable change that satisfies the current feature
- keep docs in sync with behavior in the same change
- preserve Linux-first scope and avoid speculative cross-platform abstractions
- commit completed feature slices with concrete messages

Before opening a pull request, run:

```bash
.venv/bin/python -m pytest
```

GitHub Actions also runs the same test suite plus minimal CLI smoke checks on
pushes and pull requests through `.github/workflows/ci.yml`.

For a quick safe baseline on a new machine or before filing a bug, run:

```bash
./scripts/run_checkout_smoke.sh
```

For the full Fedora checkout gate, run:

```bash
./scripts/run_fedora_gate.sh --dry-run
```

Use these commands for quick local inspection:

```bash
.venv/bin/python -m operance.cli --version
.venv/bin/python -m operance.cli --doctor
.venv/bin/python -m operance.cli --support-bundle
.venv/bin/python -m operance.cli --support-snapshot
.venv/bin/python -m operance.cli --print-config
```

## Pull requests

A good pull request for this repo should:

- describe the user-visible behavior or developer workflow change
- list the exact verification commands you ran
- note doc updates in `README.md`, `docs/requirements/linux.md`, and
  `CHANGELOG.md` when applicable
- call out any deferred work or platform limitations explicitly
- keep the current public handoff support contract honest instead of silently widening claims

## Issues

Use the issue templates for reproducible bugs or feature requests. Include:

- do not use the normal bug-report flow for security issues; follow
  [SECURITY.md](SECURITY.md) instead

- platform and desktop session details
- `.venv/bin/python -m operance.cli --version` output so maintainers can tie the report back to an exact version and checkout
- `.venv/bin/python -m operance.cli --support-bundle` output or the saved archive path when the bug involves setup, voice, tray, or Linux runtime behavior
  The bundle is redacted by default and is the preferred issue artifact because it packages the support snapshot, voice-loop runtime snapshot, and any available service log excerpts in one file.
- `.venv/bin/python -m operance.cli --support-snapshot` output only when the raw JSON is easier to inspect inline
  This output also redacts home-directory paths by default; use `--support-snapshot-raw` only when exact local paths matter.
- whether you are using developer mode, mock adapters, or live Linux adapters
- exact CLI commands, transcripts, or setup actions involved
- expected versus actual behavior

If you are not ready to submit code, high-quality issue reports and doc fixes are still useful contributions.

## License

By contributing to this repository, you agree that your contributions are
submitted under the [MIT License](LICENSE).
