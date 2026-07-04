## Summary

Describe the concrete behavior or workflow change.

## Spec or issue

Link the relevant PRD section, milestone spec section, or goal-spec issue.

- [ ] Linked a goal/spec issue for non-trivial behavior, UX, architecture,
      packaging, release, or public-doc changes
- [ ] Small change with no issue needed; explain why:

## Verification

List the exact commands you ran.

- [ ] `.venv/bin/python -m pytest`
- [ ] `python3 scripts/check_spec_sync.py --base origin/main` for behavior-changing work
- [ ] `.venv/bin/python -m operance.cli --adapter-conformance` when provider, adapter, registry, or executor surfaces changed
- [ ] relevant `operance.cli` probe or smoke command
- [ ] actual user-facing workflow tested when the PR claims runnable behavior
- [ ] release/package artifact gate tested when packaging or release distribution changed

## Documentation

- [ ] `README.md` updated when runnable behavior changed
- [ ] `docs/requirements/linux.md` updated when Linux setup or integration changed
- [ ] release docs updated when packaging, beta distribution, or release gates changed
- [ ] `CHANGELOG.md` updated

## Scope boundary

Explain whether the change is portable-core only, Linux-specific, or both.

## Deferred work

List anything intentionally left for a later feature.
