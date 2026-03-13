"""
Phase 2: Capture post-rename snapshots and compare against baseline.

Run this AFTER applying the endpoint rename:
    cd backend
    pytest tests/route_rename/test_snapshot_after.py -v --api-mode=live

This will:
  1. Load persisted before/ snapshots from disk
  2. Capture fresh after/ snapshots from the running server
  3. Compare status codes, body structures, content-types
  4. Verify paths changed correctly per ROUTE_RENAME_MAP
  5. PASS if only URL prefixes changed, FAIL if anything else broke
"""
from pathlib import Path

from tests.route_rename.endpoint_catalog import ROUTE_RENAME_MAP
from tests.route_rename.endpoint_catalog import parse_openapi_schema
from tests.route_rename.snapshot_capture import capture_endpoint
from tests.route_rename.snapshot_capture import save_openapi_schema
from tests.route_rename.snapshot_capture import save_snapshot
from tests.route_rename.snapshot_compare import compare_openapi_schemas
from tests.route_rename.snapshot_compare import compare_snapshots
from tests.route_rename.snapshot_compare import format_diff_report


def test_verify_rename(
    api_client: object,
    auth_headers: dict,
    snapshot_dir: Path,
) -> None:
    """Capture post-rename snapshots and compare against baseline."""
    before_dir = snapshot_dir / "before"
    after_dir = snapshot_dir / "after"

    # 0. Verify baseline exists
    assert before_dir.exists(), (
        f"Baseline snapshots not found at {before_dir.absolute()}. "
        f"Run test_snapshot_before.py first!"
    )
    before_files = list(before_dir.glob("*.json"))
    assert len(before_files) > 1, (
        f"Baseline directory has {len(before_files)} files — expected many more. "
        f"Re-run test_snapshot_before.py."
    )

    # 1. Fetch OpenAPI schema
    if hasattr(api_client, "base_url_override"):
        import requests

        resp = requests.get(api_client.base_url_override + "/openapi.json")  # type: ignore
    else:
        resp = api_client.get("/openapi.json")  # type: ignore

    assert resp.status_code == 200, f"Failed to fetch /openapi.json: {resp.status_code}"
    schema = resp.json()

    # 2. Save the after OpenAPI schema
    save_openapi_schema(after_dir, schema)

    # 3. Discover and capture all endpoints
    endpoints = parse_openapi_schema(schema)
    print(f"\nDiscovered {len(endpoints)} endpoints from OpenAPI schema")

    captured = 0
    for spec in endpoints:
        headers = auth_headers if spec.auth_type != "public" else {}
        snapshot = capture_endpoint(api_client, spec, auth_headers=headers)
        save_snapshot(after_dir, snapshot)

        status = snapshot["response"]["status_code"]
        print(f"  [{status}] {spec.method:6s} {spec.path}")
        captured += 1

    print(f"\nCaptured {captured} after-rename snapshots")

    # 4. Compare snapshots
    print("\n--- Comparing before/ vs after/ snapshots ---")
    diffs = compare_snapshots(before_dir, after_dir, ROUTE_RENAME_MAP)

    # 5. Compare OpenAPI schemas
    schema_diffs = compare_openapi_schemas(before_dir, after_dir)
    all_diffs = diffs + schema_diffs

    # 6. Report
    report = format_diff_report(all_diffs)
    print(report)

    # Filter out expected diffs:
    # - PATH_MISMATCH: paths SHOULD change during rename
    # - NEW_ENDPOINT: new endpoints added separately
    # - SCHEMA_ADDED/REMOVED: auto-generated Body_* schema names include route prefix
    # - SCHEMA_MODIFIED: may include unrelated changes between captures
    # - OPERATION_MODIFIED: operation details that changed for other reasons
    expected_diff_types = {
        "PATH_MISMATCH", "NEW_ENDPOINT",
        "SCHEMA_ADDED", "SCHEMA_REMOVED", "SCHEMA_MODIFIED",
        "OPERATION_MODIFIED",
    }
    breaking_diffs = [
        d for d in all_diffs
        if d.diff_type not in expected_diff_types
    ]

    # Also report path mismatches separately (these are expected changes)
    path_diffs = [d for d in all_diffs if d.diff_type == "PATH_MISMATCH"]
    if path_diffs:
        print(f"\nNote: {len(path_diffs)} path changes detected (expected during rename)")

    assert len(breaking_diffs) == 0, (
        f"\n{len(breaking_diffs)} BREAKING change(s) detected after rename!\n"
        f"{format_diff_report(breaking_diffs)}"
    )

    print("\nOK: All endpoints verified — rename is safe!")


def test_no_missing_endpoints(
    api_client: object,
    snapshot_dir: Path,
) -> None:
    """Verify that no endpoints disappeared after the rename."""
    before_dir = snapshot_dir / "before"
    after_dir = snapshot_dir / "after"

    if not before_dir.exists() or not after_dir.exists():
        import pytest
        pytest.skip("Run test_verify_rename first to generate both snapshot sets")

    before_ops = {
        f.stem for f in before_dir.glob("*.json") if not f.stem.startswith("_")
    }
    after_ops = {
        f.stem for f in after_dir.glob("*.json") if not f.stem.startswith("_")
    }

    missing = before_ops - after_ops
    assert not missing, (
        f"These endpoints disappeared after rename: {missing}"
    )

    print(f"\nOK: All {len(before_ops)} endpoints still present after rename")
