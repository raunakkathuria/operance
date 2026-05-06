#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

python_bin=".venv/bin/python"
dry_run=0
workdir=""
cleanup_workdir=0

usage() {
    cat <<'EOF'
Usage: scripts/run_demo.sh [options]

Run the checked-in deterministic Operance demo against developer-mode mock adapters.

Options:
  --python PATH   Python executable to use. Defaults to .venv/bin/python.
  --workdir PATH  Reuse PATH for demo data instead of creating a temporary workspace.
  --dry-run       Print the demo steps without executing them.
  -h, --help      Show this help text.
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

run_step() {
    local title="$1"
    local display="$2"
    shift 2

    echo
    echo "== ${title} =="
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
        --workdir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--workdir requires a path"
            fi
            workdir="$1"
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

if [[ ! -x "${python_bin}" ]]; then
    fail "python executable not found: ${python_bin}"
fi

if [[ -z "${workdir}" ]]; then
    workdir="$(mktemp -d "${TMPDIR:-/tmp}/operance-demo.XXXXXX")"
    cleanup_workdir=1
fi

if [[ "${dry_run}" -eq 0 ]]; then
    mkdir -p "${workdir}"
fi

if [[ "${cleanup_workdir}" -eq 1 ]]; then
    trap 'rm -rf "${workdir}"' EXIT
fi

export OPERANCE_DEVELOPER_MODE=1
export OPERANCE_LOG_LEVEL=WARNING
export OPERANCE_LOG_JSON=0
export OPERANCE_DATA_DIR="${workdir}/data"
export OPERANCE_DESKTOP_DIR="${workdir}/Desktop"

echo "== Operance deterministic demo =="
echo "Workspace: ${workdir}"
echo "Python: ${python_bin}"

run_step "Status snapshot" \
    "${python_bin} -m operance.cli --status" \
    "${python_bin}" -m operance.cli --status

run_step "Launch command" \
    "${python_bin} -m operance.cli --transcript \"open firefox\"" \
    "${python_bin}" -m operance.cli --transcript "open firefox"

run_step "Confirmation session" \
    "${python_bin} -m operance.cli --transcript-file demo/phase0a_confirmation.txt" \
    "${python_bin}" -m operance.cli --transcript-file "demo/phase0a_confirmation.txt"

run_step "Replay summary" \
    "${python_bin} -m operance.cli --replay-file demo/phase0a_replay.jsonl" \
    "${python_bin}" -m operance.cli --replay-file "demo/phase0a_replay.jsonl"

run_step "Corpus summary" \
    "${python_bin} -m operance.cli --run-corpus" \
    "${python_bin}" -m operance.cli --run-corpus
