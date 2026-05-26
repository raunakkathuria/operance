#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

root_dir="${repo_root}/dist/package-artifacts"
output_dir="${repo_root}/dist/release"
version=""
bundle_python=""
bundle_source_site_packages=""
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/build_release_artifacts.sh [options]

Build the Fedora KDE release artifact set.

Options:
  --root-dir PATH                  Root directory for package artifacts. Defaults to dist/package-artifacts.
  --output-dir PATH                Directory for release artifacts. Defaults to dist/release.
  --version VALUE                  Package version. Defaults to pyproject.toml.
  --bundle-python PATH             Python executable used for the mvp runtime bundle.
  --bundle-source-site-packages PATH
                                   Override source site-packages for runtime bundling.
  --dry-run                        Print commands without executing them.
  -h, --help                       Show this help text.
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

run_step() {
    local display="$1"
    shift

    echo "+ ${display}"
    if [[ "${dry_run}" -eq 0 ]]; then
        "$@"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--root-dir requires a path"
            fi
            root_dir="$1"
            ;;
        --output-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--output-dir requires a path"
            fi
            output_dir="$1"
            ;;
        --version)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--version requires a value"
            fi
            version="$1"
            ;;
        --bundle-python)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-python requires a path"
            fi
            bundle_python="$1"
            ;;
        --bundle-source-site-packages)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-source-site-packages requires a path"
            fi
            bundle_source_site_packages="$1"
            ;;
        --dry-run)
            dry_run=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"
            ;;
    esac
    shift
done

cd "${repo_root}"

if [[ -z "${version}" ]]; then
    version="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)"
fi
if [[ -z "${version}" ]]; then
    fail "could not determine version from pyproject.toml"
fi

if [[ -z "${bundle_python}" ]]; then
    bundle_python=".venv/bin/python"
fi

root_dir="${root_dir%/}"
output_dir="${output_dir%/}"
rpm_path="${root_dir}/rpm/operance-${version}-1.noarch.rpm"
public_rpm_path="${output_dir}/operance-${version}-1.noarch.rpm"
public_setup_path="${output_dir}/setup.sh"
checksums_path="${output_dir}/SHA256SUMS"
manifest_path="${output_dir}/release-artifacts-manifest.json"

build_display="./scripts/build_package_artifacts.sh --rpm --root-dir ${root_dir} --version ${version} --bundle-profile mvp --bundle-python ${bundle_python}"
build_args=(
    "./scripts/build_package_artifacts.sh"
    "--rpm"
    "--root-dir" "${root_dir}"
    "--version" "${version}"
    "--bundle-profile" "mvp"
    "--bundle-python" "${bundle_python}"
)
if [[ -n "${bundle_source_site_packages}" ]]; then
    build_display="${build_display} --bundle-source-site-packages ${bundle_source_site_packages}"
    build_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    build_display="${build_display} --dry-run"
    build_args+=("--dry-run")
fi
run_step "${build_display}" bash "${build_args[@]}"

run_step "rpm -Kv ${rpm_path}" rpm -Kv "${rpm_path}"
run_step "mkdir -p ${output_dir}" mkdir -p "${output_dir}"
run_step "cp ${rpm_path} ${public_rpm_path}" cp "${rpm_path}" "${public_rpm_path}"
run_step "cp scripts/setup.sh ${public_setup_path}" cp "scripts/setup.sh" "${public_setup_path}"

checksum_display="cd ${output_dir} && sha256sum $(basename "${public_rpm_path}") setup.sh > SHA256SUMS"
echo "+ ${checksum_display}"
if [[ "${dry_run}" -eq 0 ]]; then
    (cd "${output_dir}" && sha256sum "$(basename "${public_rpm_path}")" setup.sh > SHA256SUMS)
fi

echo "+ render release artifact manifest -> ${manifest_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    python3 - "${manifest_path}" "${public_rpm_path}" "${public_setup_path}" "${checksums_path}" "${version}" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
rpm_path = Path(sys.argv[2])
setup_path = Path(sys.argv[3])
checksums_path = Path(sys.argv[4])
version = sys.argv[5]

def git_value(*args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        check=False,
        text=True,
    )
    value = completed.stdout.strip()
    return value or None

payload = {
    "artifact_profile": "mvp",
    "artifacts": [
        {
            "path": str(rpm_path),
            "sha256": hashlib.sha256(rpm_path.read_bytes()).hexdigest(),
            "size_bytes": rpm_path.stat().st_size,
            "type": "fedora-rpm",
        },
        {
            "path": str(checksums_path),
            "type": "checksums",
        },
        {
            "path": str(setup_path),
            "sha256": hashlib.sha256(setup_path.read_bytes()).hexdigest(),
            "size_bytes": setup_path.stat().st_size,
            "type": "setup-script",
        },
    ],
    "git_commit": git_value("rev-parse", "HEAD"),
    "git_commit_short": git_value("rev-parse", "--short", "HEAD"),
    "git_tag": git_value("describe", "--tags", "--exact-match"),
    "install_command": f"sudo dnf install -y {rpm_path.name}",
    "package_version": version,
    "supported_target": "Fedora KDE Plasma Wayland",
    "validation_commands": [
        "operance --version",
        "operance --installed-smoke",
        "operance --supported-commands --supported-commands-available-only",
        "operance --support-bundle",
    ],
}

manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
fi

cat <<EOF
Release artifacts:
- ${public_rpm_path}
- ${public_setup_path}
- ${checksums_path}
- ${manifest_path}
EOF
