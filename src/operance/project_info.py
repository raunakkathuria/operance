"""Project identity helpers for support and release surfaces."""

from __future__ import annotations

from functools import lru_cache
import importlib.metadata
import json
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
    build_info = _read_build_info(repo_root)
    install_mode = "packaged" if build_info else "source_checkout"

    identity = {
        "name": _PROJECT_NAME,
        "version": version,
        "version_source": version_source,
        "install_mode": install_mode,
        "git_commit": _git_output(repo_root, "rev-parse", "--short", "HEAD"),
        "git_branch": _git_output(repo_root, "branch", "--show-current"),
        "git_dirty": _git_dirty(repo_root),
    }
    if build_info:
        identity.update(
            {
                "build_git_commit": build_info.get("git_commit"),
                "build_git_commit_short": build_info.get("git_commit_short"),
                "build_git_branch": build_info.get("git_branch"),
                "build_git_tag": build_info.get("git_tag"),
                "build_git_dirty": build_info.get("git_dirty"),
                "build_time": build_info.get("build_time"),
                "package_profile": build_info.get("package_profile"),
                "package_version": build_info.get("package_version"),
                "install_root": build_info.get("install_root"),
                "entrypoint": build_info.get("entrypoint"),
                "python_bin": build_info.get("python_bin"),
            }
        )
    return identity


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


def _read_build_info(repo_root: Path | None) -> dict[str, object] | None:
    if repo_root is None:
        return None
    build_info_path = repo_root / "build-info.json"
    if not build_info_path.exists():
        return None
    try:
        payload = json.loads(build_info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


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
