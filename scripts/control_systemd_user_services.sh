#!/usr/bin/env bash
set -euo pipefail

target="tray"
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/control_systemd_user_services.sh <action> [options]

Control the repo-local Operance tray or voice-loop user services.

Actions:
  start
  stop
  restart
  status
  enable
  disable

Options:
  --voice-loop  Target the continuous voice-loop user service.
  --all         Target both the tray and voice-loop user services.
  --dry-run     Print the systemctl command without executing it.
  -h, --help    Show this help text.
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

action="$1"
shift

case "${action}" in
    start|stop|restart|status|enable|disable)
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        fail "Unknown action: ${action}"
        ;;
esac

while [[ $# -gt 0 ]]; do
    case "$1" in
        --voice-loop)
            if [[ "${target}" == "all" ]]; then
                fail "--voice-loop cannot be combined with --all"
            fi
            target="voice-loop"
            ;;
        --all)
            if [[ "${target}" == "voice-loop" ]]; then
                fail "--all cannot be combined with --voice-loop"
            fi
            target="all"
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

services=("operance-tray.service")
if [[ "${target}" == "voice-loop" ]]; then
    services=("operance-voice-loop.service")
elif [[ "${target}" == "all" ]]; then
    services=("operance-tray.service" "operance-voice-loop.service")
fi

command=(systemctl --user "${action}")
display="+ systemctl --user ${action}"
if [[ "${action}" == "enable" || "${action}" == "disable" ]]; then
    command+=(--now)
    display="${display} --now"
fi
command+=("${services[@]}")
for service in "${services[@]}"; do
    display="${display} ${service}"
done
if [[ "${action}" == "status" ]]; then
    command+=(--no-pager)
    display="${display} --no-pager"
fi

echo "${display}"
if [[ "${dry_run}" -eq 0 ]]; then
    "${command[@]}"
fi
