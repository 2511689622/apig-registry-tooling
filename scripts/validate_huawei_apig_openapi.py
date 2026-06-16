#!/usr/bin/env python
import re
import sys
import yaml

METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
INTERNAL_PREFIXES = ("/debug", "/metrics", "/internal", "/admin")
PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")


def fail(path, message):
    raise SystemExit(f"{path}: {message}")


def operations(paths):
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() in METHODS:
                yield path, method.lower(), op


def require_mapping(value, path, message):
    if not isinstance(value, dict):
        fail(path, message)
    return value


def validate_backend(doc_path, api_path, method, op):
    backend = require_mapping(
        op.get("x-apigateway-backend"),
        doc_path,
        f"{method.upper()} {api_path} missing x-apigateway-backend",
    )
    backend_type = backend.get("type")
    if backend_type not in ("HTTP", "FUNCTION"):
        fail(doc_path, f"{method.upper()} {api_path} x-apigateway-backend.type must be HTTP or FUNCTION")

    if backend_type == "FUNCTION":
        endpoint = require_mapping(
            backend.get("functionEndpoints"),
            doc_path,
            f"{method.upper()} {api_path} FUNCTION backend requires functionEndpoints",
        )
        for field in ("function-urn", "invocation-type", "network-type", "timeout", "version"):
            if field not in endpoint or endpoint[field] in (None, ""):
                fail(doc_path, f"{method.upper()} {api_path} functionEndpoints.{field} is required")

    if backend_type == "HTTP":
        endpoint = require_mapping(
            backend.get("httpEndpoints"),
            doc_path,
            f"{method.upper()} {api_path} HTTP backend requires httpEndpoints",
        )
        for field in ("address", "scheme", "method", "path", "timeout"):
            if field not in endpoint or endpoint[field] in (None, ""):
                fail(doc_path, f"{method.upper()} {api_path} httpEndpoints.{field} is required")

    mapped_path_params = set()
    for param in backend.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        if str(param.get("in", "")).upper() == "PATH" and param.get("origin") == "REQUEST":
            mapped_path_params.add(param.get("value"))
    for name in PATH_PARAM_RE.findall(api_path):
        if name not in mapped_path_params:
            fail(doc_path, f"{method.upper()} {api_path} missing backend PATH mapping for {{{name}}}")


def validate_parameters(doc_path, api_path, method, op):
    declared_path_params = set()
    for param in op.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        if param.get("in") == "path":
            if not param.get("required"):
                fail(doc_path, f"{method.upper()} {api_path} path parameter {param.get('name')} must be required")
            declared_path_params.add(param.get("name"))
        if "schema" not in param:
            fail(doc_path, f"{method.upper()} {api_path} parameter {param.get('name')} missing schema")
        if "x-apigateway-pass-through" not in param:
            fail(doc_path, f"{method.upper()} {api_path} parameter {param.get('name')} missing x-apigateway-pass-through")
        if "x-apigateway-orchestrations" not in param:
            fail(doc_path, f"{method.upper()} {api_path} parameter {param.get('name')} missing x-apigateway-orchestrations")

    for name in PATH_PARAM_RE.findall(api_path):
        if name not in declared_path_params:
            fail(doc_path, f"{method.upper()} {api_path} missing OpenAPI path parameter {{{name}}}")


def validate_responses(doc_path, api_path, method, op):
    responses = require_mapping(op.get("responses"), doc_path, f"{method.upper()} {api_path} missing responses")
    default = require_mapping(responses.get("default"), doc_path, f"{method.upper()} {api_path} missing responses.default")
    if "description" not in default:
        fail(doc_path, f"{method.upper()} {api_path} responses.default.description is required")
    for field in ("x-apigateway-result-failure-sample", "x-apigateway-result-normal-sample"):
        if field not in default:
            fail(doc_path, f"{method.upper()} {api_path} responses.default.{field} is required")


def validate_security(doc_path, doc, api_path, method, op):
    schemes = ((doc.get("components") or {}).get("securitySchemes") or {})
    for entry in op.get("security") or []:
        if not isinstance(entry, dict):
            continue
        for name in entry:
            if name not in schemes:
                fail(doc_path, f"{method.upper()} {api_path} references unknown security scheme {name}")


def validate_operation(doc_path, doc, api_path, method, op):
    if not isinstance(op, dict):
        fail(doc_path, f"{method.upper()} {api_path} operation must be a mapping")
    if not op.get("operationId"):
        fail(doc_path, f"{method.upper()} {api_path} missing operationId")
    validate_responses(doc_path, api_path, method, op)
    validate_parameters(doc_path, api_path, method, op)
    validate_security(doc_path, doc, api_path, method, op)
    validate_backend(doc_path, api_path, method, op)

    required_fields = {
        "x-apigateway-cors": bool,
        "x-apigateway-is-send-fg-body-base64": bool,
        "x-apigateway-match-mode": str,
        "x-apigateway-request-type": str,
    }
    for field, typ in required_fields.items():
        if field not in op:
            fail(doc_path, f"{method.upper()} {api_path} missing {field}")
        if not isinstance(op[field], typ):
            fail(doc_path, f"{method.upper()} {api_path} {field} has invalid type")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_huawei_apig_openapi.py <openapi.yaml>")
    doc_path = sys.argv[1]
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    if not isinstance(doc, dict):
        fail(doc_path, "OpenAPI document must be a mapping")
    if doc.get("openapi") != "3.0.3":
        fail(doc_path, "Huawei APIG import YAML must use openapi: 3.0.3")
    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        fail(doc_path, "paths is required")

    seen_operation_ids = set()
    for api_path, method, op in operations(paths):
        if api_path.startswith(INTERNAL_PREFIXES):
            fail(doc_path, f"{method.upper()} {api_path} internal path must not be exposed")
        validate_operation(doc_path, doc, api_path, method, op)
        operation_id = op.get("operationId")
        if operation_id in seen_operation_ids:
            fail(doc_path, f"duplicate operationId {operation_id}")
        seen_operation_ids.add(operation_id)

    print(f"validated Huawei APIG OpenAPI: {doc_path}")


if __name__ == "__main__":
    main()
