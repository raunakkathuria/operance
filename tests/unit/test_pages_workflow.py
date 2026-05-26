from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"


def test_github_pages_workflow_deploys_static_site_artifact() -> None:
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "name: Pages" in workflow
    assert "site/**" in workflow
    assert "site/index.html site/styles.css" in workflow
    assert "assets/icons/operance.svg" in workflow
    assert 'html.replace("../assets/icons/operance.svg", "assets/icons/operance.svg")' in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow
