#!/usr/bin/env bash
set -euo pipefail

destination="${1:-requirements.txt}"
temporary="$(mktemp)"
trap 'rm -f "$temporary"' EXIT

read -r -a uv_command <<< "${BBRIPPER_UV:-uv}"
if ! uv_version="$("${uv_command[@]}" --version 2>/dev/null)"; then
    printf '%s\n' \
        "error: requirements export requires uv 0.12.24; unable to run ${uv_command[*]}" \
        >&2
    exit 1
fi
if [[ ! "$uv_version" =~ ^uv\ 0\.12\.24(\ |$) ]]; then
    printf '%s\n' \
        "error: requirements export requires uv 0.12.24; found $uv_version" \
        "run with BBRIPPER_UV='uvx uv@0.12.24' scripts/export_requirements.sh" \
        >&2
    exit 1
fi

"${uv_command[@]}" export \
    --locked \
    --format requirements-txt \
    --no-dev \
    --no-emit-project \
    --no-header > "$temporary"

{
    printf '%s\n' '# Generated from uv.lock; do not edit by hand.'
    printf '%s\n' '# Regenerate with: scripts/export_requirements.sh'
    cat "$temporary"
} > "$destination"
