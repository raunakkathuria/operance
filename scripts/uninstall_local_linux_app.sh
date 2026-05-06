#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

venv_path=".venv"
remove_voice_loop=0
remove_venv=0
skip_systemctl=0
dry_run=0
unit_dir=""

usage() {
    cat <<'EOF'
Usage: scripts/uninstall_local_linux_app.sh [options]

Remove the repo-local Operance tray service and optionally delete the local venv.

Options:
  --venv PATH        Virtual environment path. Defaults to .venv.
  --unit-dir PATH    Override the systemd user unit directory.
  --voice-loop       Remove the continuous voice-loop user service too.
  --remove-venv      Delete the virtual environment after removing the service.
  --skip-systemctl   Remove the service file without calling systemctl --user.
  --dry-run          Print the orchestration steps without executing them.
  -h, --help         Show this help text.
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
        --venv)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--venv requires a path"
            fi
            venv_path="$1"
            ;;
        --voice-loop)
            remove_voice_loop=1
            ;;
        --unit-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--unit-dir requires a path"
            fi
            unit_dir="$1"
            ;;
        --remove-venv)
            remove_venv=1
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

venv_path="${venv_path%/}"

service_display="./scripts/uninstall_systemd_user_service.sh"
service_args=("./scripts/uninstall_systemd_user_service.sh")
if [[ -n "${unit_dir}" ]]; then
    service_display="${service_display} --unit-dir ${unit_dir}"
    service_args+=("--unit-dir" "${unit_dir}")
fi
if [[ "${skip_systemctl}" -eq 1 ]]; then
    service_display="${service_display} --skip-systemctl"
    service_args+=("--skip-systemctl")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    service_display="${service_display} --dry-run"
    service_args+=("--dry-run")
fi

run_step "${service_display}" "${service_args[@]}"

if [[ "${remove_voice_loop}" -eq 1 ]]; then
    voice_loop_service_display="./scripts/uninstall_voice_loop_user_service.sh"
    voice_loop_service_args=("bash" "./scripts/uninstall_voice_loop_user_service.sh")
    if [[ -n "${unit_dir}" ]]; then
        voice_loop_service_display="${voice_loop_service_display} --unit-dir ${unit_dir}"
        voice_loop_service_args+=("--unit-dir" "${unit_dir}")
    fi
    if [[ "${skip_systemctl}" -eq 1 ]]; then
        voice_loop_service_display="${voice_loop_service_display} --skip-systemctl"
        voice_loop_service_args+=("--skip-systemctl")
    fi
    if [[ "${dry_run}" -eq 1 ]]; then
        voice_loop_service_display="${voice_loop_service_display} --dry-run"
        voice_loop_service_args+=("--dry-run")
    fi

    run_step "${voice_loop_service_display}" "${voice_loop_service_args[@]}"
fi

if [[ "${remove_venv}" -eq 1 ]]; then
    run_step "rm -rf ${venv_path}" rm -rf "${venv_path}"
fi
