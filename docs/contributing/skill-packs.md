# Desktop Skill Packs

Skill packs let contributors add safe phrase shortcuts without changing the
portable core or writing OS-specific adapter code.

Use a skill pack when an existing typed action already covers the behavior. If a
new shared capability is needed, follow [command-authoring.md](command-authoring.md)
instead.

## Current Scope

The current skill-pack surface is intentionally small:

- format: JSON
- matching: exact normalized phrases
- output: registered Operance typed actions only
- execution: normal validator, policy, confirmation, executor, and adapter path
- raw shell: not allowed
- platform-native scripts: not allowed

This keeps skills useful for aliases, shortcuts, product workflows, and
contributor examples without creating a second unsafe automation runtime.

## Example

```json
{
  "skill_id": "example.browser",
  "name": "Browser shortcuts",
  "description": "Safe browser command aliases.",
  "platforms": ["linux", "windows", "macos"],
  "commands": [
    {
      "id": "open_project_docs",
      "description": "Open project docs in the default browser.",
      "phrases": ["open project docs"],
      "actions": [
        {
          "tool": "apps.launch",
          "target": {
            "kind": "url",
            "value": "github.com/raunakkathuria/operance"
          }
        }
      ]
    }
  ]
}
```

Validate the pack:

```bash
.venv/bin/python -m operance.cli --skill-validate ./browser.json
```

Load one or more packs:

```bash
export OPERANCE_SKILL_PACKS="./browser.json"
.venv/bin/python -m operance.cli --skills
.venv/bin/python -m operance.cli --transcript "open project docs"
```

Use the platform path separator to load multiple files or directories:

```bash
export OPERANCE_SKILL_PACKS="./browser.json:./skills"
```

Directories load `*.json` files in sorted order.

## Safety Rules

Every action in a skill pack must use an existing `ToolName` from
`src/operance/models/actions.py`.

Allowed:

```json
{"tool": "apps.launch", "args": {"app": "firefox"}}
```

Rejected:

```json
{"tool": "shell.run", "args": {"command": "rm -rf /"}}
```

Skill actions are validated against `src/operance/registry.py`. That means:

- missing required args fail validation
- unexpected args fail validation
- wrong arg types fail validation
- high-risk tools keep their registry risk tier
- confirmation-gated tools remain confirmation-gated

Skill packs do not bypass adapter availability. If a tool is blocked on the
current OS, a skill that emits that tool is still blocked at runtime.

## Safe Targets

Prefer `target` when a command points at a common user-facing thing. Operance
resolves the target into registered action args before validation.

Supported target kinds:

- `app`: valid for `apps.launch`, `apps.focus`, and `apps.quit`
- `url`: valid for `apps.launch`; hostnames are normalized to `https://...`
- `desktop_file`: valid for `files.open` and `files.delete_file`
- `desktop_folder`: valid for `files.open` and `files.delete_folder`

Examples:

```json
{"tool": "apps.launch", "target": {"kind": "app", "name": "firefox"}}
```

```json
{"tool": "apps.launch", "target": {"kind": "url", "value": "example.com/docs"}}
```

```json
{"tool": "files.open", "target": {"kind": "desktop_file", "name": "notes.txt"}}
```

## When To Use Skills

Good use cases:

- app or URL aliases
- project-specific shortcuts
- common developer workflows that map to existing typed actions
- safer phrase experiments before promoting a phrase into built-in intent parsing

Bad use cases:

- arbitrary shell commands
- OS-specific scripts
- destructive file workflows without confirmation
- new platform automation APIs
- commands that need a new typed action contract

## Release Promotion

Before moving a skill-provided behavior into a release claim:

- validate the pack with `--skill-validate`
- test the phrase with `--transcript`
- verify `--supported-commands` shows the skill metadata
- keep docs limited to behavior that was actually tested
