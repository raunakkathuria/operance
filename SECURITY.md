# Security Policy

## Scope

Operance is pre-`1.0` and Linux-first. Security fixes in this repository land on
the current `main` branch. Reproduce any issue against current `main` before
reporting it as a vulnerability.

## Reporting a vulnerability

Do **not** open a public GitHub issue for a suspected vulnerability.

Current reporting path:

1. Use GitHub private vulnerability reporting if it is enabled for the
   repository.
2. If private vulnerability reporting is not available, request a private
   maintainer contact path without disclosing exploit details publicly.
3. Include the affected commit or version, Linux distribution, desktop session,
   reproduction steps, expected impact, and any required local configuration.

If the issue involves runtime state, attach a redacted support bundle when it is
safe to do so:

```bash
.venv/bin/python -m operance.cli --support-bundle
```

Do not include secrets, private keys, or unrelated personal data in the report.

## Response expectations

The project aims to:

- acknowledge reports within 7 days
- confirm whether the issue is in scope
- coordinate a fix before public disclosure when the report is valid

## Out of scope

The following are generally out of scope for this repository:

- vulnerabilities in third-party packages or system tools that Operance invokes
- issues that require local root compromise before Operance is involved
- purely theoretical findings without a credible reproduction path
