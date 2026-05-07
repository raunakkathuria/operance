#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
template_path="${repo_root}/packaging/systemd/operance-tray.service.in"

python_bin=".venv/bin/python"
unit_dir="${HOME}/.config/systemd/user"
dry_run=0
skip_systemctl=0

usage() {
    cat <<'EOF'
Usage: scripts/install_systemd_user_service.sh [options]

Render and optionally install the repo-local Operance tray user service.

Options:
  --python PATH       Python executable to use. Defaults to .venv/bin/python.
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
        --python)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--python requires a path"
            fi
            python_bin="$1"
            ;;
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

if [[ ! -x "${python_bin}" ]] && [[ "${dry_run}" -eq 0 ]] && [[ "${skip_systemctl}" -eq 0 ]]; then
    fail "python executable not found: ${python_bin}"
fi

if [[ "${python_bin}" = /* ]]; then
    python_abs="${python_bin}"
else
    python_abs="${repo_root}/${python_bin}"
fi
unit_dir="${unit_dir%/}"
unit_path="${unit_dir}/operance-tray.service"

escape_sed() {
    printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

run_step "mkdir -p ${unit_dir}" mkdir -p "${unit_dir}"

echo "+ render packaging/systemd/operance-tray.service.in -> ${unit_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed \
        -e "s/__REPO_ROOT__/$(escape_sed "${repo_root}")/g" \
        -e "s/__PYTHON_BIN__/$(escape_sed "${python_abs}")/g" \
        "${template_path}" > "${unit_path}"
fi

if [[ "${skip_systemctl}" -eq 1 ]]; then
    exit 0
fi

run_step "systemctl --user daemon-reload" systemctl --user daemon-reload
run_step "systemctl --user enable --now operance-tray.service" systemctl --user enable --now operance-tray.service
