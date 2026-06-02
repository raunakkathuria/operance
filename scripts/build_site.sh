#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

output_dir="${repo_root}/dist/pages"

rm -rf "${output_dir}"
mkdir -p "${output_dir}/assets/icons"

cp "${repo_root}/site/index.html" "${repo_root}/site/styles.css" "${output_dir}/"
cp "${repo_root}/assets/icons/operance.svg" "${output_dir}/assets/icons/operance.svg"
cp "${repo_root}/assets/icons/favicon.ico" "${output_dir}/favicon.ico"

python3 - "${output_dir}/index.html" <<'PY'
from pathlib import Path
import sys

index = Path(sys.argv[1])
html = index.read_text(encoding="utf-8")
html = html.replace("../assets/icons/operance.svg", "assets/icons/operance.svg")
index.write_text(html, encoding="utf-8")
if "../assets/icons/operance.svg" in html:
    raise SystemExit("deployment artifact still points outside the Pages root")
PY

echo "Built site artifact at ${output_dir}"
