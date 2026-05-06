# Release Plan

Status: Current release plan  
Type: Maintainer release sequencing  
Audience: Founder, maintainers

---

## 1. Immediate Goal

Ship a **public developer alpha** for the Linux-first local core without
over-claiming the current product maturity.

That means:

- open-source the repository now
- publish `v0.1.0-alpha.1`
- position it as Fedora KDE Wayland first
- keep source checkout as the primary supported path
- keep RPM as the secondary base-runtime path

---

## 2. Release Sequence

### Phase A: Public repo export

- create the new public `operance` repository
- export the current tree with one initial public commit
- apply the GitHub metadata from
  [public-repo-metadata.md](./public-repo-metadata.md)

### Phase B: Developer alpha release

- run the pre-export gate
- publish tag `v0.1.0-alpha.1`
- attach the release notes from [v0.1.0-alpha.1.md](./v0.1.0-alpha.1.md)
- optionally attach the Fedora RPM artifact from the same code

### Phase C: Early feedback loop

- collect issues with support bundles
- focus on Fedora KDE bring-up, packaging, and MVP runtime reliability
- keep the public verified command subset conservative

---

## 3. What Counts As “Good Enough” For This Release

For `v0.1.0-alpha.1`, the repo is good enough when:

- the architecture boundary is honest and documented
- the public branding is clean
- the test suite passes
- the source-checkout bring-up path is documented and stable
- the Fedora alpha gate exists and is documented
- the public docs are narrower than the full internal capability inventory

Do not block the open-source release on a broader packaged consumer path.

---

## 4. What Comes After This Release

The next meaningful release goal is **broader public alpha**, not “more random
commands.”

That work should focus on:

- bundling or otherwise solving the optional UI and voice backend dependency story for the installed path
- widening the release-verified command subset one command family at a time
- keeping tray plus click-to-talk reliable from the installed product
- improving outside-developer onboarding and failure capture

---

## 5. Explicit Non-goals For The Current Release

Do not treat these as blockers for `v0.1.0-alpha.1`:

- Windows or macOS support
- a general third-party plugin SDK
- wake-word-first product interaction
- a fully bundled consumer desktop installer
- claiming the full implemented Linux command surface as release-verified

---

## 6. Recommended Next Maintainer Step

After the public repo is created:

1. publish `v0.1.0-alpha.1`
2. point early users to the source-checkout path first
3. treat the RPM path as a developer-alpha artifact, not the main onboarding story
4. use incoming issues to decide which runtime areas deserve graduation into the verified subset next
