# Public Beta Distribution

Status: Current public beta path  
Type: Outside-developer onboarding and release artifact guide  
Audience: Early adopters, contributors, maintainers

---

## 1. What Operance Is

Operance is a local-first desktop action layer. It lets a developer tell their
desktop what they want in natural language, then routes that request through
typed actions, validation, policy, and OS-specific adapters before anything
runs.

The current public beta is intentionally narrow:

- target: Fedora KDE Plasma Wayland
- interaction: tray plus click-to-talk
- execution: local desktop adapters by default in the packaged RPM
- optional AI: local OpenAI-compatible planner fallback after readiness passes
- reporting: support bundles attached to GitHub issues

This is not yet a broad consumer launch, Windows or macOS release, wake-word
first product, or zero-setup installer.

---

## 2. What Works In The Beta

The packaged `mvp` RPM has been validated for the current Fedora KDE developer
path. It installs the `operance` command, tray service, packaged source tree,
tray UI runtime, and STT runtime needed for click-to-talk.

Supported command families are intentionally conservative:

- open apps, the default browser, and websites
- focus or quit apps, with confirmation for quit
- answer time, battery, Wi-Fi, volume, and mute status
- set, mute, and unmute audio
- show recent files
- create, rename, move, or delete Desktop entries with confirmation where needed
- list windows or switch to a visible window

Use the command catalog for the exact current subset on a machine:

```bash
operance --supported-commands --supported-commands-available-only
```

---

## 3. Try The Packaged Beta

Download the Fedora RPM from the GitHub release assets, then install it:

```bash
sudo dnf install -y ./operance-0.1.0-1.noarch.rpm
systemctl --user enable --now operance-tray.service
operance --version
operance --installed-smoke
```

Open the tray icon and try:

```text
open browser
open google.com
open firefox
open localhost:3000
open firefox and notify me
what time is it
wifi status
what is the volume
```

The tray menu is the primary non-terminal surface. Use **First run setup** to
walk through runtime readiness, packaged-install readiness when running the RPM,
the click-to-talk smoke commands, optional local AI planner validation, and
support-bundle capture. The same menu also shows supported commands, local AI
setup, planner readiness, installed readiness, and support-bundle actions.

If anything fails, collect one support bundle before changing the machine:

```bash
operance --support-bundle
```

Attach that archive to a GitHub issue.

---

## 4. Try The Source Checkout

Use this path when developing Operance itself:

```bash
./scripts/install_linux_dev.sh --ui --voice
.venv/bin/python -m operance.cli --doctor
.venv/bin/python -m operance.cli --getting-started
./scripts/run_mvp.sh
./scripts/run_checkout_smoke.sh
```

Collect a source-checkout support bundle with:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

---

## 5. Local AI Planner

The beta can use a local AI model, but the model is not required for the tray to
work. Deterministic supported commands run without any model.

The planner path is intentionally gated:

- it must use an OpenAI-compatible `/v1/chat/completions` endpoint
- it must return only the Operance typed action schema
- Operance still validates and policy-checks the returned plan
- confirmation-gated actions remain gated
- raw shell, PowerShell, AppleScript, or KWin scripts are never accepted as model
  output

Start with the setup template:

```bash
operance --planner-setup-template ollama
operance --planner-readiness "open firefox and notify me"
```

Only enable live fallback after readiness reports `safe_to_enable: true`:

```bash
export OPERANCE_PLANNER_ENABLED=1
```

For an explicit one-off model execution test, use:

```bash
operance --planner-execute "let me know when this is done"
```

---

## 6. Maintainer Release Artifact Build

Before publishing a GitHub release, build the upload set:

```bash
./scripts/build_release_artifacts.sh --bundle-python .venv/bin/python
```

That writes:

- `dist/release/operance-0.1.0-1.noarch.rpm`
- `dist/release/SHA256SUMS`
- `dist/release/release-artifacts-manifest.json`

Then run the installed package evidence gate on the target Fedora KDE machine:

```bash
./scripts/run_package_evidence_gate.sh --bundle-python .venv/bin/python --support-bundle-out /tmp/operance-installed-support.tar.gz
```

Publish the RPM, `SHA256SUMS`, and release artifact manifest as GitHub release
assets only after the manual tray click-to-talk checks pass.

---

## 7. Useful Beta Feedback

Useful issues include:

- exact install path: RPM or source checkout
- output from `operance --version`
- output from `operance --installed-smoke` for RPM reports
- the support bundle archive
- the spoken command or CLI transcript that failed
- expected behavior versus actual behavior
- whether the issue is tray, microphone, local AI planner, packaging, or a
  specific desktop command

Do not paste secrets or private local data into public issues. Support bundles
redact home-directory paths by default.
