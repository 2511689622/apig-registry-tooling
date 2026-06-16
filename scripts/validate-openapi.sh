#!/usr/bin/env bash
set -euo pipefail

file="${1:?usage: validate-openapi.sh <openapi.yaml>}"

python - "$file" <<'PY'
import sys
import yaml

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f)

if not isinstance(doc, dict):
    raise SystemExit(f"{path}: OpenAPI document must be a mapping")
if doc.get("openapi") != "3.0.3":
    raise SystemExit(f"{path}: Huawei APIG import YAML must use openapi: 3.0.3")
info = doc.get("info")
if not isinstance(info, dict) or not info.get("title") or not info.get("version"):
    raise SystemExit(f"{path}: info.title and info.version are required")
paths = doc.get("paths")
if not isinstance(paths, dict) or not paths:
    raise SystemExit(f"{path}: paths is required")
print(f"validated OpenAPI: {path}")
PY

python scripts/validate_huawei_apig_openapi.py "$file"
