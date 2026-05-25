---
name: Command failure
about: Report a voice, transcript, planner, or desktop command that did not work
title: "[command] "
labels: bug, command
assignees: ""
---

## Command

- Spoken phrase or CLI transcript:
- Expected result:
- Actual result:
- Did Operance report success, failure, unmatched, or confirmation required?

## Environment

- OS:
- Desktop session:
- Install method: packaged RPM or source checkout
- Operance version:
- Developer mode or live adapters:
- Local AI planner enabled? yes/no

## Diagnostics

- [ ] `operance --installed-smoke` if using the RPM
- [ ] `operance --support-bundle` or `.venv/bin/python -m operance.cli --support-bundle`
- [ ] pasted `issue-report.md` from the support bundle or `operance --issue-report`

## Notes

Attach the support bundle when possible. It is redacted by default and includes
`issue-report.md` to reduce manual issue formatting.
