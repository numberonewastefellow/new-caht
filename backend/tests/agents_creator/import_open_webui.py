"""
Open WebUI → Onyx Assistant Importer
======================================
Converts Open WebUI model/assistant exports to Onyx format and creates them.

Usage:
    python import_open_webui.py                              # Preview all from open_web_ui/
    python import_open_webui.py --file bot.json              # Preview a specific file
    python import_open_webui.py --save-only                  # Save to assistants/ folder only
    python import_open_webui.py --create                     # Convert and create via API directly

Field Mapping (Open WebUI → Onyx):
    name                          → name  (underscores replaced with spaces)
    meta.description              → description
    params.system                 → system_prompt
    meta.suggestion_prompts[]     → starter_messages[]
    meta.tags[]                   → tags line in description
    meta.capabilities.vision      → adds image generation tool

API key is read from apikey.txt, .env, or ONYX_API_KEY env var.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from config import (
    ASSISTANTS_DIR,
    DEFAULTS,
    OPEN_WEBUI_DIR,
    TOOL_IDS,
    add_common_args,
    api,
    apply_common_args,
)


# ── Field Mapping ───────────────────────────────────────────────────────────


def clean_name(name: str) -> str:
    """Convert Open WebUI name to clean display name.
    'Marketing_expert' → 'Marketing Expert'
    'my-cool-bot' → 'My Cool Bot'
    """
    name = name.replace("_", " ").replace("-", " ")
    words = name.split()
    result = []
    for word in words:
        if word.isupper() and len(word) > 1:
            result.append(word)
        else:
            result.append(word.capitalize())
    return " ".join(result)


def derive_starter_name(content: str) -> str:
    """Derive a short starter message name from the prompt content."""
    content = re.sub(
        r"^(create|write|help|explain|generate|design|make|build|give|provide|tell)\s+(me\s+)?(a\s+|an\s+)?",
        "",
        content,
        flags=re.IGNORECASE,
    )
    words = content.split()
    name_words = []
    length = 0
    for w in words:
        if length + len(w) > 30:
            break
        name_words.append(w.capitalize())
        length += len(w) + 1

    name = " ".join(name_words).rstrip(".,;:!?")
    return name or "Chat"


def convert_one(owui: dict) -> dict:
    """Convert a single Open WebUI model/assistant to Onyx format."""
    meta = owui.get("meta", {})
    params = owui.get("params", {})

    raw_name = owui.get("name", "Unnamed Assistant")
    name = clean_name(raw_name)

    description = meta.get("description", "").strip()
    if not description:
        description = f"Imported from Open WebUI: {raw_name}"

    tags = [t.get("name", "") for t in meta.get("tags", []) if t.get("name")]
    tags_line = ""
    if tags:
        tags_line = "[" + ", ".join(tags) + "] "

    system_prompt = params.get("system", "").strip()

    suggestion_prompts = meta.get("suggestion_prompts", []) or []
    starter_messages = []
    for sp in suggestion_prompts:
        content = sp.get("content", "").strip()
        title = sp.get("title", "").strip()
        if content:
            starter_messages.append({
                "name": title or derive_starter_name(content),
                "description": "",
                "message": content,
            })

    capabilities = meta.get("capabilities", {})
    tool_ids = list(DEFAULTS["tool_ids"])
    if capabilities.get("vision"):
        img_tool = TOOL_IDS.get("image_generation")
        if img_tool and img_tool not in tool_ids:
            tool_ids.append(img_tool)

    return {
        "name": name,
        "description": tags_line + description,
        "system_prompt": system_prompt,
        "starter_messages": starter_messages or None,
        "tool_ids": tool_ids,
        "_open_webui_id": owui.get("id", ""),
        "_open_webui_tags": tags,
    }


def convert_all(models: list[dict]) -> list[dict]:
    """Convert a list of Open WebUI models to Onyx format."""
    return [convert_one(m) for m in models]


# ── File Loading ────────────────────────────────────────────────────────────


def load_open_webui_files(source: str | None) -> list[dict]:
    """Load Open WebUI exports from a file or the open_web_ui/ folder."""
    if source:
        p = Path(source)
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]

    if not OPEN_WEBUI_DIR.exists():
        print(f"ERROR: Open WebUI folder not found: {OPEN_WEBUI_DIR}")
        print("Create it and add exported JSON files, or use --file to specify a file.")
        sys.exit(1)

    json_files = sorted(OPEN_WEBUI_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {OPEN_WEBUI_DIR}")
        sys.exit(1)

    all_models = []
    for f in json_files:
        print(f"Loading: {f.name}")
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            all_models.extend(data)
        else:
            all_models.append(data)

    return all_models


# ── Actions ─────────────────────────────────────────────────────────────────


def preview(converted: list[dict]):
    """Print a preview of what would be created."""
    print(f"\n{'='*70}")
    print(f"  Preview: {len(converted)} assistant(s) to import")
    print(f"{'='*70}\n")

    for i, a in enumerate(converted, 1):
        tags = a.get("_open_webui_tags", [])
        starters = a.get("starter_messages") or []
        prompt_preview = (a["system_prompt"][:120] + "...") if len(a["system_prompt"]) > 120 else a["system_prompt"]

        print(f"  [{i}] {a['name']}")
        print(f"      Open WebUI ID : {a.get('_open_webui_id', 'N/A')}")
        print(f"      Description   : {a['description'][:80]}{'...' if len(a['description']) > 80 else ''}")
        print(f"      Tags          : {', '.join(tags) if tags else 'none'}")
        print(f"      System Prompt : {prompt_preview or '(empty)'}")
        print(f"      Starters      : {len(starters)} message(s)")
        for s in starters:
            print(f"          - {s['name']}: {s['message'][:60]}...")
        print(f"      Tool IDs      : {a['tool_ids']}")
        print()


def save_to_folder(converted: list[dict], output_file: str | None = None):
    """Save converted assistants as Onyx-format JSON."""
    ASSISTANTS_DIR.mkdir(exist_ok=True)

    clean = []
    for a in converted:
        entry = {k: v for k, v in a.items() if not k.startswith("_")}
        clean.append(entry)

    if output_file:
        out = Path(output_file)
    else:
        out = ASSISTANTS_DIR / "imported_open_webui.json"

    out.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    print(f"\nSaved {len(clean)} assistant(s) to {out}")
    print("You can now run: python create_assistants.py to create them.\n")


def create_via_api(converted: list[dict], skip_existing: bool = True):
    """Create assistants directly via the Onyx API."""
    existing_names = set()
    if skip_existing:
        resp = api("GET", "persona")
        if resp.status_code == 200:
            existing_names = {a["name"] for a in resp.json()}

    created, skipped, failed = 0, 0, 0
    for a in converted:
        name = a["name"]
        if skip_existing and name in existing_names:
            print(f"  [SKIP] {name} (already exists)")
            skipped += 1
            continue

        clean = {k: v for k, v in a.items() if not k.startswith("_")}
        body = {**DEFAULTS, **clean}

        resp = api("POST", "persona", body)
        if resp.status_code == 200:
            result = resp.json()
            print(f"  [OK]  ID={result['id']}  {name}")
            created += 1
        else:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            print(f"  [FAIL] {name} -> {resp.status_code}: {err}")
            failed += 1

    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed\n")


def list_tools():
    resp = api("GET", "tool")
    resp.raise_for_status()
    tools = resp.json()
    print(f"\n{'ID':<6} {'Name':<25} {'Display Name'}")
    print("-" * 55)
    for t in tools:
        print(f"{t['id']:<6} {t['name']:<25} {t.get('display_name', 'N/A')}")
    print()


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Import Open WebUI assistants into Onyx",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python import_open_webui.py                                  # Preview all from open_web_ui/
  python import_open_webui.py --file open_web_ui/bot.json      # Preview a specific file
  python import_open_webui.py --save-only                      # Save to assistants/ folder
  python import_open_webui.py --save-only -o my_bots.json      # Save to custom file
  python import_open_webui.py --create                         # Create directly via API
  python import_open_webui.py --create --force                 # Create even if name exists
  python import_open_webui.py --list-tools                     # Show available Onyx tool IDs

Field Mapping:
  Open WebUI                    Onyx
  ─────────────────────────     ──────────────────
  name                       →  name (cleaned)
  meta.description           →  description
  params.system              →  system_prompt
  meta.suggestion_prompts[]  →  starter_messages[]
  meta.tags[]                →  [tags] in description
  meta.capabilities.vision   →  image_generation tool
        """,
    )
    parser.add_argument("--file", "-f", help="Path to a specific Open WebUI JSON file")
    parser.add_argument("--save-only", "-s", action="store_true", help="Save as Onyx JSON (don't create via API)")
    parser.add_argument("--create", "-c", action="store_true", help="Create assistants via API directly")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (same as default, explicit flag)")
    parser.add_argument("--force", action="store_true", help="Create even if name already exists")
    parser.add_argument("--output", "-o", help="Output file path (used with --save-only)")
    parser.add_argument("--list-tools", action="store_true", help="List available Onyx tool IDs")
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    if args.list_tools:
        list_tools()
        return

    models = load_open_webui_files(args.file)
    print(f"\nLoaded {len(models)} Open WebUI model(s)\n")

    converted = convert_all(models)
    preview(converted)

    if args.save_only:
        save_to_folder(converted, args.output)
    elif args.create:
        create_via_api(converted, skip_existing=not args.force)
    else:
        print("Use --save-only to save as Onyx JSON, or --create to push to API directly.\n")


if __name__ == "__main__":
    main()
