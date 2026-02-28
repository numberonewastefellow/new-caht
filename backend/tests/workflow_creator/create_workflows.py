"""
Bulk Workflow Creator & Manager for VirtualAI
==============================================
Creates, updates, lists, deletes, and runs workflows from JSON files via the API.

Usage:
    python create_workflows.py                          # Create from workflows/ folder
    python create_workflows.py --file my_workflow.json  # Create from a specific file
    python create_workflows.py --list                   # List existing workflows
    python create_workflows.py --delete 5               # Delete workflow by ID
    python create_workflows.py --export out.json        # Export all workflows to JSON
    python create_workflows.py --run 1 "Hello world"    # Run a workflow with a message
    python create_workflows.py --update                 # Update existing workflows by name
    python create_workflows.py --backfill-personas      # Create wrapper personas for all workflows
    python create_workflows.py --no-icons               # Create without generating icons

API key is read from agents_creator/apikey.txt, .env, or VIRTUALAI_API_KEY env var.
"""

import argparse
import json
import sys
from pathlib import Path

from config import (
    WORKFLOW_DEFAULTS,
    WORKFLOWS_DIR,
    add_common_args,
    api,
    apply_common_args,
    resolve_or_create_persona,
    stream_api,
)


# ── Core Actions ────────────────────────────────────────────────────────────


def list_workflows():
    """List all workflows from the server."""
    resp = api("GET", "workflow")
    resp.raise_for_status()
    workflows = resp.json()
    print(f"\n{'ID':<6} {'Name':<35} {'Mode':<15} {'Steps':<6} {'Public'}")
    print("-" * 80)
    for w in workflows:
        steps = len(w.get("steps", []))
        mode = w.get("orchestration_mode", "?")
        public = "Yes" if w.get("is_public") else "No"
        print(f"{w['id']:<6} {w['name']:<35} {mode:<15} {steps:<6} {public}")
    print(f"\nTotal: {len(workflows)} workflows\n")


def _update_persona_starter_messages(persona_id: int, starter_messages: list[dict]) -> None:
    """Update an existing persona's starter_messages via PATCH."""
    # First fetch the current persona to preserve existing fields
    resp = api("GET", f"persona/{persona_id}")
    if resp.status_code != 200:
        print(f"  [WARN] Could not fetch persona {persona_id} for starter messages")
        return

    p = resp.json()
    patch_body = {
        "name": p["name"],
        "description": p.get("description") or "",
        "system_prompt": p.get("system_prompt") or "",
        "task_prompt": p.get("task_prompt") or "",
        "num_chunks": p.get("num_chunks", 0),
        "is_public": p.get("is_public", True),
        "recency_bias": p.get("recency_bias", "base_decay"),
        "llm_filter_extraction": p.get("llm_filter_extraction", False),
        "llm_relevance_filter": p.get("llm_relevance_filter", False),
        "replace_base_system_prompt": p.get("replace_base_system_prompt", True),
        "datetime_aware": p.get("datetime_aware", True),
        "document_set_ids": p.get("document_set_ids", []),
        "tool_ids": [t["id"] for t in p.get("tools", [])],
        "label_ids": [l["id"] for l in p.get("labels", [])],
        "starter_messages": starter_messages,
        "users": [], "groups": [], "hierarchy_node_ids": [],
        "document_ids": [], "user_file_ids": [],
    }

    resp = api("PATCH", f"persona/{persona_id}", patch_body)
    if resp.status_code == 200:
        print(f"  [OK]  Starter messages set for {p['name']} (ID={persona_id})")
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [WARN] Failed to set starter messages for {p['name']}: {resp.status_code} {err}")


def _resolve_steps(raw_steps: list[dict]) -> list[dict]:
    """Resolve persona references in step definitions.

    Each step can have:
      - persona_id: int (used directly)
      - persona_name: str (resolved by lookup, auto-created if missing)
      - persona_def: dict (full definition for auto-creation)
    """
    resolved = []
    for step in raw_steps:
        persona_id = resolve_or_create_persona(step)
        if persona_id is None:
            print(f"  [SKIP] Step '{step.get('step_name', '?')}': no persona resolved")
            continue

        # Update starter_messages on the sub-agent persona if defined
        persona_def = step.get("persona_def", {})
        sub_starter = persona_def.get("starter_messages")
        if sub_starter and persona_id:
            _update_persona_starter_messages(persona_id, sub_starter)

        resolved.append({
            "persona_id": persona_id,
            "step_order": step.get("step_order", len(resolved)),
            "step_name": step["step_name"],
            "step_description": step.get("step_description"),
            "input_mapping": step.get("input_mapping"),
            "output_key": step.get("output_key", "output"),
            "condition": step.get("condition"),
            "is_terminal": step.get("is_terminal", False),
        })
    return resolved


