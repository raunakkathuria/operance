from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repo_has_no_old_brand_references() -> None:
    needle = "".join(["vo", "xos"])

    result = subprocess.run(
        ["git", "grep", "-n", "-i", needle, "--", "."],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )

    assert result.returncode == 1, result.stdout
