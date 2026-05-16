# Project Technical Specification

## Working title: Local-First Voice Runtime for KDE/Wayland

Status: Draft v1.0
Type: Living technical specification
Audience: Founder, core contributors, AI coding agents, future maintainers

---

## 1. Executive summary

This project is **not** a new Linux distribution in its initial phases.
It is a **local-first desktop action runtime** for **KDE Plasma on Wayland** with:

- local voice input and output

- typed, validated desktop actions

- a confirmation and permission system

- an MCP-compatible tool server

- optional cloud services layered on top of an open-source local core

  The product goal is to become the **trusted action layer for Linux desktop voice control**.

  The key product constraint is scope:

- do **not** build a broad multi-channel AI agent platform

- do **not** build a smart-speaker framework clone

- do **not** build a generic cross-platform automation system at the start

- do **not** ship arbitrary shell execution as the main execution path

  The initial wedge is:

> Reliable, local-first, permissioned voice control for KDE/Wayland desktop actions.

---

## 2. Why this product exists

There are already strong projects for adjacent layers:

- agent gateways and messaging surfaces

- general-purpose agent runtimes

- smart-speaker / satellite voice frameworks

- commercial voice productivity apps on macOS and Windows

  Therefore this project should occupy the missing layer:

> A Linux desktop execution substrate that is voice-native, model-compatible, safe, local-first, and MCP-addressable.

---

## 3. Product definition

### 3.1 Product statement

The project is a **daemon + UI + adapter layer** that lets users control KDE/Wayland desktop functions with voice or via agent tool calls.

### 3.2 Primary users

- Linux power users on KDE Plasma
- accessibility / hands-free users
- developers who want local voice workflows
- self-hosters who want local desktop control
- future teams who want managed Linux workstation automation

### 3.3 Core value proposition

- works locally
- privacy-preserving by default
- safe by default
- deterministic for common actions
- interoperable with the emerging MCP ecosystem

---

## 4. Product boundaries

### 4.1 In scope for v1

- KDE Plasma on Wayland
- local wake/listen/transcribe/respond loop
- typed desktop actions for common workflows
- confirmation and risk tier enforcement
- action preview and undo for reversible operations
- MCP server exposing approved desktop tools
- native packaging and setup wizard

### 4.2 Explicitly out of scope for v1

- custom distro as the primary product
- custom Wayland compositor
- custom LLM / STT / TTS model training as a core dependency
- generic remote chat gateway
- long-horizon memory platform
- fully autonomous agents operating without user approvals
- broad cross-platform support
- a plugin marketplace
- enterprise device fleet management

### 4.3 Deferred scope

- Universal Blue image
- OVOS/HiveMind satellite compatibility
- team management and policy plane
- paid cloud relay and hosted inference
- Windows / macOS companions

### 4.4 Cross-platform roadmap

Cross-platform expansion should stay phased:

- Phase 1: Linux/KDE/Wayland
- Phase 2: Windows
- Phase 3: macOS

That ordering is about execution risk, not ambition. The portable core should remain shared across platforms, including voice orchestration, planner logic, typed action schemas, the safety model, and the MCP server, while each operating system gets its own execution adapter layer. Do not let this roadmap turn the current Linux-first milestone into a simultaneous multi-platform launch target.

---

## 5. Product principles

1. **Local-first**: core desktop control must remain useful without cloud.
2. **Typed actions over shell**: primary execution path must be structured.
3. **Permissioned execution**: every action has a risk tier and validation path.
4. **Determinism first**: common commands should work without requiring an LLM.
5. **Model optionality**: planner model should be swappable.
6. **Interoperability first**: expose tools through MCP early.
7. **No rewrite mandate**: Python remains the primary control-plane language through Phase 2 unless profiling proves otherwise.
8. **Distribution follows reliability**: package later, image later still.
9. **KISS**: prefer the simplest implementation that satisfies the current milestone and runnable slice.
10. **YAGNI**: do not add speculative abstractions or future-phase capabilities before the current phase requires them.
11. **DRY**: remove duplication when it materially improves clarity and maintenance, but avoid abstractions that overcomplicate a small slice.

---

## 6. Open-source and monetization strategy

### 6.1 Open-source boundary

The following remain open source:

- local daemon
- action registry and validators
- desktop adapters
- local voice loop
- MCP server
- SDK / plugin API
- local setup tooling

### 6.2 Paid boundary

Paid offerings should be convenience and operations layers, not the core local product:

