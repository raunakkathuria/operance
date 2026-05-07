# Repository Guidelines

## Project Structure & Module Organization

Source code lives under `src/operance/`. Keep portable core logic in modules such as `models/`, `intent/`, `planner/`, `policy.py`, `validator.py`, and `executor.py`. Platform readiness and setup policy belong in `src/operance/platforms/`; OS-native execution belongs in `src/operance/adapters/`, with `mock.py` used for developer-mode execution. Tests live in `tests/unit/`. Product and setup requirements are maintained in `docs/requirements/`, and the initial implementation brief is in `docs/prompt/initial.md`.

## Build, Test, and Development Commands

Create and activate the local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Run the full test suite with `.venv/bin/python -m pytest`. Run the CLI locally with `.venv/bin/python -m operance.cli --print-config` or `.venv/bin/python -m operance.cli --doctor`. Use `.venv/bin/python -m operance.cli --planner-request "open firefox"` to inspect planner payloads during development.

## Coding Style & Naming Conventions

Target Python `3.12+`. Use 4-space indentation, type hints, and small typed data models. Prefer `snake_case` for functions, modules, and variables, and `PascalCase` for classes and dataclasses. Keep platform-specific APIs out of portable core modules; expose them through adapter interfaces in `src/operance/adapters/base.py`. Match existing direct, minimal docstrings and avoid broad refactors in feature slices.

## Architecture Guardrails

Treat the repo as a Linux-first portable core with per-platform host integration.

- Portable core under `src/operance/` owns typed actions, registry, validator, policy, planner, executor, daemon, MCP, and shared voice orchestration.
- Platform providers under `src/operance/platforms/` own host detection, adapter selection, doctor checks, setup metadata, setup actions, blocked recommendations, next steps, and release-verification policy.
- Adapters under `src/operance/adapters/` own OS-native execution details.

Enforce these boundaries when making changes:

- New operating-system support should start with a provider plus adapters, not with new branching in shared core modules.
- Shared core modules must not carry OS transport details such as Linux command arguments, Wayland protocol quirks, or platform-native key sequences.
- Keep shared input definitions semantic; native input translation belongs in the adapter that executes it.
- For an existing tool on a new OS, prefer provider or adapter changes only. Core changes are expected only when adding a genuinely new tool or changing shared safety semantics.
- Keep the current public positioning honest: Linux first, Fedora KDE Wayland first, source checkout first, RPM base-runtime second.

Apply these engineering principles in every slice:

- `KISS`: prefer the simplest implementation that satisfies the current runnable requirement.
- `YAGNI`: do not add future-phase abstractions, options, or integrations before the current milestone needs them.
- `DRY`: remove duplication when it improves clarity, but do not force premature abstractions that make a small slice harder to follow.

## Testing Guidelines

Use `pytest` and follow TDD: write or update a failing test first, implement the smallest fix, then rerun `.venv/bin/python -m pytest`. Name tests `test_<behavior>.py` and keep them under `tests/unit/`. Add regression coverage for new CLI flags, planner contracts, validator rules, and adapter-facing executor behavior.

## Commit & Pull Request Guidelines

Commits should be small, phase-scoped, and descriptive, following the current history: `add cli output for planner service requests`, `refresh linux setup guidance and current README status`. Commit after each completed step. Pull requests should explain user-visible behavior, list doc updates, note test coverage, and mention any deferred work or platform limits.

## Execution Mode

Default to feature-level execution, not slice-level execution.

When the user asks to work on a feature, continue through all required sub-slices and commits without pausing for confirmation between sub-slices.

Stop only when:

- the feature is complete
- there is a real blocker
- destructive or external approval is required
- it is time to propose the next feature

The agent may create multiple small commits within one feature request.
Do not stop after each commit or slice.
At the end of a feature, summarize the completed commits and propose the next feature.

## Documentation & Agent Workflow

Keep `README.md`, `docs/requirements/linux.md`, and `CHANGELOG.md` in sync with code in the same change. Use `README.md` for current runnable behavior, `docs/requirements/linux.md` for Linux integration status and setup, and `CHANGELOG.md` for completed implementation slices. Do not describe features as implemented unless they are runnable now. When working outside Linux, limit changes to portable logic, mocks, schemas, tests, and simulated adapter paths.

When using Codex or other coding agents on this repo, treat these as enforcement rules:

- ask for or make the smallest viable change that keeps the current slice simple
- require failing-test-first behavior for non-trivial changes
- require docs updates in the same change when behavior or workflow changes
- reject speculative abstractions unless the current tests or current Linux integration path need them
