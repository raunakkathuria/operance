#!/usr/bin/env bash
set -euo pipefail

lines=50
follow=0
dry_run=0
unit_name="operance-tray.service"

usage() {
    cat <<'EOF'
Usage: scripts/tail_systemd_user_service_logs.sh [options]

Read recent journal entries for the repo-local Operance tray or voice-loop user service.

Options:
  --lines N    Number of recent log lines to show. Defaults to 50.
  --voice-loop Tail logs for the continuous voice-loop user service instead of the tray service.
  --follow     Follow the journal stream after printing the initial lines.
  --dry-run    Print the journalctl command without executing it.
  -h, --help   Show this help text.
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lines)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--lines requires a value"
            fi
            lines="$1"
            ;;
        --voice-loop)
            unit_name="operance-voice-loop.service"
            ;;
        --follow)
            follow=1
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

if ! [[ "${lines}" =~ ^[0-9]+$ ]] || [[ "${lines}" -lt 1 ]]; then
    fail "--lines must be a positive integer"
fi

command=(journalctl --user --unit "${unit_name}" -n "${lines}" --no-pager)
display="+ journalctl --user --unit ${unit_name} -n ${lines} --no-pager"
if [[ "${follow}" -eq 1 ]]; then
    command+=(--follow)
    display="${display} --follow"
fi

echo "${display}"
if [[ "${dry_run}" -eq 0 ]]; then
    "${command[@]}"
fi
