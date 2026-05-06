#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
source_path=""
force=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_voice_loop_user_config.sh [options]

Copy a voice-loop args example into the current user config path.

Options:
  --source PATH       Override the source example file. Defaults to
                      /etc/operance/voice-loop.args.example when it exists,
                      otherwise packaging/etc/voice-loop.args.example.in in the repo.
  --config-home PATH  Override the user config root. Defaults to
                      $XDG_CONFIG_HOME or ~/.config.
  --force             Overwrite an existing target config file.
  --dry-run           Print the copy steps without executing them.
  -h, --help          Show this help text.
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
        --source)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--source requires a path"
            fi
            source_path="$1"
            ;;
        --config-home)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--config-home requires a path"
            fi
            config_home="$1"
            ;;
        --force)
            force=1
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

if [[ -z "${source_path}" ]]; then
    if [[ -f "/etc/operance/voice-loop.args.example" ]]; then
        source_path="/etc/operance/voice-loop.args.example"
    else
        source_path="${repo_root}/packaging/etc/voice-loop.args.example.in"
    fi
fi

if [[ ! -f "${source_path}" ]]; then
    fail "source example not found: ${source_path}"
fi

config_dir="${config_home%/}/operance"
target_path="${config_dir}/voice-loop.args"

if [[ -f "${target_path}" && "${force}" -eq 0 ]]; then
    fail "target config already exists: ${target_path}"
fi

run_step "mkdir -p ${config_dir}" mkdir -p "${config_dir}"
run_step "cp ${source_path} ${target_path}" cp "${source_path}" "${target_path}"
