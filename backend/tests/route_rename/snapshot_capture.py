"""
Captures endpoint responses and normalizes them for comparison.
"""
import json
import re
from pathlib import Path

from tests.route_rename.endpoint_catalog import EndpointSpec
from tests.route_rename.request_factory import build_request

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
ISO_DATE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", re.IGNORECASE
)


def normalize_body(body: object) -> object:
    """Replace dynamic values with type markers for stable comparison.

    Examples:
        {"id": "abc-123-def"} -> {"id": "<uuid>"}
        {"count": 5} -> {"count": "<int>"}
        {"items": [{"name": "foo"}]} -> {"items": ["<list_item>": {"name": "<str>"}]}
    """
    if body is None:
        return "<null>"
    if isinstance(body, bool):
        return "<bool>"
    if isinstance(body, int):
        return "<int>"
    if isinstance(body, float):
        return "<float>"
    if isinstance(body, str):
        if UUID_PATTERN.match(body):
            return "<uuid>"
        if ISO_DATE_PATTERN.match(body):
            return "<datetime>"
        if body.startswith("http://") or body.startswith("https://"):
            return "<url>"
        return "<str>"
    if isinstance(body, list):
        if not body:
            return "<empty_list>"
        # Normalize just the first element to capture the shape
        return [normalize_body(body[0])]
    if isinstance(body, dict):
        return {k: normalize_body(v) for k, v in sorted(body.items())}

    return "<unknown>"


def capture_endpoint(
    client: object,
    spec: EndpointSpec,
    auth_headers: dict | None = None,
) -> dict:
    """Send a request to an endpoint and capture the response as a snapshot."""
    request = build_request(
        spec.operation_id,
        spec.path,
        spec.parameters,
        spec.request_body_schema,
    )

    url = request["url"]
    method = spec.method.upper()
    body = request["body"]
    query_params = request["query_params"]

    headers = {"Content-Type": "application/json"}
    if auth_headers:
        headers.update(auth_headers)

    # Use the client (TestClient or requests.Session)
    try:
        kwargs: dict = {"headers": headers}
        if query_params:
            kwargs["params"] = query_params
        if body is not None and method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = body

        # Support both TestClient and requests.Session
        if hasattr(client, "base_url_override"):
            # Live server mode - prepend base URL
            actual_url = client.base_url_override + url  # type: ignore
            import requests

            response = requests.request(method, actual_url, **kwargs)
        else:
            # TestClient mode
            response = client.request(method, url, **kwargs)  # type: ignore

        status_code = response.status_code
        content_type = response.headers.get("content-type", "")

        # Parse response body
        response_body = None
        if "application/json" in content_type:
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
        else:
            response_body = response.text[:500] if response.text else None

        body_structure = normalize_body(response_body) if response_body else None

    except Exception as e:
        status_code = -1
        content_type = "error"
        response_body = str(e)
        body_structure = f"<error: {type(e).__name__}>"

    return {
        "operation_id": spec.operation_id,
        "path": spec.path,
        "method": spec.method,
        "auth_type": spec.auth_type,
        "request": {
            "body": body,
            "query_params": query_params,
            "path_params": request["path_params"],
        },
        "response": {
            "status_code": status_code,
            "content_type": content_type.split(";")[0].strip() if content_type else "",
            "body_structure": body_structure,
            "body_raw": response_body,
        },
    }


def save_snapshot(snapshot_dir: Path, snapshot: dict) -> Path:
    """Save a snapshot to a JSON file."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = snapshot_dir / f"{snapshot['operation_id']}.json"

    # Don't save raw body in persisted snapshots (too large, dynamic)
    save_data = {**snapshot}
    save_data["response"] = {
        k: v for k, v in snapshot["response"].items() if k != "body_raw"
    }

    file_path.write_text(json.dumps(save_data, indent=2, default=str))
    return file_path


def save_openapi_schema(snapshot_dir: Path, schema: dict) -> Path:
    """Save the full OpenAPI schema for schema-level comparison."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = snapshot_dir / "_openapi_schema.json"
    file_path.write_text(json.dumps(schema, indent=2))
    return file_path


def load_snapshot(file_path: Path) -> dict:
    """Load a snapshot from a JSON file."""
    return json.loads(file_path.read_text())
