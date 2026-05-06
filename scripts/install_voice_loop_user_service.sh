#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
template_path="${repo_root}/packaging/systemd/operance-voice-loop.service.in"

unit_dir="${HOME}/.config/systemd/user"
dry_run=0
skip_systemctl=0

usage() {
    cat <<'EOF'
Usage: scripts/install_voice_loop_user_service.sh [options]

Render and optionally install the repo-local Operance continuous voice-loop user service.

Options:
  --unit-dir PATH     Target systemd user unit directory.
  --skip-systemctl    Render the unit file without calling systemctl --user.
  --dry-run           Print the install steps without executing them.
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
        --unit-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--unit-dir requires a path"
            fi
            unit_dir="$1"
            ;;
        --skip-systemctl)
            skip_systemctl=1
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

if [[ ! -f "${template_path}" ]]; then
    fail "service template not found: ${template_path}"
fi

unit_dir="${unit_dir%/}"
unit_path="${unit_dir}/operance-voice-loop.service"

escape_sed() {
    printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

run_step "mkdir -p ${unit_dir}" mkdir -p "${unit_dir}"

echo "+ render packaging/systemd/operance-voice-loop.service.in -> ${unit_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed \
        -e "s/__REPO_ROOT__/$(escape_sed "${repo_root}")/g" \
        "${template_path}" > "${unit_path}"
fi

if [[ "${skip_systemctl}" -eq 1 ]]; then
    exit 0
fi

run_step "systemctl --user daemon-reload" systemctl --user daemon-reload
run_step "systemctl --user enable --now operance-voice-loop.service" systemctl --user enable --now operance-voice-loop.service
