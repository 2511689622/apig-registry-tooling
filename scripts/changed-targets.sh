#!/usr/bin/env bash
set -euo pipefail

base_ref="${1:-origin/main}"

if git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
  files="$(git diff --name-only "$base_ref"...HEAD)"
else
  files="$(git diff --name-only HEAD~1...HEAD)"
fi

printf '%s\n' "$files" \
  | awk -F/ '/^services\/[^/]+\/communities\/[^/]+\// { print $2 " " $4 }' \
  | sort -u
