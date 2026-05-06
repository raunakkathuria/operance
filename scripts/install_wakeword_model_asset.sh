#!/usr/bin/env bash
set -euo pipefail

config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
source_path=""
force=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_wakeword_model_asset.sh --source PATH [options]

Copy an external wake-word model asset into the user-scoped Operance config path.

Options:
  --source PATH       Path to the source wake-word model file.
  --config-home PATH  Override the user config root. Defaults to
                      $XDG_CONFIG_HOME or ~/.config.
  --force             Overwrite an existing target model file.
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
    fail "--source is required"
fi

if [[ ! -f "${source_path}" ]]; then
    fail "source model not found: ${source_path}"
fi

target_dir="${config_home%/}/operance/wakeword"
target_path="${target_dir}/operance.onnx"

if [[ -f "${target_path}" && "${force}" -eq 0 ]]; then
    fail "target wake-word model already exists: ${target_path}"
fi

run_step "mkdir -p ${target_dir}" mkdir -p "${target_dir}"
run_step "cp ${source_path} ${target_path}" cp "${source_path}" "${target_path}"
