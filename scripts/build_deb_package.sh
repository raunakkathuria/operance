#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

control_template="${repo_root}/packaging/deb/control.in"

staging_dir="${repo_root}/dist/deb/operance"
output_dir="${repo_root}/dist/deb"
entrypoint="/usr/bin/operance"
version=""
skip_build=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/build_deb_package.sh [options]

Render a Debian package staging tree for the current Operance base runtime,
tray, and voice-loop assets.

Options:
  --staging-dir PATH  Package staging directory.
  --output-dir PATH   Output directory for the .deb artifact.
  --entrypoint PATH   Installed operance entrypoint path. Defaults to /usr/bin/operance.
  --version VALUE     Package version. Defaults to the version from pyproject.toml.
  --skip-build        Render the staging tree without calling dpkg-deb.
  --dry-run           Print the build steps without executing them.
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
        --staging-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--staging-dir requires a path"
            fi
            staging_dir="$1"
            ;;
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
        --version)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--version requires a value"
            fi
            version="$1"
            ;;
        --skip-build)
            skip_build=1
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

if [[ -z "${version}" ]]; then
    version="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)"
fi
if [[ -z "${version}" ]]; then
    fail "could not determine version from pyproject.toml"
fi

staging_dir="${staging_dir%/}"
output_dir="${output_dir%/}"
control_dir="${staging_dir}/DEBIAN"
config_dir="${staging_dir}/etc/operance"
entrypoint_path="${staging_dir}${entrypoint}"
entrypoint_dir="$(dirname "${entrypoint_path}")"
applications_dir="${staging_dir}/usr/share/applications"
lib_dir="${staging_dir}/usr/lib/operance"
site_packages_dir="${lib_dir}/site-packages/operance"
systemd_dir="${staging_dir}/usr/lib/systemd/user"
assets_dir="${staging_dir}/.rendered"
control_path="${control_dir}/control"
packaged_entrypoint_path="${assets_dir}/bin/operance"
voice_loop_args_example_path="${config_dir}/voice-loop.args.example"
desktop_entry_path="${applications_dir}/operance.desktop"
packaged_pyproject_path="${lib_dir}/pyproject.toml"
packaged_runtime_source_dir="${assets_dir}/lib/operance/site-packages/operance"
voice_loop_launcher_path="${lib_dir}/voice-loop-launcher"
service_unit_path="${systemd_dir}/operance-tray.service"
voice_loop_service_unit_path="${systemd_dir}/operance-voice-loop.service"
package_path="${output_dir}/operance_${version}_all.deb"

escape_sed() {
    printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

run_step "mkdir -p ${control_dir}" mkdir -p "${control_dir}"
run_step "mkdir -p ${config_dir}" mkdir -p "${config_dir}"
run_step "mkdir -p ${entrypoint_dir}" mkdir -p "${entrypoint_dir}"
run_step "mkdir -p ${applications_dir}" mkdir -p "${applications_dir}"
run_step "mkdir -p ${lib_dir}" mkdir -p "${lib_dir}"
run_step "mkdir -p ${site_packages_dir}" mkdir -p "${site_packages_dir}"
run_step "mkdir -p ${systemd_dir}" mkdir -p "${systemd_dir}"

echo "+ render packaging/deb/control.in -> ${control_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed -e "s/__VERSION__/$(escape_sed "${version}")/g" "${control_template}" > "${control_path}"
fi

render_display="./scripts/render_packaged_assets.sh --output-dir ${assets_dir} --entrypoint ${entrypoint}"
render_args=("./scripts/render_packaged_assets.sh" "--output-dir" "${assets_dir}" "--entrypoint" "${entrypoint}")
if [[ "${dry_run}" -eq 1 ]]; then
    render_args+=("--dry-run")
fi
run_step "${render_display}" "${render_args[@]}"

run_step "cp ${packaged_entrypoint_path} ${entrypoint_path}" cp "${packaged_entrypoint_path}" "${entrypoint_path}"
run_step "cp ${assets_dir}/etc/operance/voice-loop.args.example ${voice_loop_args_example_path}" cp "${assets_dir}/etc/operance/voice-loop.args.example" "${voice_loop_args_example_path}"
run_step "cp ${assets_dir}/applications/operance.desktop ${desktop_entry_path}" cp "${assets_dir}/applications/operance.desktop" "${desktop_entry_path}"
run_step "cp ${assets_dir}/lib/operance/pyproject.toml ${packaged_pyproject_path}" cp "${assets_dir}/lib/operance/pyproject.toml" "${packaged_pyproject_path}"
run_step "cp -R ${packaged_runtime_source_dir}/. ${site_packages_dir}" cp -R "${packaged_runtime_source_dir}/." "${site_packages_dir}"
run_step "cp ${assets_dir}/lib/operance/voice-loop-launcher ${voice_loop_launcher_path}" cp "${assets_dir}/lib/operance/voice-loop-launcher" "${voice_loop_launcher_path}"
run_step "cp ${assets_dir}/systemd/operance-tray.service ${service_unit_path}" cp "${assets_dir}/systemd/operance-tray.service" "${service_unit_path}"
run_step "cp ${assets_dir}/systemd/operance-voice-loop.service ${voice_loop_service_unit_path}" cp "${assets_dir}/systemd/operance-voice-loop.service" "${voice_loop_service_unit_path}"

if [[ "${skip_build}" -eq 0 ]]; then
    run_step "dpkg-deb --build ${staging_dir} ${package_path}" dpkg-deb --build "${staging_dir}" "${package_path}"
fi
