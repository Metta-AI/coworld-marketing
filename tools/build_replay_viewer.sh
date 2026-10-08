#!/usr/bin/env bash
# Coworld build hook: recreate the static replay viewer bundle from the game's own jury page.
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-}"
if [[ -z "${output_dir}" ]]; then
  echo "usage: tools/build_replay_viewer.sh /absolute/output/dir" >&2
  exit 1
fi
if [[ "${output_dir}" != /* && ! "${output_dir}" =~ ^[A-Za-z]:[\\/] ]] \
  || [[ "${output_dir}" == "/" || "${output_dir}" == "${repo_dir}" ]]; then
  echo "unsafe bundle output: ${output_dir}" >&2
  exit 1
fi

rm -rf "${output_dir}"
mkdir -p "${output_dir}"
cp "${repo_dir}/videomarketing/static/jury.html" "${output_dir}/index.html"
test -s "${output_dir}/index.html"
echo "replay viewer bundle written to ${output_dir}"
