"""
Generate professional avatar icons for workflow wrapper personas and upload them.

Reuses the icon generation logic from agents_creator/generate_icon.py with
workflow-specific color palette additions.

Usage:
    python generate_icon.py --all-workflows       # Generate & upload for all workflow personas
    python generate_icon.py --id ID               # Generate & upload for a specific persona ID
    python generate_icon.py --preview             # Generate preview images without uploading
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent tests/ dir to path so we can import from agents_creator
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from agents_creator.config import resolve_api_key, api  # noqa: E402
from agents_creator.generate_icon import (  # noqa: E402
    DEPARTMENT_COLORS,
    generate_icon,
    process_agent,
    get_all_personas,
)

# ── Workflow-specific colors ────────────────────────────────────────────────
# Add workflow label to the department colors palette
DEPARTMENT_COLORS["workflow"] = ("#1A237E", "#7C4DFF")  # Deep indigo + vivid purple
DEPARTMENT_COLORS["multi-agent"] = ("#311B92", "#B388FF")  # Deep purple
DEPARTMENT_COLORS["research"] = ("#0D47A1", "#42A5F5")  # Deep blue
DEPARTMENT_COLORS["code review"] = ("#1B5E20", "#66BB6A")  # Green
DEPARTMENT_COLORS["customer support"] = ("#E65100", "#FF9800")  # Orange
DEPARTMENT_COLORS["travel"] = ("#00695C", "#26A69A")  # Teal


def get_workflow_personas() -> list[dict]:
    """Fetch all personas that are workflow wrappers (have the 'Workflow' label)."""
    personas = get_all_personas()
    return [
        p for p in personas
        if any(lbl.lower() == "workflow" for lbl in p.get("labels", []))
    ]


def main():
    parser = argparse.ArgumentParser(description="Generate and upload workflow persona icons")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-workflows", action="store_true", help="Process all workflow wrapper personas")
    group.add_argument("--id", type=int, help="Process a specific persona ID")
    group.add_argument("--preview", action="store_true", help="Generate preview images only (no upload)")
    parser.add_argument("--preview-dir", type=str, default="workflow_icons_preview", help="Directory for preview images")

    args = parser.parse_args()
    resolve_api_key()

    if args.preview:
        personas = get_workflow_personas()
        if not personas:
            print("No workflow personas found. Create workflows first or run --backfill-personas.")
            return
        os.makedirs(args.preview_dir, exist_ok=True)
        print(f"Generating preview icons for {len(personas)} workflow personas...")
        for agent in personas:
            process_agent(agent, preview_dir=args.preview_dir, upload=False)
        print(f"\nDone! Preview icons saved to: {args.preview_dir}/")
        return

    if args.id:
        personas = get_all_personas()
        agent = next((p for p in personas if p["id"] == args.id), None)
        if not agent:
            print(f"Persona ID {args.id} not found")
            sys.exit(1)
        process_agent(agent)
        return

    if args.all_workflows:
        personas = get_workflow_personas()
        if not personas:
            print("No workflow personas found. Create workflows first or run --backfill-personas.")
            return
        print(f"Processing {len(personas)} workflow personas...")
        ok, fail = 0, 0
        for agent in personas:
            if process_agent(agent):
                ok += 1
            else:
                fail += 1
        print(f"\nDone: {ok} succeeded, {fail} failed")
        return


if __name__ == "__main__":
    main()
