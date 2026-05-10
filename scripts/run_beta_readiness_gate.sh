#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
support_bundle_out=""
run_package_gate=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/run_beta_readiness_gate.sh [options]

Run the current beta-readiness gate from a source checkout.

Options:
  --python PATH              Python executable to use. Defaults to .venv/bin/python.
  --support-bundle-out PATH  Forward an output path to the source-checkout beta smoke.
  --run-package-gate         Run the full reset-aware Fedora package gate instead of
                             only dry-running it.
  --dry-run                  Print the gate commands without executing them.
  -h, --help                 Show this help text.
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

run_old_brand_guard() {
    local old_brand
    old_brand="$(
        printf '%s%s\n' "vo" "xos"
    )"
    local display="git grep -n -i <old-brand> -- ."
    echo "+ ${display}"
    if [[ "${dry_run}" -eq 1 ]]; then
        return
    fi

    set +e
    git grep -n -i "${old_brand}" -- .
    local status=$?
    set -e
    if [[ "${status}" -eq 0 ]]; then
        fail "old brand references found"
    fi
    if [[ "${status}" -ne 1 ]]; then
        fail "old brand guard failed with exit code ${status}"
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
        --run-package-gate)
            run_package_gate=1
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

if [[ ! -x "${python_bin}" ]] && [[ "${dry_run}" -eq 0 ]]; then
    fail "python executable not found: ${python_bin}"
fi

cd "${repo_root}"

run_step "${python_bin} -m pytest" "${python_bin}" "-m" "pytest"
run_old_brand_guard

beta_smoke_display="./scripts/run_beta_smoke.sh --python ${python_bin}"
beta_smoke_args=("./scripts/run_beta_smoke.sh" "--python" "${python_bin}")
if [[ -n "${support_bundle_out}" ]]; then
    beta_smoke_display="${beta_smoke_display} --support-bundle-out ${support_bundle_out}"
    beta_smoke_args+=("--support-bundle-out" "${support_bundle_out}")
fi
run_step "${beta_smoke_display}" bash "${beta_smoke_args[@]}"

package_gate_display="./scripts/run_fedora_alpha_gate.sh --reset-user-services"
package_gate_args=("./scripts/run_fedora_alpha_gate.sh" "--reset-user-services")
if [[ "${run_package_gate}" -eq 0 ]]; then
    package_gate_display="${package_gate_display} --dry-run"
    package_gate_args+=("--dry-run")
fi
run_step "${package_gate_display}" bash "${package_gate_args[@]}"

installed_desktop_display="./scripts/run_installed_desktop_smoke.sh"
installed_desktop_args=("./scripts/run_installed_desktop_smoke.sh")
if [[ "${run_package_gate}" -eq 0 ]]; then
    installed_desktop_display="${installed_desktop_display} --dry-run"
    installed_desktop_args+=("--dry-run")
fi
run_step "${installed_desktop_display}" bash "${installed_desktop_args[@]}"
