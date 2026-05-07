#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

spec_template="${repo_root}/packaging/rpm/operance.spec.in"

spec_dir="${repo_root}/dist/rpm"
output_dir="${repo_root}/dist/rpm"
output_dir_set=0
entrypoint="/usr/bin/operance"
version=""
bundle_profile="base"
bundle_python=""
bundle_source_site_packages=""
skip_build=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/build_rpm_package.sh [options]

Render an RPM spec tree for the current Operance base runtime, tray, and
voice-loop assets.

Options:
  --spec-dir PATH                 Top-level rpmbuild directory. Defaults to dist/rpm.
  --output-dir PATH               Output directory for the built .rpm artifact.
                                  Defaults to dist/rpm.
  --entrypoint PATH               Installed operance entrypoint path. Defaults to /usr/bin/operance.
  --version VALUE                 Package version. Defaults to the version from pyproject.toml.
  --bundle-profile PROFILE        Dependency bundle profile forwarded to render_packaged_assets.sh.
                                  Supported: base, mvp. Defaults to base.
  --bundle-python PATH            Python executable used for non-base runtime bundling.
  --bundle-source-site-packages PATH
                                  Override the source site-packages directory for runtime bundling.
  --skip-build                    Render the RPM spec tree without calling rpmbuild.
  --dry-run                       Print the build steps without executing them.
  -h, --help                      Show this help text.
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
        --spec-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--spec-dir requires a path"
            fi
            spec_dir="$1"
            ;;
        --output-dir)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--output-dir requires a path"
            fi
            output_dir="$1"
            output_dir_set=1
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

spec_dir="${spec_dir%/}"
if [[ "${output_dir_set}" -eq 0 ]]; then
    output_dir="${spec_dir}"
fi
output_dir="${output_dir%/}"
sources_dir="${spec_dir}/SOURCES"
assets_dir="${sources_dir}/packaged-assets"
spec_path="${spec_dir}/operance.spec"
source_tarball="${sources_dir}/operance-packaged-assets-${version}.tar.gz"
built_package_glob="${spec_dir}/RPMS/noarch/operance-${version}-*.noarch.rpm"
package_path="${output_dir}/operance-${version}-1.noarch.rpm"

escape_sed() {
    printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

run_step "mkdir -p ${sources_dir}" mkdir -p "${sources_dir}"

echo "+ render packaging/rpm/operance.spec.in -> ${spec_path}"
if [[ "${dry_run}" -eq 0 ]]; then
    sed \
        -e "s/__VERSION__/$(escape_sed "${version}")/g" \
        -e "s#__ENTRYPOINT__#$(escape_sed "${entrypoint}")#g" \
        "${spec_template}" > "${spec_path}"
fi

render_display="./scripts/render_packaged_assets.sh --output-dir ${assets_dir} --entrypoint ${entrypoint} --bundle-profile ${bundle_profile}"
render_args=("./scripts/render_packaged_assets.sh" "--output-dir" "${assets_dir}" "--entrypoint" "${entrypoint}" "--bundle-profile" "${bundle_profile}")
if [[ -n "${bundle_python}" ]]; then
    render_display="${render_display} --bundle-python ${bundle_python}"
    render_args+=("--bundle-python" "${bundle_python}")
fi
if [[ -n "${bundle_source_site_packages}" ]]; then
    render_display="${render_display} --bundle-source-site-packages ${bundle_source_site_packages}"
    render_args+=("--bundle-source-site-packages" "${bundle_source_site_packages}")
fi
if [[ "${dry_run}" -eq 1 ]]; then
    render_args+=("--dry-run")
fi
run_step "${render_display}" "${render_args[@]}"

run_step "tar -czf ${source_tarball} -C ${sources_dir} packaged-assets" tar -czf "${source_tarball}" -C "${sources_dir}" packaged-assets

if [[ "${skip_build}" -eq 0 ]]; then
    run_step "rpmbuild --define _topdir ${spec_dir} -bb ${spec_path}" rpmbuild --define "_topdir ${spec_dir}" -bb "${spec_path}"
    run_step "mkdir -p ${output_dir}" mkdir -p "${output_dir}"
    built_package_path="${built_package_glob}"
    if [[ "${dry_run}" -eq 0 ]]; then
        shopt -s nullglob
        built_packages=("${spec_dir}/RPMS/noarch/operance-${version}-"*.noarch.rpm)
        shopt -u nullglob
        if [[ "${#built_packages[@]}" -ne 1 ]]; then
            fail "expected exactly one built RPM matching ${built_package_glob}"
        fi
        built_package_path="${built_packages[0]}"
    fi
    run_step "cp ${built_package_glob} ${package_path}" cp "${built_package_path}" "${package_path}"
fi
