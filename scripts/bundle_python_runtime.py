#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata as metadata
import shutil
import sys
from pathlib import Path

try:
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
except ImportError as exc:  # pragma: no cover - hard failure path for misconfigured build envs
    raise SystemExit(
        "packaging is required to bundle the packaged Python runtime; run the build from the local Operance venv"
    ) from exc


PROFILE_SEEDS: dict[str, tuple[str, ...]] = {
    "mvp": ("PySide6", "moonshine-voice"),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy an installed Python dependency closure into a packaged Operance site-packages tree."
        )
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_SEEDS),
        required=True,
        help="Runtime bundle profile to vendor into the package tree.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Destination site-packages directory inside the packaged asset tree.",
    )
    parser.add_argument(
        "--source-site-packages",
        help=(
            "Override the source site-packages directory. Defaults to the current interpreter's first site-packages path."
        ),
    )
    return parser.parse_args()


def _discover_source_site_packages(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).resolve()
        if not path.is_dir():
            raise SystemExit(f"source site-packages directory does not exist: {path}")
        return path

    candidates = [Path(item).resolve() for item in sys.path if "site-packages" in item]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SystemExit("could not determine a source site-packages directory from the current interpreter")



def _build_distribution_map(source_site_packages: Path) -> dict[str, metadata.Distribution]:
    distribution_map: dict[str, metadata.Distribution] = {}
    for distribution in metadata.distributions(path=[str(source_site_packages)]):
        name = distribution.metadata.get("Name")
        if not name:
            continue
        distribution_map[canonicalize_name(name)] = distribution
    return distribution_map



def _resolve_distribution_closure(
    profile: str,
    distribution_map: dict[str, metadata.Distribution],
) -> list[metadata.Distribution]:
    environment = default_environment()
    environment["extra"] = ""
    pending = [canonicalize_name(name) for name in PROFILE_SEEDS[profile]]
    ordered: list[metadata.Distribution] = []
    seen: set[str] = set()

    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        distribution = distribution_map.get(current)
        if distribution is None:
            raise SystemExit(f"required distribution not found in source site-packages: {current}")
        seen.add(current)
        ordered.append(distribution)

        for raw_requirement in distribution.requires or []:
            requirement = Requirement(raw_requirement)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in seen:
                pending.append(dependency)

    return ordered



def _copy_distribution_tree(
    distribution: metadata.Distribution,
    *,
    source_site_packages: Path,
    output_dir: Path,
    copied_files: set[Path],
) -> None:
    for relative_entry in distribution.files or []:
        source_path = Path(distribution.locate_file(relative_entry)).resolve()
        try:
            relative_path = source_path.relative_to(source_site_packages)
        except ValueError:
            continue
        destination_path = output_dir / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        if destination_path in copied_files:
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        destination_mode = destination_path.stat().st_mode
        destination_path.chmod(destination_mode & ~0o111)
        copied_files.add(destination_path)



def main() -> int:
    args = _parse_args()
    source_site_packages = _discover_source_site_packages(args.source_site_packages)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    distribution_map = _build_distribution_map(source_site_packages)
    selected_distributions = _resolve_distribution_closure(args.profile, distribution_map)

    copied_files: set[Path] = set()
    for distribution in selected_distributions:
        _copy_distribution_tree(
            distribution,
            source_site_packages=source_site_packages,
            output_dir=output_dir,
            copied_files=copied_files,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
