#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

python_bin=".venv/bin/python"
dry_run=0
keep_fixture=0

usage() {
    cat <<'EOF'
Usage: scripts/run_live_command_smoke.sh [options]

Run live-adapter command smoke checks against controlled fixtures.

Options:
  --python PATH    Python executable to use. Defaults to .venv/bin/python.
  --dry-run        Print the smoke commands without executing them.
  --keep-fixture   Keep the temporary desktop fixture for debugging.
  -h, --help       Show this help text.
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

assert_transcript_success() {
    local payload="$1"
    local transcript="$2"

    "${python_bin}" - "${payload}" "${transcript}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected_transcript = sys.argv[2]

if payload.get("transcript") != expected_transcript:
    raise SystemExit(f"unexpected transcript: {payload.get('transcript')!r}")
if payload.get("status") != "success":
    raise SystemExit(f"transcript failed: {payload}")
if payload.get("simulated") is not False:
    raise SystemExit(f"expected live mode payload, got: {payload}")
PY
}

assert_transcript_sequence_success() {
    local payload="$1"
    local command_transcript="$2"

    "${python_bin}" - "${payload}" "${command_transcript}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected_command = sys.argv[2]
expected_transcripts = [expected_command, "confirm"]
expected_statuses = ["awaiting_confirmation", "success"]

if payload.get("total_transcripts") != 2:
    raise SystemExit(f"expected two transcript results, got: {payload}")

results = payload.get("results")
if not isinstance(results, list) or len(results) != 2:
    raise SystemExit(f"expected two transcript results, got: {payload}")

for index, result in enumerate(results):
    if result.get("transcript") != expected_transcripts[index]:
        raise SystemExit(f"unexpected transcript sequence: {payload}")
    if result.get("status") != expected_statuses[index]:
        raise SystemExit(f"unexpected transcript status sequence: {payload}")
    if result.get("simulated") is not False:
        raise SystemExit(f"expected live mode payload, got: {payload}")
PY
}

write_transcript_fixture() {
    local fixture_path="$1"
    local command_transcript="$2"

    echo "+ write ${fixture_path}"
    if [[ "${dry_run}" -eq 0 ]]; then
        printf '%s\nconfirm\n' "${command_transcript}" > "${fixture_path}"
    fi
}

run_live_transcript() {
    local desktop_dir="$1"
    local transcript="$2"
    local display="OPERANCE_DEVELOPER_MODE=0 ${python_bin} -m operance.cli --desktop-dir ${desktop_dir} --transcript \"${transcript}\""

    echo "+ ${display}"
    if [[ "${dry_run}" -eq 1 ]]; then
        return
    fi

    local output
    output="$(
        OPERANCE_DEVELOPER_MODE=0 "${python_bin}" -m operance.cli \
            --desktop-dir "${desktop_dir}" \
            --transcript "${transcript}"
    )"
    printf '%s\n' "${output}"
    assert_transcript_success "$(printf '%s\n' "${output}" | tail -n 1)" "${transcript}"
}

run_live_confirmation_transcripts() {
    local desktop_dir="$1"
    local fixture_path="$2"
    local command_transcript="$3"
    local display="OPERANCE_DEVELOPER_MODE=0 ${python_bin} -m operance.cli --desktop-dir ${desktop_dir} --transcript-file ${fixture_path}"

    echo "+ ${display}"
    if [[ "${dry_run}" -eq 1 ]]; then
        return
    fi

    local output
    output="$(
        OPERANCE_DEVELOPER_MODE=0 "${python_bin}" -m operance.cli \
            --desktop-dir "${desktop_dir}" \
            --transcript-file "${fixture_path}"
    )"
    printf '%s\n' "${output}"
    assert_transcript_sequence_success "$(printf '%s\n' "${output}" | tail -n 1)" "${command_transcript}"
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
        --keep-fixture)
            keep_fixture=1
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

cd "${repo_root}"

