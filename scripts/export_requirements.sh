#!/usr/bin/env bash
set -euo pipefail

destination="${1:-requirements.txt}"
temporary="$(mktemp)"
trap 'rm -f "$temporary"' EXIT

uv export \
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
