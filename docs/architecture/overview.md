# Operance Architecture Overview

This document describes the current module boundaries for the open-source local
core.

## 1. Product shape

Operance is Linux-first today:

- Phase 1: Linux/KDE/Wayland
- Phase 2: Windows
- Phase 3: macOS

The architecture stays cross-platform by keeping the runtime model portable,
routing host-specific readiness through platform providers, and isolating
OS-specific execution behind adapters.

## 2. Portable core

The portable core lives under `src/operance/`. It should remain platform-neutral
and reusable across Linux, Windows, and macOS.

Current portable-core responsibilities:

- typed action models and result models
- deterministic intent matching
- planner prompt, request, parser, and routing logic
- validator and policy enforcement
- executor orchestration
- daemon state machine and audit flow
- voice pipeline orchestration contracts
- MCP server surfaces
- generic setup-state projection assembly and repo-local control UI

Representative modules:

- `models/`
- `intent/`
- `planner/`
- `validator.py`
- `policy.py`
- `executor.py`
- `daemon.py`
- `mcp/`
- `voice/`
- `ui/setup.py`

`doctor.py`, `supported_commands.py`, and `ui/setup.py` should assemble shared
state and call the active provider for host-specific readiness, remediation, and
verification policy. They should not grow new Linux, Windows, or macOS branches
for provider-owned concerns.

## 3. Platform providers

Platform providers live under `src/operance/platforms/`.

Providers own the host-specific integration surface that should not leak into
the portable core:

- selecting the right adapter set for the current host
- building platform-specific `--doctor` checks
- supplying platform-specific setup-step metadata
- probing platform services, sessions, and transport readiness
- generating platform-specific setup actions, blocked recommendations, and next steps
- defining tool blockers and remediation hints for live command availability
- defining the current release-verified tool subset for that platform target

Current provider modules:

- `src/operance/platforms/linux.py`
- `src/operance/platforms/unsupported.py`

That split is intentional:

- the portable core keeps one shared tool and safety model
- providers decide what the current host can support without rewriting core
  planner, validator, daemon, or MCP code
- future Windows and macOS work should start with a provider plus adapters, not
  with new branching in `doctor.py`, `supported_commands.py`, or `ui/setup.py`

Read [adapter-authoring.md](./adapter-authoring.md) before widening the
cross-platform surface.

## 4. Platform adapters

All platform-specific execution belongs behind adapter interfaces.

Current Linux-specific execution lives in:

- `src/operance/adapters/linux.py`
- Linux-specific audio and playback helpers
- repo-local Linux service and packaging scripts

That split is intentional:

- Linux-specific D-Bus, KWin, NetworkManager, PipeWire, and Wayland details stay
  out of the portable runtime
- input transport translation such as `wtype` key-sequence arguments stays in
  adapters, not in shared key-definition modules
- future Windows support should add Windows adapters and native automation
  surfaces
- future macOS support should add macOS adapters and native accessibility or
  automation surfaces

## 5. Runtime flow

The current runtime path is:

1. input arrives through CLI, tray, MCP, or voice loop
2. deterministic intent or planner fallback builds an action plan
3. validator and policy enforce typed constraints and confirmation rules
4. executor dispatches approved actions through adapters
5. runtime state, audit entries, status snapshots, and user-facing responses are
   updated

This keeps one shared safety and execution model even when invocation surfaces
change.

## 6. Voice and planner boundaries

Voice and planner work should follow the same rule:

- orchestration, contracts, routing, and safety stay portable
- model invocation and OS integration remain replaceable
- external model assets stay optional and must not be assumed to exist by
  default

## 7. Open-source boundary

This repository is intended to remain the permissively licensed local core:

- local daemon
- action registry and validators
- desktop adapters
- local voice loop
- MCP server
- local setup and packaging tooling

Optional hosted relay, sync, or managed inference layers can remain outside this
repo later without changing the local-core boundaries described here.

## 8. Contribution rule

When adding a feature, prefer one of these shapes:

- portable-core change only
- platform-provider change only
- Linux adapter or Linux packaging change only
- a portable-core change plus the minimal Linux adapter change needed to make it
  runnable now

Avoid speculative abstractions for Windows or macOS until those phases start.