- hosted relay and sync
- optional hosted STT / TTS / planning fallback
- multi-device account sync
- team / fleet control plane
- audit logs, policies, SSO
- signed LTS builds and support
- professional services and integrations

### 6.3 Monetization principles

- never paywall offline/local control
- never make cloud mandatory for core tasks
- keep BYOK cloud routing available for self-hosters
- monetize convenience, management, compliance, and support

---

## 7. Naming and positioning

### 7.1 Naming requirement

Before public launch, perform a brand review and likely rename if necessary to avoid confusion with existing voice productivity brands.

### 7.2 Positioning line

Recommended positioning:

> Local-first voice control runtime for KDE/Wayland.

Alternative:

> Safe desktop actions for Linux, powered by voice and MCP.

---

## 8. Target platforms and environments

### 8.1 Primary platform

- KDE Plasma 6 on Wayland
- Fedora Kinoite / Fedora KDE / Bluefin KDE / Kubuntu as secondary validation targets

### 8.2 Supported packaging order

1. native install script + systemd user service
2. `.deb` and `.rpm`
3. Flatpak companion UI or partially sandboxed app
4. Universal Blue derived image

### 8.3 Unsupported in early phases

- GNOME-first support
- X11-first support
- non-Linux desktop platforms

---

## 9. High-level architecture

```text
Microphone / PipeWire
        |
        v
 Wake Word Detector -----> Listening State Controller
        |                         |
        v                         v
  Streaming STT ----------> Transcript Event Bus
                                    |
                    +---------------+----------------+
                    |                                |
                    v                                v
       Deterministic Intent Matcher          Local Planner Model
                    |                                |
                    +---------------+----------------+
                                    |
                                    v
                         Action Plan Validator
                                    |
                      +-------------+-------------+
                      |                           |
                      v                           v
               Confirmation UI              Auto-approved path
                      |                           |
                      +-------------+-------------+
                                    |
                                    v
                           Action Executor
                                    |
               +--------------------+----------------------+
               |          |          |         |           |
               v          v          v         v           v
             KWin      Files      Network   UPower   Notifications
                                    |
                                    v
                              Result Event Bus
                                    |
                         TTS / Visual Feedback / Logs
                                    |
                                    v
                               MCP Tool Server
```

---

## 10. Language and runtime policy

See [tech.md](./tech.md) for the authoritative technology stack decision, portability policy, and language-boundary rules.
See [linux.md](./linux.md) for the focused Linux machine requirements and handoff checklist.

### 10.1 Primary language

- **Python** for the main daemon, adapters, validation, UI integration glue, tests, evals, and MCP server.

### 10.2 Native runtimes used but not rewritten

- llama.cpp for local LLM serving
- PipeWire as audio substrate
- KDE / KWin / D-Bus services for desktop actions

### 10.3 Optional later native helper

A small Rust helper may be introduced later only if profiling shows a clear need for:

- lower-latency microphone processing
- a smaller privileged helper
- a lightweight satellite binary

### 10.4 Rewrite policy

No full rewrite before the end of Phase 2.
Only isolate hotspots after metrics justify it.

---

## 11. Recommended technology stack

### 11.1 Core control plane

- Python 3.12+
- uv or poetry for development environment management
- systemd user service for daemon lifecycle
- structured logging in JSON
- SQLite for local state and audit metadata

### 11.2 Audio and speech

- PipeWire for microphone capture
- openWakeWord-compatible wake-word layer
- Moonshine for local STT
- Kokoro for local TTS

### 11.3 Planning

- deterministic matcher for common commands
- llama.cpp local server for planner model
- Qwen-class 4B or 8B model as initial planner
- schema-constrained JSON outputs only

### 11.4 Desktop/system integration

- D-Bus adapters
- KWin scripting integration
- freedesktop notifications
- NetworkManager
- UPower
- xdg-open / desktop files for app launch

### 11.5 UI

- PySide6 tray app and confirmation dialogs
- optional KRunner integration later

### 11.6 Interoperability

- MCP server: stdio first, Streamable HTTP later

---

## 12. Licensing constraints and distribution rules

### 12.1 Commercial distribution rule

Commercial builds must not depend on non-commercial model assets bundled by default.

### 12.2 Initial licensing stance

- local daemon and SDK: permissive open-source license
- hosted control plane: may be source-available, copyleft, or proprietary depending on fundraising and community strategy

### 12.3 Language scope for commercial distribution

Start with English-first support if model licensing for other languages is unclear.

---

## 13. Core modules

### 13.1 `audio.capture`

Responsibilities:

- microphone discovery

- PipeWire capture

