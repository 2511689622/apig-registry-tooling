#!/usr/bin/env bash
set -euo pipefail

openapi=""
apig=""
dry_run=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --openapi)
      openapi="${2:?--openapi requires a value}"
      shift 2
      ;;
    --apig)
      apig="${2:?--apig requires a value}"
      shift 2
      ;;
    --dry-run)
      dry_run="--dry-run"
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$openapi" || -z "$apig" ]]; then
  echo "usage: import-apig.sh --openapi <openapi.yaml> --apig <apig.yaml> [--dry-run]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$script_dir/validate-openapi.sh" "$openapi"
"$script_dir/validate-apig-config.sh" "$apig"
python "$script_dir/import_apig.py" --openapi "$openapi" --apig "$apig" $dry_run
