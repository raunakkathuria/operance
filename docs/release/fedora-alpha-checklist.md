# Fedora Alpha Checklist

Status: Working release gate  
Type: Fedora KDE alpha handoff checklist  
Audience: Founder, maintainers, first outside developers

---

## 1. Scope

This checklist defines the current Fedora-first release gate for Operance.

Use it when deciding whether the repo is ready for an outside-developer alpha
drop on the current target platform:

- Fedora KDE Plasma
- Wayland session
- Linux-first packaged or source-checkout delivery

This checklist is intentionally narrower than the full roadmap. It does not try
to prove Windows, macOS, or a fully bundled cross-platform install story.

---

## 2. Current Stop Line

The current repo can now prove:

- the source checkout passes the full test suite
- the repo-local beta smoke path works
- the native package scaffolds build a runnable base `operance` CLI wrapper
- the RPM handoff path can be exercised through one Fedora release-smoke script
- installed package smoke can verify the packaged desktop entry, user units, and
  base CLI diagnostics

The current repo does **not** yet prove a fully bundled end-user desktop build.

Known remaining gaps before a broader public launch:

- the native package path does not yet bundle optional UI or voice Python
  backends such as PySide6, Moonshine, openWakeWord, or Kokoro
- the safest default product path remains tray plus click-to-talk from a
  prepared developer machine, not a zero-setup consumer installer
- wake word remains secondary to click-to-talk for launch reliability

That means the realistic public position today is:

`Linux first`, `Fedora KDE first`, `developer alpha`, `local-first`, and
`click-to-talk before wake word`.

---

## 3. Source-Checkout Gate

From the checked-out tree:

```bash
.venv/bin/python -m pytest
./scripts/run_beta_smoke.sh
./scripts/run_fedora_release_smoke.sh --dry-run
```

All three must pass before a package-backed alpha candidate is considered.

Or use the combined checkout gate:

```bash
./scripts/run_fedora_alpha_gate.sh
```

If that gate stops immediately with `rpmbuild not found`, install the Fedora
packaging prerequisite first:

```bash
./scripts/install_packaging_tools.sh --rpm
```

---

## 4. RPM Gate

Build the RPM artifact and then exercise the installed-package smoke path:

```bash
./scripts/build_package_artifacts.sh --rpm
./scripts/run_installed_beta_smoke.sh \
  --package dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm \
  --installer dnf
```

Or use the combined release gate:

```bash
./scripts/run_fedora_release_smoke.sh
```

The combined alpha gate above already covers both the source-checkout gate and this
RPM gate in one command for a prepared Fedora checkout.

Success means all of the following are true:

- the RPM artifact is built at the documented path
- the package installs cleanly
- the packaged desktop entry exists
- the packaged tray and voice-loop user units exist
- `operance --version` runs from the installed command
- `operance --doctor` runs from the installed command
- the runnable supported-command subset can be projected from the installed command
- the installed command can write a support bundle

---

## 5. Failure Capture

When the Fedora release gate fails, always capture one artifact before changing
the machine again:

```bash
operance --support-bundle
```

If the failure happened during a source-checkout run instead of the installed
RPM path, collect:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

Attach that bundle to the bug report together with:

- Fedora version
- KDE Plasma version
- session type
- install method
- exact script or command that failed

---

## 6. Alpha Decision Rule

The current repo is ready for a Fedora developer alpha only when:

1. the source-checkout gate passes
2. the RPM gate passes on the target Fedora machine
3. the known limitations above are documented honestly in the launch notes
4. the expected tester workflow is explicit:
   source checkout first, Fedora RPM `mvp` package second, and a human
   tray-plus-microphone smoke before tagging a packaged alpha release

If the goal changes from `developer alpha` to `wider public alpha`, the next
required feature is not another desktop command. It is tightening the installed
tray plus click-to-talk UX and collecting enough Fedora feedback to know whether
the packaged `mvp` runtime is stable enough for non-developer testers.
