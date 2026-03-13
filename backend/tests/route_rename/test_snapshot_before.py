"""
Phase 1: Capture baseline API snapshots BEFORE the endpoint rename.

Run this with the current (pre-rename) code:
    cd backend
    pytest tests/route_rename/test_snapshot_before.py -v --api-mode=live

Snapshots are written to tests/route_rename/snapshots/before/
Commit these to git so they persist across Docker restarts.
"""
import json
from pathlib import Path

from tests.route_rename.endpoint_catalog import parse_openapi_schema
from tests.route_rename.snapshot_capture import capture_endpoint
from tests.route_rename.snapshot_capture import save_openapi_schema
from tests.route_rename.snapshot_capture import save_snapshot


def test_capture_baseline(
    api_client: object,
    auth_headers: dict,
    snapshot_dir: Path,
) -> None:
    """Capture response snapshots for all discovered endpoints."""
    before_dir = snapshot_dir / "before"

    # 1. Fetch OpenAPI schema
    if hasattr(api_client, "base_url_override"):
        import requests

        resp = requests.get(api_client.base_url_override + "/openapi.json")  # type: ignore
    else:
        resp = api_client.get("/openapi.json")  # type: ignore

    assert resp.status_code == 200, f"Failed to fetch /openapi.json: {resp.status_code}"
    schema = resp.json()

    # 2. Save the full OpenAPI schema
    save_openapi_schema(before_dir, schema)
    print(f"\nSaved OpenAPI schema to {before_dir / '_openapi_schema.json'}")

    # 3. Discover all endpoints
    endpoints = parse_openapi_schema(schema)
    print(f"Discovered {len(endpoints)} endpoints from OpenAPI schema")

    # 4. Capture snapshot for each endpoint
    captured = 0
    errors = 0
    for spec in endpoints:
        headers = auth_headers if spec.auth_type != "public" else {}
        snapshot = capture_endpoint(api_client, spec, auth_headers=headers)

        file_path = save_snapshot(before_dir, snapshot)
        status = snapshot["response"]["status_code"]

        if status == -1:
            errors += 1
            print(f"  ERROR  {spec.method:6s} {spec.path} -> {snapshot['response'].get('body_raw', 'unknown error')}")
        else:
            captured += 1
            print(f"  [{status}] {spec.method:6s} {spec.path}")

    print(f"\nBaseline capture complete:")
    print(f"  Captured: {captured} endpoints")
    print(f"  Errors:   {errors} endpoints")
    print(f"  Saved to: {before_dir.absolute()}")

    # 5. Write a summary file
    summary = {
        "total_endpoints": len(endpoints),
        "captured": captured,
        "errors": errors,
        "endpoints": [
            {"operation_id": s.operation_id, "path": s.path, "method": s.method}
            for s in endpoints
        ],
    }
    (before_dir / "_summary.json").write_text(json.dumps(summary, indent=2))

    assert captured > 0, "No endpoints were captured — check server connectivity"
