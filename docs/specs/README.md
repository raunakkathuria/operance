# Operance Specs

This directory is the source of truth for product and milestone specs.

Use these specs before implementation. Operance should move from idea to
release through this loop:

1. Write or update the relevant spec.
2. Define the supported user behavior and non-goals.
3. Check architecture impact before touching code.
4. Implement the smallest runnable change.
5. Verify with tests and at least one real user-facing command path.
6. Update public docs and changelog in the same PR.

Specs are not meant to become large design documents. They should be short
enough to read before a PR review and concrete enough to decide whether the PR
is complete.

## Required Sections

Every feature or milestone spec should include:

- User problem: the user friction being removed.
- Product behavior: what the user sees, says, clicks, or expects.
- Supported scope: platform, install mode, and command surface covered now.
- Non-goals: what this PR or milestone must not solve.
- Architecture impact: core, planner, policy, provider, adapter, tray, voice,
  packaging, docs, or website areas touched.
- Safety model: validation, confirmation, audit, rollback, denial, or
  fail-closed behavior.
- Test evidence: unit tests, CLI smoke, package/install smoke, and manual checks.
- Documentation impact: README, Linux docs, architecture docs, contributor docs,
  website, release docs, and changelog updates.

## Acceptance Rules

- Keep `KISS`, `YAGNI`, and `DRY` as acceptance criteria, not slogans.
- Do not widen the portable core with platform-native details.
- Do not add tray menu items unless they help an end user in the moment.
- Do not document behavior as shipped until it is runnable and tested.
- Do not use release-phase names such as `alpha` or `beta` in new script
  filenames.
- Do not bypass typed action validation, policy, confirmation, or adapter
  execution with model output or shell commands.

## Current Canonical Specs

- [beta-product-direction.md](beta-product-direction.md): product direction,
  current beta contract, spec-to-PR workflow, and milestone roadmap.

