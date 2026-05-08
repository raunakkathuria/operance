#!/usr/bin/env bash
set -euo pipefail

package_path=""
installer=""
use_sudo=1
dry_run=0
replace_existing=0

usage() {
    cat <<'EOF'
Usage: scripts/install_package_artifact.sh [options]

Install a built Operance native package artifact through the matching distro package manager.

Options:
  --package PATH      Built package artifact path (.deb or .rpm).
  --installer NAME    Package installer to use. Supported: apt, dnf.
  --replace-existing  Replace an already installed package with the provided artifact.
  --no-sudo           Run the installer directly instead of prefixing it with sudo.
  --dry-run           Print the install command without executing it.
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
        --package)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--package requires a path"
            fi
            package_path="$1"
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
        --replace-existing)
            replace_existing=1
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

if [[ -z "${package_path}" ]]; then
    fail "--package is required"
fi
if [[ ! -f "${package_path}" ]]; then
    fail "package artifact not found: ${package_path}"
fi

case "${package_path}" in
    *.deb)
        package_type="deb"
        default_installer="apt"
        ;;
    *.rpm)
        package_type="rpm"
        default_installer="dnf"
        ;;
    *)
        fail "package artifact must end in .deb or .rpm"
        ;;
esac

if [[ -z "${installer}" ]]; then
    installer="${default_installer}"
fi

case "${installer}" in
    apt)
        if [[ "${package_type}" != "deb" ]]; then
            fail "apt installer requires a .deb package artifact"
        fi
        ;;
    dnf)
        if [[ "${package_type}" != "rpm" ]]; then
            fail "dnf installer requires a .rpm package artifact"
        fi
        ;;
    *)
        fail "unsupported installer: ${installer}"
        ;;
esac

if [[ "${dry_run}" -eq 0 ]] && ! command -v "${installer}" >/dev/null 2>&1; then
    fail "installer not found on PATH: ${installer}"
fi

installer_subcommand="install"
if [[ "${replace_existing}" -eq 1 ]]; then
    if [[ "${installer}" == "dnf" ]]; then
        installer_subcommand="reinstall"
        if [[ "${dry_run}" -eq 0 ]]; then
            if ! command -v rpm >/dev/null 2>&1; then
                fail "rpm not found on PATH: rpm"
            fi
            package_name="$(rpm -qp --queryformat '%{NAME}' "${package_path}")" || {
                fail "unable to read RPM package name from artifact: ${package_path}"
            }
            if ! rpm -q "${package_name}" >/dev/null 2>&1; then
                installer_subcommand="install"
            fi
        fi
    else
        fail "--replace-existing is currently supported only with dnf"
    fi
fi

install_args=("${installer}" "${installer_subcommand}" "-y" "${package_path}")
display="${installer} ${installer_subcommand} -y ${package_path}"
if [[ "${use_sudo}" -eq 1 ]]; then
    install_args=("sudo" "${install_args[@]}")
    display="sudo ${display}"
fi

run_step "${display}" "${install_args[@]}"
