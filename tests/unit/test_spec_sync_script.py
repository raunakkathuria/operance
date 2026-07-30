from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_spec_sync.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_spec_sync", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_spec_sync"] = module
    spec.loader.exec_module(module)
    return module


def test_spec_sync_passes_when_behavior_change_has_changelog_and_docs() -> None:
    module = _load_module()

    report = module.build_report(
        [
            "src/operance/intent/deterministic.py",
            "tests/unit/test_intent.py",
            "README.md",
            "CHANGELOG.md",
            "docs/specs/beta-product-direction.md",
        ]
    )

    assert report.ok is True
    assert report.errors == ()


def test_spec_sync_fails_behavior_change_without_changelog() -> None:
    module = _load_module()

    report = module.build_report(
        [
            "src/operance/ui/tray.py",
            "tests/unit/test_tray.py",
            "README.md",
        ]
    )

    assert report.ok is False
    assert report.errors == ("Behavior-changing files changed without CHANGELOG.md.",)


def test_spec_sync_fails_behavior_change_without_docs() -> None:
    module = _load_module()

    report = module.build_report(
        [
            "src/operance/voice/live.py",
            "tests/unit/test_voice_pipeline.py",
            "CHANGELOG.md",
        ]
    )

    assert report.ok is False
    assert report.errors == (
        "Behavior-changing files changed without README/docs/spec/template evidence.",
    )


def test_spec_sync_allows_docs_only_change() -> None:
    module = _load_module()

    report = module.build_report(["docs/specs/product-prd.md", "README.md"])

    assert report.ok is True
    assert report.errors == ()


def test_spec_sync_warns_when_behavior_change_has_docs_but_no_spec_file() -> None:
    module = _load_module()

    report = module.build_report(
        [
            "src/operance/registry.py",
            "CHANGELOG.md",
            "README.md",
        ]
    )

    assert report.ok is True
    assert report.warnings == (
        "No docs/specs/ file changed. Confirm the linked goal-spec issue covers scope, "
        "or update a spec when product behavior changed.",
    )


def test_ci_workflow_runs_the_spec_sync_gate() -> None:
    """The gate is only useful if automation runs it, not just contributors."""

    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "spec-sync:" in workflow
    assert "scripts/check_spec_sync.py" in workflow
    assert "fetch-depth: 0" in workflow
    assert "github.event.pull_request.base.sha" in workflow


def test_ci_workflow_runs_lint_and_type_checks() -> None:
    """Static checks are only useful if CI blocks on them."""

    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "static-checks:" in workflow
    assert "ruff check" in workflow
    assert "mypy" in workflow
    assert "continue-on-error" not in workflow


def test_mypy_debt_list_does_not_grow() -> None:
    """The per-module ignore list is debt. It may shrink, never grow."""

    pyproject = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    section = pyproject.split("[[tool.mypy.overrides]]", 1)[1]
    ignored = [line for line in section.splitlines() if line.strip().startswith('"operance.')]

    assert len(ignored) <= 15, (
        "New modules must type-check. Fix the errors instead of extending the ignore list."
    )
