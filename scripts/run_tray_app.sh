#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
dry_run=0
extra_args=()

usage() {
    cat <<'EOF'
Usage: scripts/run_tray_app.sh [options] [-- extra operance.cli args]

Run the repo-local Operance tray app.

Options:
  --python PATH   Python executable to use. Defaults to .venv/bin/python.
  --dry-run       Print the tray command without executing it.
  -h, --help      Show this help text.

Any arguments after `--` are forwarded to `operance.cli` after `--tray-run`.
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
        --)
            shift
            extra_args=("$@")
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

if [[ ! -x "${python_bin}" ]] && [[ "${dry_run}" -eq 0 ]]; then
    fail "python executable not found: ${python_bin}"
fi

cd "${repo_root}"

display="${python_bin} -m operance.cli --tray-run"
command=("${python_bin}" "-m" "operance.cli" "--tray-run")
for extra_arg in "${extra_args[@]}"; do
    display="${display} ${extra_arg}"
    command+=("${extra_arg}")
done

run_step "${display}" "${command[@]}"
