"""
Register Office MCP Server in VirtualAI
========================================
Registers the unified Office MCP Server (PPT + DOCX + PDF) as an MCP server,
discovers its 91 tools, and optionally attaches them to workflow agent personas.

Usage:
    python register_office_mcp.py                           # Register with defaults
    python register_office_mcp.py --url http://host:8100    # Custom server URL
    python register_office_mcp.py --list-tools              # Just list discovered tools
    python register_office_mcp.py --attach-to-personas      # Attach MCP tools to all Office workflow personas
    python register_office_mcp.py --delete                  # Remove the MCP server

Requires the Office MCP server to be running (see office-mcp-server/docker-compose.yml).
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent tests/ dir to path so we can import from agents_creator
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from workflow_creator.config import api, add_common_args, apply_common_args

DEFAULT_SERVER_URL = "http://localhost:8100"
SERVER_NAME = "Office Document Generator"
SERVER_DESCRIPTION = (
    "Unified MCP server for creating office documents. "
    "91 tools: 37 PPT tools (ppt_*) for PowerPoint via python-pptx, "
    "54 DOCX tools (docx_*) for Word documents via python-docx, "
    "plus PDF generation via docx_convert_to_pdf."
)

# Personas that should get PPT tools (ppt_*)
PPT_PERSONAS = ["WF PPT Builder", "WF PPT Reviewer"]

# Personas that should get the FULL DOCX toolset (docx_*) — builders that write
DOCX_WRITE_PERSONAS = ["WF DOCX Builder"]

# Read-only DOCX tools — inspection only, no document mutation. Review-only
# personas get ONLY these so a "review" step can never write/re-save the
# document (which would create duplicate download files).
DOCX_READONLY_TOOL_NAMES = {
    "docx_get_document_info",
    "docx_get_document_text",
    "docx_get_document_outline",
    "docx_find_text_in_document",
    "docx_get_table_data",
    "docx_list_available_documents",
}

# Personas that should get ONLY the read-only DOCX subset (review-only)
DOCX_READONLY_PERSONAS = ["WF DOCX Reviewer"]

# Personas that should get ALL tools (both ppt_* and docx_*)
ALL_TOOL_PERSONAS = ["WF Document Builder"]


def find_existing_server(name: str) -> dict | None:
    """Find an existing MCP server by name."""
    resp = api("GET", "admin/mcp/servers")
    if resp.status_code != 200:
        return None
    for srv in resp.json().get("mcp_servers", resp.json() if isinstance(resp.json(), list) else []):
        if srv.get("name") == name:
            return srv
    return None


def register_server(server_url: str) -> int | None:
    """Register the Office MCP server via the admin API. Returns server_id."""
    existing = find_existing_server(SERVER_NAME)
    if existing:
        print(f"  [EXISTS] Server '{SERVER_NAME}' already registered (ID={existing['id']})")
        return existing["id"]

    body = {
        "name": SERVER_NAME,
        "description": SERVER_DESCRIPTION,
        "server_url": server_url,
        "auth_type": "NONE",
        "auth_performer": "ADMIN",
        "transport": "STREAMABLE_HTTP",
    }

    resp = api("POST", "admin/mcp/servers/create", body)
    if resp.status_code == 200:
        result = resp.json()
        server_id = result["server_id"]
        print(f"  [OK] Registered MCP server '{SERVER_NAME}' (ID={server_id})")
        print(f"       URL: {server_url}")
        return server_id
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] Could not register server: {resp.status_code} {err}")
        return None


def discover_tools(server_id: int) -> list[dict]:
    """Discover tools from the registered MCP server. Returns tool list."""
    print(f"\n  Discovering tools from server ID={server_id}...")

    resp = api("GET", f"admin/mcp/server/{server_id}/tools")
    if resp.status_code == 200:
        result = resp.json()
        tools = result.get("tools", [])
        ppt_count = sum(1 for t in tools if t.get("name", "").startswith("ppt_"))
        docx_count = sum(1 for t in tools if t.get("name", "").startswith("docx_"))
        print(f"  [OK] Discovered {len(tools)} tools ({ppt_count} PPT, {docx_count} DOCX)")
        return tools
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [FAIL] Tool discovery failed: {resp.status_code} {err}")
        return []


def list_tools(server_id: int) -> None:
    """List all tools from the MCP server with their IDs."""
    tools = discover_tools(server_id)
    if not tools:
        print("  No tools found.")
        return

    print(f"\n  {'ID':<6} {'Name':<45} {'Description':<55}")
    print("  " + "-" * 106)
    for t in sorted(tools, key=lambda x: x.get("name", "")):
        name = t.get("name", "?")
        desc = (t.get("description") or "")[:53]
        tid = t.get("id", t.get("tool_id", "?"))
        print(f"  {tid:<6} {name:<45} {desc}")

    print(f"\n  Total: {len(tools)} tools")

    # Print tool IDs by category
    ppt_ids = [t.get("id", t.get("tool_id")) for t in tools if t.get("name", "").startswith("ppt_")]
    docx_ids = [t.get("id", t.get("tool_id")) for t in tools if t.get("name", "").startswith("docx_")]
    all_ids = [t.get("id", t.get("tool_id")) for t in tools]
    if ppt_ids:
        print(f"\n  PPT Tool IDs ({len(ppt_ids)}):  {json.dumps(ppt_ids)}")
    if docx_ids:
        print(f"  DOCX Tool IDs ({len(docx_ids)}): {json.dumps(docx_ids)}")
    if all_ids:
        print(f"  All Tool IDs ({len(all_ids)}):  {json.dumps(all_ids)}")


def get_tool_ids_from_db(server_id: int) -> dict:
    """Get tool IDs from DB, categorized by prefix."""
    resp = api("GET", f"admin/mcp/server/{server_id}/tools/snapshots?source=db")
    if resp.status_code != 200:
        return {"ppt": [], "docx": [], "docx_readonly": [], "all": []}

    tools = resp.json()
    result = {"ppt": [], "docx": [], "docx_readonly": [], "all": []}
    for t in tools:
        tid = t["id"]
        result["all"].append(tid)
        name = t.get("name", "")
        if name.startswith("ppt_"):
            result["ppt"].append(tid)
        elif name.startswith("docx_"):
            result["docx"].append(tid)
            if name in DOCX_READONLY_TOOL_NAMES:
                result["docx_readonly"].append(tid)
    return result


def attach_tools_to_personas(tool_ids: dict) -> None:
    """Attach MCP tools to appropriate workflow personas."""
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        print(f"  [FAIL] Could not fetch personas: {resp.status_code}")
        return

    all_personas = resp.json()

    # (persona_name, tool_ids_to_assign, replace_docx)
    # replace_docx=True drops any DOCX tools NOT in the assigned set (used for
    # review-only personas so previously-attached write tools are removed).
    assignments = []
    for pname in PPT_PERSONAS:
        assignments.append((pname, tool_ids["ppt"], False))
    for pname in DOCX_WRITE_PERSONAS:
        assignments.append((pname, tool_ids["docx"], False))
    for pname in DOCX_READONLY_PERSONAS:
        assignments.append((pname, tool_ids["docx_readonly"], True))
    for pname in ALL_TOOL_PERSONAS:
        assignments.append((pname, tool_ids["all"], False))

    docx_all_ids = set(tool_ids.get("docx", []))

    for pname, mcp_tool_ids, replace_docx in assignments:
        if not mcp_tool_ids:
            continue

        persona = next((p for p in all_personas if p["name"] == pname), None)
        if not persona:
            print(f"  [SKIP] Persona '{pname}' not found — deploy the workflow first")
            continue

        existing_ids = [t["id"] for t in persona.get("tools", [])]
        if replace_docx:
            # Keep non-DOCX tools; drop existing DOCX write tools, then add the
            # read-only subset. Net effect: reviewer ends up with ONLY read-only
            # docx tools (plus any unrelated tools it already had).
            kept = [tid for tid in existing_ids if tid not in docx_all_ids]
            merged_ids = list(set(kept) | set(mcp_tool_ids))
        else:
            merged_ids = list(set(existing_ids + mcp_tool_ids))

        patch_body = {
            "name": persona["name"],
            "description": persona.get("description") or "",
            "system_prompt": persona.get("system_prompt") or "",
            "task_prompt": persona.get("task_prompt") or "",
            "num_chunks": persona.get("num_chunks", 0),
            "is_public": persona.get("is_public", True),
            "recency_bias": persona.get("recency_bias", "base_decay"),
            "llm_filter_extraction": persona.get("llm_filter_extraction", False),
            "llm_relevance_filter": persona.get("llm_relevance_filter", False),
            "replace_base_system_prompt": persona.get("replace_base_system_prompt", True),
            "datetime_aware": persona.get("datetime_aware", True),
            "document_set_ids": persona.get("document_set_ids", []),
            "tool_ids": merged_ids,
            "label_ids": [l["id"] for l in persona.get("labels", [])],
            "starter_messages": persona.get("starter_messages") or [],
            "users": [], "groups": [], "hierarchy_node_ids": [],
            "document_ids": [], "knowledge_file_ids": [],
        }

        if mcp_tool_ids == tool_ids["ppt"]:
            prefix = "ppt_*"
        elif mcp_tool_ids == tool_ids["docx"]:
            prefix = "docx_*"
        elif mcp_tool_ids == tool_ids.get("docx_readonly"):
            prefix = "docx_* (read-only)"
        else:
            prefix = "all"
        resp = api("PATCH", f"persona/{persona['id']}", patch_body)
        if resp.status_code == 200:
            print(f"  [OK] Attached {len(mcp_tool_ids)} MCP tools ({prefix}) to '{pname}' (ID={persona['id']})")
        else:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            print(f"  [FAIL] Could not update '{pname}': {resp.status_code} {err}")


def delete_server(server_id: int) -> None:
    """Delete the MCP server."""
    resp = api("DELETE", f"admin/mcp/server/{server_id}")
    if resp.status_code == 200:
        print(f"  [OK] Deleted MCP server ID={server_id}")
    else:
        print(f"  [FAIL] Could not delete server: {resp.status_code} {resp.text}")


def main():
    parser = argparse.ArgumentParser(
        description="Register Office MCP server in VirtualAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mcp-url", default=DEFAULT_SERVER_URL,
        help=f"Office MCP server URL (default: {DEFAULT_SERVER_URL})",
    )
    parser.add_argument(
        "--list-tools", action="store_true",
        help="Just list discovered tools (server must already be registered)",
    )
    parser.add_argument(
        "--attach-to-personas", action="store_true",
        help="Attach discovered MCP tools to workflow personas (PPT→PPT personas, DOCX→DOCX personas)",
    )
    parser.add_argument(
        "--delete", action="store_true",
        help="Delete the registered MCP server",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    print(f"\n--- Office MCP Server Registration ---\n")

    if args.delete:
        existing = find_existing_server(SERVER_NAME)
        if existing:
            delete_server(existing["id"])
        else:
            print(f"  Server '{SERVER_NAME}' not found")
        return

    if args.list_tools:
        existing = find_existing_server(SERVER_NAME)
        if existing:
            list_tools(existing["id"])
        else:
            print(f"  Server '{SERVER_NAME}' not registered yet. Run without --list-tools first.")
        return

    # Step 1: Register server
    server_id = register_server(args.mcp_url)
    if server_id is None:
        sys.exit(1)

    # Step 2: Discover tools
    list_tools(server_id)

    # Step 3: Get DB tool IDs categorized
    tool_ids = get_tool_ids_from_db(server_id)
    if tool_ids["all"]:
        print(f"\n  DB Tool IDs: {len(tool_ids['ppt'])} PPT, {len(tool_ids['docx'])} DOCX, {len(tool_ids['all'])} total")

    # Step 4: Optionally attach tools to workflow personas
    if args.attach_to_personas and tool_ids["all"]:
        print(f"\n--- Attaching MCP tools to workflow personas ---\n")
        attach_tools_to_personas(tool_ids)
    elif args.attach_to_personas and not tool_ids["all"]:
        print(f"\n  [WARN] No DB tool IDs to attach. Discover tools first.")

    print(f"\n--- Done ---\n")


if __name__ == "__main__":
    main()
