#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

root_dir="${repo_root}/dist/package-artifacts"
entrypoint=""
version=""
bundle_profile="base"
bundle_python=""
bundle_source_site_packages=""
build_deb=0
build_rpm=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/build_package_artifacts.sh [options]

Build Operance package artifacts through the existing Debian and RPM helper scripts.

Options:
  --root-dir PATH                  Root directory for the package build trees.
                                   Defaults to dist/package-artifacts.
  --entrypoint PATH                Installed operance entrypoint path. When omitted, child
                                   scripts use their own default entrypoint.
  --version VALUE                  Package version. Defaults to the version from pyproject.toml.
  --bundle-profile PROFILE         Dependency bundle profile forwarded to package builders.
                                   Supported: base, mvp. Defaults to base.
  --bundle-python PATH             Python executable used for non-base runtime bundling.
  --bundle-source-site-packages PATH
                                   Override the source site-packages directory for runtime bundling.
  --deb                            Build only the Debian artifact.
  --rpm                            Build only the RPM artifact.
  --dry-run                        Print the build steps without executing them.
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
        --bundle-profile)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-profile requires a value"
            fi
            bundle_profile="$1"
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
        --deb)
            build_deb=1
            ;;
        --rpm)
            build_rpm=1
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

if [[ "${build_deb}" -eq 0 && "${build_rpm}" -eq 0 ]]; then
    build_deb=1
    build_rpm=1
fi

root_dir="${root_dir%/}"

if [[ "${build_deb}" -eq 1 ]]; then
    deb_staging_dir="${root_dir}/deb/operance"
    deb_output_dir="${root_dir}/deb"
    deb_display="./scripts/build_deb_package.sh --staging-dir ${deb_staging_dir} --output-dir ${deb_output_dir} --bundle-profile ${bundle_profile}"
    deb_args=(
        "./scripts/build_deb_package.sh"
        "--staging-dir" "${deb_staging_dir}"
        "--output-dir" "${deb_output_dir}"
        "--bundle-profile" "${bundle_profile}"
    )
    if [[ -n "${version}" ]]; then
        deb_display="${deb_display} --version ${version}"
        deb_args+=("--version" "${version}")
    fi
    if [[ -n "${entrypoint}" ]]; then
        deb_display="${deb_display} --entrypoint ${entrypoint}"
        deb_args+=("--entrypoint" "${entrypoint}")
    fi
    if [[ -n "${bundle_python}" ]]; then
        deb_display="${deb_display} --bundle-python ${bundle_python}"
        deb_args+=("--bundle-python" "${bundle_python}")
    fi
    if [[ -n "${bundle_source_site_packages}" ]]; then
        deb_display="${deb_display} --bundle-source-site-packages ${bundle_source_site_packages}"
        deb_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
    fi
    if [[ "${dry_run}" -eq 1 ]]; then
        deb_display="${deb_display} --dry-run"
        deb_args+=("--dry-run")
    fi
    run_step "${deb_display}" bash "${deb_args[@]}"
fi

if [[ "${build_rpm}" -eq 1 ]]; then
    rpm_spec_dir="${root_dir}/rpm"
    rpm_output_dir="${root_dir}/rpm"
    rpm_display="./scripts/build_rpm_package.sh --spec-dir ${rpm_spec_dir} --output-dir ${rpm_output_dir} --bundle-profile ${bundle_profile}"
    rpm_args=(
        "./scripts/build_rpm_package.sh"
        "--spec-dir" "${rpm_spec_dir}"
        "--output-dir" "${rpm_output_dir}"
        "--bundle-profile" "${bundle_profile}"
    )
    if [[ -n "${version}" ]]; then
        rpm_display="${rpm_display} --version ${version}"
        rpm_args+=("--version" "${version}")
    fi
    if [[ -n "${entrypoint}" ]]; then
        rpm_display="${rpm_display} --entrypoint ${entrypoint}"
        rpm_args+=("--entrypoint" "${entrypoint}")
    fi
    if [[ -n "${bundle_python}" ]]; then
        rpm_display="${rpm_display} --bundle-python ${bundle_python}"
        rpm_args+=("--bundle-python" "${bundle_python}")
    fi
    if [[ -n "${bundle_source_site_packages}" ]]; then
        rpm_display="${rpm_display} --bundle-source-site-packages ${bundle_source_site_packages}"
        rpm_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
    fi
    if [[ "${dry_run}" -eq 1 ]]; then
        rpm_display="${rpm_display} --dry-run"
        rpm_args+=("--dry-run")
    fi
    run_step "${rpm_display}" bash "${rpm_args[@]}"
fi