- buffering and framing

- VAD hooks if needed later

  Outputs:

- `AudioFrame`

### 13.2 `wakeword`

Responsibilities:

- low-latency wake-word inference

- per-model threshold config

- debounce and cooldown logic

  Outputs:

- `WakeEvent`

### 13.3 `stt`

Responsibilities:

- streaming transcription

- final transcript segmentation

- confidence estimation

- transcript normalization

  Outputs:

- `TranscriptEvent`

### 13.4 `intent`

Responsibilities:

- deterministic matching for known commands

- argument extraction where possible

- confidence score

- route unknowns to planner

  Outputs:

- `IntentMatch`

### 13.5 `planner`

Responsibilities:

- transform transcript + context into schema-valid action plan

- never bypass validator

- never execute directly

  Outputs:

- `ActionPlan`

### 13.6 `validator`

Responsibilities:

- schema validation

- parameter normalization

- risk tier assignment

- policy enforcement

- confirmation decision

- undo / rollback presence check

  Outputs:

- `ValidatedActionPlan`

### 13.7 `executor`

Responsibilities:

- call typed adapters

- collect structured results

- emit events

- populate audit log

  Outputs:

- `ActionResult`

### 13.8 `adapters.*`

Initial adapters:

- `adapters.apps`
- `adapters.windows`
- `adapters.notifications`
- `adapters.power`
- `adapters.network`
- `adapters.files`
- `adapters.audio`
- `adapters.clipboard`

### 13.9 `tts`

Responsibilities:

- convert short responses to speech
- choose voice
- support interruption / barge-in later

### 13.10 `ui.tray`

Responsibilities:

- tray state
- microphone and wake state visibility
- last command preview
- confirmation dialogs
- failure notifications

### 13.11 `mcp.server`

Responsibilities:

- expose approved tools and resources
- provide tool schemas
- enforce same validator / permissions as local UI
- deny unsupported actions cleanly

### 13.12 `audit`

Responsibilities:

- append-only structured action history
- reversible action references
- privacy-preserving local logs

---

## 14. State machine

The runtime must implement a visible, testable state machine.

States:

- `IDLE`

- `WAKE_DETECTED`

- `LISTENING`

- `TRANSCRIBING`

- `UNDERSTANDING`

- `AWAITING_CONFIRMATION`

- `EXECUTING`

- `RESPONDING`

- `ERROR`

- `COOLDOWN`

  State transitions must be logged.
  The tray UI must reflect the current state.

---

## 15. Interaction modes

### 15.1 Local direct mode

User speaks to the desktop.
System responds locally.

### 15.2 Push-to-talk mode

Useful for noisy environments and dev mode.

### 15.3 Agent mode via MCP

External agent invokes the same tools through MCP.
The same policies apply.

### 15.4 Cloud-augmented mode

Optional. Cloud may assist with planning or speech only when the user explicitly enables it.

---

## 16. Data contracts

### 16.1 `TranscriptEvent`

```json
{
  "id": "uuid",
  "timestamp": "2026-04-12T10:00:00Z",
  "text": "open firefox",
  "is_final": true,
  "confidence": 0.93,
  "source": "microphone"
}
```

### 16.2 `ActionPlan`

```json
{
  "plan_id": "uuid",
  "source": "deterministic|planner",
  "original_text": "open firefox",
  "actions": [
    {
      "tool": "apps.launch",
      "args": {"app": "firefox"},
      "risk_tier": 0,
      "requires_confirmation": false,
      "undoable": false
    }
  ]
}
```

### 16.3 `ActionResult`

```json
{
  "plan_id": "uuid",
  "status": "success|partial|failed|denied|cancelled",
  "results": [
    {
      "tool": "apps.launch",
      "status": "success",
      "message": "Firefox launched",
      "undo_token": null
    }
  ]
}
```

### 16.4 `ActionPlanEvent`

```json
{
  "event_id": "uuid",
  "timestamp": "2026-04-12T10:00:01Z",
  "kind": "action.plan_generated",
  "plan": {
    "plan_id": "uuid",
    "source": "deterministic",
    "original_text": "open firefox",
    "actions": [
      {
        "tool": "apps.launch",
        "args": {"app": "firefox"},
        "risk_tier": 0,
        "requires_confirmation": false,
        "undoable": false
      }
    ]
  }
}
```

### 16.5 `ActionResultEvent`

