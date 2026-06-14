#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

root_dir="${repo_root}/dist/package-artifacts"
version=""
bundle_profile="mvp"
bundle_python=""
bundle_source_site_packages=""
support_bundle_out=""
evidence_dir=""
use_sudo=1
reset_user_services=1
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/run_package_evidence_gate.sh [options]

Build, install, inspect, and leave the Fedora RPM in place for manual beta validation.

Options:
  --root-dir PATH                  Root directory for package artifacts. Defaults to dist/package-artifacts.
  --version VALUE                  Package version. Defaults to pyproject.toml.
  --bundle-profile PROFILE         Dependency bundle profile. Supported: base, mvp. Defaults to mvp.
  --bundle-python PATH             Python executable used for non-base runtime bundling.
  --bundle-source-site-packages PATH
                                   Override source site-packages for runtime bundling.
  --support-bundle-out PATH        Write the installed support bundle to this path.
  --evidence-dir PATH              Write installed JSON evidence files to this directory.
  --no-sudo                        Forward --no-sudo to package install.
  --no-reset-user-services         Do not remove stale user services before install.
  --dry-run                        Print commands without executing them.
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
        fail "dnf not found; run this package evidence gate on a Fedora-style host"
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

run_evidence_step() {
    local output_file="$1"
    local display="$2"
    shift 2

    echo "+ ${display}"
    if [[ "${dry_run}" -eq 1 ]]; then
        return
    fi
    if [[ -n "${output_file}" ]]; then
        mkdir -p "$(dirname "${output_file}")"
        "$@" >"${output_file}"
    else
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
        --evidence-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--evidence-dir requires a path"
            fi
            evidence_dir="$1"
            ;;
        --no-sudo)
            use_sudo=0
            ;;
        --no-reset-user-services)
            reset_user_services=0
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

rpm_verify_display="rpm -Kv ${package_path}"
run_step "${rpm_verify_display}" rpm -Kv "${package_path}"

install_display="./scripts/install_package_artifact.sh --package ${package_path} --installer dnf --replace-existing"
install_args=(
    "./scripts/install_package_artifact.sh"
    "--package" "${package_path}"
    "--installer" "dnf"
    "--replace-existing"
)
if [[ "${reset_user_services}" -eq 1 ]]; then
    install_display="${install_display} --reset-user-services"
    install_args+=("--reset-user-services")
fi
if [[ "${use_sudo}" -eq 0 ]]; then
    install_display="${install_display} --no-sudo"
    install_args+=("--no-sudo")
fi
run_step "${install_display}" bash "${install_args[@]}"

run_step "./scripts/run_installed_desktop_smoke.sh" bash "./scripts/run_installed_desktop_smoke.sh"

if [[ -n "${evidence_dir}" && -z "${support_bundle_out}" ]]; then
    support_bundle_out="${evidence_dir%/}/operance-installed-support.tar.gz"
fi

evidence_file() {
    local name="$1"
    if [[ -z "${evidence_dir}" ]]; then
        echo ""
    else
        echo "${evidence_dir%/}/${name}"
    fi
}

run_evidence_step "$(evidence_file build-identity.json)" "operance --about" operance --about
run_evidence_step "$(evidence_file installed-smoke.json)" "operance --installed-smoke" operance --installed-smoke
run_evidence_step "$(evidence_file public-beta-checklist.json)" "operance --public-beta-checklist" operance --public-beta-checklist
run_evidence_step "$(evidence_file command-coach.json)" "operance --command-coach" operance --command-coach
run_evidence_step "$(evidence_file local-ai-coach.json)" "operance --local-ai-coach" operance --local-ai-coach
run_evidence_step "$(evidence_file supported-commands-available.json)" \
    "operance --supported-commands --supported-commands-available-only" \
    operance --supported-commands --supported-commands-available-only

support_bundle_display="operance --support-bundle"
support_bundle_command=("operance" "--support-bundle")
if [[ -n "${support_bundle_out}" ]]; then
    support_bundle_display="${support_bundle_display} --support-bundle-out ${support_bundle_out}"
    support_bundle_command+=("--support-bundle-out" "${support_bundle_out}")
fi
run_step "${support_bundle_display}" "${support_bundle_command[@]}"

if [[ -n "${evidence_dir}" && "${dry_run}" -eq 0 ]]; then
    cat >"${evidence_dir%/}/README.txt" <<EOF
Operance packaged release evidence

Generated by: ./scripts/run_package_evidence_gate.sh --evidence-dir ${evidence_dir}

Included files:
- build-identity.json
- installed-smoke.json
- public-beta-checklist.json
- command-coach.json
- local-ai-coach.json
- supported-commands-available.json
- $(basename "${support_bundle_out}")

Manual checks still required:
- Click the tray icon and say: open firefox
- Click the tray icon and say: open localhost:3000
- Click the tray icon and say: open firefox and notify me
- Click the tray icon and say: search google for linux automation
EOF
fi

cat <<'EOF'
Manual packaged evidence checks:
- Click the tray icon and say: open firefox
- Click the tray icon and say: open localhost:3000
- Click the tray icon and say: open firefox and notify me
- Click the tray icon and say: search google for linux automation
- Open the tray menu and inspect: Try commands
- Open the tray menu and inspect: Local AI setup
- Click the tray icon and say: let me know when this is done
- Attach the installed support bundle if any check fails
EOF
