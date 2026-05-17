#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

command_path="operance"
systemctl_command="systemctl"
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/run_installed_desktop_smoke.sh [options]

Run installed-runtime checks and print the manual tray click-to-talk smoke.

Options:
  --command PATH             Installed operance command to use. Defaults to operance.
  --systemctl-command PATH   systemctl command to use. Defaults to systemctl.
  --dry-run                  Print checks and manual smoke commands without executing checks.
  -h, --help                 Show this help text.
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

print_manual_checks() {
    cat <<'EOF'
Manual tray click-to-talk checks:
- open firefox
- open localhost:3000
- open firefox and load localhost:3000
- what time is it
- wifi status
- what is the volume
- is audio muted
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --command)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--command requires a path"
            fi
            command_path="$1"
            ;;
        --systemctl-command)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--systemctl-command requires a path"
            fi
            systemctl_command="$1"
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

cd "${repo_root}"

mvp_check_display="python3 scripts/check_installed_mvp_runtime.py --command ${command_path} --check-tray-service"
mvp_check_args=(python3 scripts/check_installed_mvp_runtime.py --command "${command_path}" --check-tray-service)
if [[ "${systemctl_command}" != "systemctl" ]]; then
    mvp_check_display="${mvp_check_display} --systemctl-command ${systemctl_command}"
    mvp_check_args+=(--systemctl-command "${systemctl_command}")
fi

run_step "${mvp_check_display}" "${mvp_check_args[@]}"
run_step "${systemctl_command} --user enable --now operance-tray.service" \
    "${systemctl_command}" --user enable --now operance-tray.service
run_step "${systemctl_command} --user status operance-tray.service --no-pager" \
    "${systemctl_command}" --user status operance-tray.service --no-pager
run_step "${command_path} --installed-smoke" "${command_path}" --installed-smoke
run_step "${command_path} --print-config" "${command_path}" --print-config
run_step "${command_path} --supported-commands --supported-commands-available-only" \
    "${command_path}" --supported-commands --supported-commands-available-only
print_manual_checks
