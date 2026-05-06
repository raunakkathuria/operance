#!/usr/bin/env bash
set -euo pipefail

unit_dir="${HOME}/.config/systemd/user"
dry_run=0
skip_systemctl=0

usage() {
    cat <<'EOF'
Usage: scripts/uninstall_voice_loop_user_service.sh [options]

Disable and remove the repo-local Operance continuous voice-loop user service.

Options:
  --unit-dir PATH     Target systemd user unit directory.
  --skip-systemctl    Remove the unit file without calling systemctl --user.
  --dry-run           Print the uninstall steps without executing them.
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

unit_dir="${unit_dir%/}"
unit_path="${unit_dir}/operance-voice-loop.service"

if [[ "${skip_systemctl}" -eq 0 ]]; then
    echo "+ systemctl --user disable --now operance-voice-loop.service || true"
    if [[ "${dry_run}" -eq 0 ]]; then
        systemctl --user disable --now operance-voice-loop.service >/dev/null 2>&1 || true
    fi
fi

run_step "rm -f ${unit_path}" rm -f "${unit_path}"

if [[ "${skip_systemctl}" -eq 0 ]]; then
    run_step "systemctl --user daemon-reload" systemctl --user daemon-reload
fi