```json
{
  "event_id": "uuid",
  "timestamp": "2026-04-12T10:00:02Z",
  "kind": "action.result_generated",
  "result": {
    "plan_id": "uuid",
    "status": "success",
    "results": [
      {
        "tool": "apps.launch",
        "status": "success",
        "message": "Launched firefox",
        "undo_token": null
      }
    ]
  }
}
```

### 16.6 `ResponseEvent`

```json
{
  "event_id": "uuid",
  "timestamp": "2026-04-12T10:00:03Z",
  "kind": "response.generated",
  "text": "Launched firefox",
  "status": "success",
  "plan_id": "uuid"
}
```

### 16.7 `CommandMetrics`

```json
{
  "transcript": "open firefox",
  "matched": true,
  "total_duration_ms": 18.5,
  "planning_duration_ms": 4.2,
  "execution_duration_ms": 9.1,
  "response_duration_ms": 1.3
}
```

---

## 17. Tooling model

### 17.1 Tool rules

Each tool must define:

- name
- description
- JSON schema for arguments
- JSON schema for result
- risk tier
- whether confirmation is required
- whether undo is available
- allowed side effects
- test fixtures

### 17.2 Initial tool set

#### Tier 0

- `apps.launch`
- `apps.focus`
- `windows.list`
- `windows.switch`
- `time.now`
- `power.battery_status`
- `audio.get_volume`
- `notifications.show`
- `files.list_recent`

#### Tier 1

- `files.create_folder`
- `audio.set_volume`
- `audio.set_muted`
- `network.set_wifi_enabled`
- `windows.minimize`

#### Tier 2

- `files.move`
- `files.rename`
- `network.connect_known_ssid`

#### Disabled in v1

- recursive delete
- package install
- system service control
- sudo escalation
- arbitrary shell

---

## 18. Permission and risk model

### 18.1 Risk tiers

- **Tier 0**: read-only or clearly harmless UI actions; auto-execute
- **Tier 1**: reversible local changes; execute with toast + undo when possible
- **Tier 2**: meaningful state changes; explicit confirmation required
- **Tier 3**: destructive or system-admin actions; disabled in v1
- **Tier 4**: privileged / dangerous operations; unsupported in v1

### 18.2 Confirmation UX

A confirmation dialog must show:

- normalized action description
- affected resource(s)
- whether undo exists
- timeout behavior
- explicit Cancel button

### 18.3 Undo policy

Tier 1 actions should support undo whenever technically possible.
Tier 2 actions must specify rollback behavior or state why rollback is unavailable.

---

## 19. Security model

1. **No raw shell default path**.
2. **All actions validated before execution**.
3. **No privilege escalation in v1**.
4. **MCP tools use the same validator and policy engine**.
5. **Cloud requests are opt-in and visibly marked**.
6. **Sensitive logs remain local by default**.
7. **Per-tool allowlists define valid targets and parameters**.
8. **File operations limited to safe roots in early phases**.
9. **All state-changing tools require audit entries**.
10. **Any experimental shell tool must be hidden behind a dev-only feature flag**.

---

## 20. Context policy

Short-lived context only in early phases.

Rules:

- keep a rolling 3 to 5 turn context

- expire after ~30 seconds of silence by default

- context must never silently raise the risk tier of a command without re-confirming

- context is for disambiguation, not autonomy

  Examples:

- “Open Firefox” -> “Now go to Gmail”

- “Create a folder on desktop called projects” -> “Rename it to clients”

---

## 21. Observability and evaluation

### 21.1 Required telemetry classes

Local-only by default:

- latency per stage
- state transitions
- validation outcomes
- execution outcomes
- confirmation accept / deny rates
- wake-word false accept / false reject counts

### 21.2 Evaluation harness

Must exist by the end of Phase 0B.

Components:

- transcript replay runner
- golden command corpus
- action-plan validator tests
- end-to-end scenario tests
- regression dashboard

### 21.3 Required metrics

- wake-word false activation rate
- STT word error trend on command corpus
- intent routing accuracy
- action validation precision
- successful completion rate by tool
- p50/p95 end-to-end latency
- crash-free session rate

---

## 22. Performance targets

### 22.1 Recommended reference targets

On recommended hardware:

- wake detect to listening indicator: under 200 ms
- final transcript for short command: under 800 ms
- validated plan creation: under 400 ms for deterministic, under 1200 ms for planner
- full response for Tier 0 launch/status actions: p95 under 2 seconds

### 22.2 Minimum acceptable targets

On minimum hardware:

- p95 short-command completion under 3 seconds
- daemon idle CPU low enough for continuous use
- always-on memory stable across 8-hour use

---

## 23. Repository structure

