#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

root_dir="${repo_root}/dist/packages"
entrypoint=""
version=""
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/build_package_scaffolds.sh [options]

Render both Debian and RPM package staging trees for the current Operance tray and voice-loop assets.

Options:
  --root-dir PATH    Root directory for the rendered package scaffolds.
                     Defaults to dist/packages.
  --entrypoint PATH  Installed operance entrypoint path. When omitted, child
                     scripts use their own default entrypoint.
  --version VALUE    Package version. Defaults to the version from pyproject.toml.
  --dry-run          Print the scaffold steps without executing them.
  -h, --help         Show this help text.
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
        --entrypoint)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--entrypoint requires a path"
            fi
            entrypoint="$1"
            ;;
        --version)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--version requires a value"
            fi
            version="$1"
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

root_dir="${root_dir%/}"
deb_staging_dir="${root_dir}/deb/operance"
deb_output_dir="${root_dir}/deb"
rpm_spec_dir="${root_dir}/rpm"

deb_display="./scripts/build_deb_package.sh --skip-build --staging-dir ${deb_staging_dir} --output-dir ${deb_output_dir}"
deb_args=(
    "./scripts/build_deb_package.sh"
    "--skip-build"
    "--staging-dir" "${deb_staging_dir}"
    "--output-dir" "${deb_output_dir}"
)
if [[ -n "${version}" ]]; then
    deb_display="${deb_display} --version ${version}"
    deb_args+=("--version" "${version}")
fi
if [[ -n "${entrypoint}" ]]; then
    deb_display="${deb_display} --entrypoint ${entrypoint}"
    deb_args+=("--entrypoint" "${entrypoint}")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    deb_display="${deb_display} --dry-run"
    deb_args+=("--dry-run")
fi

rpm_display="./scripts/build_rpm_package.sh --skip-build --spec-dir ${rpm_spec_dir}"
rpm_args=(
    "./scripts/build_rpm_package.sh"
    "--skip-build"
    "--spec-dir" "${rpm_spec_dir}"
)
if [[ -n "${version}" ]]; then
    rpm_display="${rpm_display} --version ${version}"
    rpm_args+=("--version" "${version}")
fi
if [[ -n "${entrypoint}" ]]; then
    rpm_display="${rpm_display} --entrypoint ${entrypoint}"
    rpm_args+=("--entrypoint" "${entrypoint}")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    rpm_display="${rpm_display} --dry-run"
    rpm_args+=("--dry-run")
fi

run_step "${deb_display}" bash "${deb_args[@]}"
run_step "${rpm_display}" bash "${rpm_args[@]}"
