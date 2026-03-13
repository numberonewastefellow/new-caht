"""
Compares before/after endpoint snapshots and reports differences.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from tests.route_rename.endpoint_catalog import ROUTE_RENAME_MAP
from tests.route_rename.endpoint_catalog import translate_path


@dataclass
class Diff:
    operation_id: str
    diff_type: str  # MISSING, PATH_MISMATCH, STATUS_CODE, BODY_STRUCTURE, CONTENT_TYPE
    message: str
    before_value: object = None
    after_value: object = None


def compare_snapshots(
    before_dir: Path,
    after_dir: Path,
    rename_map: dict[str, str] | None = None,
) -> list[Diff]:
    """Compare before/ and after/ snapshot directories.

    Returns a list of Diff objects for any mismatches.
    """
    if rename_map is None:
        rename_map = ROUTE_RENAME_MAP

    diffs: list[Diff] = []

    # Load all before snapshots
    before_files = {f.stem: f for f in before_dir.glob("*.json") if not f.stem.startswith("_")}
    after_files = {f.stem: f for f in after_dir.glob("*.json") if not f.stem.startswith("_")}

    # Check for missing endpoints
    for op_id in before_files:
        if op_id not in after_files:
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="MISSING",
                    message=f"Endpoint '{op_id}' exists in before/ but missing in after/",
                )
            )

    # Check for unexpected new endpoints
    for op_id in after_files:
        if op_id not in before_files:
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="NEW_ENDPOINT",
                    message=f"Endpoint '{op_id}' exists in after/ but not in before/ (unexpected new endpoint)",
                )
            )

    # Compare matching endpoints
    for op_id in before_files:
        if op_id not in after_files:
            continue

        before = json.loads(before_files[op_id].read_text())
        after = json.loads(after_files[op_id].read_text())

        before_resp = before["response"]
        after_resp = after["response"]

        # 1. Verify path changed correctly
        expected_new_path = translate_path(before["path"], rename_map)
        actual_new_path = after["path"]
        if actual_new_path != expected_new_path:
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="PATH_MISMATCH",
                    message=f"Path rename incorrect",
                    before_value=f"{before['path']} -> expected: {expected_new_path}",
                    after_value=actual_new_path,
                )
            )

        # 2. Status codes must match
        if before_resp["status_code"] != after_resp["status_code"]:
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="STATUS_CODE",
                    message=f"Status code changed",
                    before_value=before_resp["status_code"],
                    after_value=after_resp["status_code"],
                )
            )

        # 3. Body structure must match
        if before_resp.get("body_structure") != after_resp.get("body_structure"):
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="BODY_STRUCTURE",
                    message=f"Response body structure changed",
                    before_value=json.dumps(before_resp.get("body_structure"), indent=2),
                    after_value=json.dumps(after_resp.get("body_structure"), indent=2),
                )
            )

        # 4. Content-type must match
        if before_resp.get("content_type") != after_resp.get("content_type"):
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="CONTENT_TYPE",
                    message=f"Content-Type header changed",
                    before_value=before_resp.get("content_type"),
                    after_value=after_resp.get("content_type"),
                )
            )

    return diffs


def compare_openapi_schemas(
    before_dir: Path,
    after_dir: Path,
    rename_map: dict[str, str] | None = None,
) -> list[Diff]:
    """Compare OpenAPI schemas, ignoring path key renames.

    Checks that components/schemas and operation details are identical.
    """
    diffs: list[Diff] = []

    before_schema_file = before_dir / "_openapi_schema.json"
    after_schema_file = after_dir / "_openapi_schema.json"

    if not before_schema_file.exists() or not after_schema_file.exists():
        diffs.append(
            Diff(
                operation_id="_openapi_schema",
                diff_type="MISSING",
                message="OpenAPI schema file missing from one or both directories",
            )
        )
        return diffs

    before_schema = json.loads(before_schema_file.read_text())
    after_schema = json.loads(after_schema_file.read_text())

    # Compare components/schemas
    # Note: FastAPI auto-generates schema names like "Body_upload_files_api_manage_admin_..."
    # that include the route prefix. When prefixes change, these names change too.
    # We filter out schema renames that are just prefix substitutions.
    before_components = before_schema.get("components", {}).get("schemas", {})
    after_components = after_schema.get("components", {}).get("schemas", {})

    if before_components != after_components:
        added = set(after_components.keys()) - set(before_components.keys())
        removed = set(before_components.keys()) - set(after_components.keys())

        # Filter out schema name changes that are just prefix renames
        # e.g., "Body_upload_files_api_manage_admin_..." -> "Body_upload_files_api_nexus_admin_..."
        if rename_map is None:
            rename_map = ROUTE_RENAME_MAP
        matched_added = set()
        matched_removed = set()
        for old_name in removed:
            for old_prefix, new_prefix in rename_map.items():
                old_slug = old_prefix.strip("/").replace("/", "_")
                new_slug = new_prefix.strip("/").replace("/", "_")
                expected_new = old_name.replace(old_slug, new_slug)
                if expected_new in added:
                    matched_added.add(expected_new)
                    matched_removed.add(old_name)
                    break
        added = added - matched_added
        removed = removed - matched_removed
        if added:
            diffs.append(
                Diff(
                    operation_id="_openapi_schema",
                    diff_type="SCHEMA_ADDED",
                    message=f"New schemas added: {added}",
                )
            )
        if removed:
            diffs.append(
                Diff(
                    operation_id="_openapi_schema",
                    diff_type="SCHEMA_REMOVED",
                    message=f"Schemas removed: {removed}",
                )
            )

        # Check for modified schemas
        for schema_name in set(before_components.keys()) & set(after_components.keys()):
            if before_components[schema_name] != after_components[schema_name]:
                diffs.append(
                    Diff(
                        operation_id="_openapi_schema",
                        diff_type="SCHEMA_MODIFIED",
                        message=f"Schema '{schema_name}' was modified",
                        before_value=json.dumps(before_components[schema_name], indent=2)[:500],
                        after_value=json.dumps(after_components[schema_name], indent=2)[:500],
                    )
                )

    # Compare operation details by operation_id (should be identical except paths)
    before_ops = _extract_operations(before_schema)
    after_ops = _extract_operations(after_schema)

    for op_id in set(before_ops.keys()) & set(after_ops.keys()):
        before_op = before_ops[op_id]
        after_op = after_ops[op_id]

        # Compare everything except the path key
        before_details = {k: v for k, v in before_op.items() if k != "path"}
        after_details = {k: v for k, v in after_op.items() if k != "path"}

        if before_details != after_details:
            diffs.append(
                Diff(
                    operation_id=op_id,
                    diff_type="OPERATION_MODIFIED",
                    message=f"Operation details changed (not just path)",
                )
            )

    return diffs


def _extract_operations(schema: dict) -> dict:
    """Extract operations indexed by operationId."""
    operations = {}
    for path, methods in schema.get("paths", {}).items():
        for method, details in methods.items():
            if method in ("parameters", "summary", "description"):
                continue
            op_id = details.get("operationId", "")
            if op_id:
                operations[op_id] = {"path": path, "method": method, **details}
    return operations


def format_diff_report(diffs: list[Diff]) -> str:
    """Format diffs into a human-readable report."""
    if not diffs:
        return "All endpoints match. No differences found."

    lines = [
        f"\n{'='*80}",
        f"  API RENAME VERIFICATION REPORT — {len(diffs)} difference(s) found",
        f"{'='*80}",
    ]

    # Group by diff type
    by_type: dict[str, list[Diff]] = {}
    for d in diffs:
        by_type.setdefault(d.diff_type, []).append(d)

    for diff_type, items in by_type.items():
        lines.append(f"\n--- {diff_type} ({len(items)}) ---")
        for d in items:
            lines.append(f"  [{d.operation_id}] {d.message}")
            if d.before_value is not None:
                lines.append(f"    BEFORE: {d.before_value}")
            if d.after_value is not None:
                lines.append(f"    AFTER:  {d.after_value}")

    lines.append(f"\n{'='*80}\n")
    return "\n".join(lines)
