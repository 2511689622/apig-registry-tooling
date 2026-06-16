#!/usr/bin/env python
import sys
import yaml

FIELDS = {"openapi", "apig", "source-repo", "source-branch", "source-openapi"}

if len(sys.argv) != 4:
    raise SystemExit("usage: target-paths.py <service> <community> <openapi|apig|source-repo|source-branch|source-openapi>")

service_name, community_name, field = sys.argv[1], sys.argv[2], sys.argv[3]
if field not in FIELDS:
    raise SystemExit(f"unknown field: {field}")

with open("catalog.yaml", "r", encoding="utf-8") as f:
    catalog = yaml.safe_load(f)

for service in catalog.get("services", []):
    if service.get("name") != service_name:
        continue
    for community in service.get("communities", []):
        if community.get("name") != community_name:
            continue
        if field == "openapi":
            print(community["registry"]["openapi"])
        elif field == "apig":
            print(community["registry"]["apig"])
        elif field == "source-repo":
            print(community["source"]["repo"])
        elif field == "source-branch":
            print(community["source"].get("branch", "main"))
        elif field == "source-openapi":
            print(community["source"]["openapi"])
        raise SystemExit(0)
raise SystemExit(f"target not found in catalog.yaml: {service_name}/{community_name}")