def _update_wrapper_persona_starter_messages(
    workflow_name: str,
    starter_messages: list[dict],
) -> None:
    """Update the wrapper persona's starter_messages after workflow creation.

    The backend auto-creates a wrapper persona with the same name as the
    workflow. This function finds it and PATCHes the starter_messages.
    """
    # Find the wrapper persona by name
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"  [WARN] Could not fetch personas to set starter messages")
        return

    wrapper = None
    for p in resp.json():
        if p["name"] == workflow_name:
            wrapper = p
            break

    if wrapper is None:
        print(f"  [WARN] Wrapper persona '{workflow_name}' not found for starter messages")
        return

    # Build PATCH body preserving existing fields
    patch_body = {
        "name": wrapper["name"],
        "description": wrapper.get("description", ""),
        "system_prompt": wrapper.get("system_prompt") or "",
        "task_prompt": wrapper.get("task_prompt") or "",
        "num_chunks": wrapper.get("num_chunks", 0),
        "is_public": wrapper.get("is_public", True),
        "recency_bias": wrapper.get("recency_bias", "base_decay"),
        "llm_filter_extraction": wrapper.get("llm_filter_extraction", False),
        "llm_relevance_filter": wrapper.get("llm_relevance_filter", False),
        "replace_base_system_prompt": wrapper.get("replace_base_system_prompt", True),
        "datetime_aware": wrapper.get("datetime_aware", True),
        "document_set_ids": wrapper.get("document_set_ids", []),
        "tool_ids": [t["id"] for t in wrapper.get("tools", [])],
        "label_ids": [l["id"] for l in wrapper.get("labels", [])],
        "starter_messages": starter_messages,
        "users": [],
        "groups": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
        "user_file_ids": [],
    }

    resp = api("PATCH", f"persona/{wrapper['id']}", patch_body)
    if resp.status_code == 200:
        print(f"  [OK]  Starter messages set for wrapper persona ID={wrapper['id']}")
    else:
        try:
            err_detail = resp.json()
        except Exception:
            err_detail = resp.text
        print(f"  [WARN] Failed to set starter messages: {resp.status_code} {err_detail}")


def create_workflow(payload: dict) -> dict | None:
    """Create a single workflow. Returns the response dict or None on failure."""
    body = {**WORKFLOW_DEFAULTS, **payload}
    name = body.get("name", "Unnamed")

    # Extract wrapper starter_messages before sending to workflow API
    wrapper_starter_messages = body.pop("starter_messages", None)

    # Resolve step persona references
    raw_steps = body.pop("steps", [])
    body["steps"] = _resolve_steps(raw_steps)

    if not body["steps"]:
        print(f"  [FAIL] {name}: no valid steps after resolution")
        return None

    resp = api("POST", "admin/workflow", body)

    if resp.status_code == 200:
        result = resp.json()
        step_count = len(result.get("steps", []))
        print(f"  [OK]  ID={result['id']}  {name}  ({step_count} steps)")

        # Set starter messages on the wrapper persona
        if wrapper_starter_messages:
            _update_wrapper_persona_starter_messages(name, wrapper_starter_messages)

        return result
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] {name} -> {resp.status_code}: {err}")
        return None


def update_workflow(workflow_id: int, payload: dict) -> dict | None:
    """Update an existing workflow by ID."""
    name = payload.get("name", "Unnamed")

    # Resolve steps if present
    if "steps" in payload:
        raw_steps = payload.pop("steps")
        payload["steps"] = _resolve_steps(raw_steps)

    resp = api("PATCH", f"admin/workflow/{workflow_id}", payload)

    if resp.status_code == 200:
        result = resp.json()
        print(f"  [OK]  ID={workflow_id}  {name}")
        return result
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] ID={workflow_id}  {name} -> {resp.status_code}: {err}")
        return None


def delete_workflow(workflow_id: int):
    """Delete a workflow by ID."""
    resp = api("DELETE", f"admin/workflow/{workflow_id}")
    if resp.status_code == 200:
        print(f"Deleted workflow ID={workflow_id}")
    else:
        print(f"Failed to delete ID={workflow_id}: {resp.status_code} {resp.text}")


