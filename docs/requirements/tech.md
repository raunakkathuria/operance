# Project Technology Stack

Status: Draft v1.0
Type: Living technical decision record
Audience: Founder, contributors, AI coding agents, future maintainers

---

## 1. Official stack decision

The project will use **Python 3.12+ as the primary implementation language through Phase 2**.

Native and external runtimes will be used where they already provide the performance-critical path:

- **llama.cpp** for local LLM serving
- **PipeWire** for low-latency audio capture and media routing
- **KDE / KWin / D-Bus system services** for Linux desktop control

This keeps product code in a fast iteration language while leaving inference, audio plumbing, and desktop integration on mature native runtimes and system APIs.

---

## 2. Language boundary

The system follows this rule:

- **Python = control plane**
- **Native runtimes = heavy compute and media**
- **Rust = optional hotspot/helper language**

Python is used for:

- daemon/orchestrator
- typed action models
- validators and policy
- executor and adapter coordination
- MCP server
- tray/setup UI
- tests, evals, and diagnostics

The application coordinates events, validates typed actions, talks to D-Bus, and calls external runtimes.
It does **not** reimplement inference engines or media frameworks in the application language.

---

## 3. Why Python is the default

Python is the shortest path to a maintainable control plane because the selected stack already aligns with it:

- **openWakeWord** is designed for direct Python use and Python packaging. ([github.com](https://github.com/dscripka/openWakeWord))
- **moonshine-voice** provides a Python package with microphone transcription support. ([pypi.org](https://pypi.org/project/moonshine-voice/))
- **Qt for Python** is the official Python binding for Qt, and `PySide6.QtDBus` is available. ([doc.qt.io](https://doc.qt.io/qtforpython-6/))
- **llama.cpp** already exposes an OpenAI-compatible server, so the app does not need embedded inference code. ([github.com](https://github.com/ggml-org/llama.cpp))

Python is therefore not a fallback choice here. It is the most phase-friendly control-plane language for the current architecture.

---

## 4. Core implementation stack

### 4.1 Control plane

- **Python 3.12+**
- **uv** for development environment and dependency management
- standard-library `dataclasses` as the default internal typed-model strategy
- JSON-serializable contract objects for events, plans, results, and status
- **SQLite** for local state and audit metadata
- structured JSON logging
- **systemd user service** for daemon lifecycle on Linux targets

### 4.2 Audio and speech

- **PipeWire** for microphone capture and routing on Linux
- **openWakeWord** for wake-word detection
- **Moonshine** via `moonshine-voice` for local STT
- **Kokoro** for local TTS

### 4.3 Planning

- deterministic matcher for common commands
- **llama.cpp server** for local planner inference
- schema-constrained JSON outputs only
- planner never executes directly

### 4.4 Desktop and system integration

- D-Bus adapters for Linux desktop/system APIs
- KWin scripting integration
- NetworkManager
- UPower
- freedesktop notifications
- `xdg-open` / desktop files for app launch where appropriate

### 4.5 UI

- **PySide6** for tray UI, setup flow, and confirmation dialogs
- `PySide6.QtDBus` is preferred for UI-facing D-Bus integration

### 4.6 Interoperability

- MCP server: stdio first, Streamable HTTP later

---

## 5. D-Bus integration rule

Use this split:

- **UI-facing code** may use `PySide6.QtDBus`
- **headless daemon code** should stay decoupled from Qt where practical and talk to D-Bus through a dedicated adapter layer

The important rule is architectural, not library-specific:

- D-Bus calls must stay behind adapter interfaces
- D-Bus objects, paths, and service names must not leak into the portable core

---

## 6. Typed model and schema policy

Use this default:

- internal runtime models: `dataclasses`
- external contracts: explicit JSON-serializable dict output from typed models
- tool and action schemas: versioned in project docs and tests

Do **not** introduce Pydantic or another runtime validation framework unless Phase 0B or later proves it reduces real duplication or safety risk.

---

## 7. Rust policy

Rust is the preferred secondary language, but only for narrow, proven hotspots.

Reserved uses:

- a tiny always-on audio helper
- a small privileged helper with a narrow attack surface
- a lightweight LAN satellite process
- a measured performance hotspot after profiling

Candidate Rust ecosystem pieces:

- **zbus** for D-Bus-facing helpers
- **PyO3** for exposing narrow Rust helpers back to Python

Rust may be introduced only if a measured issue persists across at least two checkpoints in one of these areas:

- p95 end-to-end latency
- always-on CPU usage
- idle memory budget
- daemon crash rate
- privileged-helper security boundary
- satellite footprint constraints

No full-language rewrite is planned.

---

## 8. Portability policy

The architecture should remain portable later, but the product is **not cross-platform in v1**.

Current scope:

- Linux
- KDE Plasma
- Wayland

Deferred scope:

- GNOME support
- Windows companion
- macOS companion

Portability rule:

- keep `models`, `intent`, `validator`, `executor`, `policy`, and MCP logic platform-neutral
- keep audio-system, D-Bus, windowing, notifications, launch, power, and network behavior behind adapters
- define per-platform capability matrices instead of pretending the same tool surface exists everywhere

---

## 9. macOS development policy

macOS is acceptable for:

- core Python development
- deterministic matcher work
- validator/policy work
- MCP/core contract work
- test harnesses
- simulated or replay-driven voice pipeline work

macOS is **not** an honest validation environment for:

- KDE/Wayland desktop actions
- PipeWire integration
- KWin integration
- Linux D-Bus behavior
- real tray behavior on the target desktop

Therefore, macOS work should focus on portable core logic and simulated platform boundaries.

---

## 10. Licensing and packaging cautions

- `openWakeWord` code is Apache-2.0, but bundled pre-trained models carry non-commercial restrictions. ([github.com](https://github.com/dscripka/openWakeWord))
- `moonshine-voice` is currently alpha, and model licensing differs by language. ([pypi.org](https://pypi.org/project/moonshine-voice/))
- Commercial builds must not silently depend on non-commercial assets.

---

## 11. Final ruling

**The official stack is Python-first.**

Use:

- Python for the product control plane
- native/external runtimes for inference and media
- Linux system services for target-platform desktop control
- Rust only for isolated hotspots justified by profiling

This is the most maintainable stack for a local-first KDE/Wayland desktop action runtime built in launchable phases.
