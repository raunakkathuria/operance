#!/usr/bin/env bash
set -euo pipefail

package_name="operance"
installer=""
use_sudo=1
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/uninstall_native_package.sh [options]

Remove an installed Operance native package through the matching distro package manager.

Options:
  --package-name NAME  Installed package name. Defaults to operance.
  --installer NAME     Package installer to use. Supported: apt, dnf.
  --no-sudo            Run the installer directly instead of prefixing it with sudo.
  --dry-run            Print the remove command without executing it.
  -h, --help           Show this help text.
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
        --package-name)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--package-name requires a value"
            fi
            package_name="$1"
            ;;
        --installer)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--installer requires a value"
            fi
            installer="$1"
            ;;
        --no-sudo)
            use_sudo=0
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

if [[ -z "${package_name}" ]]; then
    fail "package name must not be empty"
fi

if [[ -z "${installer}" ]]; then
    if command -v apt >/dev/null 2>&1; then
        installer="apt"
    elif command -v dnf >/dev/null 2>&1; then
        installer="dnf"
    else
        fail "could not detect a supported installer; use --installer apt|dnf"
    fi
fi

case "${installer}" in
    apt|dnf)
        ;;
    *)
        fail "unsupported installer: ${installer}"
        ;;
esac

if [[ "${dry_run}" -eq 0 ]] && ! command -v "${installer}" >/dev/null 2>&1; then
    fail "installer not found on PATH: ${installer}"
fi

remove_args=("${installer}" "remove" "-y" "${package_name}")
display="${installer} remove -y ${package_name}"
if [[ "${use_sudo}" -eq 1 ]]; then
    remove_args=("sudo" "${remove_args[@]}")
    display="sudo ${display}"
fi

run_step "${display}" "${remove_args[@]}"