```text
repo/
  apps/
    tray/
    setup_wizard/
  services/
    daemon/
    mcp_server/
  libs/
    contracts/
    audio/
    wakeword/
    stt/
    intent/
    planner/
    validator/
    executor/
    adapters/
    audit/
    tts/
    ui_shared/
  tests/
    unit/
    integration/
    e2e/
    fixtures/
    eval/
  packaging/
    deb/
    rpm/
    systemd/
    flatpak/
    ublue/
  docs/
    architecture/
    schemas/
    runbooks/
    threat_model/
```

---

## 24. Development workflow

### 24.1 Branching

- trunk-based or short-lived branches
- every merge must keep the daemon runnable

### 24.2 Quality gates

Before merge:

- lint
- type checking where practical
- unit tests for changed modules
- contract tests for tool schemas
- integration tests for affected adapters

### 24.3 AI-assisted development rules

When using AI agents:

- require the agent to change only one bounded surface per task
- require tests and updated docs in the same PR
- prohibit architecture drift from this spec without an ADR
- prohibit adding new privileged execution paths without explicit approval

---

## 25. Architecture decision records

Every major deviation requires an ADR.
Initial ADR list:

- ADR-001 Python as control-plane language
- ADR-002 KDE/Wayland first, X11 out of scope
- ADR-003 Typed actions over shell
- ADR-004 MCP as first-class interface
- ADR-005 Native packaging before Flatpak-first distribution
- ADR-006 Universal Blue image only after stable daemon

---

## 26. Phased delivery plan

## Phase 0A — Deterministic local demo

### Goal

Prove the local loop works safely without relying on an LLM.

### Scope

- microphone capture
- wake-word detection
- Moonshine transcription
- deterministic intent matching
- typed execution for 8 to 10 commands
- basic tray state
- spoken or visual response

### Commands in scope

- open Firefox
- open terminal
- what time is it
- what is my battery level
- set volume to 50 percent
- mute / unmute audio
- turn Wi-Fi on / off
- show a notification
- show files modified today
- create folder on desktop

### Deliverables

- runnable daemon
- event schemas
- structured logs
- minimal tray app
- demo script and video
- reproducible install script

### Checkpoints

- microphone works across at least 2 KDE target distros
- wake-word false activation measured on idle background audio
- deterministic matcher handles paraphrase set for each command
- no raw shell on normal path

### Exit criteria

- 95%+ success on curated command corpus
- no unconfirmed destructive action path exists
- p95 latency under 2 seconds on recommended hardware
- demo repeatable by another developer

### Stop criteria

Do not proceed if:

- wake-word false accepts are too high for practical use
- deterministic routing cannot reliably support the seed command set
- the daemon is unstable over a 1-hour session

---

## Phase 0B — Safe execution engine

### Goal

Replace demo glue with a production-worthy action system.

### Scope

- action registry
- validator
- permission tiers
- confirmation dialogs
- undo support for reversible actions
- audit log
- replay/eval harness

### Deliverables

- JSON schema for `ActionPlan`
- validator and policy engine
- per-tool metadata
- reversible action framework
- transcript replay runner
- regression test corpus

### Checkpoints

- every tool has a schema and risk tier
- every state-changing tool has tests
- confirmation UX is human-readable and consistent
- audit entries created for all state-changing actions

### Exit criteria

- zero direct executor paths that bypass validation
- 100% of shipped tools covered by contract tests
- all Tier 1 tools either support undo or document why not
- at least 50 replay scenarios passing

### Stop criteria

Do not proceed if:

- the validator is bypassable from any shipped path
- confirmation prompts are too vague to be safe
- there is no reliable audit trail

---

## Phase 1 — Local planner release

### Goal

Add a local LLM for paraphrase handling and simple planning.

### Scope

- planner model via llama.cpp
- strict schema-constrained JSON output
- 2-step action chains maximum
- short-lived conversation context
- clear preview of planned actions

### Planner responsibilities

- map natural language to existing tools
- extract arguments
- choose among valid tools
- explain intended action in plain language

### Planner prohibitions

- no arbitrary shell generation
- no tool creation at runtime
- no silent policy bypass
- no direct execution

### Deliverables

- planner service client
- planner prompt template
- planner fallback routing rules
- confidence thresholds
- preview/confirmation UI improvements

### Checkpoints

- planner output passes schema validation on regression suite
- deterministic matcher remains primary for known commands
- context expiration works as designed
- all planner-routed state changes still pass through confirmation tiers

### Exit criteria

