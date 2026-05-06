#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

venv_path=".venv"
include_voice=0
install_voice_loop=0
skip_bootstrap=0
skip_systemctl=0
dry_run=0
unit_dir=""

usage() {
    cat <<'EOF'
Usage: scripts/install_local_linux_app.sh [options]

Bootstrap the repo-local Operance environment and install the tray user service.

Options:
  --voice           Include the optional voice dependencies.
  --voice-loop      Install the continuous voice-loop user service in addition to the tray service.
  --venv PATH       Virtual environment path. Defaults to .venv.
  --unit-dir PATH   Override the systemd user unit directory.
  --skip-bootstrap  Skip the venv/bootstrap step and only install the service.
  --skip-systemctl  Render the service unit without calling systemctl --user.
  --dry-run         Print the orchestration steps without executing them.
  -h, --help        Show this help text.
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
        --voice)
            include_voice=1
            ;;
        --voice-loop)
            install_voice_loop=1
            include_voice=1
            ;;
        --venv)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--venv requires a path"
            fi
            venv_path="$1"
            ;;
        --unit-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--unit-dir requires a path"
            fi
            unit_dir="$1"
            ;;
        --skip-bootstrap)
            skip_bootstrap=1
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
venv_python="${venv_path}/bin/python"
requested_unit_dir="${unit_dir}"

bootstrap_display="./scripts/install_linux_dev.sh --ui"
bootstrap_args=("./scripts/install_linux_dev.sh" "--ui")
if [[ "${include_voice}" -eq 1 ]]; then
    bootstrap_display="${bootstrap_display} --voice"
    bootstrap_args+=("--voice")
fi
bootstrap_display="${bootstrap_display} --venv ${venv_path}"
bootstrap_args+=("--venv" "${venv_path}")
if [[ "${dry_run}" -eq 1 ]]; then
    bootstrap_args+=("--dry-run")
fi

service_display="./scripts/install_systemd_user_service.sh --python ${venv_python}"
service_args=("./scripts/install_systemd_user_service.sh" "--python" "${venv_python}")
if [[ -n "${requested_unit_dir}" ]]; then
    service_display="${service_display} --unit-dir ${requested_unit_dir}"
    service_args+=("--unit-dir" "${requested_unit_dir}")
fi
if [[ "${skip_systemctl}" -eq 1 ]]; then
    service_display="${service_display} --skip-systemctl"
    service_args+=("--skip-systemctl")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    service_args+=("--dry-run")
fi

if [[ "${skip_bootstrap}" -eq 0 ]]; then
    run_step "${bootstrap_display}" "${bootstrap_args[@]}"
fi

run_step "${service_display}" "${service_args[@]}"

if [[ "${install_voice_loop}" -eq 1 ]]; then
    voice_loop_service_display="./scripts/install_voice_loop_user_service.sh"
    voice_loop_service_args=("bash" "./scripts/install_voice_loop_user_service.sh")
    if [[ -n "${requested_unit_dir}" ]]; then
        voice_loop_service_display="${voice_loop_service_display} --unit-dir ${requested_unit_dir}"
        voice_loop_service_args+=("--unit-dir" "${requested_unit_dir}")
    fi
    if [[ "${skip_systemctl}" -eq 1 ]]; then
        voice_loop_service_display="${voice_loop_service_display} --skip-systemctl"
        voice_loop_service_args+=("--skip-systemctl")
    fi
    if [[ "${dry_run}" -eq 1 ]]; then
        voice_loop_service_args+=("--dry-run")
    fi

    run_step "${voice_loop_service_display}" "${voice_loop_service_args[@]}"
fi
