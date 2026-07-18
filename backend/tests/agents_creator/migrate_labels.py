"""
Label Migration Script: Consolidate 331 labels → 45 labels
============================================================
Reads the mapping, creates new labels, updates all agents, deletes orphans.

Usage:
    python migrate_labels.py --dry-run     # Preview changes without applying
    python migrate_labels.py --apply       # Apply migration
    python migrate_labels.py --cleanup     # Delete orphaned labels after migration
"""

import argparse
import json
import sys

from config import api, resolve_api_key, add_common_args, apply_common_args

# ── Complete agent ID → new labels mapping ──────────────────────────────────
# This is the source of truth from the approved plan.

AGENT_LABEL_MAP = {
    # Police (IDs 7-11)
    7: ["Police & Law", "Legal"],
    8: ["Police & Law"],
    9: ["Police & Law", "Legal"],
    10: ["Police & Law", "Legal"],
    11: ["Police & Law"],

    # Revenue/Collector (IDs 12-21)
    12: ["District Administration"],
    13: ["District Administration"],
    14: ["District Administration"],
    15: ["District Administration", "Disaster Management"],
    16: ["District Administration", "Government"],
    17: ["District Administration", "Government"],
    18: ["District Administration", "Legal"],
    19: ["District Administration", "Government"],
    20: ["District Administration", "Welfare"],
    21: ["District Administration", "Legal"],

    # Health (IDs 22-25)
    22: ["Healthcare"],
    23: ["Healthcare"],
    24: ["Healthcare"],
    25: ["Healthcare", "Government"],

    # Cross-dept / Disaster (IDs 26-31)
    26: ["Government", "Legal"],
    27: ["Disaster Management"],
    28: ["Disaster Management"],
    29: ["Disaster Management"],
    30: ["Disaster Management", "Infrastructure"],
    31: ["Disaster Management", "Welfare"],

    # Law & Order (IDs 32-34)
    32: ["Police & Law", "District Administration"],
    33: ["Police & Law", "Government"],
    34: ["Police & Law", "Government"],

    # Sports (IDs 35-36)
    35: ["Sports & Youth"],
    36: ["Sports & Youth", "Welfare"],

    # Village Admin (IDs 37-42)
    37: ["Village & Panchayat"],
    38: ["Village & Panchayat", "Welfare"],
    39: ["Village & Panchayat", "Infrastructure"],
    40: ["Village & Panchayat", "Welfare"],
    41: ["Village & Panchayat", "Permits & Licenses"],
    42: ["Village & Panchayat", "Government"],

    # Education/Elections/RTI (IDs 43-46)
    43: ["Education", "Government"],
    44: ["Education", "Welfare"],
    45: ["Government"],
    46: ["Government", "Legal"],

    # Revenue/Land (IDs 47-48)
    47: ["District Administration", "Legal"],
    48: ["Municipal Services", "Finance & Tax"],

    # Municipality (IDs 49-53)
    49: ["Municipal Services", "Permits & Licenses"],
    50: ["Municipal Services", "Environment"],
    51: ["Municipal Services", "Infrastructure"],
    52: ["Municipal Services", "Permits & Licenses"],
    53: ["Municipal Services", "Government"],

    # Irrigation (IDs 54-57)
    54: ["Water & Irrigation", "Disaster Management"],
    55: ["Water & Irrigation"],
    56: ["Water & Irrigation", "Environment"],
    57: ["Water & Irrigation", "Village & Panchayat"],

    # Registration (IDs 58-61)
    58: ["Real Estate", "District Administration"],
    59: ["Real Estate", "District Administration"],
    60: ["Real Estate", "Legal"],
    61: ["Real Estate", "Legal"],

    # Sub-departments (IDs 62-67)
    62: ["Transport", "Permits & Licenses"],
    63: ["Labour & Industry", "Legal"],
    64: ["Permits & Licenses", "District Administration"],
    65: ["Permits & Licenses", "Environment"],
    66: ["Religious Affairs", "District Administration"],
    67: ["Municipal Services", "Permits & Licenses"],

    # Finance (IDs 68-71)
    68: ["Finance & Tax", "Government"],
    69: ["Finance & Tax", "Government"],
    70: ["Finance & Tax", "Legal"],
    71: ["Finance & Tax"],

    # Stock Market (IDs 72-76)
    72: ["Stock Market", "Investment"],
    73: ["Stock Market"],
    74: ["Investment"],
    75: ["Stock Market", "Investment"],
    76: ["Stock Market"],

    # Banking/Insurance (IDs 77-82)
    77: ["Banking & Loans"],
    78: ["Insurance"],
    79: ["Finance & Tax", "Personal Finance"],
    80: ["Investment", "Stock Market"],
    81: ["Crypto & Forex"],
    82: ["Crypto & Forex", "Finance & Tax"],

    # Advanced Finance (IDs 83-87)
    83: ["Stock Market", "Legal"],
    84: ["Real Estate", "Investment"],
    85: ["Personal Finance"],
    86: ["Startups & Business"],
    87: ["Personal Finance"],

    # Entertainment (IDs 88-98)
    88: ["Entertainment", "Creative Writing"],
    89: ["Entertainment"],
    90: ["Entertainment", "Creative Writing"],
    91: ["Entertainment", "Gaming"],
    92: ["Entertainment", "Content Creation"],
    93: ["Entertainment", "Content Creation"],
    94: ["Gaming", "Creative Writing"],
    95: ["Photography & Visual Arts"],
    96: ["Entertainment"],
    97: ["Entertainment"],
    98: ["Creative Writing"],

    # Education New (IDs 99-108)
    99: ["Competitive Exams", "Education"],
    100: ["Competitive Exams", "Education"],
    101: ["Education", "Creative Writing"],
    102: ["Education"],
    103: ["Education"],
    104: ["Education", "Sports & Youth"],
    105: ["Education"],
    106: ["Education", "Technology"],
    107: ["Education", "Government"],
    108: ["Education"],

    # Science (IDs 109-118)
    109: ["Science"],
    110: ["Science"],
    111: ["Science", "Environment"],
    112: ["Science"],
    113: ["Science", "Technology"],
    114: ["Science"],
    115: ["Science", "Environment"],
    116: ["Science", "Police & Law"],
    117: ["AI & Robotics", "Science"],
    118: ["AI & Robotics", "Technology"],

    # Technology (IDs 119-128)
    119: ["Technology", "Web & Mobile Dev"],
    120: ["Networking & Sysadmin"],
    121: ["Networking & Sysadmin"],
    122: ["Networking & Sysadmin"],
    123: ["Networking & Sysadmin", "Technology"],
    124: ["Web & Mobile Dev", "Technology"],
    125: ["Cybersecurity"],
    126: ["Cloud & DevOps"],
    127: ["Cloud & DevOps"],
    128: ["Cybersecurity"],

    # Real Estate (IDs 129-133)
    129: ["Real Estate"],
    130: ["Real Estate", "Legal"],
    131: ["Real Estate"],
    132: ["Real Estate", "Investment"],
    133: ["Interior & Renovation"],

    # Social Media (IDs 134-138)
    134: ["Digital Marketing"],
    135: ["Social Media"],
    136: ["Social Media", "Digital Marketing"],
    137: ["Social Media"],
    138: ["Digital Marketing"],

    # Loans (IDs 139-143)
    139: ["Banking & Loans"],
    140: ["Banking & Loans"],
    141: ["Banking & Loans", "Startups & Business"],
    142: ["Banking & Loans", "Education"],
    143: ["Banking & Loans"],

    # Content Generators (IDs 144-153)
    144: ["Content Creation"],
    145: ["Content Creation"],
    146: ["Content Creation", "LinkedIn"],
    147: ["Content Creation", "LinkedIn"],
    148: ["Content Creation", "Twitter & Instagram"],
    149: ["Content Creation", "Twitter & Instagram"],
    150: ["Content Creation", "Twitter & Instagram"],
    151: ["Twitter & Instagram", "Social Media"],
    152: ["Content Creation", "Investment"],
    153: ["Content Creation", "Digital Marketing"],
}


