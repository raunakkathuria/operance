#!/usr/bin/env bash
set -euo pipefail

config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
wakeword_threshold=""
wakeword_model=""
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/update_voice_loop_user_config.sh [options]

Update the current user-scoped Operance voice-loop args file.

Options:
  --config-home PATH       Override the user config root. Defaults to
                           $XDG_CONFIG_HOME or ~/.config.
  --wakeword-threshold N   Set or replace the wake-word threshold.
  --wakeword-model VALUE   Set or replace the wake-word model token.
                           Use "auto" to resolve a discovered external asset.
  --dry-run                Print the update steps without executing them.
  -h, --help               Show this help text.
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
        --config-home)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--config-home requires a path"
            fi
            config_home="$1"
            ;;
        --wakeword-threshold)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--wakeword-threshold requires a value"
            fi
            wakeword_threshold="$1"
            ;;
        --wakeword-model)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--wakeword-model requires a value"
            fi
            wakeword_model="$1"
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

if [[ -z "${wakeword_threshold}" && -z "${wakeword_model}" ]]; then
    fail "at least one update flag is required"
fi

if [[ -n "${wakeword_threshold}" ]]; then
    if ! [[ "${wakeword_threshold}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        fail "wake-word threshold must be a number"
    fi
    if ! awk -v value="${wakeword_threshold}" 'BEGIN { exit !(value > 0 && value <= 1) }'; then
        fail "wake-word threshold must be greater than 0 and at most 1"
    fi
fi

config_dir="${config_home%/}/operance"
target_path="${config_dir}/voice-loop.args"

existing_lines=()
if [[ -f "${target_path}" ]]; then
    mapfile -t existing_lines < "${target_path}"
fi

filtered_lines=()
skip_next=0
for line in "${existing_lines[@]}"; do
    if [[ "${skip_next}" -eq 1 ]]; then
        skip_next=0
        continue
    fi
    if [[ -n "${wakeword_model}" && "${line}" == "--wakeword-model" ]]; then
        skip_next=1
        continue
    fi
    if [[ -n "${wakeword_threshold}" && "${line}" == "--wakeword-threshold" ]]; then
        skip_next=1
        continue
    fi
    filtered_lines+=("${line}")
done

if [[ -n "${wakeword_model}" ]]; then
    filtered_lines+=("--wakeword-model" "${wakeword_model}")
fi
if [[ -n "${wakeword_threshold}" ]]; then
    filtered_lines+=("--wakeword-threshold" "${wakeword_threshold}")
fi

write_config() {
    : > "${target_path}"
    for line in "${filtered_lines[@]}"; do
        printf '%s\n' "${line}" >> "${target_path}"
    done
}

run_step "mkdir -p ${config_dir}" mkdir -p "${config_dir}"
run_step "write ${target_path}" write_config
