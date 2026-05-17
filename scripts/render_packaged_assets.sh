#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

desktop_template="${repo_root}/packaging/operance.desktop.in"
icon_source_path="${repo_root}/assets/icons/operance.svg"
entrypoint_template="${repo_root}/packaging/bin/operance-entrypoint.in"
voice_loop_args_template="${repo_root}/packaging/etc/voice-loop.args.example.in"
voice_loop_launcher_template="${repo_root}/packaging/bin/operance-voice-loop-launcher.in"
tray_service_template="${repo_root}/packaging/systemd/operance-tray-packaged.service.in"
voice_loop_service_template="${repo_root}/packaging/systemd/operance-voice-loop-packaged.service.in"
runtime_source_dir="${repo_root}/src/operance"
pyproject_source_path="${repo_root}/pyproject.toml"

output_dir="${repo_root}/dist/packaged-assets"
entrypoint="/usr/bin/operance"
python_bin="/usr/bin/python3"
bundle_profile="base"
bundle_python=""
bundle_source_site_packages=""
install_root="/usr/lib/operance"
package_version=""
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/render_packaged_assets.sh [options]

Render the shared packaged Operance CLI wrapper, bundled Python source tree,
desktop entry, voice-loop launcher, and tray plus voice-loop systemd assets.

Options:
  --output-dir PATH             Output directory for rendered assets.
  --entrypoint PATH             Installed operance entrypoint path. Defaults to /usr/bin/operance.
  --python-bin PATH             Python executable used by the packaged operance wrapper.
                                Defaults to /usr/bin/python3.
  --bundle-profile PROFILE      Dependency bundle profile. Supported: base, mvp.
                                Defaults to base.
  --bundle-python PATH          Python executable used to inspect the source site-packages
                                when bundling a non-base runtime profile.
  --bundle-source-site-packages PATH
                                Override the source site-packages directory for runtime bundling.
  --package-version VALUE       Package version to record in build metadata.
  --dry-run                     Print the render steps without executing them.
  -h, --help                    Show this help text.
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
        --output-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--output-dir requires a path"
            fi
            output_dir="$1"
            ;;
        --entrypoint)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--entrypoint requires a path"
            fi
            entrypoint="$1"
            ;;
        --python-bin)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--python-bin requires a path"
            fi
            python_bin="$1"
            ;;
        --bundle-profile)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-profile requires a value"
            fi
            bundle_profile="$1"
            ;;
        --bundle-python)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-python requires a path"
            fi
            bundle_python="$1"
            ;;
        --bundle-source-site-packages)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--bundle-source-site-packages requires a path"
            fi
            bundle_source_site_packages="$1"
            ;;
        --package-version)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--package-version requires a value"
            fi
            package_version="$1"
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

case "${bundle_profile}" in
    base|mvp)
        ;;
    *)
        fail "unsupported bundle profile: ${bundle_profile}"
        ;;
esac

if [[ -z "${bundle_python}" ]]; then
    if [[ -x "${repo_root}/.venv/bin/python" ]]; then
        bundle_python="${repo_root}/.venv/bin/python"
    else
        bundle_python="python3"
    fi
fi
if [[ -z "${package_version}" ]]; then
    package_version="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)"
fi
if [[ -z "${package_version}" ]]; then
    fail "could not determine package version from pyproject.toml"
fi

desktop_dir="${output_dir%/}/applications"
entrypoint_dir="${output_dir%/}/bin"
config_dir="${output_dir%/}/etc/operance"
icon_dir="${output_dir%/}/icons/hicolor/scalable/apps"
libexec_dir="${output_dir%/}/lib/operance"
runtime_dir="${output_dir%/}/lib/operance"
site_packages_root="${runtime_dir}/site-packages"
site_packages_dir="${site_packages_root}/operance"
systemd_dir="${output_dir%/}/systemd"
desktop_entry_path="${desktop_dir}/operance.desktop"
icon_path="${icon_dir}/operance.svg"
entrypoint_path="${entrypoint_dir}/operance"
voice_loop_args_path="${config_dir}/voice-loop.args.example"
packaged_pyproject_path="${runtime_dir}/pyproject.toml"
build_info_path="${runtime_dir}/build-info.json"
voice_loop_launcher_path="${libexec_dir}/voice-loop-launcher"
tray_service_unit_path="${systemd_dir}/operance-tray.service"
voice_loop_service_unit_path="${systemd_dir}/operance-voice-loop.service"

