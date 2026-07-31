# Development Environments

Operance ships a Fedora KDE Plasma Wayland package, but most contributors do not
develop on Fedora. This describes which work can be verified where, and why some
verification cannot be faked.

## The short version

| Work | Where |
|---|---|
| Portable core: typed actions, validator, policy, registry, planner, MCP, intent grammar, skill packs | Any host, including macOS |
| Full test suite | Linux CI is the source of truth |
| Fedora packaging: RPM build, install, installed CLI | Fedora container |
| KWin window control, tray, clipboard, input, audio | Fedora KDE Wayland VM or machine |
| Microphone quality and wake-word tuning | Real hardware |

## Any host

The portable core has no OS dependencies. `OPERANCE_DEVELOPER_MODE=1` is the
default for a source checkout and selects mock adapters, so the daemon, planner,
MCP surface, and command grammar all run anywhere.

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python -m mypy
```

## Linux CI is the source of truth for tests

Local suites are not authoritative, because both common development hosts fail
tests for environmental reasons and neither is a superset of the other. A
macOS host cannot run the Linux shell-script tests, and a bare Fedora container
lacks the display the tray tests expect. GitHub Actions runs the suite on Linux,
and that run is the one that counts.

If a test fails locally but passes in CI, check whether it depends on a host
binary or a display before assuming the code is wrong. Tests should inject their
dependencies rather than rely on what happens to be installed.

## Fedora container: the packaging path

Neither macOS nor the Linux CI runners build and install a real RPM. CI runs
packaging dry runs only. This is the gap a container closes:

```bash
bash scripts/run_fedora_container_smoke.sh
```

That builds the RPM, installs it with `dnf`, and checks the installed `operance`
command responds and the systemd unit files landed. It runs on Docker or Podman
via `--runtime`, and needs neither systemd nor privileged mode, because the RPM
spec installs its unit files as data and has no install scriptlets.

Because `BuildArch` is `noarch`, an ARM container on an Apple Silicon machine
produces the same artifact that ships. There is no architecture caveat and no
emulation needed.

Do not install the `ui` extra in a container. PySide6 installs cleanly but,
without a display, makes the tray tests fail rather than skip.

## Fedora KDE VM: session-dependent behavior

Window control goes through `gdbus` to `org.kde.KWin` and its `/Scripting`
interface, so it needs a live KWin on the session bus. Clipboard and input use
Wayland protocols through `wl-copy`, `wl-paste`, and `wtype`. The tray needs a
running Plasma shell. None of that can be honestly verified headless, and a
nested compositor in a container does not represent a real session.

Use a Fedora KDE Spin virtual machine. On Apple Silicon, UTM uses Apple's
Virtualization framework and runs the aarch64 spin well; VMware Fusion is free
for personal use. Inside that VM:

```bash
./scripts/run_release_readiness_gate.sh
operance --installed-smoke        # then work through the manual checks it lists
```

This is the environment required before promoting a command into
`release_verified_tools`. `docs/requirements/tech.md` section 9 is explicit that
a non-Linux host is not an honest validation environment for this stack, and
that rule exists so the supported-command catalog stays truthful.

## Real hardware: audio

Microphone capture, wake-word thresholds, and false-activation behavior depend
on real audio hardware and a real room. Virtual machine microphone passthrough
works well enough for a smoke check but is not representative for tuning. Always-on
listening is scoped as experimental, so this rarely blocks other work.

## Choosing where to work

Most changes never leave the first tier. Reach for the container when touching
packaging, release scripts, or anything under `packaging/`. Reach for the VM when
touching adapters, the tray, the voice loop, or when promoting a command family.
