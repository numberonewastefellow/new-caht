"""
Bulk Assistant Creator & Updater for VirtualAI
================================================
Creates or updates assistants from JSON files via the VirtualAI API.

Usage:
    python create_assistants.py                          # Create from assistants/ folder
    python create_assistants.py --file my_bots.json      # Create from a specific file
    python create_assistants.py --update                 # Update ALL from assistants/ folder
    python create_assistants.py --update --file f.json   # Update from a specific file
    python create_assistants.py --update --id 42         # Update only one assistant by ID
    python create_assistants.py --list                   # List existing assistants
    python create_assistants.py --delete 5               # Delete assistant by ID
    python create_assistants.py --export out.json        # Export all assistants to JSON

API key is read from apikey.txt, .env, or VIRTUALAI_API_KEY env var.
"""

import argparse
import json
import sys
from pathlib import Path

from config import ASSISTANTS_DIR, DEFAULTS, add_common_args, api, apply_common_args, get_or_create_labels


# ── Core Actions ────────────────────────────────────────────────────────────


def list_assistants():
    resp = api("GET", "persona")
    resp.raise_for_status()
    assistants = resp.json()
    print(f"\n{'ID':<6} {'Name':<30} {'Labels':<25} {'Tools'}")
    print("-" * 90)
    for a in assistants:
        tools = ", ".join(t["display_name"] for t in a.get("tools", []))
        labels = ", ".join(l["name"] for l in a.get("labels", []))
        print(f"{a['id']:<6} {a['name']:<30} {labels:<25} {tools}")
    print(f"\nTotal: {len(assistants)} assistants\n")


def list_tools():
    resp = api("GET", "tool")
    resp.raise_for_status()
    tools = resp.json()
    print(f"\n{'ID':<6} {'Name':<25} {'Display Name'}")
    print("-" * 55)
    for t in tools:
        print(f"{t['id']:<6} {t['name']:<25} {t.get('display_name', 'N/A')}")
    print()


def create_assistant(payload: dict) -> dict | None:
    """Create a single assistant. Returns the response dict or None on failure."""
    body = {**DEFAULTS, **payload}
    name = body.get("name", "Unnamed")

    # Resolve label names → IDs if "labels" field present
    label_names = body.pop("labels", None)
    if label_names and isinstance(label_names, list):
        body["label_ids"] = get_or_create_labels(label_names)

    resp = api("POST", "persona", body)

    if resp.status_code == 200:
        result = resp.json()
        print(f"  [OK]  ID={result['id']}  {name}")
        return result
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] {name} -> {resp.status_code}: {err}")
        return None


def update_assistant(persona_id: int, existing: dict, new_data: dict) -> dict | None:
    """Update an existing assistant via PATCH. Merges new_data on top of existing.

    The PATCH API requires a full payload (all required fields). We fetch the
    current state and overlay the JSON fields on top so only changed fields
    differ while keeping everything else intact.
    """
    name = new_data.get("name", existing.get("name", "Unnamed"))

    # Build the PATCH body from the existing persona, then overlay new_data
    body = {
        "name": new_data.get("name", existing["name"]),
        "description": new_data.get("description", existing.get("description", "")),
        "system_prompt": new_data.get("system_prompt", existing.get("system_prompt", "")),
        "task_prompt": new_data.get("task_prompt", existing.get("task_prompt", "")),
        "num_chunks": new_data.get("num_chunks", existing.get("num_chunks", 10.0)),
        "is_public": new_data.get("is_public", existing.get("is_public", True)),
        "recency_bias": new_data.get("recency_bias", existing.get("recency_bias", "base_decay")),
        "llm_filter_extraction": new_data.get("llm_filter_extraction", existing.get("llm_filter_extraction", False)),
        "llm_relevance_filter": new_data.get("llm_relevance_filter", existing.get("llm_relevance_filter", False)),
        "replace_base_system_prompt": new_data.get("replace_base_system_prompt", existing.get("replace_base_system_prompt", True)),
        "datetime_aware": new_data.get("datetime_aware", existing.get("datetime_aware", True)),
        "document_set_ids": new_data.get("document_set_ids", existing.get("document_set_ids", [])),
        "users": new_data.get("users", []),
        "groups": new_data.get("groups", []),
        "hierarchy_node_ids": new_data.get("hierarchy_node_ids", []),
        "document_ids": new_data.get("document_ids", []),
        "user_file_ids": new_data.get("user_file_ids", []),
    }

    # Tool IDs: from JSON or from existing tools
    if "tool_ids" in new_data:
        body["tool_ids"] = new_data["tool_ids"]
    else:
        body["tool_ids"] = [t["id"] for t in existing.get("tools", [])]

    # Starter messages
    if "starter_messages" in new_data:
        body["starter_messages"] = new_data["starter_messages"]
    elif existing.get("starter_messages"):
        body["starter_messages"] = existing["starter_messages"]

    # Labels: resolve names → IDs
    if "labels" in new_data and isinstance(new_data["labels"], list):
        body["label_ids"] = get_or_create_labels(new_data["labels"])
    elif existing.get("labels"):
        body["label_ids"] = [l["id"] for l in existing["labels"]]

    resp = api("PATCH", f"persona/{persona_id}", body)

    if resp.status_code == 200:
        result = resp.json()
        print(f"  [OK]  ID={persona_id}  {name}")
        return result
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] ID={persona_id}  {name} -> {resp.status_code}: {err}")
        return None


