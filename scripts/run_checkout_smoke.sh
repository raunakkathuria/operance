#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
dry_run=0
support_bundle_out=""

usage() {
    cat <<'EOF'
Usage: scripts/run_checkout_smoke.sh [options]

Run the current safe smoke sequence for a source checkout.

Options:
  --python PATH              Python executable to use. Defaults to .venv/bin/python.
  --dry-run                  Print the smoke commands without executing them.
  --support-bundle-out PATH  Forward an output path to the final support-bundle step.
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--python requires a path"
            fi
            python_bin="$1"
            ;;
        --dry-run)
            dry_run=1
            ;;
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
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

run_step "${python_bin} -m operance.cli --version" "${python_bin}" "-m" "operance.cli" "--version"
run_step "${python_bin} -m operance.cli --about" "${python_bin}" "-m" "operance.cli" "--about"
run_step "${python_bin} -m operance.cli --doctor" "${python_bin}" "-m" "operance.cli" "--doctor"
run_step "${python_bin} -m operance.cli --setup-actions" "${python_bin}" "-m" "operance.cli" "--setup-actions"
run_step \
    "${python_bin} -m operance.cli --supported-commands --supported-commands-available-only" \
    "${python_bin}" "-m" "operance.cli" "--supported-commands" "--supported-commands-available-only"

support_bundle_display="${python_bin} -m operance.cli --support-bundle"
support_bundle_command=("${python_bin}" "-m" "operance.cli" "--support-bundle")
if [[ -n "${support_bundle_out}" ]]; then
    support_bundle_display="${support_bundle_display} --support-bundle-out ${support_bundle_out}"
    support_bundle_command+=("--support-bundle-out" "${support_bundle_out}")
fi

run_step "${support_bundle_display}" "${support_bundle_command[@]}"
