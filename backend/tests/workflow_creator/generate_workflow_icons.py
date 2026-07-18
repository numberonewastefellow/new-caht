"""
Generate vibrant, professional icons for ALL workflow agents using real
SVG icons from the Iconify API (200k+ icons from Material Design, Fluent,
Carbon, etc.) on vibrant gradient backgrounds.

Supports:
    --all                 Generate & upload icons for every agent in workflows 22-28
    --missing             Only generate for agents that have no icon yet
    --workflow ID         Only process agents belonging to a specific workflow ID
    --id ID               Process a single agent by ID
    --preview             Save PNGs locally without uploading
    --list                Show icon status for all workflow agents (dry-run)
    --style flat          Use flat colored icons (no background)

Dependencies:
    pip install Pillow svglib reportlab requests

Examples:
    python generate_workflow_icons.py --list
    python generate_workflow_icons.py --missing
    python generate_workflow_icons.py --all
    python generate_workflow_icons.py --all --preview
    python generate_workflow_icons.py --workflow 53
    python generate_workflow_icons.py --id 325
    python generate_workflow_icons.py --all --style flat
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
from agents_creator.generate_icon_v2 import (  # noqa: E402
    generate_icon_with_svg,
    upload_image,
    update_agent_image,
    extract_search_queries,
    find_best_icon,
    DEPARTMENT_COLORS,
)


# ── Per-agent icon overrides ──────────────────────────────────────────────
# Manually curated best icons for each workflow role. These bypass the search
# and guarantee a perfect, relevant icon for every agent.

AGENT_ICON_MAP = {
    # ── Medical Diagnosis Panel (workflow 53) ──────────────────────────
    "Medical Diagnosis Panel":       "mdi:medical-bag",
    "WF Triage Doctor":              "mdi:clipboard-pulse",
    "WF Lab Analyst":                "mdi:flask",
    "WF Primary Care Physician":     "mdi:stethoscope",
    "WF Endocrinologist":            "mdi:diabetes",
    "WF Cardiologist":               "mdi:heart-pulse",
    "WF Gastroenterologist":         "mdi:stomach",
    "WF Rheumatologist":             "mdi:bone",
    "WF Nephrologist":               "mdi:water",
    "WF Hematologist":               "mdi:blood-bag",
    "WF Diagnosis Synthesizer":      "mdi:file-document-check",

    # ── Financial Crime Investigation (workflow 54) ────────────────────
    "Financial Crime Investigation":       "mdi:shield-search",
    "WF Alert Triage Analyst":             "mdi:alert-decagram",
    "WF KYC Analyst":                      "mdi:card-account-details-star",
    "WF Transaction Pattern Analyst":      "mdi:chart-timeline-variant",
    "WF Sanctions Screening Specialist":   "mdi:cancel",
    "WF Trade Finance Investigator":       "mdi:swap-horizontal-bold",
    "WF Crypto Digital Assets Analyst":    "mdi:bitcoin",
    "WF Geopolitical Risk Analyst":        "mdi:earth",
    "WF Forensic Accountant":              "mdi:magnify-scan",
    "WF SAR Report Writer":               "mdi:file-alert",

    # ── Engineering Failure Analysis (workflow 55) ─────────────────────
    "Engineering Failure Analysis":        "mdi:wrench-cog",
    "WF Incident Triage Engineer":         "mdi:clipboard-alert",
    "WF Materials Engineer":               "mdi:hammer-wrench",
    "WF Stress Structural Analyst":        "mdi:bridge",
    "WF Corrosion Specialist":             "mdi:water-alert",
    "WF Welding Joining Engineer":         "mdi:fire",
    "WF Quality Systems Auditor":          "mdi:clipboard-check",
    "WF Thermal Fluids Engineer":          "mdi:thermometer",
    "WF Electrical Electronics Engineer":  "mdi:flash",
    "WF Root Cause Analyst":               "mdi:magnify",
    "WF Corrective Action Writer":         "mdi:file-document-edit",

    # ── Cybersecurity Incident Response (workflow 56) ──────────────────
    "Cybersecurity Incident Response":     "mdi:shield-lock",
    "WF SOC Triage Analyst":               "mdi:radar",
    "WF Network Forensics Analyst":        "mdi:lan",
    "WF Endpoint Malware Analyst":         "mdi:bug",
    "WF Identity Access Analyst":          "mdi:key-chain",
    "WF Cloud Security Analyst":           "mdi:cloud-lock",
    "WF Email Phishing Analyst":           "mdi:email-alert",
    "WF Threat Intelligence Analyst":      "mdi:crosshairs-gps",
    "WF Data Loss Analyst":                "mdi:database-alert",
    "WF Incident Report Writer":           "mdi:file-document-alert",

    # ── Insurance Claims Investigation (workflow 57) ───────────────────
    "Insurance Claims Investigation":      "mdi:shield-check",
    "WF Claims Triage Adjuster":           "mdi:clipboard-text-search",
    "WF Property Damage Assessor":         "mdi:home-alert",
    "WF Auto Accident Reconstructionist":  "mdi:car-emergency",
    "WF Medical Claims Reviewer":          "mdi:hospital-box",
    "WF Fraud Investigator":               "mdi:incognito",
    "WF Weather Catastrophe Analyst":      "mdi:weather-lightning-rainy",
    "WF Subrogation Specialist":           "mdi:scale-balance",
    "WF Policy Coverage Analyst":          "mdi:file-document-check",
    "WF Settlement Report Writer":         "mdi:cash-check",

    # ── M&A Due Diligence Panel (workflow 58) ──────────────────────────
    "M&A Due Diligence Panel":             "mdi:handshake",
    "WF Deal Triage Analyst":              "mdi:filter",
    "WF M&A Financial Analyst":            "mdi:chart-areaspline",
    "WF M&A Tax Specialist":               "mdi:calculator",
    "WF M&A Legal Analyst":                "mdi:gavel",
    "WF M&A Commercial Analyst":           "mdi:store",
    "WF M&A Technology Analyst":           "mdi:chip",
    "WF M&A HR Analyst":                   "mdi:account-group",
    "WF M&A Operations Analyst":           "mdi:cog-transfer",
    "WF M&A ESG Analyst":                  "mdi:leaf",
    "WF Investment Memo Writer":           "mdi:file-chart",

    # ── Drug Development Pipeline Review (workflow 59) ─────────────────
    "Drug Development Pipeline Review":    "mdi:pill",
    "WF Program Triage Manager":           "mdi:clipboard-flow",
    "WF Medicinal Chemist":                "mdi:flask-round-bottom",
    "WF Biostatistician":                  "mdi:chart-bell-curve-cumulative",
    "WF Toxicologist":                     "mdi:skull-crossbones",
    "WF Regulatory Affairs Specialist":    "mdi:badge-account",
    "WF Clinical Operations Analyst":      "mdi:hospital-building",
    "WF Pharmacoeconomist":                "mdi:currency-usd",
    "WF IP Patent Analyst":                "mdi:certificate",
    "WF Manufacturing CMC Specialist":     "mdi:factory",
    "WF Stage Gate Report Writer":         "mdi:gate",
}


# ── Domain-specific vibrant gradient colors ───────────────────────────────
# (top_color, bottom_color) — bright at top, darker at bottom

WORKFLOW_DOMAIN_COLORS = {
    "medical": {
        "_base":         ("#EF5350", "#B71C1C"),   # Vibrant red
        "triage":        ("#FF7043", "#BF360C"),   # Orange-red
        "lab":           ("#AB47BC", "#6A1B9A"),   # Purple
        "primary care":  ("#66BB6A", "#2E7D32"),   # Green
        "endocrin":      ("#CE93D8", "#6A1B9A"),   # Light purple
        "cardiolog":     ("#EF5350", "#C62828"),   # Bright red
        "gastro":        ("#FFA726", "#E65100"),   # Orange
        "rheumatol":     ("#42A5F5", "#0D47A1"),   # Vibrant blue (joints)
        "nephrol":       ("#29B6F6", "#0277BD"),   # Sky blue
        "hematol":       ("#F06292", "#AD1457"),   # Pink
        "synthe":        ("#26C6DA", "#00695C"),   # Teal (synthesis/merge)
    },
    "financial": {
        "_base":         ("#5C6BC0", "#1A237E"),   # Indigo
        "triage":        ("#42A5F5", "#0D47A1"),   # Blue
        "kyc":           ("#66BB6A", "#2E7D32"),   # Green
        "transaction":   ("#AB47BC", "#6A1B9A"),   # Purple
        "sanction":      ("#EF5350", "#B71C1C"),   # Red
        "trade":         ("#26C6DA", "#00838F"),   # Cyan
        "crypto":        ("#FFD54F", "#F57F17"),   # Gold
        "geopolit":      ("#FF7043", "#D84315"),   # Vibrant orange (geopolitics)
        "forensic":      ("#7C4DFF", "#311B92"),   # Electric purple (forensics)
        "sar":           ("#EC407A", "#AD1457"),   # Vibrant pink (reports)
    },
    "engineering": {
        "_base":         ("#5C6BC0", "#283593"),   # Vibrant indigo (not grey)
        "triage":        ("#42A5F5", "#0D47A1"),   # Vibrant blue (triage)
        "material":      ("#FF7043", "#BF360C"),   # Deep orange (metals/forge)
        "stress":        ("#EF5350", "#C62828"),   # Red
        "corrosion":     ("#FFA726", "#E65100"),   # Amber-orange
        "weld":          ("#FFB74D", "#E65100"),   # Amber
        "quality":       ("#66BB6A", "#2E7D32"),   # Green
        "thermal":       ("#FF7043", "#BF360C"),   # Deep orange
        "electri":       ("#42A5F5", "#0D47A1"),   # Blue
        "root cause":    ("#7C4DFF", "#311B92"),   # Purple
        "corrective":    ("#26C6DA", "#00838F"),   # Cyan
    },
    "cybersecurity": {
        "_base":         ("#7C4DFF", "#311B92"),   # Electric purple
        "soc":           ("#5C6BC0", "#1A237E"),   # Indigo
        "network":       ("#42A5F5", "#0D47A1"),   # Blue
        "endpoint":      ("#EF5350", "#B71C1C"),   # Red
        "identity":      ("#AB47BC", "#6A1B9A"),   # Purple
        "cloud":         ("#4FC3F7", "#0277BD"),   # Sky blue
        "phish":         ("#FF7043", "#D84315"),   # Orange
        "threat":        ("#EC407A", "#880E4F"),   # Vibrant magenta (threat)
        "data loss":     ("#F06292", "#AD1457"),   # Pink
        "report":        ("#26C6DA", "#00695C"),   # Teal (reports)
    },
    "insurance": {
        "_base":         ("#42A5F5", "#0D47A1"),   # Blue
        "triage":        ("#5C6BC0", "#283593"),   # Indigo
        "property":      ("#FF7043", "#BF360C"),   # Vibrant orange (property)
        "auto":          ("#5C6BC0", "#1A237E"),   # Vibrant indigo (vehicles)
        "medical":       ("#EF5350", "#C62828"),   # Red
        "fraud":         ("#FF1744", "#B71C1C"),   # Bright red
        "weather":       ("#29B6F6", "#01579B"),   # Blue
        "subrog":        ("#AB47BC", "#6A1B9A"),   # Purple
        "policy":        ("#5C6BC0", "#1A237E"),   # Indigo
        "settlement":    ("#66BB6A", "#2E7D32"),   # Green
    },
    "mna": {
        "_base":         ("#7C4DFF", "#311B92"),   # Electric purple (M&A brand)
        "deal":          ("#42A5F5", "#0D47A1"),   # Blue
        "financial":     ("#66BB6A", "#2E7D32"),   # Green
        "tax":           ("#AB47BC", "#6A1B9A"),   # Purple
        "legal":         ("#5C6BC0", "#1A237E"),   # Vibrant indigo (legal)
        "commercial":    ("#FF7043", "#D84315"),   # Orange
        "technol":       ("#4FC3F7", "#0277BD"),   # Sky blue
        "hr":            ("#F06292", "#AD1457"),   # Pink
        "operation":     ("#26C6DA", "#00695C"),   # Vibrant teal (operations)
        "esg":           ("#66BB6A", "#1B5E20"),   # Deep green
        "memo":          ("#EC407A", "#AD1457"),   # Vibrant pink (memo)
    },
    "drug": {
        "_base":         ("#42A5F5", "#0D47A1"),   # Blue
        "program":       ("#5C6BC0", "#283593"),   # Indigo
        "chemist":       ("#AB47BC", "#6A1B9A"),   # Purple
        "biostat":       ("#4FC3F7", "#0277BD"),   # Sky blue
        "toxicol":       ("#EF5350", "#B71C1C"),   # Red
        "regulat":       ("#FF7043", "#BF360C"),   # Vibrant orange (regulatory)
        "clinical":      ("#66BB6A", "#2E7D32"),   # Green
        "pharmaco":      ("#26C6DA", "#00838F"),   # Teal
        "patent":        ("#7C4DFF", "#311B92"),   # Electric purple (IP)
        "manufactur":    ("#FFA726", "#E65100"),   # Amber (factory)
        "stage gate":    ("#EC407A", "#AD1457"),   # Vibrant pink (gate)
    },
}

# Map workflow names to domain keys
WORKFLOW_NAME_TO_DOMAIN = {
    "Medical Diagnosis Panel":           "medical",
    "Financial Crime Investigation":     "financial",
    "Engineering Failure Analysis":      "engineering",
    "Cybersecurity Incident Response":   "cybersecurity",
    "Insurance Claims Investigation":    "insurance",
    "M&A Due Diligence Panel":           "mna",
    "Drug Development Pipeline Review":  "drug",
}


def _match_role_color(agent_name: str, domain_colors: dict) -> tuple[str, str]:
    """Match a agent name to the best role-specific color in the domain palette."""
    name_lower = agent_name.lower()
    for role_key, colors in domain_colors.items():
        if role_key.startswith("_"):
            continue
        if role_key in name_lower:
            return colors
    return domain_colors["_base"]


# ── Fetch helpers ─────────────────────────────────────────────────────────


def get_all_workflows() -> list[dict]:
    """Fetch all workflows from the server."""
    resp = api("GET", "workflow")
    resp.raise_for_status()
    return resp.json()


def get_all_agents_map() -> dict[int, dict]:
    """Fetch all agents, return as {id: agent_dict}."""
    resp = api("GET", "admin/agent")
    if resp.status_code != 200:
        resp = api("GET", "agent")
    resp.raise_for_status()
    return {
        p["id"]: {
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "labels": [lbl["name"] for lbl in p.get("labels", [])],
            "uploaded_image_id": p.get("uploaded_image_id"),
        }
        for p in resp.json()
    }


def collect_workflow_agents(
    workflows: list[dict],
    agent_map: dict[int, dict],
    workflow_id: int | None = None,
) -> list[dict]:
    """Collect all agents (wrapper + sub-agents) for target workflows."""
    result = []
    seen_ids = set()

    for wf in workflows:
        wf_name = wf["name"]
        domain = WORKFLOW_NAME_TO_DOMAIN.get(wf_name)
        if domain is None:
            continue

        if workflow_id is not None and wf["id"] != workflow_id:
            continue

        domain_colors = WORKFLOW_DOMAIN_COLORS[domain]

        # Wrapper agent (same name as workflow)
        for pid, pdata in agent_map.items():
            if pdata["name"] == wf_name and pid not in seen_ids:
                bg, accent = domain_colors["_base"]
                result.append({
                    **pdata,
                    "workflow_name": wf_name,
                    "workflow_id": wf["id"],
                    "domain": domain,
                    "is_wrapper": True,
                    "_colors": (bg, accent),
                })
                seen_ids.add(pid)
                break

        # Sub-agent agents from steps
        for step in wf.get("steps", []):
            pid = step.get("agent_id")
            if pid and pid in agent_map and pid not in seen_ids:
                pdata = agent_map[pid]
                bg, accent = _match_role_color(pdata["name"], domain_colors)
                result.append({
                    **pdata,
                    "workflow_name": wf_name,
                    "workflow_id": wf["id"],
                    "domain": domain,
                    "is_wrapper": False,
                    "_colors": (bg, accent),
                })
                seen_ids.add(pid)

    return result


# ── Icon generation using Iconify SVGs ────────────────────────────────────


def _inject_colors_into_v2(top_color: str, bottom_color: str):
    """Temporarily override DEPARTMENT_COLORS in v2 so get_color_for_agent
    returns our domain-specific colors regardless of label matching."""
    # We'll call generate_icon_with_svg with a fake label that maps to our colors
    DEPARTMENT_COLORS["__workflow_override__"] = (top_color, bottom_color)


def process_agent(
    agent: dict,
    preview_dir: str | None = None,
    upload: bool = True,
    style: str = "monochrome",
) -> bool:
    """Generate vibrant icon with real SVG and optionally upload."""
    name = agent["name"]
    pid = agent["id"]
    domain = agent.get("domain", "?")
    is_wrapper = agent.get("is_wrapper", False)
    role = "WRAPPER" if is_wrapper else "agent"
    top_color, bottom_color = agent["_colors"]

    print(f"\n{'='*60}")
    print(f"  [{role}] {name} (ID={pid}, domain={domain})")

    # Inject our domain colors so v2's get_color_for_agent uses them
    _inject_colors_into_v2(top_color, bottom_color)

    # Use curated icon if available, otherwise let v2 search Iconify
    curated_icon = AGENT_ICON_MAP.get(name)
    if curated_icon:
        print(f"  Curated icon: {curated_icon}")

    # Call v2's generate function with our override label
    icon_bytes, icon_used = generate_icon_with_svg(
        name,
        labels=["__workflow_override__"] + agent.get("labels", []),
        icon_id=curated_icon,
        size=256,
        style=style,
    )
    print(f"  Generated: {len(icon_bytes)} bytes")

    # Save preview
    if preview_dir:
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:50]
        path = os.path.join(preview_dir, f"{pid}_{safe}.png")
        with open(path, "wb") as f:
            f.write(icon_bytes)
        print(f"  Preview: {path}")

    if not upload:
        return True

    # Upload
    file_id = upload_image(icon_bytes, f"wf_{pid}_{name[:20]}.png")
    if not file_id:
        print(f"  [FAIL] Upload failed")
        return False
    print(f"  Uploaded: file_id={file_id}")

    # Update agent
    if update_agent_image(pid, file_id):
        print(f"  [OK] Icon set for {name}")
        return True
    else:
        print(f"  [FAIL] Could not update agent {pid}")
        return False


# ── List / status ─────────────────────────────────────────────────────────


def list_icon_status(agents: list[dict]):
    """Print a table showing icon status for all workflow agents."""
    print(f"\n{'ID':<6} {'Icon':<8} {'Type':<9} {'Domain':<15} {'Curated':<8} {'Name'}")
    print("-" * 95)

    has_icon = no_icon = 0
    for p in sorted(agents, key=lambda x: (x.get("workflow_id", 0), not x.get("is_wrapper"), x["id"])):
        icon_status = "YES" if p.get("uploaded_image_id") else "---"
        role = "WRAPPER" if p.get("is_wrapper") else "agent"
        domain = p.get("domain", "?")
        curated = "YES" if p["name"] in AGENT_ICON_MAP else "---"

        if p.get("uploaded_image_id"):
            has_icon += 1
        else:
            no_icon += 1

        if p.get("is_wrapper"):
            print(f"\n  -- Workflow {p.get('workflow_id', '?')}: {p.get('workflow_name', '?')} --")

        print(f"  {p['id']:<6} {icon_status:<8} {role:<9} {domain:<15} {curated:<8} {p['name']}")

    print(f"\n  Total: {has_icon + no_icon} agents | {has_icon} with icon | {no_icon} missing")
    curated_count = sum(1 for p in agents if p["name"] in AGENT_ICON_MAP)
    print(f"  Curated icons: {curated_count}/{len(agents)}")


# ── CLI ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate vibrant workflow icons using Iconify SVG icons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_workflow_icons.py --list                  # Show icon status
  python generate_workflow_icons.py --missing               # Only missing icons
  python generate_workflow_icons.py --all                   # Regenerate ALL
  python generate_workflow_icons.py --all --preview         # Preview only
  python generate_workflow_icons.py --workflow 53            # Medical only
  python generate_workflow_icons.py --id 325                # Single agent
  python generate_workflow_icons.py --all --style flat       # Flat colored icons
        """,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="Generate for ALL workflow agents")
    mode.add_argument("--missing", action="store_true", help="Only agents WITHOUT icons")
    mode.add_argument("--list", action="store_true", help="Show icon status (no changes)")
    mode.add_argument("--id", type=int, help="Single agent ID")

    parser.add_argument("--workflow", type=int, help="Filter to a specific workflow ID")
    parser.add_argument("--preview", action="store_true", help="Save PNGs locally, don't upload")
    parser.add_argument("--preview-dir", default="workflow_icons_preview", help="Preview directory")
    parser.add_argument("--style", choices=["monochrome", "flat"], default="monochrome",
                        help="monochrome (white icon on gradient) or flat (colored icon, no bg)")

    args = parser.parse_args()
    resolve_api_key()

    # Fetch data
    print("Fetching workflows and agents...")
    workflows = get_all_workflows()
    agent_map = get_all_agents_map()
    all_agents = collect_workflow_agents(workflows, agent_map, args.workflow)

    if not all_agents:
        print("No workflow agents found. Check that workflows are deployed.")
        sys.exit(1)

    wrappers = [p for p in all_agents if p.get("is_wrapper")]
    agents = [p for p in all_agents if not p.get("is_wrapper")]
    print(f"Found {len(wrappers)} wrapper(s) + {len(agents)} sub-agent(s) = {len(all_agents)} total")

    if args.list:
        list_icon_status(all_agents)
        return

    if args.id:
        target = next((p for p in all_agents if p["id"] == args.id), None)
        if not target:
            if args.id in agent_map:
                pdata = agent_map[args.id]
                pdata["_colors"] = ("#5C6BC0", "#283593")
                pdata["domain"] = "custom"
                pdata["is_wrapper"] = False
                target = pdata
            else:
                print(f"Agent ID {args.id} not found")
                sys.exit(1)
        process_agent(target, preview_dir=args.preview_dir if args.preview else None,
                        upload=not args.preview, style=args.style)
        return

    targets = all_agents
    if args.missing:
        targets = [p for p in all_agents if not p.get("uploaded_image_id")]
        if not targets:
            print("\nAll agents already have icons!")
            list_icon_status(all_agents)
            return
        print(f"\n{len(targets)} agent(s) missing icons")

    preview_dir = None
    if args.preview:
        preview_dir = args.preview_dir
        os.makedirs(preview_dir, exist_ok=True)
        print(f"\nPreview mode — saving to {preview_dir}/")

    scope = f"workflow {args.workflow}" if args.workflow else "all workflows"
    mode_label = "all" if args.all else "missing"
    print(f"\nProcessing {len(targets)} agents ({mode_label}, {scope}, style={args.style})...\n")

    ok, fail = 0, 0
    for agent in sorted(targets, key=lambda x: (x.get("workflow_id", 0), not x.get("is_wrapper"), x["id"])):
        if process_agent(agent, preview_dir=preview_dir, upload=not args.preview, style=args.style):
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"\nDone: {ok} succeeded, {fail} failed")
    if args.preview:
        print(f"Preview images saved to: {preview_dir}/")


if __name__ == "__main__":
    main()