def delete_assistant(persona_id: int):
    resp = api("DELETE", f"persona/{persona_id}")
    if resp.status_code == 200:
        print(f"Deleted assistant ID={persona_id}")
    else:
        print(f"Failed to delete ID={persona_id}: {resp.status_code} {resp.text}")


def export_assistants(output_file: str):
    resp = api("GET", "persona")
    resp.raise_for_status()
    assistants = resp.json()

    exported = []
    for a in assistants:
        if a.get("builtin_persona"):
            continue
        detail_resp = api("GET", f"persona/{a['id']}")
        if detail_resp.status_code == 200:
            d = detail_resp.json()
        else:
            d = a
        labels = [l["name"] for l in d.get("labels", [])]
        exported.append({
            "name": d["name"],
            "description": d["description"],
            "system_prompt": d.get("system_prompt") or "",
            "task_prompt": d.get("task_prompt") or "",
            "tool_ids": [t["id"] for t in d.get("tools", [])],
            "is_public": d["is_public"],
            "starter_messages": d.get("starter_messages") or [],
            "num_chunks": d.get("num_chunks", 10.0),
            "labels": labels,
        })
        print(f"  Exported: {d['name']}")

    out = Path(output_file)
    out.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    print(f"\nExported {len(exported)} assistants to {out}")


# ── Bulk Load ───────────────────────────────────────────────────────────────


