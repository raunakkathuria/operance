#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

command_path="operance"
package_path=""
installer=""
package_name="operance"
desktop_entry_path="/usr/share/applications/operance.desktop"
tray_unit_path="/usr/lib/systemd/user/operance-tray.service"
voice_loop_unit_path="/usr/lib/systemd/user/operance-voice-loop.service"
use_sudo=1
uninstall_after=0
dry_run=0
support_bundle_out=""
require_mvp_runtime=0
reset_user_services=0

usage() {
    cat <<'EOF'
Usage: scripts/run_installed_package_smoke.sh [options]

Run the current safe smoke sequence against an installed Operance package.

Options:
  --command PATH             Installed operance command to use. Defaults to operance.
  --package PATH             Native package artifact to install before running the smoke sequence.
  --installer NAME           Package installer to use for --package or --uninstall-after. Supported: apt, dnf.
  --package-name NAME        Installed package name for --uninstall-after. Defaults to operance.
  --desktop-entry-path PATH  Desktop entry path to verify. Defaults to /usr/share/applications/operance.desktop.
  --tray-unit-path PATH      Packaged tray user-unit path to verify. Defaults to /usr/lib/systemd/user/operance-tray.service.
  --voice-loop-unit-path PATH
                             Packaged voice-loop user-unit path to verify. Defaults to /usr/lib/systemd/user/operance-voice-loop.service.
  --no-sudo                  Forward --no-sudo to the package install or uninstall helpers.
  --uninstall-after          Remove the installed package after the smoke sequence completes.
  --dry-run                  Print the smoke commands without executing them.
  --support-bundle-out PATH  Forward an output path to the final support-bundle step.
  --require-mvp-runtime      Verify installed tray UI and STT runtime dependencies through --doctor.
  --reset-user-services      Forward --reset-user-services to package install.
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

infer_installer_from_package() {
    case "$1" in
        *.deb)
            printf '%s' "apt"
            ;;
        *.rpm)
            printf '%s' "dnf"
            ;;
        *)
            fail "package artifact must end in .deb or .rpm"
            ;;
    esac
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
        --package-name)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--package-name requires a value"
            fi
            package_name="$1"
            ;;
        --desktop-entry-path)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--desktop-entry-path requires a path"
            fi
            desktop_entry_path="$1"
            ;;
        --tray-unit-path)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--tray-unit-path requires a path"
            fi
            tray_unit_path="$1"
            ;;
        --voice-loop-unit-path)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--voice-loop-unit-path requires a path"
            fi
            voice_loop_unit_path="$1"
            ;;
        --no-sudo)
            use_sudo=0
            ;;
        --uninstall-after)
            uninstall_after=1
            ;;
        --dry-run)
            dry_run=1
            ;;
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
            ;;
        --require-mvp-runtime)
            require_mvp_runtime=1
            ;;
        --reset-user-services)
            reset_user_services=1
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

if [[ "${uninstall_after}" -eq 1 ]] && [[ -z "${package_path}" ]]; then
    fail "--uninstall-after requires --package"
fi

if [[ -n "${package_path}" ]] && [[ -z "${installer}" ]]; then
    installer="$(infer_installer_from_package "${package_path}")"
fi

cd "${repo_root}"

if [[ -n "${package_path}" ]]; then
    install_display="./scripts/install_package_artifact.sh --package ${package_path}"
    install_args=("./scripts/install_package_artifact.sh" "--package" "${package_path}")
    if [[ -n "${installer}" ]]; then
        install_display="${install_display} --installer ${installer}"
        install_args+=("--installer" "${installer}")
    fi
    if [[ "${installer}" == "dnf" ]]; then
        install_display="${install_display} --replace-existing"
        install_args+=("--replace-existing")
    fi
    if [[ "${reset_user_services}" -eq 1 ]]; then
        install_display="${install_display} --reset-user-services"
        install_args+=("--reset-user-services")
    fi
    if [[ "${use_sudo}" -eq 0 ]]; then
        install_display="${install_display} --no-sudo"
        install_args+=("--no-sudo")
    fi
    run_step "${install_display}" bash "${install_args[@]}"
fi

run_step "test -f ${desktop_entry_path}" test -f "${desktop_entry_path}"
run_step "test -f ${tray_unit_path}" test -f "${tray_unit_path}"
run_step "test -f ${voice_loop_unit_path}" test -f "${voice_loop_unit_path}"

run_step "${command_path} --version" "${command_path}" "--version"
run_step "${command_path} --doctor" "${command_path}" "--doctor"
if [[ "${require_mvp_runtime}" -eq 1 ]]; then
    run_step \
        "python3 scripts/check_installed_mvp_runtime.py --command ${command_path} --check-tray-service" \
        python3 scripts/check_installed_mvp_runtime.py --command "${command_path}" --check-tray-service
fi
run_step \
    "${command_path} --supported-commands --supported-commands-available-only" \
    "${command_path}" "--supported-commands" "--supported-commands-available-only"

support_bundle_display="${command_path} --support-bundle"
support_bundle_command=("${command_path}" "--support-bundle")
if [[ -n "${support_bundle_out}" ]]; then
    support_bundle_display="${support_bundle_display} --support-bundle-out ${support_bundle_out}"
    support_bundle_command+=("--support-bundle-out" "${support_bundle_out}")
fi
run_step "${support_bundle_display}" "${support_bundle_command[@]}"

if [[ "${uninstall_after}" -eq 1 ]]; then
    uninstall_display="./scripts/uninstall_native_package.sh"
    uninstall_args=("./scripts/uninstall_native_package.sh")
    if [[ -n "${installer}" ]]; then
        uninstall_display="${uninstall_display} --installer ${installer}"
        uninstall_args+=("--installer" "${installer}")
    fi
    uninstall_display="${uninstall_display} --package-name ${package_name}"
    uninstall_args+=("--package-name" "${package_name}")
    if [[ "${use_sudo}" -eq 0 ]]; then
        uninstall_display="${uninstall_display} --no-sudo"
        uninstall_args+=("--no-sudo")
    fi
    run_step "${uninstall_display}" bash "${uninstall_args[@]}"
fi
