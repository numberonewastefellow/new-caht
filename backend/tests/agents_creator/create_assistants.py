"""
Bulk Assistant Creator for Onyx
================================
Creates assistants from JSON files via the Onyx API.

Usage:
    python create_assistants.py                          # Create from assistants/ folder
    python create_assistants.py --file my_bots.json      # Create from a specific file
    python create_assistants.py --list                   # List existing assistants
    python create_assistants.py --delete 5               # Delete assistant by ID
    python create_assistants.py --export out.json        # Export all assistants to JSON

API key is read from apikey.txt, .env, or ONYX_API_KEY env var.
"""

import argparse
import json
import sys
from pathlib import Path

from config import ASSISTANTS_DIR, DEFAULTS, add_common_args, api, apply_common_args


# ── Core Actions ────────────────────────────────────────────────────────────


def list_assistants():
    resp = api("GET", "persona")
    resp.raise_for_status()
    assistants = resp.json()
    print(f"\n{'ID':<6} {'Name':<30} {'Public':<8} {'Visible':<8} {'Tools'}")
    print("-" * 80)
    for a in assistants:
        tools = ", ".join(t["display_name"] for t in a.get("tools", []))
        print(f"{a['id']:<6} {a['name']:<30} {a['is_public']!s:<8} {a['is_visible']!s:<8} {tools}")
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
        exported.append({
            "name": d["name"],
            "description": d["description"],
            "system_prompt": d.get("system_prompt") or "",
            "task_prompt": d.get("task_prompt") or "",
            "tool_ids": [t["id"] for t in d.get("tools", [])],
            "is_public": d["is_public"],
            "starter_messages": d.get("starter_messages") or [],
            "num_chunks": d.get("num_chunks", 10.0),
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
        description="Bulk create/manage Onyx assistants from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_assistants.py                      # Create from assistants/ folder
  python create_assistants.py --file bots.json     # Create from specific file
  python create_assistants.py --list               # List all assistants
  python create_assistants.py --list-tools         # List available tool IDs
  python create_assistants.py --delete 5           # Delete assistant ID=5
  python create_assistants.py --export backup.json # Export assistants to JSON
  python create_assistants.py --force              # Create even if name exists
        """,
    )
    parser.add_argument("--file", "-f", help="Path to a specific JSON file")
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
    else:
        bulk_create(args.file, skip_existing=not args.force)


if __name__ == "__main__":
    main()
