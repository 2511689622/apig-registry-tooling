#!/usr/bin/env python
import argparse
import os
import sys

import yaml


def expand(value):
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def load_apig_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    target = cfg["importTarget"]
    for key in ("region", "projectId", "instanceId", "groupId", "apiMode", "extendMode"):
        if key in target:
            target[key] = expand(target[key])
    return cfg


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def main():
    parser = argparse.ArgumentParser(description="Import OpenAPI YAML into Huawei Cloud APIG")
    parser.add_argument("--openapi", required=True)
    parser.add_argument("--apig", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_apig_config(args.apig)
    target = cfg["importTarget"]
    service = cfg.get("service", "")

    if args.dry_run:
        print(f"Dry-run APIG import: service={service} openapi={args.openapi} apig={args.apig}")
        print(
            "Target: "
            f"region={target.get('region')} "
            f"projectId={target.get('projectId')} "
            f"instanceId={target.get('instanceId')} "
            f"groupId={target.get('groupId')} "
            f"apiMode={target.get('apiMode', 'merge')} "
            f"extendMode={target.get('extendMode', 'merge')}"
        )
        print("Dry-run only; no Huawei Cloud API call was made.")
        return 0

    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkapig.v2 import ApigClient
    from huaweicloudsdkapig.v2.model.import_api_definitions_v2_request import ImportApiDefinitionsV2Request
    from huaweicloudsdkapig.v2.model.import_api_definitions_v2_request_body import ImportApiDefinitionsV2RequestBody
    from huaweicloudsdkapig.v2.region.apig_region import ApigRegion

    credentials = BasicCredentials(
        required_env("HUAWEICLOUD_SDK_AK"),
        required_env("HUAWEICLOUD_SDK_SK"),
        target["projectId"],
    )
    client = (
        ApigClient.new_builder()
        .with_credentials(credentials)
        .with_region(ApigRegion.value_of(target["region"]))
        .build()
    )

    request = ImportApiDefinitionsV2Request()
    request.instance_id = target["instanceId"]

    with open(args.openapi, "rb") as openapi_file:
        body = ImportApiDefinitionsV2RequestBody(
            is_create_group=target.get("isCreateGroup", False),
            group_id=target.get("groupId"),
            extend_mode=target.get("extendMode", "merge"),
            simple_mode=target.get("simpleMode", False),
            mock_mode=target.get("mockMode", False),
            api_mode=target.get("apiMode", "merge"),
            file_name=openapi_file,
        )
        request.body = body
        response = client.import_api_definitions_v2(request)

    success = getattr(response, "success", None) or []
    failure = getattr(response, "failure", None) or []
    ignore = getattr(response, "ignore", None) or []
    group_id = getattr(response, "group_id", "")

    print(
        f"Imported APIG OpenAPI: service={service} groupId={group_id} "
        f"success={len(success)} failure={len(failure)} ignored={len(ignore)}"
    )
    for item in failure:
        print(
            "Failure: "
            f"{getattr(item, 'method', '')} {getattr(item, 'path', '')} "
            f"{getattr(item, 'error_code', '')} {getattr(item, 'error_msg', '')}"
        )
    if failure:
        raise SystemExit(f"APIG import reported {len(failure)} failed API definitions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
