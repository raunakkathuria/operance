"""Project identity helpers for support and release surfaces."""

from __future__ import annotations

from functools import lru_cache
import importlib.metadata
from pathlib import Path
import subprocess
import tomllib

_PROJECT_NAME = "operance"


@lru_cache(maxsize=1)
def project_version() -> str:
    try:
        return importlib.metadata.version(_PROJECT_NAME)
    except importlib.metadata.PackageNotFoundError:
        return _read_pyproject_version()


@lru_cache(maxsize=1)
def build_project_identity() -> dict[str, object]:
    version_source = "package_metadata"
    try:
        version = importlib.metadata.version(_PROJECT_NAME)
    except importlib.metadata.PackageNotFoundError:
        version = _read_pyproject_version()
        version_source = "pyproject"

    repo_root = _repo_root()
    return {
        "name": _PROJECT_NAME,
        "version": version,
        "version_source": version_source,
        "git_commit": _git_output(repo_root, "rev-parse", "--short", "HEAD"),
        "git_branch": _git_output(repo_root, "branch", "--show-current"),
        "git_dirty": _git_dirty(repo_root),
    }


def _read_pyproject_version() -> str:
    repo_root = _repo_root()
    if repo_root is None:
        raise RuntimeError("could not determine project version")
    pyproject_path = repo_root / "pyproject.toml"
    with pyproject_path.open("rb") as file_handle:
        payload = tomllib.load(file_handle)
    return str(payload["project"]["version"])


def _repo_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").exists():
        return candidate
    return None


def _git_output(repo_root: Path | None, *args: str) -> str | None:
    if repo_root is None or not (repo_root / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
        text=True,
        timeout=2,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _git_dirty(repo_root: Path | None) -> bool | None:
    if repo_root is None or not (repo_root / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--short"],
        capture_output=True,
        check=False,
        text=True,
        timeout=2,
    )
    if completed.returncode != 0:
        return None
    return bool(completed.stdout.strip())
