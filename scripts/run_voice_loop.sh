#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
args_file=""
default_repo_args_file="${repo_root}/.operance/voice-loop.args"
default_user_args_file="${XDG_CONFIG_HOME:-${HOME}/.config}/operance/voice-loop.args"
dry_run=0
extra_args=()

usage() {
    cat <<'EOF'
Usage: scripts/run_voice_loop.sh [options] [-- extra operance.cli args]

Run the repo-local continuous Operance voice loop.

Options:
  --python PATH   Python executable to use. Defaults to .venv/bin/python.
  --args-file PATH
                  Load extra operance.cli args from a file when it exists.
  --dry-run       Print the voice-loop command without executing it.
  -h, --help      Show this help text.

Any arguments after `--` are forwarded to `operance.cli` after `--voice-loop`.
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
        --args-file)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--args-file requires a path"
            fi
            args_file="$1"
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

display="${python_bin} -m operance.cli --voice-loop"
command=("${python_bin}" "-m" "operance.cli" "--voice-loop")
if [[ -z "${args_file}" ]]; then
    if [[ -f "${default_repo_args_file}" ]]; then
        args_file="${default_repo_args_file}"
    elif [[ -f "${default_user_args_file}" ]]; then
        args_file="${default_user_args_file}"
    fi
fi
if [[ -n "${args_file}" ]] && [[ -f "${args_file}" ]]; then
    while IFS= read -r extra_arg || [[ -n "${extra_arg}" ]]; do
        if [[ -z "${extra_arg}" ]] || [[ "${extra_arg}" == \#* ]]; then
            continue
        fi
        display="${display} ${extra_arg}"
        command+=("${extra_arg}")
    done < "${args_file}"
fi
for extra_arg in "${extra_args[@]}"; do
    display="${display} ${extra_arg}"
    command+=("${extra_arg}")
done

run_step "${display}" "${command[@]}"
