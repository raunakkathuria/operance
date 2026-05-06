#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
dry_run=0
supported_commands=0
supported_commands_available_only=0
support_snapshot=0
support_snapshot_out=""
support_bundle=0
support_bundle_out=""
extra_args=()

usage() {
    cat <<'EOF'
Usage: scripts/run_mvp.sh [options] [-- extra operance.cli args]

Launch the preferred current Operance MVP path.

Options:
  --python PATH   Python executable to use. Defaults to .venv/bin/python.
  --dry-run       Print the MVP launch command without executing it.
  --supported-commands
                  Print the supported-command catalog command instead of launching the MVP path.
  --supported-commands-available-only
                  When printing supported commands, filter to commands that are runnable now.
  --support-snapshot
                  Print the support-snapshot command instead of launching the MVP path.
  --support-snapshot-out PATH
                  Forward an output path to --support-snapshot.
  --support-bundle
                  Print the support-bundle command instead of launching the MVP path.
  --support-bundle-out PATH
                  Forward an output path to --support-bundle.
  -h, --help      Show this help text.

Any arguments after `--` are forwarded to `operance.cli` after `--mvp-launch`.
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
        --dry-run)
            dry_run=1
            ;;
        --supported-commands)
            supported_commands=1
            ;;
        --supported-commands-available-only)
            supported_commands_available_only=1
            ;;
        --support-snapshot)
            support_snapshot=1
            ;;
        --support-snapshot-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-snapshot-out requires a path"
            fi
            support_snapshot_out="$1"
            ;;
        --support-bundle)
            support_bundle=1
            ;;
        --support-bundle-out)
            shift
            if [[ $# -eq 0 ]]; then
                fail "--support-bundle-out requires a path"
            fi
            support_bundle_out="$1"
            ;;
        --)
            shift
            extra_args=("$@")
            break
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

if [[ ! -x "${python_bin}" ]] && [[ "${dry_run}" -eq 0 ]]; then
    fail "python executable not found: ${python_bin}"
fi

if [[ -n "${support_snapshot_out}" ]] && [[ "${support_snapshot}" -ne 1 ]]; then
    fail "--support-snapshot-out requires --support-snapshot"
fi
if [[ -n "${support_bundle_out}" ]] && [[ "${support_bundle}" -ne 1 ]]; then
    fail "--support-bundle-out requires --support-bundle"
fi
if [[ "${supported_commands_available_only}" -eq 1 ]] && [[ "${supported_commands}" -ne 1 ]]; then
    fail "--supported-commands-available-only requires --supported-commands"
fi

cd "${repo_root}"

if [[ "${support_bundle}" -eq 1 ]]; then
    display="${python_bin} -m operance.cli --support-bundle"
    command=("${python_bin}" "-m" "operance.cli" "--support-bundle")
    if [[ -n "${support_bundle_out}" ]]; then
        display="${display} --support-bundle-out ${support_bundle_out}"
        command+=("--support-bundle-out" "${support_bundle_out}")
    fi
elif [[ "${support_snapshot}" -eq 1 ]]; then
    display="${python_bin} -m operance.cli --support-snapshot"
    command=("${python_bin}" "-m" "operance.cli" "--support-snapshot")
    if [[ -n "${support_snapshot_out}" ]]; then
        display="${display} --support-snapshot-out ${support_snapshot_out}"
        command+=("--support-snapshot-out" "${support_snapshot_out}")
    fi
elif [[ "${supported_commands}" -eq 1 ]]; then
    display="${python_bin} -m operance.cli --supported-commands"
    command=("${python_bin}" "-m" "operance.cli" "--supported-commands")
    if [[ "${supported_commands_available_only}" -eq 1 ]]; then
        display="${display} --supported-commands-available-only"
        command+=("--supported-commands-available-only")
    fi
else
    display="${python_bin} -m operance.cli --mvp-launch"
    command=("${python_bin}" "-m" "operance.cli" "--mvp-launch")
fi
for extra_arg in "${extra_args[@]}"; do
    display="${display} ${extra_arg}"
    command+=("${extra_arg}")
done

run_step "${display}" "${command[@]}"
