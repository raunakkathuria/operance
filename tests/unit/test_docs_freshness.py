"""Guardrails that keep architecture docs in step with the code they describe.

The existing documentation tests assert that specific prose is present. These
assert the opposite direction: that structural facts in the code have made it
into the docs. Content-presence checks cannot catch a new adapter protocol or a
new subsystem being added without ever being written down.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE_DIR = REPO_ROOT / "docs" / "architecture"
ADAPTER_BASE = REPO_ROOT / "src" / "operance" / "adapters" / "base.py"
PACKAGE_ROOT = REPO_ROOT / "src" / "operance"

# Subpackages whose internals the architecture docs deliberately do not describe.
UNDOCUMENTED_BY_DESIGN: frozenset[str] = frozenset()


def _architecture_docs_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(ARCHITECTURE_DIR.glob("*.md"))
    )


def _adapter_protocols() -> list[str]:
    source = ADAPTER_BASE.read_text(encoding="utf-8")
    return re.findall(r"^class (\w+Adapter)\(Protocol\):", source, re.MULTILINE)


def _subpackages() -> list[str]:
    return sorted(
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith((".", "_"))
    )


def test_adapter_protocols_are_listed_in_the_architecture_docs() -> None:
    """A new-OS author implements these by name, so the docs must name them."""

    docs = _architecture_docs_text()
    protocols = _adapter_protocols()

    assert protocols, "expected to find adapter protocols in adapters/base.py"
    missing = [name for name in protocols if name not in docs]

    assert missing == [], (
        "Adapter protocols missing from docs/architecture: "
        f"{', '.join(missing)}. Add them to adapter-authoring.md."
    )


def test_subpackages_are_mentioned_in_the_architecture_docs() -> None:
    """Every subsystem should be findable from the architecture overview."""

    docs = _architecture_docs_text()
    missing = [
        name
        for name in _subpackages()
        if name not in UNDOCUMENTED_BY_DESIGN
        and f"{name}/" not in docs
        and f"`{name}`" not in docs
    ]

    assert missing == [], (
        "Subpackages missing from docs/architecture: "
        f"{', '.join(missing)}. Describe them in overview.md."
    )


@pytest.mark.parametrize("doc_name", ["overview.md", "adapter-authoring.md"])
def test_architecture_docs_do_not_reference_missing_source_paths(doc_name: str) -> None:
    """Docs should not point at files that no longer exist."""

    text = (ARCHITECTURE_DIR / doc_name).read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(src/operance/[A-Za-z0-9_/]+\.py)`", text))
    # adapters/windows.py and adapters/macos.py are described as work to be done,
    # using "should implement" phrasing, so they are allowed to be absent.
    aspirational = {"src/operance/adapters/windows.py", "src/operance/adapters/macos.py"}

    missing = sorted(
        path for path in referenced - aspirational if not (REPO_ROOT / path).exists()
    )

    assert missing == [], f"{doc_name} references missing files: {', '.join(missing)}"


def test_tool_domains_are_documented_in_the_supported_command_surface() -> None:
    """Every typed-action domain should appear in the Linux command documentation."""

    from operance.models.actions import ToolName

    linux_doc = (REPO_ROOT / "docs" / "requirements" / "linux.md").read_text(encoding="utf-8")
    domains = sorted({tool.value.split(".", 1)[0] for tool in ToolName})
    missing = [domain for domain in domains if domain not in linux_doc]

    assert missing == [], (
        f"Tool domains missing from docs/requirements/linux.md: {', '.join(missing)}."
    )


def test_release_docs_reference_the_tray_regression_checklist() -> None:
    """The tray's Qt surface has no automated coverage, so the manual pass must be findable."""

    checklist = REPO_ROOT / "docs" / "release" / "tray-regression-checklist.md"
    assert checklist.exists()

    for doc_name in ("release-plan.md", "fedora-checklist.md"):
        text = (REPO_ROOT / "docs" / "release" / doc_name).read_text(encoding="utf-8")
        assert "tray-regression-checklist.md" in text, f"{doc_name} should link the checklist"


def test_tray_regression_checklist_covers_the_release_verified_tools() -> None:
    """Section 2 exists to catch regressions in tools users already rely on."""

    from operance.platforms.linux import CURRENT_RELEASE_VERIFIED_TOOLS

    text = (
        REPO_ROOT / "docs" / "release" / "tray-regression-checklist.md"
    ).read_text(encoding="utf-8")
    missing = sorted(
        tool.value for tool in CURRENT_RELEASE_VERIFIED_TOOLS if tool.value not in text
    )

    assert missing == [], (
        "Release-verified tools with no regression check: "
        f"{', '.join(missing)}. Add them to section 2 or explain the omission."
    )
