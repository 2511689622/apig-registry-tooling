#!/usr/bin/env python
import argparse
import yaml

parser = argparse.ArgumentParser(description="List enabled APIG registry targets")
parser.add_argument("--service", default="all")
parser.add_argument("--community", default="all")
parser.add_argument("--catalog", default="catalog.yaml")
args = parser.parse_args()

with open(args.catalog, "r", encoding="utf-8") as f:
    catalog = yaml.safe_load(f)

for service in catalog.get("services", []):
    service_name = service["name"]
    if not service.get("enabled", True):
        continue
    if args.service != "all" and args.service != service_name:
        continue
    for community in service.get("communities", []):
        community_name = community["name"]
        if not community.get("enabled", True):
            continue
        if args.community != "all" and args.community != community_name:
            continue
        print(f"{service_name} {community_name}")
