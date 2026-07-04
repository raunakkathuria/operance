---
name: Goal spec
about: Define a non-trivial Operance goal before implementation
title: "[goal] "
labels: enhancement
assignees: ""
---

## PRD alignment

Link the relevant section of `docs/specs/product-prd.md` or explain why the PRD
needs to change first.

## User problem

Describe the user friction or contributor blocker this goal removes.

## User outcome

Describe what the user can see, say, click, install, diagnose, or contribute
after this goal is complete.

## Supported scope

- Platform:
- Install mode:
- User surface:
- Command or workflow surface:

## Non-goals

List what this goal must not solve.

## Architecture impact

Mark the areas this goal is allowed to touch.

- [ ] portable core
- [ ] platform provider
- [ ] OS adapter
- [ ] voice pipeline
- [ ] local AI planner
- [ ] MCP or tray surface
- [ ] setup or packaging
- [ ] website or public docs
- [ ] tests only

## Safety impact

Describe validation, policy, confirmation, audit, denial, rollback, planner, or
adapter safety requirements.

## Acceptance criteria

- [ ] Product behavior is implemented only within the supported scope above.
- [ ] Implementation does not put OS-native transport details into portable core
      modules.
- [ ] Tray changes are end-user focused.
- [ ] Specs or docs are updated if behavior changes.
- [ ] Deferred work is explicit.

## Test evidence

List expected tests, CLI probes, package/install smoke checks, or manual
user-facing workflows.

## Documentation impact

List expected updates to README, Linux docs, architecture docs, contributor
docs, website, release docs, changelog, or this spec.

## Release notes

State whether this should be tagged/released after merge, and why.