def get_all_new_labels():
    """Extract the unique set of new labels from the mapping."""
    labels = set()
    for label_list in AGENT_LABEL_MAP.values():
        labels.update(label_list)
    return sorted(labels)


def dry_run():
    """Preview what the migration would do."""
    new_labels = get_all_new_labels()
    print(f"\n=== DRY RUN: Label Migration Preview ===\n")
    print(f"New label count: {len(new_labels)}")
    print(f"Agents to update: {len(AGENT_LABEL_MAP)}")
    print(f"\nNew labels ({len(new_labels)}):")
    for l in new_labels:
        # Count how many agents use this label
        count = sum(1 for labels in AGENT_LABEL_MAP.values() if l in labels)
        print(f"  [{count:2d} agents] {l}")

    # Fetch current server state for comparison
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"\nERROR: Could not fetch personas: {resp.status_code}")
        return
    personas = resp.json()
    id_to_persona = {p["id"]: p for p in personas}

    print(f"\n--- Agent Label Changes ---")
    for pid, new_labels_list in sorted(AGENT_LABEL_MAP.items()):
        if pid not in id_to_persona:
            print(f"  ID={pid:3d}  [NOT FOUND ON SERVER]")
            continue
        p = id_to_persona[pid]
        old = sorted([l["name"] for l in p.get("labels", [])])
        new = sorted(new_labels_list)
        if old != new:
            print(f"  ID={pid:3d}  {p['name'][:50]}")
            print(f"         OLD: {old}")
            print(f"         NEW: {new}")

    print(f"\n=== Use --apply to execute migration ===\n")


