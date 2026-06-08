# Release Readiness

Status: Current release target  
Type: Release criteria  
Audience: Maintainers, contributors

---

## 1. Position

Operance is targeting a narrow Fedora KDE Wayland developer release. Release
work should stay organized around coherent, validated batches instead of
isolated polish fixes.

For this project, release-ready means:

- a new Fedora KDE Wayland developer can install, run, and validate the product
  from documented commands
- the default interaction path is tray plus click-to-talk
- the supported command subset is intentionally narrow but reliable
- source-checkout and packaged RPM paths are both exercised by repeatable gates
- support bundles and setup output are sufficient for maintainers to debug most
  external reports

Release-ready does not mean broad distro support, Windows or macOS support, or
a consumer-grade zero-setup installer.

---

## 2. Current Gate

Use the fast release-readiness gate during normal development:

```bash
./scripts/run_release_readiness_gate.sh
```

That gate runs:

- the full unit test suite
- the adapter conformance check for the active adapter set
- the old-brand reference guard
- the controlled live command smoke against a temporary desktop fixture
- the source-checkout smoke
- the reset-aware Fedora package gate in dry-run mode
- the installed desktop smoke checklist in dry-run mode
- the packaged evidence gate in dry-run mode

Before tagging a release candidate, run the full package gate as well:

```bash
./scripts/run_release_readiness_gate.sh --run-package-gate
```

The full package gate keeps the RPM installed so the installed desktop smoke and
manual tray click-to-talk checks can run against the same package payload.
Fresh release-candidate package rebuilds must also pass:

```bash
./scripts/build_package_artifacts.sh --rpm --bundle-profile mvp
rpm -Kv dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm
```

For the current Fedora KDE packaged beta path, prefer the packaged evidence gate
before tagging:

```bash
./scripts/run_package_evidence_gate.sh --bundle-python .venv/bin/python
```

That gate rebuilds the `mvp` RPM, verifies the artifact, installs it with stale
user-service reset, runs installed desktop smoke, writes an installed support
bundle when requested, and leaves the package installed for the manual
click-to-talk checks.

After the installed package evidence gate and manual tray checks pass, prepare
the GitHub release upload set:

```bash
./scripts/build_release_artifacts.sh --bundle-python .venv/bin/python
```

That writes the normalized RPM, stable `setup.sh`, `SHA256SUMS`, and a release
artifact manifest under `dist/release/`. The manifest should include both the
local package command, `bash ./setup.sh --package ./operance-0.1.0-1.noarch.rpm`,
and the release-asset command,
`bash <(curl -fsSL https://github.com/raunakkathuria/operance/releases/download/<tag>/setup.sh) --release-url https://github.com/raunakkathuria/operance/releases/download/<tag>`.
Both commands must go through `setup.sh`, not raw `dnf install`, so the public
release path exercises stale user-service reset, tray startup, installed smoke,
runnable-command discovery, and support-bundle capture.

Use `--support-bundle-out <path>` when the gate is being run for a release
handoff and the source-checkout smoke should write a predictable support bundle
artifact.

Use the installed desktop smoke helper directly when validating a freshly
installed RPM in the active KDE session:

```bash
./scripts/run_installed_desktop_smoke.sh
```

It verifies the installed command, tray service path, live-mode config, starts
and checks the packaged tray user service, and projects the supported-command
subset. It then prints the manual tray click-to-talk commands that still require
a human microphone and desktop session.

---

## 3. Stop Line

The current public release should require all of the following:

- `./scripts/run_release_readiness_gate.sh --run-package-gate` passes on the
  target Fedora KDE Wayland machine
- `./scripts/run_package_evidence_gate.sh --bundle-python .venv/bin/python`
  passes on the target Fedora KDE Wayland machine before tagging
- a fresh `./scripts/build_package_artifacts.sh --rpm --bundle-profile mvp`
  rebuild completes and the normalized RPM passes `rpm -Kv`
- a fresh installed RPM can launch the tray app from the desktop session
- `./scripts/run_installed_desktop_smoke.sh` passes against that installed RPM
- tray click-to-talk can open Firefox from a spoken command
- tray click-to-talk can open a localhost URL from a spoken command
- `./scripts/build_release_artifacts.sh --bundle-python .venv/bin/python`
  prepares the RPM, checksums, and release artifact manifest for upload
- `operance --supported-commands --supported-commands-available-only` lists only
  commands that have been smoke-tested on the target machine
- README and Linux docs describe only the supported path, with deeper
  diagnostics kept in the Linux requirements document
- Windows and macOS remain clearly documented as unverified provider scaffolds
  until native adapters and release gates exist

Manual desktop-session checks remain part of the stop line because microphone
capture, KDE tray state, and real app launching cannot be fully proven in CI.

---

## 4. Work Batches

Prioritize larger coherent batches:

- **Release readiness gate and docs:** keep the release stop line executable and
  discoverable from setup.
- **Installed desktop smoke:** make packaged tray launch, service state, and
  click-to-talk verification easier to run and easier to diagnose.
- **Verified command graduation:** expand the supported command subset one
  command family at a time only after live KDE smoke passes.
- **Onboarding and issue capture:** improve setup output, support bundle
  content, generated `issue-report.md` drafts, and troubleshooting docs based
  on real external failure modes.

Avoid unrelated feature accumulation in release branches. Each PR should
represent one release-quality batch with tests, docs, and validation.
