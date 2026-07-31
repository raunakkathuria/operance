#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

container_runtime="docker"
image="fedora:41"
dry_run=0
keep_container=0

usage() {
    cat <<'EOF'
Usage: scripts/run_fedora_container_smoke.sh [options]

Build and install the Fedora RPM inside a container, then check the installed
package responds. This validates the packaging path from any host, including
macOS, without needing a Fedora machine.

This does not need systemd or a privileged container, because the RPM spec
installs its systemd unit files as data and has no install scriptlets.

Session-dependent behavior such as KWin window control, the tray, clipboard,
input, and audio cannot be verified here. Those need a real Plasma Wayland
session. See docs/contributing/development-environments.md.

Options:
  --runtime NAME    Container runtime to use. Defaults to docker.
  --image NAME      Container image to use. Defaults to fedora:41.
  --keep            Keep the container after the run for inspection.
  --dry-run         Print the steps without executing them.
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
        --runtime)
            [[ $# -ge 2 ]] || fail "--runtime requires a value"
            container_runtime="$2"
            shift 2
            ;;
        --image)
            [[ $# -ge 2 ]] || fail "--image requires a value"
            image="$2"
            shift 2
            ;;
        --keep)
            keep_container=1
            shift
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"
            ;;
    esac
done

# The container build intentionally installs only the base dev extra. Installing
# the ui extra pulls in PySide6, which fails tray tests when no display exists.
container_script='set -euo pipefail
dnf install -y -q python3 python3-pip rpm-build rpmdevtools >/dev/null
cp -r /src /work
cd /work
bash scripts/build_rpm_package.sh >/dev/null
rpm_path="$(find dist/rpm -name "operance-*.noarch.rpm" | head -1)"
test -n "${rpm_path}" || { echo "no rpm artifact produced" >&2; exit 1; }
echo "built ${rpm_path}"
dnf install -y -q "./${rpm_path}" >/dev/null
operance --version
operance --doctor >/dev/null
test -f /usr/lib/systemd/user/operance-tray.service
test -f /usr/lib/systemd/user/operance-voice-loop.service
echo "installed package responds and unit files are present"'

remove_flag="--rm"
if [[ "${keep_container}" -eq 1 ]]; then
    remove_flag=""
fi

if [[ "${dry_run}" -eq 1 ]]; then
    echo "+ ${container_runtime} run ${remove_flag} -v ${repo_root}:/src:ro ${image} bash -lc '<build, install, verify>'"
    exit 0
fi

command -v "${container_runtime}" >/dev/null 2>&1 \
    || fail "${container_runtime} not found. Install it or pass --runtime."

run_step "${container_runtime} run ${remove_flag} -v ${repo_root}:/src:ro ${image} bash -lc '<build, install, verify>'" \
    "${container_runtime}" run ${remove_flag} \
    -v "${repo_root}:/src:ro" \
    "${image}" \
    bash -lc "${container_script}"

echo "Fedora container packaging smoke passed."