- 20 to 30 stable commands / intents
- one-week internal dogfood with no critical safety incident
- action completion rate significantly better than deterministic-only build for paraphrases

### Stop criteria

Do not proceed if:

- planner hallucinates tools or unsafe arguments too often
- latency is unacceptable on target hardware
- users cannot understand the preview / confirmation text

---

## Phase 2 — Distribution release

### Goal

Make installation and daily use easy.

### Scope

- setup wizard
- native packaging
- systemd user service
- user-facing settings panel
- crash recovery and better diagnostics
- optional Flatpak companion UI

### Deliverables

- `.deb` and `.rpm` packages or equivalent installer
- first-run setup wizard
- mic test, wake-word calibration, TTS test
- settings export/import
- basic docs site

### Checkpoints

- clean install from fresh OS
- auto-start works after reboot
- setup completion under 2 minutes
- rollback strategy for upgrades

### Exit criteria

- first successful command within 5 minutes of install for a new tester
- stable 8-hour dogfood sessions
- installation support burden low enough for open release

### Stop criteria

Do not proceed if:

- setup fails frequently on target distros
- upgrade path is brittle
- bug reports are dominated by packaging and environment drift

---

## Phase 3 — Interoperability and ecosystem

### Goal

Make the runtime broadly useful to outside agents and contributors.

### Scope

- MCP server GA
- stable plugin API for new tools
- optional OVOS/HiveMind bridge exploration
- public SDK docs

### Deliverables

- stdio MCP server
- Streamable HTTP MCP server
- tool/resource docs
- plugin developer guide
- signed plugin manifest format

### Checkpoints

- MCP Inspector can enumerate and invoke tools successfully
- policy engine behaves identically for local and MCP calls
- third-party developer can add one new safe tool from docs alone

### Exit criteria

- at least 3 third-party contributed tools
- stable external MCP integration story
- no security regression from remote tool invocation

### Stop criteria

Do not proceed if:

- MCP surface grows faster than the validator can secure
- plugin API is unstable between releases

---

## Phase 4 — Optional cloud and teams

### Goal

Add monetizable cloud features without weakening the OSS local core.

### Scope

- hosted relay
- optional hosted inference
- multi-device sync
- account system
- team policies and audit logs
- admin console

### Deliverables

- hosted account service
- encrypted sync for settings/history metadata
- team workspace model
- device enrollment
- role-based permissions
- update channels

### Checkpoints

- local-only path remains fully functional
- cloud indicators are visible and honest
- BYOK remains supported for advanced users

### Exit criteria

- first paid preview customers can use hosted convenience features
- self-hosted users can ignore cloud completely

### Stop criteria

Do not proceed if:

- cloud becomes required for core tasks
- the architecture forks into incompatible local vs cloud products

---

## Phase 5 — Image / appliance distribution

### Goal

Ship a polished image after the runtime is already stable.

### Scope

- Universal Blue derived image
- preinstalled runtime and models
- tuned defaults
- atomic updates

### Deliverables

- bootable image
- image build pipeline
- recovery docs
- update ring strategy

### Exit criteria

- image improves onboarding materially versus package install
- no major divergence from the package-based product

---

## 27. Validation plan by phase

### Phase-gate rule

No phase advances until all exit criteria for the current phase are satisfied.

Development workflow additions:

- use TDD within each milestone: write or adjust the test first, then implement the minimal code to satisfy it
- create a git commit at the end of each completed implementation step, not only at phase or milestone checkpoints
- use a descriptive commit message that states the concrete behavior or interface added in that step
- avoid bundling work from a later phase into the current checkpoint commit

Documentation sync rule:

- keep this document as the source of truth for scope, milestone boundaries, stop lines, and status
- update this document in the same slice whenever scope, interfaces, workflow, or milestone status changes
- update `README.md` in the same slice whenever runnable behavior, setup, or developer commands change
- do not create a checkpoint commit until code, tests, and docs agree on the current state

### Mandatory review at each gate

- product review
- safety review
- latency review
- installation review
- user experience review
- scope review

### Gate outputs

Each phase must conclude with:

- release notes
- measured metrics report
- top 10 bugs
- go / no-go recommendation
- updated roadmap

---

## 28. Monetization plan

## 28.1 Free open-source core

Free tier includes:

- local voice runtime
- local desktop actions
- MCP server
- setup wizard
- single-device use
- BYOK support

## 28.2 Personal cloud subscription

Target offer:

- remote access / relay

- cross-device settings sync

- encrypted backup and restore

- optional hosted voice/planner credits

- satellite relay outside the LAN

  Indicative price band:

