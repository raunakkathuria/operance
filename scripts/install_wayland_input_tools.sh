#!/usr/bin/env bash
set -euo pipefail

installer="auto"
clipboard_only=0
text_input_only=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: scripts/install_wayland_input_tools.sh [options]

Install the Linux Wayland clipboard and text-input tools used by Operance.

Options:
  --installer NAME   Package installer to use. Supported: auto, apt, dnf.
                     Defaults to auto.
  --clipboard-only   Install only wl-clipboard.
  --text-input-only  Install only wtype.
  --dry-run          Print the install command without executing it.
  -h, --help         Show this help text.
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
        --clipboard-only)
            clipboard_only=1
            ;;
        --text-input-only)
            text_input_only=1
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

if [[ "${clipboard_only}" -eq 1 && "${text_input_only}" -eq 1 ]]; then
    fail "--clipboard-only and --text-input-only cannot be used together"
fi

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

packages=()
if [[ "${clipboard_only}" -eq 1 ]]; then
    packages=("wl-clipboard")
elif [[ "${text_input_only}" -eq 1 ]]; then
    packages=("wtype")
else
    packages=("wl-clipboard" "wtype")
fi

display="sudo ${installer} install -y ${packages[*]}"
run_step "${display}" sudo "${installer}" install -y "${packages[@]}"
