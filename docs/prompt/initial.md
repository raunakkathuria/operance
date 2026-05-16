You are the lead engineer and technical architect for this project.

Project:
Build an open-source, local-first KDE/Wayland desktop action runtime with voice UX and MCP compatibility.
This is not a new Linux distro in the early phases. It is a safe desktop action layer that can later be packaged as a distribution/image.

Primary goals:
1. Keep the core open source.
2. Build in small launchable phases.
3. Follow KISS, DRY, and YAGNI strictly.
4. Prefer reliable deterministic behavior over impressive demos.
5. Do not build broad agent features before the desktop action core is solid.
6. Always stop at the end of each phase/milestone for review and feedback before moving on.

Product principles:
- Local-first by default
- KDE + Wayland first
- English-first initially
- Typed actions, not arbitrary shell commands
- Deterministic commands before LLM planning
- Safety and confirmation from day one
- MCP as a first-class interface after core actions are stable
- No speculative abstractions
- No custom kernel, compositor, model training, or distro work in early phases

Language and implementation policy:
- Use Python as the main language through Phase 2 unless profiling proves a hotspot.
- Use native/external runtimes where they already exist, such as llama.cpp and system services.
- Do not introduce Rust, Go, or C/C++ for our own code unless there is a measured reason.
- Prefer simple modules, explicit interfaces, and standard libraries where practical.

Core stack assumptions:
- Python 3.12+
- PySide6 for tray/setup UI if needed
- PipeWire for audio
- openWakeWord for wake word
- Moonshine for STT and deterministic intent recognition where practical
- Kokoro for TTS
- llama.cpp server for local LLM planning later
- D-Bus adapters for KDE/KWin, NetworkManager, UPower, notifications
- pytest for tests
- ruff + black + mypy for code quality

Non-negotiable engineering rules:
- KISS: choose the simplest design that works for the current phase
- DRY: avoid duplicate logic, but do not create abstractions too early
- YAGNI: do not implement features for future phases unless required now
- No premature plugin system
- No generic workflow engine
- No generic memory layer
- No remote cloud dependency for core functionality
- No raw shell execution in the normal path
- No work on future phases until the current phase exit criteria are met

Execution style:
Work in phases and milestones.
For each phase:
1. Restate the goal in one paragraph.
2. List only the scope for this phase.
3. List what is explicitly out of scope.
4. Propose the smallest implementation that can work.
5. Define file/module structure.
6. Define interfaces and JSON schemas only for what is needed now.
7. Implement incrementally.
8. Add tests.
9. Add a short README/update note for that phase.
10. Stop and present a checkpoint summary with:
   - what was built
   - what works
   - what is mocked or deferred
   - known risks
   - exact next recommended milestone

Important behavior constraints:
- Do not jump ahead.
- Do not silently refactor the architecture into something more abstract than needed.
- Do not add optional frameworks or infrastructure unless the current phase requires them.
- When uncertain between a simpler and more powerful design, choose the simpler one.
- Prefer explicit typed data classes/Pydantic models over magic or dynamic patterns.
- Prefer composition over inheritance.
- Keep modules small and understandable.
- Keep public interfaces stable and internals replaceable.

Project phases:
Phase 0A: Deterministic local demo
Goal:
wake word -> speech -> deterministic intent -> typed desktop action -> spoken/text response

In scope:
- repo scaffold
- config system
- structured logging
- app state machine
- event models
- typed command models
- simple daemon skeleton
- mockable adapters
- initial adapters for:
  - app launch
  - time/date
  - battery status
  - volume set/get
  - Wi-Fi toggle/status
  - notifications
- minimal CLI runner
- test harness
- no LLM yet
- no destructive file actions

Exit criteria:
- 8 to 10 deterministic commands work
- clear module boundaries exist
- tests pass
- demo can run locally
- p95 latency target is tracked, even if still rough

Phase 0B: Safe execution engine
In scope:
- structured action graph
- validator
- permission tiers
- preview/confirm flow
- rollback/undo for reversible actions
- action audit log
- replayable transcript/action fixtures

Exit criteria:
- every action flows through validation
- no raw shell on normal path
- reversible actions have undo or explicit rationale if not possible
- destructive actions remain disabled

Phase 1: Local planner release
In scope:
- local LLM via llama.cpp
- schema-constrained JSON outputs
- paraphrase-to-intent mapping
- parameter extraction
- very limited 2-step plans
- short-lived conversational context
- strict fallback to deterministic path

Exit criteria:
- local planner improves usability without bypassing safety
- planner cannot directly execute actions
- current actions remain typed and validated
- measurable success rate improves on paraphrased commands

Phase 2: Packaging and onboarding
In scope:
- install script and/or native packages
- setup wizard
- system tray integration
- autostart service
- configuration management
- logs and diagnostics export

Exit criteria:
- clean install on target distro(s)
- first successful command within a few minutes
- setup understandable by a non-developer tester

Phase 3: MCP interface and ecosystem hooks
In scope:
- MCP server exposing safe typed desktop actions
- minimal auth/trust model for local usage
- stable tool schemas
- docs for external agent integration

Exit criteria:
- another agent/client can call our desktop tools safely
- tool schemas are versioned and documented

Phase 4: Optional hosted monetization layer
In scope:
- only after local core is useful and open source
- remote access relay
- encrypted sync/backup
- optional hosted inference credits
- team/fleet administration
- keep local core fully functional without subscription

Exit criteria:
- paid features are convenience and fleet features, not core functionality
- OSS core remains valuable and self-hostable

Current task:
Start with Phase 0A only.

What I want from you right now:
1. Propose the minimal architecture for Phase 0A.
2. Propose the repository structure.
3. Define the core modules and interfaces for this phase only.
4. Define the event model and typed action model for current deterministic commands only.
5. Generate the initial implementation plan in small steps.
6. Then generate the code for the first milestone only:
   - project scaffold
   - pyproject.toml
   - package layout
   - config module
   - logger module
   - shared models
   - state machine skeleton
   - stub adapter interfaces
   - pytest setup
   - basic README
7. Include tests for the generated code.
8. Stop after milestone 1 and give a concise checkpoint report.

Output format:
- Section 1: Phase 0A architecture
- Section 2: Repo structure
- Section 3: Milestone plan
- Section 4: Code for milestone 1
- Section 5: Tests
- Section 6: Checkpoint summary

Quality bar:
- Production-minded but not overengineered
- Readable code over clever code
- Small modules
- Strong typing
- Clear docstrings where useful
- Tests for core behavior
- No placeholder complexity for imagined future needs

Remember:
We are optimizing for iterative shipping, real feedback, and maintainability.
Build the smallest solid foundation first, then stop.