- low monthly consumer subscription

## 28.3 Team / fleet subscription

Target offer:

- device enrollment

- organization policies

- audit logs

- shared action packs

- update rings

- admin console

- SSO later

  Indicative model:

- per device or per active admin / user

## 28.4 Enterprise support / LTS

Target offer:

- signed builds
- long-term support
- security response SLA
- onboarding and deployment help
- private issue handling

## 28.5 Professional services

Early revenue path:

- custom integrations
- deployment support
- policy templates
- accessibility-focused workflows
- custom wake-word / vocabulary tuning where licensing allows

## 28.6 Later revenue options

- OEM / preinstalled mini PCs
- certified appliance image
- marketplace revenue share only after ecosystem maturity

---

## 29. Business KPIs

Open-source KPIs:

- GitHub stars and contributors

- install-to-weekly-active ratio

- crash-free sessions

- command success rate

- community-added tools

  Business KPIs:

- free-to-paid conversion

- support revenue

- design partner count

- net revenue retention for teams

- cloud gross margin

---

## 30. Immediate next milestones

### Milestone M0 — Spec lock

- approve scope and naming direction
- approve language policy
- approve no-shell-by-default policy
- approve MCP-first interoperability policy

### Milestone M1 — Repo scaffold

- repository layout
- contracts package
- structured logging
- event bus abstraction
- daemon skeleton

#### Milestone M1 implementation profile

Goal:
Create the smallest runnable Python package that establishes the Phase 0A control-plane boundaries without pulling in wake-word, STT, TTS, D-Bus, or UI dependencies yet.

Implementation constraints:

- keep the initial code in a single Python package under `src/operance/`
- prefer standard-library implementations for config, logging, and in-memory event dispatch
- model the Phase 0A runtime contracts now, but keep execution adapters as interfaces only
- make the daemon runnable in a no-op developer mode so tests and local inspection work before audio integration exists

Milestone M1 repository shape:

```text
repo/
  docs/
    prompt/
    requirements/
  src/
    operance/
      adapters/
      models/
      runtime/
  tests/
    unit/
```

Milestone M1 modules:

- `operance.config`: environment-backed application settings and path defaults
- `operance.logger`: JSON logging formatter and bootstrap helper
- `operance.models.events`: runtime state, transcript, wake, and state transition contracts
- `operance.models.actions`: typed deterministic action plan and result contracts for the seed command set
- `operance.runtime.event_bus`: synchronous in-memory pub/sub abstraction for early wiring
- `operance.runtime.state_machine`: explicit, validated runtime state transitions with transition history
- `operance.adapters.base`: protocol-style interfaces for apps, power, audio, network, notifications, and files adapters
- `operance.daemon`: lightweight daemon skeleton that wires config, logging, event bus, and state machine together
- `operance.cli`: minimal command-line entry point for developer smoke tests

Milestone M1 test scope:

- config defaults and environment overrides
- JSON log formatting
- shared model serialization expectations
- allowed and rejected state transitions
- daemon bootstrap and event emission through the in-memory bus

Milestone M1 stop line:

- do not add real audio capture, wake-word inference, STT, TTS, D-Bus calls, or tray UI
- do not add a validator, permission dialogs, or undo logic yet
- do not add planner hooks or generic plugin abstractions

### Milestone M2 — Deterministic voice loop

- wake-word
- STT
- deterministic commands
- tray UI

Current implementation slice:

- deterministic transcript-to-action matching is in progress before real wake-word, STT, and tray wiring
- the current matcher targets the Phase 0A seed command set and produces single-action typed plans only
- explicit mute / unmute handling is modeled as `audio.set_muted` in the current action surface
- final transcripts are now wired through the daemon to emit structured action-plan events and execute against mock adapters in developer mode
- developer-mode file actions are kept inside a configured desktop root, defaulting to `.operance/Desktop`
- final transcripts now also emit a plain-text response event, including an unmatched fallback for unknown commands
- deterministic command handling now records in-memory timing metrics and exposes p95 tracking for total command latency
- a built-in deterministic command corpus can now be run to report success rate and p95 latency for the current seed command set
- reusable transcript sources can now drive deterministic batch sessions without requiring audio integration
- the daemon now completes `RESPONDING -> COOLDOWN -> IDLE`, enabling sequential command handling within one reusable session
- a terminal-driven interactive session mode now exists for typed local demos while audio integration remains deferred
- the deterministic matcher now passes a curated paraphrase corpus above the Phase 0A `95%+` success threshold in tests
- a structured runtime status snapshot now exists to support a future tray UI and current developer diagnostics
- platform-neutral `audio.capture`, `wakeword`, and `stt` boundaries now exist with a scripted developer pipeline for non-Linux environments
- an environment doctor command now reports whether the current machine matches Linux/KDE target expectations
- the Linux doctor output now also reports the command-line desktop surfaces required by the first real Linux adapter slice, including `gdbus` for desktop-service-backed calls
- replayable transcript fixtures now exist for deterministic regression checks and pass/fail summaries

