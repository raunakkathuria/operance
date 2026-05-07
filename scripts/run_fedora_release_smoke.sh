#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

root_dir="${repo_root}/dist/package-artifacts"
version=""
bundle_profile="base"
bundle_python=""
bundle_source_site_packages=""
support_bundle_out=""
use_sudo=1
uninstall_after=1
extra_smoke_args=()
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/run_fedora_release_smoke.sh [options] [-- extra run_installed_beta_smoke.sh args]

Build the current RPM artifact and run the installed-package beta smoke flow
against it on Fedora-style hosts.

Options:
  --root-dir PATH                  Root directory for the RPM build tree.
                                   Defaults to dist/package-artifacts.
  --version VALUE                  Package version. Defaults to the version from pyproject.toml.
  --bundle-profile PROFILE         Dependency bundle profile forwarded to the RPM build path.
                                   Supported: base, mvp. Defaults to base.
  --bundle-python PATH             Python executable used for non-base runtime bundling.
  --bundle-source-site-packages PATH
                                   Override the source site-packages directory for runtime bundling.
  --support-bundle-out PATH        Forward an output path to the installed-package support-bundle step.
  --no-sudo                        Forward --no-sudo to the installed-package smoke step.
  --keep-installed                 Do not uninstall the package after the smoke sequence.
  --dry-run                        Print the build and smoke commands without executing them.
  -h, --help                       Show this help text.

Any arguments after `--` are forwarded to `run_installed_beta_smoke.sh`.
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

require_release_prerequisites() {
    if [[ "${dry_run}" -eq 1 ]]; then
        return
    fi
    if ! command -v rpmbuild >/dev/null 2>&1; then
        fail "rpmbuild not found; install RPM packaging tools with ./scripts/install_packaging_tools.sh --rpm"
    fi
    if ! command -v dnf >/dev/null 2>&1; then
        fail "dnf not found; run this Fedora release gate on a host with dnf available"
    fi
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
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
            ;;
        --no-sudo)
            use_sudo=0
            ;;
        --keep-installed)
            uninstall_after=0
            ;;
        --dry-run)
            dry_run=1
            ;;
        --)
            shift
            extra_smoke_args=("$@")
            break
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

require_release_prerequisites

if [[ -z "${version}" ]]; then
    version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "${repo_root}/pyproject.toml" | head -n 1)"
fi
if [[ -z "${version}" ]]; then
    fail "could not determine version from pyproject.toml"
fi

root_dir="${root_dir%/}"
package_path="${root_dir}/rpm/operance-${version}-1.noarch.rpm"

cd "${repo_root}"

build_display="./scripts/build_package_artifacts.sh --rpm --root-dir ${root_dir} --version ${version} --bundle-profile ${bundle_profile}"
build_args=(
    "./scripts/build_package_artifacts.sh"
    "--rpm"
    "--root-dir" "${root_dir}"
    "--version" "${version}"
    "--bundle-profile" "${bundle_profile}"
)
if [[ -n "${bundle_python}" ]]; then
    build_display="${build_display} --bundle-python ${bundle_python}"
    build_args+=("--bundle-python" "${bundle_python}")
fi
if [[ -n "${bundle_source_site_packages}" ]]; then
    build_display="${build_display} --bundle-source-site-packages ${bundle_source_site_packages}"
    build_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    build_display="${build_display} --dry-run"
    build_args+=("--dry-run")
fi
run_step "${build_display}" bash "${build_args[@]}"

smoke_display="./scripts/run_installed_beta_smoke.sh --package ${package_path} --installer dnf"
smoke_args=(
    "./scripts/run_installed_beta_smoke.sh"
    "--package" "${package_path}"
    "--installer" "dnf"
)
if [[ -n "${support_bundle_out}" ]]; then
    smoke_display="${smoke_display} --support-bundle-out ${support_bundle_out}"
    smoke_args+=("--support-bundle-out" "${support_bundle_out}")
fi
if [[ "${use_sudo}" -eq 0 ]]; then
    smoke_display="${smoke_display} --no-sudo"
    smoke_args+=("--no-sudo")
fi
if [[ "${uninstall_after}" -eq 1 ]]; then
    smoke_display="${smoke_display} --uninstall-after"
    smoke_args+=("--uninstall-after")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    smoke_display="${smoke_display} --dry-run"
    smoke_args+=("--dry-run")
fi
for extra_arg in "${extra_smoke_args[@]}"; do
    smoke_display="${smoke_display} ${extra_arg}"
    smoke_args+=("${extra_arg}")
done
run_step "${smoke_display}" bash "${smoke_args[@]}"
