# Beta Product Direction

Status: Current planning spec
Audience: maintainers, contributors, AI coding agents

## Product Vision

Operance is a local-first AI desktop action layer that lets users control their
computer with natural language.

The public product should feel like:

> Tell your computer what you want. Operance turns that intent into safe,
> typed desktop actions.

The developer platform should feel like:

> Add operating-system adapters, safe commands, and local skills without
> rewriting the portable core.

## Current Beta Contract

Operance is Linux-first today. The current supported runtime target is Fedora
KDE Wayland with the packaged tray-first workflow.

Supported user-facing contract:

- Click-to-talk is the most reliable interaction path.
- Optional always-on listening is wake-word gated.
- Always-on listening gives visible feedback when the wake word is heard.
- If no command follows the wake word, Operance reports that and returns to
  wake waiting.
- Commands execute through typed actions, validation, policy, and adapters.
- Local AI planning is opt-in and must still produce typed actions that pass
  validation and policy.
- The tray remains an end-user product surface, not a raw developer console.
- Setup, status, issue reporting, and support capture should be accessible
  without requiring users to memorize many terminal commands.

Current non-claims:

- No broad Linux desktop support beyond the current verified target.
- No live Windows or macOS support yet.
- No arbitrary shell execution in the normal path.
- No autonomous execution that bypasses confirmation gates.
- No marketplace or hosted service in the current repo scope.

## Product Principles

- Local-first: core desktop control should work without cloud services.
- Safe by default: typed actions, validation, policy, confirmation, and audit
  are part of the product, not implementation details.
- Deterministic first: common commands should work without requiring a local
  model.
- AI bounded by schema: local models may propose actions, but Operance validates
  and executes.
- Do not make users think in product internals: phrases such as `open
  google.com` should map to the default browser without requiring users to know
  adapter names.
- Linux first, cross-platform architecture: core remains portable, while
  providers and adapters own operating-system-specific behavior.

## Engineering Principles

Every feature must satisfy:

- `KISS`: prefer the simplest runnable implementation that solves the current
  user problem.
- `YAGNI`: do not add future-phase surfaces before the current milestone needs
  them.
- `DRY`: remove duplication when it improves clarity, but do not force premature
  abstraction.

These principles are PR acceptance criteria. A PR can be rejected for violating
them even if tests pass.

## Architecture Contract

Portable core under `src/operance/` owns:

- typed models
- intent and planner contracts
- validation and policy
- executor orchestration
- daemon state
- MCP surfaces
- shared voice orchestration

Platform providers under `src/operance/platforms/` own:

- host detection
- readiness checks
- setup metadata and actions
- release-verified command policy
- platform-specific blockers and next steps

Adapters under `src/operance/adapters/` own:

- OS-native execution
- desktop APIs
- app/window/system/file transport details
- native input translation

New OS support starts with a provider plus adapters. Shared core changes are
expected only for a genuinely new typed tool, shared safety semantics, or
portable orchestration behavior.

## Spec-to-PR Workflow

Before implementation:

1. Identify or create the relevant spec in `docs/specs/`.
2. State the user problem and product behavior in plain language.
3. Mark supported scope and non-goals.
4. Identify architecture areas touched.
5. Define safety and confirmation requirements.
6. Define the test and manual evidence needed before merge.

During implementation:

1. Write or update a failing test first for non-trivial behavior.
2. Keep the change bounded to the spec.
3. Avoid speculative abstractions.
4. Keep platform details behind providers or adapters.
5. Keep tray changes end-user focused.

Before merge:

1. Run relevant tests and architecture-boundary checks.
2. Run at least one user-facing command path that the PR claims to improve.
3. Update README, Linux docs, architecture docs, contributor docs, website, or
   release docs when behavior changes.
4. Update `CHANGELOG.md` for completed implementation slices.
5. Document deferred work explicitly.

## Milestone Roadmap

### Milestone 1: Beta UX Reliability

Goal: make Operance understandable and trustworthy for outside beta users.

Scope:

- clear tray state and feedback
- reliable click-to-talk path
- wake-word feedback and bounded always-on behavior
- understandable first-run setup/status
- support bundle and issue-report flow
- release evidence for packaged installs

Non-goals:

- broad command expansion
- Windows or macOS implementation
- AI autonomy beyond typed action planning

### Milestone 2: Generalized Safe Command Model

Goal: make common desktop requests feel natural while preserving typed safety.

Scope:

- consistent grammar for `open`, `focus`, `search`, `show`, `set`, `mute`,
  `unmute`, and confirmation-gated close/delete operations
- safe target resolver for apps, URLs, known folders, files, and windows
- adapter-owned OS resolution
- product documentation that explains behavior from a user perspective

Non-goals:

- every Linux shell command
- raw terminal command execution
- destructive file management without confirmation and audit

### Milestone 3: Local AI Assist Mode

Goal: use local models to improve phrasing coverage without weakening safety.

Scope:

- local OpenAI-compatible endpoint support
- readiness diagnostics
- schema-only typed action output
- deterministic fallback
- confidence and failure cooldowns
- clear tray/CLI messaging when planner help is unavailable

Non-goals:

- model-hosting as a required dependency
- remote cloud planner by default
- model output executing directly

### Milestone 4: Contributor Adapter SDK

Goal: let contributors add platform support without changing core behavior.

Scope:

- adapter capability contracts
- conformance tests
- provider registration rules
- simulated Windows/macOS adapter examples
- contributor checklist and architecture docs

Non-goals:

- claiming live Windows/macOS support before native adapters are tested
- changing the core tool model for one platform-specific quirk

### Milestone 5: Distribution and Public Adoption

Goal: reduce terminal-heavy setup and improve public beta traction.

Scope:

- release-asset install flow
- clearer website and README entry points
- setup/status surfaced through the tray
- update diagnostics
- feedback loop and issue templates
- release evidence that matches the claim being shipped

Non-goals:

- native app stores
- auto-update without explicit user action
- paid cloud service

## Release Criteria

A release is worth tagging when it contains a user-visible improvement that is
documented, tested, and supported by release evidence.

Do not tag for documentation-only changes unless the documentation materially
changes public onboarding or release instructions.

Before tagging:

- full test suite passes
- release gate or package evidence gate passes when packaging changes are in
  scope
- manual tray checks match the release claim
- README and release docs match the installed behavior
- changelog contains the release slice
- tag is signed when creating the release tag