if [[ "${dry_run}" -eq 1 ]]; then
    run_step 'tmp_dir="$(mktemp -d)"' true
    run_step 'mkdir -p "${tmp_dir}/Desktop"' true
    run_step 'touch "${tmp_dir}/Desktop/operance-recent-smoke.txt"' true
    run_live_transcript '${tmp_dir}/Desktop' "show a notification saying live smoke passed"
    run_live_transcript '${tmp_dir}/Desktop' "show recent files"
    run_live_transcript '${tmp_dir}/Desktop' "create folder on desktop called projects"
    run_step 'test -d "${tmp_dir}/Desktop/projects"' true
    write_transcript_fixture '${tmp_dir}/delete-folder.txt' "delete folder on desktop called projects"
    run_live_confirmation_transcripts '${tmp_dir}/Desktop' '${tmp_dir}/delete-folder.txt' "delete folder on desktop called projects"
    run_step 'test ! -e "${tmp_dir}/Desktop/projects"' true
    run_step 'touch "${tmp_dir}/Desktop/notes.txt"' true
    write_transcript_fixture '${tmp_dir}/delete-file.txt' "delete file on desktop called notes.txt"
    run_live_confirmation_transcripts '${tmp_dir}/Desktop' '${tmp_dir}/delete-file.txt' "delete file on desktop called notes.txt"
    run_step 'test ! -e "${tmp_dir}/Desktop/notes.txt"' true
    run_step 'mkdir -p "${tmp_dir}/Desktop/projects"' true
    write_transcript_fixture '${tmp_dir}/rename-folder.txt' "rename folder on desktop from projects to archive"
    run_live_confirmation_transcripts '${tmp_dir}/Desktop' '${tmp_dir}/rename-folder.txt' "rename folder on desktop from projects to archive"
    run_step 'test -d "${tmp_dir}/Desktop/archive"' true
    run_step 'test ! -e "${tmp_dir}/Desktop/projects"' true
    run_step 'rm -rf "${tmp_dir}/Desktop/archive"' true
    run_step 'mkdir -p "${tmp_dir}/Desktop/projects" "${tmp_dir}/Desktop/archive"' true
    write_transcript_fixture '${tmp_dir}/move-folder.txt' "move folder on desktop called projects to archive"
    run_live_confirmation_transcripts '${tmp_dir}/Desktop' '${tmp_dir}/move-folder.txt' "move folder on desktop called projects to archive"
    run_step 'test -d "${tmp_dir}/Desktop/archive/projects"' true
    run_step 'test ! -e "${tmp_dir}/Desktop/projects"' true
    run_step 'rm -rf "${tmp_dir}"' true
    exit 0
fi

tmp_dir="$(mktemp -d)"
if [[ "${keep_fixture}" -eq 0 ]]; then
    trap 'rm -rf "${tmp_dir}"' EXIT
fi

desktop_dir="${tmp_dir}/Desktop"
run_step "mkdir -p ${desktop_dir}" mkdir -p "${desktop_dir}"
run_step "touch ${desktop_dir}/operance-recent-smoke.txt" touch "${desktop_dir}/operance-recent-smoke.txt"
run_live_transcript "${desktop_dir}" "show a notification saying live smoke passed"
run_live_transcript "${desktop_dir}" "show recent files"
run_live_transcript "${desktop_dir}" "create folder on desktop called projects"
run_step "test -d ${desktop_dir}/projects" test -d "${desktop_dir}/projects"

delete_folder_fixture="${tmp_dir}/delete-folder.txt"
write_transcript_fixture "${delete_folder_fixture}" "delete folder on desktop called projects"
run_live_confirmation_transcripts "${desktop_dir}" "${delete_folder_fixture}" "delete folder on desktop called projects"
run_step "test ! -e ${desktop_dir}/projects" test ! -e "${desktop_dir}/projects"

run_step "touch ${desktop_dir}/notes.txt" touch "${desktop_dir}/notes.txt"
delete_file_fixture="${tmp_dir}/delete-file.txt"
write_transcript_fixture "${delete_file_fixture}" "delete file on desktop called notes.txt"
run_live_confirmation_transcripts "${desktop_dir}" "${delete_file_fixture}" "delete file on desktop called notes.txt"
run_step "test ! -e ${desktop_dir}/notes.txt" test ! -e "${desktop_dir}/notes.txt"

run_step "mkdir -p ${desktop_dir}/projects" mkdir -p "${desktop_dir}/projects"
rename_fixture="${tmp_dir}/rename-folder.txt"
write_transcript_fixture "${rename_fixture}" "rename folder on desktop from projects to archive"
run_live_confirmation_transcripts "${desktop_dir}" "${rename_fixture}" "rename folder on desktop from projects to archive"
run_step "test -d ${desktop_dir}/archive" test -d "${desktop_dir}/archive"
run_step "test ! -e ${desktop_dir}/projects" test ! -e "${desktop_dir}/projects"

run_step "rm -rf ${desktop_dir}/archive" rm -rf "${desktop_dir}/archive"
run_step "mkdir -p ${desktop_dir}/projects ${desktop_dir}/archive" mkdir -p "${desktop_dir}/projects" "${desktop_dir}/archive"
move_fixture="${tmp_dir}/move-folder.txt"
write_transcript_fixture "${move_fixture}" "move folder on desktop called projects to archive"
run_live_confirmation_transcripts "${desktop_dir}" "${move_fixture}" "move folder on desktop called projects to archive"
run_step "test -d ${desktop_dir}/archive/projects" test -d "${desktop_dir}/archive/projects"
run_step "test ! -e ${desktop_dir}/projects" test ! -e "${desktop_dir}/projects"

if [[ "${keep_fixture}" -eq 1 ]]; then
    echo "Kept live command smoke fixture: ${tmp_dir}"
fi