def export_workflows(output_file: str):
    """Export all workflows to a JSON file."""
    resp = api("GET", "workflow")
    resp.raise_for_status()
    workflows = resp.json()

    exported = []
    for w in workflows:
        exported.append({
            "name": w["name"],
            "description": w.get("description"),
            "orchestration_mode": w.get("orchestration_mode", "llm_decision"),
            "orchestrator_prompt": w.get("orchestrator_prompt"),
            "max_steps": w.get("max_steps", 10),
            "timeout_seconds": w.get("timeout_seconds", 1800),
            "is_public": w.get("is_public", True),
            "icon_name": w.get("icon_name"),
            "steps": [
                {
                    "persona_id": s["persona_id"],
                    "persona_name": s.get("persona_name"),
                    "step_order": s["step_order"],
                    "step_name": s["step_name"],
                    "step_description": s.get("step_description"),
                    "input_mapping": s.get("input_mapping"),
                    "output_key": s.get("output_key", "output"),
                    "condition": s.get("condition"),
                    "is_terminal": s.get("is_terminal", False),
                }
                for s in w.get("steps", [])
            ],
        })
        print(f"  Exported: {w['name']}")

    out = Path(output_file)
    out.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    print(f"\nExported {len(exported)} workflows to {out}")


def _safe_print(text: str, **kwargs):
    """Print with Unicode fallback for Windows terminals (cp1252)."""
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Strip non-encodable characters for the current terminal
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="ignore").decode(
            sys.stdout.encoding or "utf-8", errors="ignore"
        )
        print(safe, **kwargs)


def run_workflow_cli(workflow_id: int, message: str):
    """Run a workflow and stream the output to the console.

    Uses stream_api() with stream=True and a 5-minute timeout so the
    response can be iterated line-by-line as the workflow executes.
    """
    print(f"\n--- Running workflow ID={workflow_id} ---")
    print(f"Message: {message}\n")

    resp = stream_api("POST", f"workflow/{workflow_id}/run", {
        "message": message,
    })

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}")
        return

    # Stream the SSE response line-by-line
    print("--- Streaming Output ---\n")
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)
            obj = packet.get("obj", packet)
            ptype = obj.get("type", "unknown")

            if ptype == "workflow_step_start":
                step_name = obj.get("step_name", "?")
                persona = obj.get("persona_name", "?")
                _safe_print(f"\n[Step: {step_name}] (Agent: {persona})")
                print("-" * 50)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                _safe_print(content)

            elif ptype == "workflow_step_end":
                step_name = obj.get("step_name", "?")
                _safe_print(f"\n[End: {step_name}]")

            elif ptype == "workflow_orchestrator_thinking":
                content = obj.get("content", "")
                _safe_print(f"\n[Orchestrator] {content}")

            # AgentResponseStart serializes as "message_start"
            elif ptype == "message_start":
                print("\n[Final Answer]")
                print("-" * 50)

            # AgentResponseDelta serializes as "message_delta"
            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                _safe_print(content, end="", flush=True)

            elif ptype == "message_end":
                pass  # End of message stream

            elif ptype == "stop":
                print("\n\n--- Workflow Complete ---")

            elif ptype == "section_end":
                pass  # Section separator

            elif ptype in (
                "reasoning_start", "reasoning_delta", "reasoning_end",
                "reasoning_done",
            ):
                pass  # Internal LLM reasoning packets — suppress

            else:
                # Print raw for debugging
                _safe_print(f"  [{ptype}] {json.dumps(obj)[:200]}")

        except json.JSONDecodeError:
            _safe_print(f"  [RAW] {line[:200]}")

    print()


def backfill_personas():
    """Create wrapper personas for all existing workflows."""
    resp = api("POST", "admin/workflow/backfill-personas")
    if resp.status_code == 200:
        print(resp.json().get("detail", "Done"))
    else:
        print(f"Failed: {resp.status_code} {resp.text}")


# ── Icon Generation ─────────────────────────────────────────────────────────


def generate_workflow_icons():
    """Generate and upload icons for all workflow wrapper personas.

    Imports generate_icon from the sibling workflow generate_icon module,
    which in turn uses agents_creator/generate_icon.py for the actual
    image generation and upload logic.
    """
    try:
        from generate_icon import get_workflow_personas
        from agents_creator.generate_icon import process_agent
    except ImportError as e:
        print(f"  [WARN] Icon generation skipped (missing dependency: {e})")
        print("         Install Pillow: pip install Pillow")
        return

    personas = get_workflow_personas()
    if not personas:
        print("  [INFO] No workflow wrapper personas found for icon generation")
        return

    print(f"\n--- Generating icons for {len(personas)} workflow persona(s) ---\n")
    ok, fail = 0, 0
    for agent in personas:
        if process_agent(agent):
            ok += 1
        else:
            fail += 1
    print(f"\nIcons: {ok} generated, {fail} failed\n")