def apply_migration():
    """Execute the migration: create labels, update agents."""
    new_label_names = get_all_new_labels()

    # Step 1: Get existing labels
    resp = api("GET", "persona/labels")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch labels: {resp.status_code}")
        sys.exit(1)
    existing_labels = {l["name"]: l["id"] for l in resp.json()}

    # Step 2: Create new labels that don't exist yet
    label_id_map = {}  # name -> id
    print(f"\n=== Step 1: Creating {len(new_label_names)} labels ===\n")
    for name in new_label_names:
        if name in existing_labels:
            label_id_map[name] = existing_labels[name]
            print(f"  [EXISTS] {name} (ID={existing_labels[name]})")
        else:
            resp = api("POST", "persona/labels", {"name": name})
            if resp.status_code == 200:
                lbl = resp.json()
                label_id_map[name] = lbl["id"]
                print(f"  [NEW]    {name} (ID={lbl['id']})")
            else:
                print(f"  [FAIL]   {name}: {resp.status_code} {resp.text}")
                sys.exit(1)

    # Step 3: Fetch all personas for update
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch personas: {resp.status_code}")
        sys.exit(1)
    personas = resp.json()
    id_to_persona = {p["id"]: p for p in personas}

    # Step 4: Update each agent with new labels
    print(f"\n=== Step 2: Updating {len(AGENT_LABEL_MAP)} agents ===\n")
    updated, failed, skipped = 0, 0, 0
    for pid, new_labels_list in sorted(AGENT_LABEL_MAP.items()):
        if pid not in id_to_persona:
            print(f"  [SKIP] ID={pid} not found on server")
            skipped += 1
            continue

        existing = id_to_persona[pid]
        new_label_ids = [label_id_map[name] for name in new_labels_list]

        # Build minimal PATCH payload
        body = {
            "name": existing["name"],
            "description": existing.get("description", ""),
            "system_prompt": existing.get("system_prompt", ""),
            "task_prompt": existing.get("task_prompt", ""),
            "num_chunks": existing.get("num_chunks", 10.0),
            "is_public": existing.get("is_public", True),
            "recency_bias": existing.get("recency_bias", "base_decay"),
            "llm_filter_extraction": existing.get("llm_filter_extraction", False),
            "llm_relevance_filter": existing.get("llm_relevance_filter", False),
            "replace_base_system_prompt": existing.get("replace_base_system_prompt", True),
            "datetime_aware": existing.get("datetime_aware", True),
            "document_set_ids": [],
            "tool_ids": [t["id"] for t in existing.get("tools", [])],
            "label_ids": new_label_ids,
            "users": [],
            "groups": [],
            "hierarchy_node_ids": [],
            "document_ids": [],
            "knowledge_file_ids": [],
        }
        if existing.get("starter_messages"):
            body["starter_messages"] = existing["starter_messages"]

        resp = api("PATCH", f"persona/{pid}", body)
        if resp.status_code == 200:
            print(f"  [OK]   ID={pid:3d}  {existing['name'][:50]}  -> {new_labels_list}")
            updated += 1
        else:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            print(f"  [FAIL] ID={pid:3d}  {existing['name'][:50]}  -> {resp.status_code}: {err}")
            failed += 1

    print(f"\nDone: {updated} updated, {skipped} skipped, {failed} failed\n")


def cleanup_orphans():
    """Delete labels that have zero agents assigned."""
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch personas: {resp.status_code}")
        sys.exit(1)
    personas = resp.json()

    # Collect all label IDs currently in use
    used_label_ids = set()
    for p in personas:
        for l in p.get("labels", []):
            used_label_ids.add(l["id"])

    # Get all labels
    resp = api("GET", "persona/labels")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch labels: {resp.status_code}")
        sys.exit(1)
    all_labels = resp.json()

    orphans = [l for l in all_labels if l["id"] not in used_label_ids]
    print(f"\n=== Orphaned Labels: {len(orphans)} out of {len(all_labels)} ===\n")

    if not orphans:
        print("No orphaned labels to delete.")
        return

    for l in sorted(orphans, key=lambda x: x["name"]):
        print(f"  Deleting: {l['name']} (ID={l['id']})")
        resp = api("DELETE", f"admin/persona/label/{l['id']}")
        if resp.status_code == 200:
            print(f"    [OK]")
        else:
            print(f"    [FAIL] {resp.status_code}: {resp.text}")

    # Verify
    resp = api("GET", "persona/labels")
    remaining = len(resp.json()) if resp.status_code == 200 else "?"
    print(f"\nLabels remaining: {remaining}")


def main():
    parser = argparse.ArgumentParser(description="Migrate 331 labels → 45 consolidated labels")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--apply", action="store_true", help="Apply migration")
    parser.add_argument("--cleanup", action="store_true", help="Delete orphaned labels")
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    if args.dry_run:
        dry_run()
    elif args.apply:
        apply_migration()
    elif args.cleanup:
        cleanup_orphans()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
