# Operance Specs

This directory is the source of truth for product and milestone specs.

Use these specs before implementation. Operance should move from idea to
release through this loop:

1. Check the product PRD for product intent.
2. Write or update the relevant milestone spec or goal-spec issue.
3. Define the supported user behavior and non-goals.
4. Check architecture impact before touching code.
5. Implement the smallest runnable change.
6. Verify with tests and at least one real user-facing command path.
7. Run `python3 scripts/check_spec_sync.py --base origin/main` and address or
   explain any warning.
8. Update specs, public docs, and changelog in the same PR when behavior
   changes.

Specs are not meant to become large design documents. They should be short
enough to read before a PR review and concrete enough to decide whether the PR
is complete.

## Spec Layers

- Product PRD: durable product intent, user promises, non-goals, and success
  metrics.
- Milestone specs: current roadmap, accepted slices, and release criteria.
- Goal-spec issues: execution contracts for non-trivial feature, UX,
  architecture, packaging, release, or public-doc changes.

## Required Sections

Every milestone spec or goal-spec issue should include:

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
- Do not let implementation drift beyond the linked spec or goal issue. Update
  the spec or issue first when scope changes.
- Use `scripts/check_spec_sync.py` as a pre-PR guardrail. It does not replace
  judgment or the linked goal-spec issue, but it catches obvious behavior
  changes that lack changelog or documentation evidence.

## Current Canonical Specs

- [product-prd.md](product-prd.md): durable product direction, current product
  promises, target users, non-goals, technical considerations, and success
  metrics.
- [beta-product-direction.md](beta-product-direction.md): current beta
  contract, spec-to-PR workflow, milestone roadmap, and release criteria.
