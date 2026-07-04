# Operance Product PRD

Status: Current product source of truth
Audience: maintainers, contributors, AI coding agents

## Overview

Operance is a local-first AI desktop action layer that lets users control their
computer with natural language.

The product turns user intent into safe, typed desktop actions. It should feel
like a practical control surface for the local computer, not a generic chatbot
or arbitrary shell runner.

## Goals

- Make common desktop actions feel natural for non-technical users.
- Keep execution local-first and safe by default.
- Support Fedora KDE Wayland well before expanding to more platforms.
- Let contributors add commands, skills, and operating-system adapters without
  rewriting the portable core.
- Build a feedback loop where beta users can install, try, diagnose, and report
  issues without terminal-heavy setup.

## Target Users

- Fedora KDE Wayland users who want voice-driven desktop control.
- Developers who want a local-first desktop action runtime they can extend.
- Contributors who want to add command coverage, skills, or platform adapters.

Future audiences include Windows and macOS users after the provider and adapter
architecture has live, tested implementations for those operating systems.

## User Stories

- As a desktop user, I can say or click-to-talk commands such as `open browser`
  or `open google.com` and see clear feedback about what Operance heard and did.
- As a beta tester, I can install Operance from a release asset, run a readiness
  check, try known commands, and attach a support bundle when something fails.
- As a safety-conscious user, I can trust that risky actions require
  confirmation and that model output cannot execute directly.
- As a contributor, I can add a typed command or adapter behind documented
  contracts without putting OS-native details in the portable core.

## Functional Requirements

- Operance must execute through typed actions, validation, policy, and adapters.
- Common deterministic commands must work without a local AI model.
- Local AI planning must be opt-in and bounded to typed action schemas.
- The tray must remain the primary end-user surface and avoid raw developer
  diagnostics by default.
- Click-to-talk must remain the most reliable beta interaction path.
- Always-on listening must be wake-word gated and visibly acknowledge wake or
  no-command states.
- Setup, readiness, supported commands, issue reporting, and support capture
  must be discoverable from product surfaces.
- New command families must preserve confirmation gates, auditability, and
  adapter-owned native execution.

## Non-Goals

- No arbitrary shell execution in the normal path.
- No autonomous execution that bypasses validation, policy, or confirmation.
- No broad Linux, Windows, or macOS support claims before live verification.
- No cloud planner requirement for core desktop control.
- No marketplace or hosted service in the current repository scope.
- No script filenames tied to release phases such as alpha or beta.

## Technical Considerations

Portable core under `src/operance/` owns typed models, intent and planner
contracts, validation, policy, executor orchestration, daemon state, MCP
surfaces, and shared voice orchestration.

Platform providers under `src/operance/platforms/` own host detection,
readiness checks, setup metadata and actions, release-verified command policy,
platform-specific blockers, and next steps.

Adapters under `src/operance/adapters/` own OS-native execution, desktop APIs,
app/window/system/file transport details, and native input translation.

New operating-system support starts with a provider plus adapters. Shared core
changes are expected only for a genuinely new typed tool, shared safety
semantics, or portable orchestration behavior.

## Success Metrics

- A new Fedora KDE Wayland beta tester can install, start the tray, run
  click-to-talk, and file a useful issue with support evidence.
- Supported commands return understandable feedback when they succeed, fail, or
  need clarification.
- PRs that change behavior link to a goal-spec issue or explicitly justify why
  no issue is needed.
- Adapter and provider changes pass conformance and architecture-boundary tests.
- Public docs describe only runnable, tested behavior.

## Open Questions

- Which command families should be promoted next after beta UX reliability and
  safe command coverage are stable?
- When should Windows move from simulated provider scaffolding to live adapter
  implementation?
- What is the minimum local AI setup that feels useful without becoming a
  required dependency?
- What contribution model should replace local skill-pack loading if a future
  marketplace is introduced?
