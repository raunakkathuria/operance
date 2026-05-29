from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"


def test_readme_embeds_architecture_svg_assets() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "docs/architecture/assets/high-level-runtime.svg" in readme
    assert "docs/architecture/assets/component-boundaries.svg" in readme
    assert (REPO_ROOT / "docs" / "architecture" / "assets" / "high-level-runtime.svg").exists()
    assert (REPO_ROOT / "docs" / "architecture" / "assets" / "component-boundaries.svg").exists()
