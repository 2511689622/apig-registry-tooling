#!/usr/bin/env bash
set -euo pipefail

file="${1:?usage: validate-apig-config.sh <apig.yaml>}"

python - "$file" <<'PY'
import re
import sys
import yaml

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f)

if not isinstance(doc, dict):
    raise SystemExit(f"{path}: APIG config must be a mapping")
if not doc.get("service"):
    raise SystemExit(f"{path}: service is required")
if not doc.get("community"):
    raise SystemExit(f"{path}: community is required")

target = doc.get("importTarget")
if not isinstance(target, dict):
    raise SystemExit(f"{path}: importTarget is required")
for field in ("region", "projectId", "instanceId"):
    if not target.get(field):
        raise SystemExit(f"{path}: importTarget.{field} is required")
if not target.get("isCreateGroup") and not target.get("groupId"):
    raise SystemExit(f"{path}: importTarget.groupId is required when isCreateGroup is false")
for field in ("apiMode", "extendMode"):
    if target.get(field, "merge") not in ("merge", "override"):
        raise SystemExit(f"{path}: importTarget.{field} must be merge or override")

secret_re = re.compile(r"(?i)(password|secret|token|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{6,})")
def scan(value, loc="root"):
    if isinstance(value, dict):
        for k, v in value.items():
            scan(v, f"{loc}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            scan(v, f"{loc}[{i}]")
    elif isinstance(value, str) and secret_re.search(value):
        raise SystemExit(f"{path}: possible credential in {loc}")
scan(doc)
print(f"validated APIG config: {path}")
PY
