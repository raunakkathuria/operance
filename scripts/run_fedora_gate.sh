#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
support_bundle_out=""
bundle_profile="mvp"
bundle_python=""
bundle_source_site_packages=""
use_sudo=1
uninstall_after=1
reset_user_services=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/run_fedora_gate.sh [options]

Run the current Fedora release gate from a source checkout.

Options:
  --python PATH                    Python executable to use for pytest and beta smoke.
                                   Defaults to .venv/bin/python.
  --support-bundle-out PATH        Forward an output path to the installed-package
                                   support-bundle step in the release smoke helper.
  --bundle-profile PROFILE         Dependency bundle profile forwarded to the RPM build path.
                                   Supported: base, mvp. Defaults to mvp.
  --bundle-python PATH             Python executable used for non-base runtime bundling.
  --bundle-source-site-packages PATH
                                   Override the source site-packages directory for runtime bundling.
  --no-sudo                        Forward --no-sudo to the release smoke helper.
  --reset-user-services            Forward --reset-user-services to the release smoke helper.
  --keep-installed                 Forward --keep-installed to the release smoke helper.
  --dry-run                        Print the gate commands without executing them.
  -h, --help                       Show this help text.
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
        fail "dnf not found; run this Fedora gate on a host with dnf available"
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
        --python)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--python requires a path"
            fi
            python_bin="$1"
            ;;
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
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
        --no-sudo)
            use_sudo=0
            ;;
        --reset-user-services)
            reset_user_services=1
            ;;
        --keep-installed)
            uninstall_after=0
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

require_release_prerequisites

if [[ ! -x "${python_bin}" ]] && [[ "${dry_run}" -eq 0 ]]; then
    fail "python executable not found: ${python_bin}"
fi

cd "${repo_root}"

run_step "${python_bin} -m pytest" "${python_bin}" "-m" "pytest"

beta_smoke_display="./scripts/run_beta_smoke.sh --python ${python_bin}"
beta_smoke_args=("./scripts/run_beta_smoke.sh" "--python" "${python_bin}")
if [[ "${dry_run}" -eq 1 ]]; then
    beta_smoke_display="${beta_smoke_display} --dry-run"
    beta_smoke_args+=("--dry-run")
fi
run_step "${beta_smoke_display}" bash "${beta_smoke_args[@]}"

release_smoke_display="./scripts/run_fedora_release_smoke.sh --bundle-profile ${bundle_profile}"
release_smoke_args=("./scripts/run_fedora_release_smoke.sh" "--bundle-profile" "${bundle_profile}")
if [[ -n "${support_bundle_out}" ]]; then
    release_smoke_display="${release_smoke_display} --support-bundle-out ${support_bundle_out}"
    release_smoke_args+=("--support-bundle-out" "${support_bundle_out}")
fi
if [[ -n "${bundle_python}" ]]; then
    release_smoke_display="${release_smoke_display} --bundle-python ${bundle_python}"
    release_smoke_args+=("--bundle-python" "${bundle_python}")
fi
if [[ -n "${bundle_source_site_packages}" ]]; then
    release_smoke_display="${release_smoke_display} --bundle-source-site-packages ${bundle_source_site_packages}"
    release_smoke_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
fi
if [[ "${use_sudo}" -eq 0 ]]; then
    release_smoke_display="${release_smoke_display} --no-sudo"
    release_smoke_args+=("--no-sudo")
fi
if [[ "${reset_user_services}" -eq 1 ]]; then
    release_smoke_display="${release_smoke_display} --reset-user-services"
    release_smoke_args+=("--reset-user-services")
fi
if [[ "${uninstall_after}" -eq 0 ]]; then
    release_smoke_display="${release_smoke_display} --keep-installed"
    release_smoke_args+=("--keep-installed")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    release_smoke_display="${release_smoke_display} --dry-run"
    release_smoke_args+=("--dry-run")
fi
run_step "${release_smoke_display}" bash "${release_smoke_args[@]}"
