#!/usr/bin/env bash
set -euo pipefail

installer="auto"
install_deb=0
install_rpm=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_packaging_tools.sh [options]

Install the native package build tools used by the current Operance Debian and
RPM artifact helpers.

Options:
  --installer NAME  Package installer to use. Supported: auto, apt, dnf.
                    Defaults to auto.
  --deb             Install Debian packaging tools.
  --rpm             Install RPM packaging tools.
  --dry-run         Print the install command without executing it.
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
        --installer)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--installer requires a value"
            fi
            installer="$1"
            ;;
        --deb)
            install_deb=1
            ;;
        --rpm)
            install_rpm=1
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

case "${installer}" in
    auto)
        if command -v apt >/dev/null 2>&1; then
            installer="apt"
        elif command -v dnf >/dev/null 2>&1; then
            installer="dnf"
        else
            fail "could not detect a supported installer; use --installer apt|dnf"
        fi
        ;;
    apt|dnf)
        ;;
    *)
        fail "unsupported installer: ${installer}"
        ;;
esac

if [[ "${install_deb}" -eq 0 && "${install_rpm}" -eq 0 ]]; then
    case "${installer}" in
        apt)
            install_deb=1
            ;;
        dnf)
            install_rpm=1
            ;;
    esac
fi

packages=()
case "${installer}" in
    apt)
        if [[ "${install_rpm}" -eq 1 ]]; then
            fail "apt installer does not support --rpm packaging tools"
        fi
        if [[ "${install_deb}" -eq 1 ]]; then
            packages=("dpkg-dev")
        fi
        ;;
    dnf)
        if [[ "${install_deb}" -eq 1 ]]; then
            fail "dnf installer does not support --deb packaging tools"
        fi
        if [[ "${install_rpm}" -eq 1 ]]; then
            packages=("rpm-build")
        fi
        ;;
esac

if [[ "${#packages[@]}" -eq 0 ]]; then
    fail "no packaging tools selected"
fi

display="sudo ${installer} install -y ${packages[*]}"
run_step "${display}" sudo "${installer}" install -y "${packages[@]}"
