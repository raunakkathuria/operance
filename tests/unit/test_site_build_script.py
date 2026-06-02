from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_site.sh"
OUTPUT_DIR = REPO_ROOT / "dist" / "pages"


def test_site_build_script_writes_self_contained_pages_artifact() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    result = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    index = (OUTPUT_DIR / "index.html").read_text(encoding="utf-8")

    assert result.returncode == 0
    assert (OUTPUT_DIR / "styles.css").exists()
    assert (OUTPUT_DIR / "favicon.ico").exists()
    assert (OUTPUT_DIR / "assets" / "icons" / "operance.svg").exists()
    assert "../assets/icons/operance.svg" not in index
    assert "assets/icons/operance.svg" in index
