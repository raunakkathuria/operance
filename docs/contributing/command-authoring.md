# Adding a Command

This guide describes the safest path for adding one Operance command without
breaking the portable-core and adapter boundary.

## Rule

Add a command by defining shared semantics once, then implementing host-specific
execution behind adapters.

Do not add Linux, Windows, or macOS transport details to planner, validator,
policy, daemon, MCP, or typed action orchestration code.

If the behavior already maps to an existing typed action, prefer a JSON desktop
skill pack instead of changing core code. See [skill-packs.md](skill-packs.md).

## Implementation Path

1. Add or update the typed tool in `src/operance/models/actions.py` only when the
   command represents a genuinely new shared capability.
2. Register the tool in `src/operance/registry.py` with description, schema,
   examples, risk tier, confirmation requirement, side effects, and validation.
3. Update deterministic intent parsing only when the phrase should work without
   local AI planner fallback.
4. Add or extend the adapter protocol in `src/operance/adapters/base.py` only if
   the existing adapter SDK does not already expose the needed execution method.
5. Add the tool-to-adapter contract in `src/operance/adapters/conformance.py`.
6. Implement the current Linux behavior in `src/operance/adapters/linux.py`, or
   keep it blocked/unverified if it is not live-tested yet.
7. Update the active platform provider in `src/operance/platforms/` with
   blockers, setup guidance, and release-verification status.
8. Add unit tests for validation, planner parsing if relevant, executor/adapter
   dispatch, provider availability, and user-facing command discovery.
9. Add live smoke coverage before promoting the command into the release-verified
   subset.
10. Update `README.md`, `docs/requirements/linux.md`, and `CHANGELOG.md` only
    when the behavior is runnable and tested now.

## Planner Boundary

The local AI planner may route natural language to typed actions, but it must not
invent raw OS commands.

Allowed planner output:

```json
{
  "actions": [
    {
      "tool": "apps.launch",
      "args": {
        "app": "firefox"
      }
    }
  ]
}
```

Not allowed:

- shell commands
- PowerShell snippets
- AppleScript snippets
- KWin scripts
- platform-native key sequences
- unregistered tool names
- arguments outside the registered schema

Validation, policy, confirmation gates, provider availability, and adapter
dispatch remain mandatory for every planner-origin action.

## Release Promotion Checklist

Before a command appears in `--supported-commands --supported-commands-available-only`:

- The typed action schema exists and rejects unexpected arguments.
- The adapter conformance gate passes.
- The platform provider marks the command available only when prerequisites are
  present.
- The command has unit coverage.
- The command has live or controlled-live smoke coverage.
- Destructive or high-risk behavior is confirmation-gated.
- Documentation describes only the tested behavior.

Run:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m operance.cli --adapter-conformance
./scripts/run_release_readiness_gate.sh --dry-run
```
