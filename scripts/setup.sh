#!/usr/bin/env bash
set -euo pipefail

package_path=""
support_bundle_out=""
use_sudo=1
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/setup.sh [options]

Set up a packaged Operance install for the supported Fedora KDE Wayland path.

Options:
  --package PATH          Built Operance RPM artifact to install.
  --support-bundle-out PATH
                          Write the setup support bundle to this path.
  --no-sudo               Forward --no-sudo to package installation.
  --dry-run               Print the setup commands without executing them.
  -h, --help              Show this help text.
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

run_optional_step() {
    local display="$1"
    shift

    echo "+ ${display}"
    if [[ "${dry_run}" -eq 0 ]]; then
        "$@" || true
    fi
}

user_systemd_dir() {
    if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
        printf '%s\n' "${XDG_CONFIG_HOME}/systemd/user"
        return
    fi
    if [[ -z "${HOME:-}" ]]; then
        fail "HOME is required when XDG_CONFIG_HOME is not set"
    fi
    printf '%s\n' "${HOME}/.config/systemd/user"
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
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
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

if [[ -z "${package_path}" ]]; then
    fail "--package is required"
fi
if [[ ! -f "${package_path}" ]]; then
    fail "package artifact not found: ${package_path}"
fi
case "${package_path}" in
    *.rpm)
        ;;
    *)
        fail "scripts/setup.sh currently supports Fedora RPM artifacts only"
        ;;
esac

if [[ "${dry_run}" -eq 0 ]]; then
    if ! command -v dnf >/dev/null 2>&1; then
        fail "dnf not found on PATH"
    fi
    if ! command -v systemctl >/dev/null 2>&1; then
        fail "systemctl not found on PATH"
    fi
fi

unit_dir="$(user_systemd_dir)"
for unit in operance-tray.service operance-voice-loop.service; do
    run_optional_step "systemctl --user disable --now ${unit}" systemctl --user disable --now "${unit}"
    run_step "rm -f ${unit_dir}/${unit}" rm -f "${unit_dir}/${unit}"
done
run_optional_step "systemctl --user daemon-reload" systemctl --user daemon-reload

package_name="operance"
if [[ "${dry_run}" -eq 0 ]] && command -v rpm >/dev/null 2>&1; then
    package_name="$(rpm -qp --queryformat '%{NAME}' "${package_path}")" || {
        fail "unable to read RPM package name from artifact: ${package_path}"
    }
fi

remove_args=("dnf" "remove" "-y" "${package_name}")
remove_display="dnf remove -y ${package_name}"
install_args=("dnf" "install" "-y" "${package_path}")
install_display="dnf install -y ${package_path}"
if [[ "${use_sudo}" -eq 0 ]]; then
    :
else
    remove_args=("sudo" "${remove_args[@]}")
    remove_display="sudo ${remove_display}"
    install_args=("sudo" "${install_args[@]}")
    install_display="sudo ${install_display}"
fi

if [[ "${dry_run}" -eq 1 ]]; then
    run_step "${remove_display}" "${remove_args[@]}"
elif command -v rpm >/dev/null 2>&1 && rpm -q "${package_name}" >/dev/null 2>&1; then
    run_step "${remove_display}" "${remove_args[@]}"
fi
run_step "${install_display}" "${install_args[@]}"

run_step "systemctl --user enable --now operance-tray.service" systemctl --user enable --now operance-tray.service
run_step "operance --installed-smoke" operance --installed-smoke
run_step "operance --supported-commands --supported-commands-available-only" operance --supported-commands --supported-commands-available-only

support_bundle_display="operance --support-bundle"
support_bundle_args=("operance" "--support-bundle")
if [[ -n "${support_bundle_out}" ]]; then
    support_bundle_display="${support_bundle_display} --support-bundle-out ${support_bundle_out}"
    support_bundle_args+=("--support-bundle-out" "${support_bundle_out}")
fi
run_step "${support_bundle_display}" "${support_bundle_args[@]}"

cat <<'EOF'
Manual click-to-talk checks:
- Click the tray icon and say: open browser
- Click the tray icon and say: open google.com
- Click the tray icon and say: open firefox
- Click the tray icon and say: open firefox and notify me
- Click the tray icon and say: what time is it
If anything fails:
- Run: operance --issue-report
- Attach the support bundle to a GitHub issue.
EOF
