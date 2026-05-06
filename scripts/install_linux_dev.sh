#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

python_bin="python3"
venv_path=".venv"
include_ui=0
include_voice=0
run_doctor=1
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_linux_dev.sh [options]

Bootstrap a local Operance development environment from a checked-out repo.

Options:
  --ui            Install the optional tray UI backend.
  --voice         Install the optional wake-word and STT backends.
  --skip-doctor   Do not run the final operance doctor check.
  --dry-run       Print the commands without executing them.
  --venv PATH     Create and use the virtual environment at PATH.
  -h, --help      Show this help text.
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
        --ui)
            include_ui=1
            ;;
        --voice)
            include_voice=1
            ;;
        --skip-doctor)
            run_doctor=0
            ;;
        --dry-run)
            dry_run=1
            ;;
        --venv)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--venv requires a path"
            fi
            venv_path="$1"
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
editable_spec=".[dev"
if [[ "${include_ui}" -eq 1 ]]; then
    editable_spec="${editable_spec},ui"
fi
if [[ "${include_voice}" -eq 1 ]]; then
    editable_spec="${editable_spec},voice"
fi
editable_spec="${editable_spec}]"

run_step "${python_bin} -m venv ${venv_path}" "${python_bin}" -m venv "${venv_path}"
run_step "${venv_python} -m pip install --upgrade pip" "${venv_python}" -m pip install --upgrade pip
run_step "${venv_python} -m pip install -e \"${editable_spec}\"" "${venv_python}" -m pip install -e "${editable_spec}"
if [[ "${run_doctor}" -eq 1 ]]; then
    run_step "${venv_python} -m operance.cli --doctor" "${venv_python}" -m operance.cli --doctor
fi
