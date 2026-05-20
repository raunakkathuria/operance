# Adapter Authoring Guide

This document describes the current extension seam for adding another operating
system backend without rewriting the portable core.

## 1. Current rule

For an existing tool surface, a new OS backend should mainly require:

- a platform provider under `src/operance/platforms/`
- adapter implementations under `src/operance/adapters/`
- provider and adapter tests

It should **not** require changing:

- `daemon.py`
- `validator.py`
- `policy.py`
- `planner/`
- MCP flow
- typed action models for existing tools

If a change requires editing those modules just to support an already-defined
tool on another OS, the boundary is wrong.

## 2. What belongs where

### Portable core

The core owns:

- `ToolName` and typed action models
- tool registry metadata and argument validation
- confirmation and safety policy
- executor orchestration
- daemon state
- planner routing and parsing
- voice orchestration
- MCP surfaces

The core defines **what** a tool means.

### Platform providers

Providers live under `src/operance/platforms/`.

A provider owns:

- building the right `AdapterSet` for the current host
- platform-specific environment checks used by `--doctor`
- platform-specific setup-step metadata
- platform-specific service discovery, session probes, and host transport checks
- platform-specific setup actions, blocked recommendations, and next steps
- live command blockers and remediation suggestions
- release-verification metadata for the current platform target

The provider defines **whether** a tool is available and how the host is wired.

### Adapters

Adapters live under `src/operance/adapters/`.

An adapter owns:

- the actual OS-specific execution path for a protocol
- translation from shared action semantics into platform-native calls
- platform-native error handling for that execution surface

The adapter defines **how** a tool is executed on that OS.

## 3. Recommended flow for a new OS

Start in this order:

1. add a provider module in `src/operance/platforms/`
2. add adapter implementations for the existing protocols you can support
3. register the provider in `src/operance/platforms/__init__.py`
4. add or reuse adapter contracts in `src/operance/adapters/conformance.py`
5. add provider tests
6. add adapter tests
7. run `.venv/bin/python -m operance.cli --adapter-conformance`
8. only then widen the verified command subset for that platform

Do not start by editing the core command model unless the new OS truly needs a
new tool, not just a new implementation.

## 4. Adapter SDK contract

The current in-repo adapter SDK is intentionally small:

- `src/operance/adapters/base.py` defines protocol methods for each adapter
  surface.
- `src/operance/adapters/conformance.py` maps every registered `ToolName` to
  the adapter field and method that must exist.
- `python3 -m operance.cli --adapter-conformance` validates the active adapter
  set against that contract and returns a JSON report.
- `scripts/run_release_readiness_gate.sh` runs the conformance check after the
  unit suite, so release work fails before smoke tests if an adapter contract is
  broken.

The conformance check is a shape contract, not a live OS smoke. It proves that an
adapter set exposes the methods required by the typed tools. Providers still own
doctor checks, live blockers, setup guidance, and release-verified tool lists.

## 5. Current non-goals

This is **not** a general external plugin SDK yet.

Today, adding a new provider still means editing the in-repo provider registry.
That is intentional for now. It keeps the release architecture simple while the
tool contract stabilizes.

The current goal is:

- easy in-repo completion of the scaffolded Windows and macOS backends
- minimal churn in portable core modules

The current non-goal is:

- arbitrary third-party tool plugins
- arbitrary external platform package discovery

## 6. Design constraints

When adding a provider or adapter:

- keep tool semantics shared across platforms
- do not leak OS-specific transport arguments into shared core modules
- keep shared key or gesture definitions semantic; native input sequences belong
  in the adapter that executes them
- prefer capability gaps over fake support
- keep unsupported tools blocked or unverified instead of pretending they work
- preserve Linux-first delivery until another platform is actually being brought up
- do not add a tool to `release_verified_tools` unless its adapter contract
  exists and the platform-specific live behavior has been tested

## 7. Practical example

For the scaffolded Windows backend:

- `src/operance/platforms/windows.py` should own Windows environment checks,
  setup-step metadata, setup actions, release-gate guidance, and verified-tool metadata
- `src/operance/adapters/windows.py` should implement the existing adapter
  protocols using Windows-native automation APIs
- `supported_commands.py`, `doctor.py`, and `ui/setup.py` should not need
  Windows-specific branching beyond the provider seam

For the scaffolded macOS backend:

- `src/operance/platforms/macos.py` should own macOS environment checks,
  setup-step metadata, setup actions, release-gate guidance, and verified-tool metadata
- `src/operance/adapters/macos.py` should implement the existing adapter
  protocols using macOS Accessibility and Automation APIs
- consent and permission handling should stay provider or adapter-owned instead
  of leaking into shared planner, policy, daemon, or MCP modules