def load_json_files(source: str | None) -> list[dict]:
    """Load assistant definitions from a file or the assistants/ folder."""
    if source:
        p = Path(source)
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]

    if not ASSISTANTS_DIR.exists():
        print(f"ERROR: Assistants folder not found: {ASSISTANTS_DIR}")
        print("Create it and add JSON files, or use --file to specify a file.")
        sys.exit(1)

    json_files = sorted(ASSISTANTS_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {ASSISTANTS_DIR}")
        sys.exit(1)

    all_assistants = []
    for f in json_files:
        print(f"Loading: {f.name}")
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            all_assistants.extend(data)
        else:
            all_assistants.append(data)

    return all_assistants


def bulk_update(source: str | None, only_id: int | None = None):
    """Update existing assistants from JSON files, matching by name.

    For each assistant in the JSON, find the matching server persona by name,
    fetch its full detail, merge the JSON fields on top, and PATCH.
    If --id is given, only update that one persona (matched by ID, not name).
    """
    # Fetch all existing personas and build lookup by name
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch personas: {resp.status_code}")
        sys.exit(1)
    all_personas = resp.json()
    name_to_persona = {p["name"]: p for p in all_personas}
    id_to_persona = {p["id"]: p for p in all_personas}

    # If --id is given, update just that one persona from JSON data
    if only_id is not None:
        if only_id not in id_to_persona:
            print(f"ERROR: No persona with ID={only_id} on server")
            sys.exit(1)

        existing = id_to_persona[only_id]
        target_name = existing["name"]

        # Load JSON to find matching definition
        assistants = load_json_files(source)
        match = next((a for a in assistants if a.get("name") == target_name), None)
        if not match:
            print(f"ERROR: No JSON definition found matching name '{target_name}'")
            sys.exit(1)

        print(f"\nUpdating 1 assistant by ID\n")
        result = update_assistant(only_id, existing, match)
        status = "1 updated" if result else "0 updated, 1 failed"
        print(f"\nDone: {status}\n")
        return

    # Bulk update: match JSON names against server
    assistants = load_json_files(source)
    print(f"\nFound {len(assistants)} assistant(s) to update\n")

    updated, skipped, failed = 0, 0, 0
    for a in assistants:
        name = a.get("name", "Unnamed")
        if name not in name_to_persona:
            print(f"  [SKIP] {name} (not found on server)")
            skipped += 1
            continue

        existing = name_to_persona[name]
        persona_id = existing["id"]

        result = update_assistant(persona_id, existing, a)
        if result:
            updated += 1
        else:
            failed += 1

    print(f"\nDone: {updated} updated, {skipped} skipped, {failed} failed\n")


def bulk_create(source: str | None, skip_existing: bool = True):
    assistants = load_json_files(source)
    print(f"\nFound {len(assistants)} assistant(s) to create\n")

    existing_names = set()
    if skip_existing:
        resp = api("GET", "persona")
        if resp.status_code == 200:
            existing_names = {a["name"] for a in resp.json()}

    created, skipped, failed = 0, 0, 0
    for a in assistants:
        name = a.get("name", "Unnamed")
        if skip_existing and name in existing_names:
            print(f"  [SKIP] {name} (already exists)")
            skipped += 1
            continue

        result = create_assistant(a)
        if result:
            created += 1
        else:
            failed += 1

    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed\n")


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Bulk create/update/manage VirtualAI assistants from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_assistants.py                          # Create from assistants/ folder
  python create_assistants.py --file bots.json         # Create from specific file
  python create_assistants.py --update                 # Update ALL from assistants/ folder
  python create_assistants.py --update --file f.json   # Update from a specific file
  python create_assistants.py --update --id 42         # Update one assistant by server ID
  python create_assistants.py --list                   # List all assistants
  python create_assistants.py --list-tools             # List available tool IDs
  python create_assistants.py --delete 5               # Delete assistant ID=5
  python create_assistants.py --export backup.json     # Export assistants to JSON
  python create_assistants.py --force                  # Create even if name exists

Update mode (--update):
  Matches assistants by NAME between JSON and server. For each match it
  PATCHes all mutable fields (description, system_prompt, task_prompt,
  starter_messages, labels, tool_ids, etc.) while preserving server-side
  PKs/FKs (id, owner, image, display_priority, builtin status).
        """,
    )
    parser.add_argument("--file", "-f", help="Path to a specific JSON file")
    parser.add_argument("--update", "-u", action="store_true", help="Update existing assistants from JSON (match by name)")
    parser.add_argument("--id", type=int, help="With --update: update only this assistant ID")
    parser.add_argument("--list", "-l", action="store_true", help="List existing assistants")
    parser.add_argument("--list-tools", action="store_true", help="List available tools and their IDs")
    parser.add_argument("--delete", "-d", type=int, help="Delete assistant by ID")
    parser.add_argument("--export", "-e", help="Export all assistants to a JSON file")
    parser.add_argument("--force", action="store_true", help="Create even if assistant name already exists")
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    if args.list:
        list_assistants()
    elif args.list_tools:
        list_tools()
    elif args.delete is not None:
        delete_assistant(args.delete)
    elif args.export:
        export_assistants(args.export)
    elif args.update:
        bulk_update(args.file, only_id=args.id)
    else:
        bulk_create(args.file, skip_existing=not args.force)


if __name__ == "__main__":
    main()
