# Adapter SDK Examples

These examples are for contributors who want to add or port desktop behavior
without changing Operance's portable core.

Start here:

```bash
python3 -m examples.adapter_sdk.minimal_adapters
```

What the examples show:

- adapters translate shared typed actions into backend-specific behavior
- providers own host readiness, setup guidance, blockers, and release policy
- conformance checks prove that an adapter set exposes the methods required by
  selected tools

What they intentionally do not show:

- real Windows, macOS, KDE, D-Bus, Accessibility, or UI Automation calls
- external plugin discovery
- release verification for a new OS

For a real OS port, read
[`docs/architecture/adapter-authoring.md`](../../docs/architecture/adapter-authoring.md)
before changing runtime code.