escape_sed() {
    printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

run_step "mkdir -p ${desktop_dir}" mkdir -p "${desktop_dir}"
run_step "mkdir -p ${entrypoint_dir}" mkdir -p "${entrypoint_dir}"
run_step "mkdir -p ${config_dir}" mkdir -p "${config_dir}"
run_step "mkdir -p ${icon_dir}" mkdir -p "${icon_dir}"
run_step "mkdir -p ${libexec_dir}" mkdir -p "${libexec_dir}"
run_step "mkdir -p ${site_packages_dir}" mkdir -p "${site_packages_dir}"
run_step "mkdir -p ${systemd_dir}" mkdir -p "${systemd_dir}"

echo "+ render packaging/operance.desktop.in -> ${desktop_entry_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed -e "s/__ENTRYPOINT__/$(escape_sed "${entrypoint}")/g" "${desktop_template}" > "${desktop_entry_path}"
fi

run_step "cp assets/icons/operance.svg ${icon_path}" cp "${icon_source_path}" "${icon_path}"

echo "+ render packaging/bin/operance-entrypoint.in -> ${entrypoint_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed \
        -e "s/__PYTHON_BIN__/$(escape_sed "${python_bin}")/g" \
        -e "s/__INSTALL_ROOT__/$(escape_sed "${install_root}")/g" \
        "${entrypoint_template}" > "${entrypoint_path}"
    chmod 0755 "${entrypoint_path}"
fi

echo "+ render packaging/etc/voice-loop.args.example.in -> ${voice_loop_args_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    cp "${voice_loop_args_template}" "${voice_loop_args_path}"
fi

echo "+ render packaging/bin/operance-voice-loop-launcher.in -> ${voice_loop_launcher_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed -e "s/__ENTRYPOINT__/$(escape_sed "${entrypoint}")/g" "${voice_loop_launcher_template}" > "${voice_loop_launcher_path}"
    chmod 0755 "${voice_loop_launcher_path}"
fi

run_step "cp pyproject.toml ${packaged_pyproject_path}" cp "${pyproject_source_path}" "${packaged_pyproject_path}"

echo "+ render packaged build metadata -> ${build_info_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    git_commit="$(git rev-parse HEAD 2>/dev/null || true)"
    git_commit_short="$(git rev-parse --short HEAD 2>/dev/null || true)"
    git_branch="$(git branch --show-current 2>/dev/null || true)"
    git_tag="$(git describe --tags --exact-match HEAD 2>/dev/null || true)"
    git_dirty="false"
    if [[ -n "$(git status --short 2>/dev/null || true)" ]]; then
        git_dirty="true"
    fi
    build_time="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    python3 - "${build_info_path}" <<PY
import json
import sys

payload = {
    "build_time": ${build_time@Q},
    "entrypoint": ${entrypoint@Q},
    "git_branch": ${git_branch@Q} or None,
    "git_commit": ${git_commit@Q} or None,
    "git_commit_short": ${git_commit_short@Q} or None,
    "git_dirty": ${git_dirty@Q} == "true",
    "git_tag": ${git_tag@Q} or None,
    "install_root": ${install_root@Q},
    "package_profile": ${bundle_profile@Q},
    "package_version": ${package_version@Q},
    "python_bin": ${python_bin@Q},
}
with open(sys.argv[1], "w", encoding="utf-8") as file_handle:
    json.dump(payload, file_handle, indent=2, sort_keys=True)
    file_handle.write("\\n")
PY
fi
run_step "cp -R src/operance/. ${site_packages_dir}" cp -R "${runtime_source_dir}/." "${site_packages_dir}"

if [[ "${bundle_profile}" != "base" ]]; then
    bundle_display="${bundle_python} ./scripts/bundle_python_runtime.py --profile ${bundle_profile} --output-dir ${site_packages_root}"
    bundle_args=("${bundle_python}" "./scripts/bundle_python_runtime.py" "--profile" "${bundle_profile}" "--output-dir" "${site_packages_root}")
    if [[ -n "${bundle_source_site_packages}" ]]; then
        bundle_display="${bundle_display} --source-site-packages ${bundle_source_site_packages}"
        bundle_args+=("--source-site-packages" "${bundle_source_site_packages}")
    fi
    run_step "${bundle_display}" "${bundle_args[@]}"
fi

echo "+ render packaging/systemd/operance-tray-packaged.service.in -> ${tray_service_unit_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed -e "s/__ENTRYPOINT__/$(escape_sed "${entrypoint}")/g" "${tray_service_template}" > "${tray_service_unit_path}"
fi

echo "+ render packaging/systemd/operance-voice-loop-packaged.service.in -> ${voice_loop_service_unit_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed -e "s/__ENTRYPOINT__/$(escape_sed "${entrypoint}")/g" "${voice_loop_service_template}" > "${voice_loop_service_unit_path}"
fi
