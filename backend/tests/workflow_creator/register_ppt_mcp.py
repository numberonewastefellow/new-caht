"""
Register PPT MCP Server in VirtualAI
=====================================
Registers the GongRzhe/Office-PowerPoint-MCP-Server as an MCP server,
discovers its tools, and optionally attaches them to workflow agent agents.

Usage:
    python register_ppt_mcp.py                           # Register with defaults
    python register_ppt_mcp.py --url http://host:8100    # Custom server URL
    python register_ppt_mcp.py --list-tools              # Just list discovered tools
    python register_ppt_mcp.py --attach-to-agents      # Attach MCP tools to PPT Builder/Reviewer agents
    python register_ppt_mcp.py --delete                  # Remove the MCP server

Requires the PPT MCP server to be running (see ppt-generator/docker-compose.yml).
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
SERVER_NAME = "PowerPoint Generator"
SERVER_DESCRIPTION = (
    "MCP server for creating and manipulating PowerPoint presentations. "
    "Supports creating slides, adding text/charts/tables/images, "
    "applying templates, and professional design features."
)


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
    """Register the PPT MCP server via the admin API. Returns server_id."""
    # Check if already registered
    existing = find_existing_server(SERVER_NAME)
    if existing:
        print(f"  [EXISTS] Server '{SERVER_NAME}' already registered (ID={existing['id']})")
        return existing["id"]

    # Create via the full create endpoint (sets auth_type + transport)
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
        print(f"       Auth: {result['auth_type']}")
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
        print(f"  [OK] Discovered {len(tools)} tools\n")
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

    print(f"  {'ID':<6} {'Name':<40} {'Description':<60}")
    print("  " + "-" * 106)
    for t in tools:
        name = t.get("name", "?")
        desc = (t.get("description") or "")[:58]
        tid = t.get("id", t.get("tool_id", "?"))
        print(f"  {tid:<6} {name:<40} {desc}")

    print(f"\n  Total: {len(tools)} tools")

    # Print tool IDs array for workflow JSON
    tool_ids = [t.get("id", t.get("tool_id")) for t in tools if t.get("id") or t.get("tool_id")]
    if tool_ids:
        print(f"\n  Tool IDs for agent config: {json.dumps(tool_ids)}")


def get_tool_ids_from_db(server_id: int) -> list[int]:
    """Get tool IDs already in DB for this server."""
    resp = api("GET", f"admin/mcp/server/{server_id}/tools/snapshots?source=db")
    if resp.status_code == 200:
        tools = resp.json()
        return [t["id"] for t in tools]
    return []


def attach_tools_to_agents(mcp_tool_ids: list[int]) -> None:
    """Attach MCP PPT tools to the PPT Builder and Reviewer agents."""
    agent_names = ["WF PPT Builder", "WF PPT Reviewer"]

    resp = api("GET", "admin/agent")
    if resp.status_code != 200:
        print(f"  [FAIL] Could not fetch agents: {resp.status_code}")
        return

    all_agents = resp.json()
    for pname in agent_names:
        agent = next((p for p in all_agents if p["name"] == pname), None)
        if not agent:
            print(f"  [SKIP] Agent '{pname}' not found — deploy the workflow first")
            continue

        # Merge existing tool_ids with MCP tool_ids (avoid duplicates)
        existing_ids = [t["id"] for t in agent.get("tools", [])]
        merged_ids = list(set(existing_ids + mcp_tool_ids))

        patch_body = {
            "name": agent["name"],
            "description": agent.get("description") or "",
            "system_prompt": agent.get("system_prompt") or "",
            "task_prompt": agent.get("task_prompt") or "",
            "num_chunks": agent.get("num_chunks", 0),
            "is_public": agent.get("is_public", True),
            "recency_bias": agent.get("recency_bias", "base_decay"),
            "llm_filter_extraction": agent.get("llm_filter_extraction", False),
            "llm_relevance_filter": agent.get("llm_relevance_filter", False),
            "replace_base_system_prompt": agent.get("replace_base_system_prompt", True),
            "datetime_aware": agent.get("datetime_aware", True),
            "document_set_ids": agent.get("document_set_ids", []),
            "tool_ids": merged_ids,
            "label_ids": [l["id"] for l in agent.get("labels", [])],
            "starter_messages": agent.get("starter_messages") or [],
            "users": [], "groups": [], "hierarchy_node_ids": [],
            "document_ids": [], "knowledge_file_ids": [],
        }

        resp = api("PATCH", f"agent/{agent['id']}", patch_body)
        if resp.status_code == 200:
            print(f"  [OK] Attached {len(mcp_tool_ids)} MCP tools to '{pname}' (ID={agent['id']})")
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
        description="Register PPT MCP server in VirtualAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mcp-url", default=DEFAULT_SERVER_URL,
        help=f"PPT MCP server URL (default: {DEFAULT_SERVER_URL})",
    )
    parser.add_argument(
        "--list-tools", action="store_true",
        help="Just list discovered tools (server must already be registered)",
    )
    parser.add_argument(
        "--attach-to-agents", action="store_true",
        help="Attach discovered MCP tools to WF PPT Builder and WF PPT Reviewer agents",
    )
    parser.add_argument(
        "--delete", action="store_true",
        help="Delete the registered MCP server",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    print(f"\n--- PPT MCP Server Registration ---\n")

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

    # Step 3: Get DB tool IDs for workflow config
    db_tool_ids = get_tool_ids_from_db(server_id)
    if db_tool_ids:
        print(f"\n  DB Tool IDs (use in workflow agent_def.tool_ids): {json.dumps(db_tool_ids)}")
        print(f"  Total DB tools: {len(db_tool_ids)}")

    # Step 4: Optionally attach tools to workflow agents
    if args.attach_to_agents and db_tool_ids:
        print(f"\n--- Attaching MCP tools to workflow agents ---\n")
        attach_tools_to_agents(db_tool_ids)
    elif args.attach_to_agents and not db_tool_ids:
        print(f"\n  [WARN] No DB tool IDs to attach. Discover tools first.")

    print(f"\n--- Done ---\n")


if __name__ == "__main__":
    main()
