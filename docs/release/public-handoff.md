# Public Handoff

Status: Current public handoff  
Type: Outside-developer release state  
Audience: Early adopters, contributors, maintainers

---

## 1. Position

Operance is currently published as a **Fedora KDE Plasma Wayland developer
release**.

This release is intentionally narrow. It is meant for developers and early
testers who can run documented commands, collect support bundles, and report
useful failures. It is not a broad consumer desktop launch.

Current positioning:

- Linux first
- Fedora KDE first
- local first
- tray plus click-to-talk first
- wake word secondary to launch reliability
- Windows and macOS as future adapter targets only

Current supported command subset on that target:

- `open <app name>` and URL-like launch targets such as `open localhost:3000`
- `focus <app name>`
- `what time is it`
- `what is my battery level`
- `wifi status`
- `what is the volume`
- `is audio muted`

---

## 2. What Is Supported Now

Primary supported path:

- source checkout
- optional `ui` and `voice` extras installed
- `./scripts/run_mvp.sh` for the default interaction path
- `./scripts/run_checkout_smoke.sh` for a safe baseline

Secondary supported path:

- Fedora RPM install of the `mvp` runtime profile
- validated through `./scripts/run_fedora_gate.sh --reset-user-services`
- useful for proving packaging, install, installed-command smoke behavior,
  bundled tray plus STT runtime availability, and live-adapter defaults for the
  packaged command

The Fedora gate defaults to:

- `./scripts/build_package_artifacts.sh --rpm --bundle-profile mvp`
- `./scripts/run_installed_package_smoke.sh --require-mvp-runtime --reset-user-services`

That verifies the installed package can expose the tray UI backend and STT
backend through `operance --doctor`, and that `operance --print-config` reports
live execution rather than developer-mode simulation. Actual tray interaction,
app launching, and microphone capture still require a human desktop-session
smoke before tagging a release.

What is already proven on the current target machine:

- the full test suite passes
- the source-checkout smoke path works
- the Fedora gate can build the RPM artifact and validate the installed command
  path plus packaged MVP runtime checks
- the installed command can produce a support bundle
- `operance.cli --supported-commands --supported-commands-available-only`
  exposes only the release-verified command subset above, not the broader
  implemented runtime surface

---

## 3. What Is Not Yet Claimed

This repo does **not** currently claim:

- broad distro or desktop-environment support
- Windows or macOS delivery
- wake-word-first as the default product interaction
- a fully bundled consumer installer with all model assets included
- a zero-setup consumer install story

Wake-word and TTS assets remain optional. The supported path is tray plus
click-to-talk on Fedora KDE Wayland.

---

## 4. How To Try It

Source-checkout path:

```bash
./scripts/install_linux_dev.sh --ui --voice
.venv/bin/python -m operance.cli --version
./scripts/run_mvp.sh
./scripts/run_checkout_smoke.sh
```

Fedora checkout gate:

```bash
./scripts/run_fedora_gate.sh --reset-user-services --dry-run
```

If you are validating the full Fedora path for real, use:

```bash
./scripts/run_fedora_gate.sh --reset-user-services
```

If the gate stops immediately with `rpmbuild not found`, install the build tool
first:

```bash
./scripts/install_packaging_tools.sh --rpm
```

For the exact release stop line, use [fedora-checklist.md](./fedora-checklist.md).
For the release-readiness stop line, use [release-readiness.md](./release-readiness.md).
For the current maintainer release sequence, use [release-plan.md](./release-plan.md).

---

## 5. How Anyone Can Contribute

Useful contribution paths right now:

- test the Fedora KDE Wayland path and report reproducible failures
- improve onboarding, quickstart, troubleshooting, and release docs
- add or tighten tests around setup, packaging, doctor, release gates, and the
  typed runtime
- fix focused Linux runtime issues that improve tray plus click-to-talk
  reliability
- harden the packaged tray plus click-to-talk path and improve installed-RPM
  desktop smoke coverage

If you are not sending code, high-quality bug reports still help materially.

Start with [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## 6. How To File Useful Issues

When possible, attach:

- `operance --version` or `.venv/bin/python -m operance.cli --version`
- a support bundle from the same environment:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

Also include:

- Fedora version
- KDE Plasma version
- session type
- whether you used source checkout or installed RPM
- the exact command or script that failed
- expected versus actual behavior
- whether the issue is in tray plus click-to-talk, packaging or install, or a
  narrower runtime command path

Use [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full contribution workflow
and [linux.md](../requirements/linux.md) for the detailed Linux setup inventory.