# ── Bulk Load ───────────────────────────────────────────────────────────────


def load_json_files(source: str | None) -> list[dict]:
    """Load workflow definitions from a file or the workflows/ folder."""
    if source:
        p = Path(source)
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]

    if not WORKFLOWS_DIR.exists():
        print(f"ERROR: Workflows folder not found: {WORKFLOWS_DIR}")
        print("Create it and add JSON files, or use --file to specify a file.")
        sys.exit(1)

    json_files = sorted(WORKFLOWS_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {WORKFLOWS_DIR}")
        sys.exit(1)

    all_workflows = []
    for f in json_files:
        print(f"Loading: {f.name}")
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            all_workflows.extend(data)
        else:
            all_workflows.append(data)

    return all_workflows


def bulk_create(source: str | None, skip_existing: bool = True, gen_icons: bool = True):
    """Create workflows from JSON files, then optionally generate icons."""
    workflows = load_json_files(source)
    print(f"\nFound {len(workflows)} workflow(s) to create\n")

    existing_names = set()
    if skip_existing:
        resp = api("GET", "workflow")
        if resp.status_code == 200:
            existing_names = {w["name"] for w in resp.json()}

    created, skipped, failed = 0, 0, 0
    for w in workflows:
        name = w.get("name", "Unnamed")
        if skip_existing and name in existing_names:
            print(f"  [SKIP] {name} (already exists)")
            skipped += 1
            continue

        result = create_workflow(w)
        if result:
            created += 1
        else:
            failed += 1

    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed\n")

    # Auto-generate icons for the newly created workflow wrapper personas
    if created > 0 and gen_icons:
        generate_workflow_icons()


def bulk_update(source: str | None):
    """Update existing workflows from JSON files, matching by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch workflows: {resp.status_code}")
        sys.exit(1)

    all_workflows = resp.json()
    name_to_id = {w["name"]: w["id"] for w in all_workflows}

    workflows = load_json_files(source)
    print(f"\nFound {len(workflows)} workflow(s) to update\n")

    updated, skipped, failed = 0, 0, 0
    for w in workflows:
        name = w.get("name", "Unnamed")
        if name not in name_to_id:
            print(f"  [SKIP] {name} (not found on server)")
            skipped += 1
            continue

        result = update_workflow(name_to_id[name], w)
        if result:
            updated += 1
        else:
            failed += 1

    print(f"\nDone: {updated} updated, {skipped} skipped, {failed} failed\n")


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Bulk create/update/manage VirtualAI workflows from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_workflows.py                          # Create from workflows/ folder
  python create_workflows.py --file workflow.json     # Create from specific file
  python create_workflows.py --update                 # Update ALL from workflows/ folder
  python create_workflows.py --list                   # List all workflows
  python create_workflows.py --delete 5               # Delete workflow ID=5
  python create_workflows.py --export backup.json     # Export workflows to JSON
  python create_workflows.py --run 1 "test message"   # Run a workflow
  python create_workflows.py --backfill-personas      # Create wrapper personas
  python create_workflows.py --force                  # Create even if name exists
  python create_workflows.py --no-icons               # Skip icon generation
        """,
    )
    parser.add_argument("--file", "-f", help="Path to a specific JSON file")
    parser.add_argument("--update", "-u", action="store_true", help="Update existing workflows from JSON")
    parser.add_argument("--list", "-l", action="store_true", help="List existing workflows")
    parser.add_argument("--delete", "-d", type=int, help="Delete workflow by ID")
    parser.add_argument("--export", "-e", help="Export all workflows to a JSON file")
    parser.add_argument("--run", "-r", nargs=2, metavar=("ID", "MESSAGE"), help="Run a workflow: --run 1 'Hello'")
    parser.add_argument("--backfill-personas", action="store_true", help="Create wrapper personas for existing workflows")
    parser.add_argument("--force", action="store_true", help="Create even if workflow name already exists")
    parser.add_argument("--no-icons", action="store_true", help="Skip automatic icon generation after create")
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    if args.list:
        list_workflows()
    elif args.delete is not None:
        delete_workflow(args.delete)
    elif args.export:
        export_workflows(args.export)
    elif args.run:
        run_workflow_cli(int(args.run[0]), args.run[1])
    elif args.backfill_personas:
        backfill_personas()
    elif args.update:
        bulk_update(args.file)
    else:
        bulk_create(args.file, skip_existing=not args.force, gen_icons=not args.no_icons)


if __name__ == "__main__":
    main()
