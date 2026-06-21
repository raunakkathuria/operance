# Beta Feedback Program

Status: Planning note  
Type: Traction and feedback acquisition plan  
Audience: Maintainers and contributors

---

## 1. Purpose

Operance needs real user feedback before broader product work can be trusted.
The first traction goal is not broad awareness. It is a small, repeatable loop
that brings in useful reports from people running the current supported target.

Initial target:

- recruit 20 to 30 Fedora KDE Plasma Wayland testers
- get at least 10 clean install attempts
- collect at least 5 useful command, tray, voice, or setup reports
- identify the top recurring install, command, and onboarding failures
- fix the highest-signal issues before broad launch surfaces

Do not market Operance as a general AI assistant yet. The credible beta promise
is narrower:

> Local-first, safety-gated voice control for Fedora KDE Wayland.

---

## 2. Audience Order

### 2.1 Fedora KDE and KDE Plasma users

These are the first users to recruit because they match the current supported
runtime. Ask for a 10-minute beta test, not a general product review.

Best places:

- KDE Discuss
- Fedora Discussion
- Fedora KDE social/community spaces where feedback requests are allowed
- r/kde
- r/Fedora

### 2.2 Linux automation and local-AI developers

Developers should see Operance as a safe desktop action runtime, not just a
voice UI. Lead with:

- typed actions
- validation, policy, and confirmation gates
- Linux provider and adapter boundaries
- optional local planner
- MCP-compatible control surface
- JSON desktop skill packs

Best places:

- GitHub
- Hacker News Show HN after the install path is ready for public traffic
- Lobsters, if a maintainer has an account and the post fits community norms
- local-AI, Linux desktop, KDE, and Python developer communities

### 2.3 Accessibility and hands-free users

Approach carefully and honestly. Operance can be useful for hands-free desktop
experiments, but it should not be presented as a mature accessibility product
until reliability is higher.

Use wording such as:

> Early hands-free workflow beta for Fedora KDE Wayland.

Avoid claiming:

- full accessibility coverage
- medical or assistive reliability
- broad desktop compatibility

### 2.4 Normal users

Normal users should come later, after technical beta feedback has reduced the
most common setup and command failures.

Normal-user messaging should focus on:

- click the tray icon
- say a simple desktop request
- Operance routes it through safe desktop actions
- issue reporting is built in if something fails

Do not lead normal-user materials with MCP, planner schemas, adapter internals,
or local model configuration.

---

## 3. Feedback Funnel

Every public feedback path should send people through the same loop:

1. Install the current packaged beta.
2. Run installed readiness.
3. Try a short command script.
4. Generate an issue report or support bundle if anything fails.
5. File a GitHub issue using the generated report.

Current setup path:

```bash
curl -fsSLO https://github.com/raunakkathuria/operance/releases/download/<release-tag>/setup.sh
bash ./setup.sh --release-url https://github.com/raunakkathuria/operance/releases/download/<release-tag>
operance --version
operance --installed-smoke
operance --public-beta-checklist
```

Tester command script:

```text
open browser
open google.com
search google for linux automation
open firefox
open downloads
what time is it
wifi status
what is the volume
set volume to 50 percent
```

Failure reporting:

```bash
operance --issue-report
operance --support-bundle
```

Ask testers to report even boring failures:

- setup did not finish
- tray did not appear
- microphone did not capture
- command was misunderstood
- command was understood but did the wrong thing
- confirmation was confusing
- supported-command help was unclear
- issue report was missing useful context

---

## 4. Repo And Website Prep

Before outreach, make sure the public materials answer the same questions.

### 4.1 GitHub repository

Keep these easy to find:

- README public beta quickstart
- `docs/release/public-beta.md`
- this feedback program
- issue templates for command failures, bugs, and feature requests
- contribution docs for safe command and skill-pack work

Recommended README addition:

> Looking for beta feedback? Start with the public beta guide and run the
> 10-minute feedback script.

### 4.2 Website

The website should have one clear early-adopter call to action:

> Try the Fedora KDE Wayland beta and send a report.

The beta page or homepage should include:

