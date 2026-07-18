"""
Seed All — One-command database restore for VirtualAI
=====================================================
Seeds LLM providers, standalone agents, and workflows from JSON definitions.

Dependency order:
    1. LLM Providers  (needed before agents can use LLM overrides)
    2. Standalone Agents  (agents_creator/assistants/*.json)
    3. Workflows  (workflow_creator/workflows/*.json + auto-creates step agents)

Usage:
    python seed_all.py                              # Seed everything
    python seed_all.py --only providers             # Only LLM providers
    python seed_all.py --only agents                # Only standalone agents
    python seed_all.py --only workflows             # Only workflows
    python seed_all.py --force                      # Re-create even if exists
    python seed_all.py --no-icons                   # Skip icon generation
    python seed_all.py --dry-run                    # Show what would be created
    python seed_all.py --llm-key sk-...             # LLM provider API key

API key for VirtualAI is read from agents_creator/apikey.txt, .env, or VIRTUALAI_API_KEY.
LLM provider key is read from --llm-key arg or LLM_API_KEY env var.
"""

import argparse
import importlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

# Add parent dirs to path for imports
_tests_dir = Path(__file__).parent
_agents_dir = _tests_dir / "agents_creator"
_workflow_dir = _tests_dir / "workflow_creator"

if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))


@contextmanager
def _workflow_path():
    """Temporarily put workflow_creator dir first on sys.path and reset the
    bare 'config' module so that create_workflows.py resolves its own config."""
    inserted = str(_workflow_dir) not in sys.path
    if inserted:
        sys.path.insert(0, str(_workflow_dir))
    # Evict the bare 'config' module so it re-resolves from the new path
    old_config = sys.modules.pop("config", None)
    try:
        yield
    finally:
        # Restore previous 'config' module
        sys.modules.pop("config", None)
        if old_config is not None:
            sys.modules["config"] = old_config
        if inserted:
            sys.path.remove(str(_workflow_dir))


from agents_creator.config import (
    CONFIG,
    add_common_args,
    api,
    apply_common_args,
)

LLM_PROVIDERS_FILE = _tests_dir / "llm_providers.json"


# ── LLM Provider Seeding ──────────────────────────────────────────────────


def seed_llm_providers(llm_key: str | None, force: bool = False, dry_run: bool = False) -> tuple[int, int, int]:
    """Seed LLM providers from llm_providers.json. Returns (created, skipped, failed)."""
    if not LLM_PROVIDERS_FILE.exists():
        print(f"  [WARN] {LLM_PROVIDERS_FILE} not found — skipping LLM provider seeding")
        return 0, 0, 0

    providers = json.loads(LLM_PROVIDERS_FILE.read_text(encoding="utf-8"))
    print(f"\n{'='*60}")
    print(f"  PHASE 1: LLM Providers ({len(providers)} defined)")
    print(f"{'='*60}\n")

    # Resolve LLM API key
    resolved_key = llm_key or os.environ.get("LLM_API_KEY", "")

    # Fetch existing providers
    existing_names: set[str] = set()
    resp = api("GET", "admin/llm/provider")
    if resp.status_code == 200:
        existing_names = {p["name"] for p in resp.json()}

    created, skipped, failed = 0, 0, 0
    for prov in providers:
        name = prov["name"]
        exists = name in existing_names

        if exists and not force:
            print(f"  [SKIP] {name} (already exists)")
            skipped += 1
            continue

        if dry_run:
            action = "would update" if exists else "would create"
            print(f"  [DRY]  {action}: {name} ({prov['provider']}, model={prov['default_model_name']})")
            created += 1
            continue

        # Fill in API key if not in JSON
        body = {**prov}
        if not body.get("api_key") and resolved_key:
            body["api_key"] = resolved_key

        if not body.get("api_key"):
            print(f"  [FAIL] {name}: No API key. Use --llm-key or set LLM_API_KEY env var")
            failed += 1
            continue

        # Mark as creation or update
        body["api_key_changed"] = True
        is_creation = not exists

        resp = api("PUT", f"admin/llm/provider?is_creation={str(is_creation).lower()}", body)
        if resp.status_code == 200:
            action = "Updated" if exists else "Created"
            print(f"  [OK]   {action}: {name} (provider={prov['provider']})")
            created += 1
        else:
            try:
                err = resp.json()
            except Exception:
                err = resp.text[:200]
            print(f"  [FAIL] {name}: {resp.status_code} {err}")
            failed += 1

    return created, skipped, failed


# ── Agent Seeding ──────────────────────────────────────────────────────────


def seed_agents(force: bool = False, dry_run: bool = False) -> tuple[int, int, int]:
    """Seed standalone agents from agents_creator/assistants/. Returns (created, skipped, failed)."""
    from agents_creator.create_assistants import load_json_files, create_assistant

    assistants_dir = _agents_dir / "assistants"
    if not assistants_dir.exists():
        print(f"  [WARN] {assistants_dir} not found — skipping agent seeding")
        return 0, 0, 0

    json_files = sorted(assistants_dir.glob("*.json"))
    if not json_files:
        print(f"  [WARN] No JSON files in {assistants_dir}")
        return 0, 0, 0

    print(f"\n{'='*60}")
    print(f"  PHASE 2: Standalone Agents ({len(json_files)} files)")
    print(f"{'='*60}\n")

    # Load all assistants
    all_assistants = []
    for f in json_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            all_assistants.extend(data)
        else:
            all_assistants.append(data)

    print(f"  Loaded {len(all_assistants)} agent(s) from {len(json_files)} files\n")

    # Fetch existing
    existing_names: set[str] = set()
    if not force:
        resp = api("GET", "agent")
        if resp.status_code == 200:
            existing_names = {a["name"] for a in resp.json()}

    created, skipped, failed = 0, 0, 0
    for a in all_assistants:
        name = a.get("name", "Unnamed")

        if not force and name in existing_names:
            print(f"  [SKIP] {name}")
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY]  would create: {name}")
            created += 1
            continue

        result = create_assistant(a)
        if result:
            created += 1
        else:
            failed += 1

    return created, skipped, failed