### Milestone M3 — Validator and permissions

- action registry
- policy engine
- confirmation dialogs
- audit log

Current implementation slice:

- a typed action registry now defines tool metadata for the current deterministic command set
- generated plans now pass through validation and metadata normalization before execution
- invalid plans are denied before execution and surfaced as structured validation outcomes
- successful and denied final commands now create local SQLite audit entries
- a policy layer now distinguishes auto-approved, confirmation-required, and denied plans before execution
- reversible mock actions now register undo callbacks and emit undo tokens within the current daemon session
- a portable in-process MCP server skeleton now enumerates approved tools with input schemas and routes direct calls through the same validator, policy, executor, and audit surfaces
- the portable MCP server now also exposes static resources for tool catalog and execution policy inspection
- rejected MCP tool requests, including unknown tool names, now create local audit entries
- the developer CLI can now inspect MCP tool metadata and invoke one MCP tool with JSON args for local smoke testing
- the developer CLI can now inspect MCP resource metadata and read static MCP resources directly
- a minimal stdio MCP session now advertises a fixed supported protocol version during `initialize`, supports JSON-RPC `ping`, `tools/list`, `tools/call`, `resources/list`, and `resources/read`, validates `jsonrpc: "2.0"` and request-object shape, and ignores notification-style messages without request ids for local transport smoke tests
- the developer CLI can now run the MCP stdio loop directly for local transport validation on macOS before Linux-specific integration
- when developer mode is disabled on Linux, the current deterministic action surface can now execute through command-backed adapters for app launch, app focus, notifications, battery, audio, network, and desktop file actions
- Linux app focus now prefers a KWin scripting bridge over the session bus, while notifications prefer the freedesktop notification service and battery status prefers UPower, all with bounded fallback paths inside the adapter layer
- the current deterministic command surface now includes app focus and `audio.get_volume` inspection in addition to the earlier launch, notification, battery, audio mutation, network, and file actions
- the current deterministic command surface now also includes `windows.list` and `windows.switch`, backed by KWin `WindowsRunner` on Linux

### Milestone M4 — Planner release

- local planner
- preview and 2-step plans
- regression harness

Current implementation slice:

- planner-origin action plans now enforce the current two-step maximum at the typed contract layer
- portable preview helpers can now render one- and two-step planner action plans into plain language before any UI work begins
- schema-constrained planner payloads can now be parsed into typed planner action plans before validation and policy enforcement
- planner fixture replay can now report parser-plus-validator pass/fail summaries for regression coverage
- the developer CLI can now render planner previews from JSON payloads and run planner regression fixtures directly on macOS
- planner payload schema generation now exposes the current constrained JSON contract with a two-step maximum
- the developer CLI can now print the planner payload schema directly for local planner setup and inspection
- planner prompt-template helpers now combine approved tool metadata with the exported constrained JSON schema
- planner service-client helpers now build llama.cpp-compatible request payloads and parse OpenAI-style planner responses
- planner fallback routing policy now captures deterministic preference, partial-transcript rejection, and confidence-based planner fallback
- short-lived planner context windows now support expiration and bounded recent history for future planner requests
- planner request construction now supports injecting active short-lived context messages into local planner calls
- the developer CLI can now print the exact planner service request payload for a transcript
- the developer CLI can now print the planner fallback routing decision for a transcript and confidence score
- exported JSON schema helpers now cover the current `ActionPlan` and `ActionResult` contracts
- the developer CLI can now print the exported `ActionPlan` and `ActionResult` schemas directly

### Milestone M5 — Installer release

- setup wizard
- distro packaging
- docs and dogfooding

---

## 31. Final recommendation

Build this as a **desktop runtime**, not as a broad agent platform and not as a distro-first effort.

The sequence should be:

1. deterministic voice + typed actions

2. validator + permissions

3. local planner

4. packaging and usability

5. MCP ecosystem

6. cloud monetization

7. image distribution

   That order preserves focus, keeps the safety story coherent, and leaves room for both open-source adoption and paid offerings.