- exact supported target
- short demo or screenshots when available
- install command
- 10-minute test script
- issue-report command
- link to GitHub issues
- known limits

### 4.3 GitHub issues

Use labels that make feedback triage visible:

- `beta-feedback`
- `install-failure`
- `command-failure`
- `tray-ux`
- `voice-stt`
- `docs`
- `fedora-kde`
- `needs-repro`
- `tester-reported`
- `good-first-issue`

---

## 5. Outreach Sequence

### 5.1 First wave: manual technical beta

Target: 20 to 30 testers.

Where:

- direct messages to Fedora KDE users and Linux desktop developers who know the
  maintainer
- KDE Discuss
- Fedora Discussion
- r/kde
- r/Fedora

Post title:

```text
Looking for Fedora KDE Wayland testers for local-first voice desktop control
```

Post structure:

1. One sentence on what Operance is.
2. Exact supported target.
3. What works today.
4. Known limits.
5. The 10-minute test ask.
6. Install link.
7. Issue-report command.
8. Maintainer promise to read reports and post a follow-up summary.

Do not cross-post everywhere on the same day. Start with one or two communities,
respond to every tester, then widen.

### 5.2 Second wave: developer launch

Run this after the first wave has fixed obvious setup and onboarding failures.

Where:

- Hacker News Show HN
- GitHub social post
- local-AI and Linux developer communities
- small developer newsletters or personal blogs

Possible Show HN title:

```text
Show HN: Operance, local-first voice control for KDE Wayland
```

Developer angle:

- safe typed desktop actions
- local-first by default
- deterministic commands without a model
- optional local planner bounded by schemas
- Linux provider and adapter architecture

### 5.3 Third wave: normal-user beta

Run this only after the project has evidence that the beta install and first
commands work reliably for technical testers.

Where:

- website homepage
- short demo video
- Fedora/KDE user spaces
- creator walkthroughs
- carefully selected hands-free or accessibility-adjacent communities

Message:

> Click the tray icon, say what you want, and Operance turns it into safe
> desktop actions.

---

## 6. Weekly Triage Loop

Run this weekly during active outreach.

```markdown
## Operance Beta Feedback Week N

Testers contacted:
Install attempts:
Successful installs:
Failed installs:
Useful issue reports:
Most failed commands:
Most confusing UX:
Fixed this week:
Still broken:
Need testers for:
```

Use the summary to decide the next engineering slice. Prioritize recurring
friction over speculative command expansion.

Default priority order:

1. Install cannot complete.
2. Tray cannot start or show state.
3. Click-to-talk cannot capture.
4. Supported commands fail.
5. Failure reports lack needed evidence.
6. Documentation causes repeated confusion.
7. Nice-to-have commands.

---

## 7. Success Metrics

Track manually at first. Do not add telemetry until there is a clear product
and privacy need.

Open-source traction:

- testers recruited
- successful installs
- issue reports filed by outside users
- repeat testers
- outside pull requests
- outside docs fixes
- GitHub stars and watchers

Product quality:

- install-to-first-command time
- first-command success rate
- command success rate for the supported script
- support-bundle usefulness
- top failed phrases
- top setup blockers

Community quality:

- time to first maintainer response
- issues closed from tester reports
- weekly update cadence
- number of testers who return after fixes

---

## 8. Maintainer Checklist

Before first outreach:

- public beta guide points to the current release path
- README beta quickstart is current
- website has a clear beta feedback call to action
- issue templates route command failures cleanly
- release tag and assets are available
- setup command has been tested on the target Fedora KDE Wayland machine
- `operance --installed-smoke` passes for the release path
- `operance --public-beta-checklist` is current
- support bundle and issue report generation work

Before Show HN or broader developer launch:

- at least 10 outside install attempts have been handled
- top install blocker has been fixed or documented
- top command failure has been fixed or documented
- known limits are explicit
- a maintainer is available to answer comments and issues for 24 to 48 hours

Before normal-user outreach:

- first command works reliably for technical testers
- tray behavior is understandable without reading developer docs
- failure reporting is clear from the product surface
- docs do not require users to understand internals
- unsupported platforms are clearly marked