# ── Workflow Seeding ───────────────────────────────────────────────────────


def seed_workflows(force: bool = False, dry_run: bool = False, gen_icons: bool = True) -> tuple[int, int, int]:
    """Seed workflows from workflow_creator/workflows/. Returns (created, skipped, failed)."""
    with _workflow_path():
        from workflow_creator.create_workflows import (
            create_workflow,
            generate_workflow_icons,
            load_json_files,
        )
        from workflow_creator.config import resolve_or_create_agent

    workflows_dir = _workflow_dir / "workflows"
    if not workflows_dir.exists():
        print(f"  [WARN] {workflows_dir} not found — skipping workflow seeding")
        return 0, 0, 0

    json_files = sorted(workflows_dir.glob("*.json"))
    if not json_files:
        print(f"  [WARN] No JSON files in {workflows_dir}")
        return 0, 0, 0

    print(f"\n{'='*60}")
    print(f"  PHASE 3: Workflows ({len(json_files)} files)")
    print(f"{'='*60}\n")

    # Load all workflows
    all_workflows = []
    for f in json_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            all_workflows.extend(data)
        else:
            all_workflows.append(data)

    print(f"  Loaded {len(all_workflows)} workflow(s) from {len(json_files)} files\n")

    # Fetch existing
    existing_names: set[str] = set()
    if not force:
        resp = api("GET", "workflow")
        if resp.status_code == 200:
            existing_names = {w["name"] for w in resp.json()}

    created, skipped, failed = 0, 0, 0
    for w in all_workflows:
        name = w.get("name", "Unnamed")

        if not force and name in existing_names:
            # Workflow exists — still sync step agent prompts so they
            # stay up-to-date with the JSON definitions.
            steps = w.get("steps", [])
            checked = 0
            for step in steps:
                if step.get("agent_def", {}).get("system_prompt"):
                    resolve_or_create_agent(step)
                    checked += 1
            if checked:
                print(f"  [SYNC] {name} — checked {checked} agent(s)")
            else:
                print(f"  [SKIP] {name}")
            skipped += 1
            continue

        if dry_run:
            steps = len(w.get("steps", []))
            print(f"  [DRY]  would create: {name} ({steps} steps)")
            created += 1
            continue

        result = create_workflow(w)
        if result:
            created += 1
        else:
            failed += 1

    # Generate icons for new workflow wrapper agents
    if created > 0 and gen_icons and not dry_run:
        generate_workflow_icons()

    return created, skipped, failed


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Seed all VirtualAI data: LLM providers, agents, and workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_all.py                              # Seed everything
  python seed_all.py --only providers             # Only LLM providers
  python seed_all.py --only agents                # Only standalone agents
  python seed_all.py --only workflows             # Only workflows
  python seed_all.py --force                      # Re-create even if exists
  python seed_all.py --dry-run                    # Preview without creating
  python seed_all.py --llm-key sk-or-...          # Provide LLM API key
        """,
    )
    parser.add_argument(
        "--only",
        choices=["providers", "agents", "workflows"],
        help="Seed only a specific category",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-create even if name already exists",
    )
    parser.add_argument(
        "--no-icons",
        action="store_true",
        help="Skip icon generation for workflows",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes",
    )
    parser.add_argument(
        "--llm-key",
        help="API key for LLM provider (or set LLM_API_KEY env var)",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    # Sync the bare 'config' module (used by create_assistants.py via
    # `from config import ...`) with the package-imported CONFIG.  Python
    # treats bare 'config' and 'agents_creator.config' as separate modules,
    # so apply_common_args only updates the package version.
    import config as _bare_config  # noqa: E402

    _bare_config.CONFIG["base_url"] = CONFIG["base_url"]
    _bare_config.CONFIG["api_key"] = CONFIG["api_key"]

    print("\n" + "=" * 60)
    print("  VirtualAI — Seed All")
    print(f"  Target: {CONFIG['base_url']}")
    if args.dry_run:
        print("  Mode: DRY RUN (no changes)")
    if args.force:
        print("  Mode: FORCE (re-create existing)")
    print("=" * 60)

    totals = {"created": 0, "skipped": 0, "failed": 0}

    def _add(result: tuple[int, int, int]):
        totals["created"] += result[0]
        totals["skipped"] += result[1]
        totals["failed"] += result[2]

    # Phase 1: LLM Providers
    if args.only is None or args.only == "providers":
        _add(seed_llm_providers(args.llm_key, force=args.force, dry_run=args.dry_run))

    # Phase 2: Standalone Agents
    if args.only is None or args.only == "agents":
        _add(seed_agents(force=args.force, dry_run=args.dry_run))

    # Phase 3: Workflows
    if args.only is None or args.only == "workflows":
        _add(seed_workflows(force=args.force, dry_run=args.dry_run, gen_icons=not args.no_icons))

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Created: {totals['created']}")
    print(f"  Skipped: {totals['skipped']}")
    print(f"  Failed:  {totals['failed']}")
    print(f"{'='*60}\n")

    if totals["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
