# Public Handoff

Status: Current public handoff  
Type: Public beta release state
Audience: Early adopters, contributors, maintainers

---

## 1. Position

Operance is currently published as a **Fedora KDE Plasma Wayland public beta**.

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

- `open <app name>` and URL-like launch targets such as `open localhost:3000`, plus safe app and URL launch chains such as `open firefox and load localhost:3000`
- narrow launch plus notification phrases such as `open firefox and notify me`
- `focus <app name>` and confirmation-gated `quit <app name>`
- `show recent files`
- read-only known-folder discovery such as `list files in downloads`, `find file named <name>`, and `search documents for <name>`
- read-only metadata commands such as `show details for <name>`, `how big is <name>`, and `show recent downloads`
- runtime self-status questions such as `what can I say`, `what did you hear`, `are you listening`, `is local AI ready`, and `why did that fail`
- Desktop folder or file create, delete, rename, and move commands with confirmation where needed
- `list windows`, `what apps are open`, `is <app> open`, and `switch to window <visible title>`
- `what time is it`, `what is my battery level`, `wifi status`, `what is the volume`, and `is audio muted`
- `set volume to 50 percent`, `mute audio`, and `unmute audio`

---

## 2. What Is Supported Now

Primary supported path:

- Fedora RPM install through the release `setup.sh` path
- packaged `/usr/bin/operance`
- installed tray user service
- installed smoke plus a human tray click-to-talk smoke

Contributor development path:

- source checkout
- optional `ui` and `voice` extras installed
- `./scripts/run_mvp.sh` for the default interaction path
- `./scripts/run_checkout_smoke.sh` for a safe baseline

The packaged Fedora gate defaults to:

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
- the package evidence gate can install the `mvp` RPM, start the tray service,
  run installed smoke, and capture an installed support bundle
- manual tray click-to-talk can open Firefox, open a localhost URL, run a
  launch-plus-notification command, and execute a local planner test command
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
- a skills marketplace or searchable skill registry

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
./scripts/run_package_evidence_gate.sh --bundle-python .venv/bin/python --support-bundle-out /tmp/operance-installed-support.tar.gz
```

If the gate stops immediately with `rpmbuild not found`, install the build tool
first:

```bash
./scripts/install_packaging_tools.sh --rpm
```

For the exact release stop line, use [fedora-checklist.md](./fedora-checklist.md).
For the release-readiness stop line, use [release-readiness.md](./release-readiness.md).
For the current maintainer release sequence, use [release-plan.md](./release-plan.md).
For the public beta install and feedback path, use [public-beta.md](./public-beta.md).

Maintainers preparing GitHub release assets should run:

```bash
./scripts/build_release_artifacts.sh --bundle-python .venv/bin/python
```

Upload the generated RPM, `setup.sh`, `SHA256SUMS`, and release artifact
manifest from `dist/release/`. The public install command for those assets is:

```bash
curl -fsSLO https://github.com/raunakkathuria/operance/releases/download/<release-tag>/setup.sh
bash ./setup.sh --release-url https://github.com/raunakkathuria/operance/releases/download/<release-tag>
```

That command uses the same reset, tray startup, installed-smoke,
command-discovery, and support-bundle path that maintainers validate.

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
- `operance --installed-smoke` when using the RPM
- a support bundle from the same environment:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

The support bundle includes `issue-report.md`, a redacted paste-ready issue
draft. If the archive is not needed, generate only the draft:

```bash
.venv/bin/python -m operance.cli --issue-report
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
