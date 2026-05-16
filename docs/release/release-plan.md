# Release Plan

Status: Current release plan  
Type: Maintainer release sequencing  
Audience: Founder, maintainers

---

## 1. Immediate Goal

Publish narrow Fedora KDE Wayland developer releases without over-claiming the
current product maturity.

The public release line has already established:

- public source repository
- Fedora KDE Wayland first positioning
- source checkout as the primary supported path
- RPM as the secondary packaged `mvp` runtime path
- reset-aware Fedora package validation
- tray plus click-to-talk as the default interaction path

---

## 2. Release Sequence

### Phase A: Public Repo Export

- create the public `operance` repository
- export the current tree with one initial public commit
- apply the GitHub metadata from
  [public-repo-metadata.md](./public-repo-metadata.md)

### Phase B: Historical Baseline

- keep already-published release-note files as history
- do not add new phase-named release gates or current handoff docs
- keep current workflow names purpose-based

### Phase C: Fedora Developer Release

- keep the stop line in [release-readiness.md](./release-readiness.md)
- run `./scripts/run_release_readiness_gate.sh` during normal release work
- run `./scripts/run_release_readiness_gate.sh --run-package-gate` before tagging
- run a human installed tray plus microphone smoke before tagging
- publish release notes from the corresponding versioned release-note file

### Phase D: Early Feedback Loop

- collect issues with support bundles
- focus on Fedora KDE bring-up, packaging, and MVP runtime reliability
- keep the public verified command subset conservative
- graduate additional commands only after live Fedora KDE smoke

---

## 3. What Counts As Good Enough For Release

The repo is good enough for the current Fedora developer release when:

- the architecture boundary is honest and documented
- the test suite passes
- the source-checkout bring-up path is documented and stable
- the Fedora gate passes on the target Fedora KDE Wayland machine
- the packaged `mvp` RPM validates the installed tray plus STT runtime
- a human click-to-talk smoke can open Firefox and a localhost URL
- public docs describe only the verified support contract

Do not block the release on a broader packaged consumer path.

---

## 4. What Comes After This Release

The next meaningful release goal is broader reliability, not a larger
speculative command surface.

That work should focus on:

- keeping fresh `mvp` RPM rebuilds repeatable before every release candidate
- tightening the packaged tray plus click-to-talk path after the runtime gate
- widening the release-verified command subset one command family at a time
- improving outside-developer onboarding and failure capture
- collecting Fedora KDE feedback before widening distro claims
- keeping Windows and macOS as scaffolded adapter targets until native adapters
  and release gates exist

---

## 5. Explicit Non-goals For Release

Do not treat these as blockers for the current Fedora developer release:

- Windows or macOS support
- broad distro or desktop-environment support
- a general third-party plugin SDK
- wake-word-first product interaction
- a zero-setup consumer desktop installer
- claiming the full implemented Linux command surface as release-verified

---

## 6. Recommended Maintainer Step

For every release candidate:

1. work in a branch and PR
2. keep each batch release-quality and documented
3. run `./scripts/run_release_readiness_gate.sh` as the fast local stop line
4. run `./scripts/run_release_readiness_gate.sh --run-package-gate` before tagging
5. tag only after the manual installed tray plus click-to-talk smoke passes
