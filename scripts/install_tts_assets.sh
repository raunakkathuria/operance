#!/usr/bin/env bash
set -euo pipefail

config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
model_source=""
voices_source=""
force=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_tts_assets.sh [options]

Copy external Kokoro model assets into the user-scoped Operance config path.

Options:
  --model PATH        Path to the source Kokoro model file.
  --voices PATH       Path to the source Kokoro voices file.
  --config-home PATH  Override the user config root. Defaults to
                      $XDG_CONFIG_HOME or ~/.config.
  --force             Overwrite existing target asset files.
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
        --model)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--model requires a path"
            fi
            model_source="$1"
            ;;
        --voices)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--voices requires a path"
            fi
            voices_source="$1"
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

if [[ -z "${model_source}" && -z "${voices_source}" ]]; then
    fail "at least one of --model or --voices is required"
fi

if [[ -n "${model_source}" && ! -f "${model_source}" ]]; then
    fail "source model not found: ${model_source}"
fi

if [[ -n "${voices_source}" && ! -f "${voices_source}" ]]; then
    fail "source voices not found: ${voices_source}"
fi

target_dir="${config_home%/}/operance/tts"
target_model_path="${target_dir}/kokoro.onnx"
target_voices_path="${target_dir}/voices.bin"

if [[ -n "${model_source}" && -f "${target_model_path}" && "${force}" -eq 0 ]]; then
    fail "target TTS model already exists: ${target_model_path}"
fi

if [[ -n "${voices_source}" && -f "${target_voices_path}" && "${force}" -eq 0 ]]; then
    fail "target TTS voices already exist: ${target_voices_path}"
fi

run_step "mkdir -p ${target_dir}" mkdir -p "${target_dir}"
if [[ -n "${model_source}" ]]; then
    run_step "cp ${model_source} ${target_model_path}" cp "${model_source}" "${target_model_path}"
fi
if [[ -n "${voices_source}" ]]; then
    run_step "cp ${voices_source} ${target_voices_path}" cp "${voices_source}" "${target_voices_path}"
fi
