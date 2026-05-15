# Public Developer Alpha

Status: Current public handoff  
Type: Outside-developer alpha state  
Audience: Early adopters, contributors, maintainers

---

## 1. Position

Operance is currently published as a **Fedora KDE Plasma Wayland developer alpha**.

This is intentionally narrower than a broader public alpha. The goal is to let outside developers try the product, file useful issues, and contribute to the Linux-first MVP without pretending the packaged path is already a zero-setup consumer install.

Current positioning:

- Linux first
- Fedora KDE first
- local first
- tray plus click-to-talk first
- wake word secondary to launch reliability

Current supported command subset on that target:

- `open <app name>` and URL-like launch targets such as `open localhost:3000`
- `focus <app name>`
- `what time is it`
- `what is my battery level`
- `wifi status`
- `what is the volume`
- `is audio muted`

This is still a founder-maintained alpha. Expect a narrow support contract, fast iteration, and a bias toward small, focused fixes over broad rewrites.

---

## 2. What is supported now

Primary supported alpha path:

- source checkout
- optional `ui` and `voice` extras installed
- `./scripts/run_mvp.sh` for the default interaction path
- `./scripts/run_beta_smoke.sh` for a safe baseline

Secondary supported alpha path:

- Fedora RPM install of the `mvp` runtime profile
- validated through `./scripts/run_fedora_alpha_gate.sh --reset-user-services`
- useful for proving packaging, install, installed-command smoke behavior, bundled tray plus STT runtime availability, and live-adapter defaults for the packaged command

The Fedora gate now defaults to:

- `./scripts/build_package_artifacts.sh --rpm --bundle-profile mvp`
- `./scripts/run_installed_beta_smoke.sh --require-mvp-runtime --reset-user-services`

That verifies the installed package can expose the tray UI backend and STT backend through `operance --doctor`, and that `operance --print-config` reports live execution rather than developer-mode simulation. Actual tray interaction, app launching, and microphone capture still require a human desktop-session smoke before tagging a release.

What is already proven on the current target machine:

- the full test suite passes
- the source-checkout beta smoke path works
- the Fedora alpha gate can build the RPM artifact and validate the installed command path plus packaged MVP runtime checks
- the installed command can produce a support bundle
- `operance.cli --supported-commands --supported-commands-available-only` now exposes only the release-verified alpha command subset above, not the broader implemented runtime surface

---

## 3. What is not yet claimed

This repo does **not** currently claim:

- a broader public alpha across distros or desktop environments
- Windows or macOS delivery
- wake-word-first as the default product interaction
- a supported native package that already bundles optional UI and voice Python backends
- a zero-setup consumer install story

The current native package path still depends on host-provided optional Python
backends when you want the tray UI, model-backed wake word, STT, or TTS.

---

## 4. How to try it

Source-checkout path:

```bash
./scripts/install_linux_dev.sh --ui --voice
.venv/bin/python -m operance.cli --version
./scripts/run_mvp.sh
./scripts/run_beta_smoke.sh
```

Fedora checkout gate:

```bash
./scripts/run_fedora_alpha_gate.sh --reset-user-services --dry-run
```

If you are validating the full Fedora path for real, use:

```bash
./scripts/run_fedora_alpha_gate.sh --reset-user-services
```

If the gate stops immediately with `rpmbuild not found`, install the build tool first:

```bash
./scripts/install_packaging_tools.sh --rpm
```

For the exact release stop line, use [fedora-alpha-checklist.md](./fedora-alpha-checklist.md).
For the beta stop line, use [beta-readiness.md](./beta-readiness.md).
For the current maintainer release sequence, use [release-plan.md](./release-plan.md).

---

## 5. How anyone can contribute

Useful contribution paths right now:

- test the Fedora KDE Wayland path and report reproducible failures
- improve onboarding, quickstart, troubleshooting, and release docs
- add or tighten tests around setup, packaging, doctor, release gates, and the typed runtime
- fix focused Linux runtime issues that improve tray plus click-to-talk reliability
- harden the packaged tray plus click-to-talk path and improve installed-RPM desktop smoke coverage

If you are not sending code, high-quality bug reports still help materially.

Start with [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## 6. How to file useful issues

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
- whether the issue is in tray plus click-to-talk, packaging or install, or a narrower runtime command path

Use [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full contribution workflow and [linux.md](../requirements/linux.md) for the detailed Linux setup inventory.
