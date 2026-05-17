---
name: Bug report
about: Report a defect in the current local core or Linux runtime path
title: "[bug] "
labels: bug
assignees: ""
---

## Summary

Describe the bug in one paragraph.

Do not use this template for security issues. Follow `SECURITY.md` instead.

## Environment

- OS:
- Desktop session:
- Operance version (`.venv/bin/python -m operance.cli --version`):
- Operance about (`operance --about` for installed packages, or `.venv/bin/python -m operance.cli --about` for source checkouts):
- Python version:
- Install method:
- Developer mode or live adapters:
- Installed smoke, if using an RPM (`operance --installed-smoke`):

## Reproduction

1. 
2. 
3. 

## Expected behavior

Describe what should have happened.

## Actual behavior

Describe what happened instead.

## Verification

- [ ] `.venv/bin/python -m pytest`
- [ ] `.venv/bin/python -m operance.cli --version`
- [ ] `.venv/bin/python -m operance.cli --about`
- [ ] `.venv/bin/python -m operance.cli --doctor`
- [ ] `operance --installed-smoke` when reporting an installed package issue
- [ ] `.venv/bin/python -m operance.cli --support-bundle`

## Notes

Attach the `--support-bundle` archive path or upload the saved bundle file when possible. If you need to paste inline details instead, add logs, screenshots, transcript text, audit details, or the `--support-snapshot` JSON here. Home-directory paths are redacted by default; only use `--support-snapshot-raw` if exact local paths are required.
