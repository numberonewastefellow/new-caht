"""
Shared configuration for the Workflow Creator toolkit.

Reuses the API client, key resolution, and label helpers from agents_creator.
Adds workflow-specific defaults and helper functions.

API key resolution order:
    1. --key CLI argument
    2. apikey.txt file in agents_creator folder
    3. .env file in agents_creator folder (VIRTUALAI_API_KEY=...)
    4. VIRTUALAI_API_KEY environment variable
"""

import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

# Add parent tests/ dir to path so we can import from agents_creator
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from agents_creator.config import (  # noqa: E402
    CONFIG,
    DEFAULTS as PERSONA_DEFAULTS,
    add_common_args,
    api,
    apply_common_args,
    get_or_create_labels,
    headers,
    resolve_api_key,
)

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
WORKFLOWS_DIR = ROOT_DIR / "workflows"

# ── Default payload values for new workflows ────────────────────────────────
WORKFLOW_DEFAULTS = {
    "orchestration_mode": "llm_decision",
    "max_steps": 10,
    "timeout_seconds": 1800,
    "is_public": True,
}

# ── Default persona payload for auto-created step personas ──────────────────
STEP_PERSONA_DEFAULTS = {
    "num_chunks": 10.0,
    "is_public": True,
    "recency_bias": "base_decay",
    "llm_filter_extraction": False,
    "llm_relevance_filter": False,
    "replace_base_system_prompt": True,
    "datetime_aware": True,
    "task_prompt": "",
    "document_set_ids": [],
    "tool_ids": [1],  # Internal Search
    "users": [],
    "groups": [],
    "label_ids": [],
    "user_file_ids": [],
    "hierarchy_node_ids": [],
    "document_ids": [],
}


# ── Streaming API helper ────────────────────────────────────────────────────


def stream_api(method: str, path: str, data: dict | None = None) -> requests.Response:
    """Make a streaming API call (for workflow run endpoints).

    Unlike the regular api() helper, this uses stream=True and a longer timeout
    so the response can be iterated line-by-line as an SSE stream.
    """
    url = urljoin(CONFIG["base_url"] + "/", f"api/{path.lstrip('/')}")
    return requests.request(
        method, url, headers=headers(), json=data, timeout=600, stream=True
    )


# ── Tool Resolution ────────────────────────────────────────────────────────

_tool_cache: dict[str, int] = {}


def _load_tool_cache() -> None:
    """Populate tool cache from the server (in_code_tool_id -> db ID)."""
    if _tool_cache:
        return
    resp = api("GET", "tool")
    if resp.status_code == 200:
        for t in resp.json():
            code_id = t.get("in_code_tool_id")
            if code_id:
                _tool_cache[code_id.lower()] = t["id"]


def resolve_tool_names(tool_names: list[str]) -> list[int]:
    """Resolve a list of in_code_tool_id names (e.g. 'PythonTool') to DB IDs."""
    _load_tool_cache()
    ids: list[int] = []
    for name in tool_names:
        tid = _tool_cache.get(name.lower())
        if tid is not None:
            ids.append(tid)
        else:
            print(f"  [WARN] Tool '{name}' not found on server — skipping")
    return ids


# ── Persona Resolution ──────────────────────────────────────────────────────

_persona_cache: dict[str, int] = {}


def resolve_persona_id(name: str) -> int | None:
    """Resolve a persona name to its ID. Returns None if not found."""
    if not _persona_cache:
        resp = api("GET", "persona")
        if resp.status_code == 200:
            for p in resp.json():
                _persona_cache[p["name"].lower()] = p["id"]

    return _persona_cache.get(name.lower())


def create_step_persona(persona_def: dict) -> int | None:
    """Create a persona for a workflow step. Returns the new persona ID.

    The created persona stays visible in the agent listing so users can
    edit its prompt, tools, or knowledge sources directly from the UI.
    """
    body = {**STEP_PERSONA_DEFAULTS, **persona_def}

    # Resolve label names → IDs if present
    label_names = body.pop("labels", None)
    if label_names and isinstance(label_names, list):
        body["label_ids"] = get_or_create_labels(label_names)

    # Resolve tool names → IDs if present (e.g. "PythonTool" → db ID)
    tool_names = body.pop("tool_names", None)
    if tool_names and isinstance(tool_names, list):
        body["tool_ids"] = resolve_tool_names(tool_names)

    resp = api("POST", "persona", body)
    if resp.status_code == 200:
        result = resp.json()
        persona_id = result["id"]
        name = body.get("name", "Unknown")
        _persona_cache[name.lower()] = persona_id
        print(f"  [PERSONA] Created: {name} (ID={persona_id})")
        return persona_id
    else:
        print(f"  [FAIL] Could not create persona: {resp.status_code} {resp.text[:200]}")
        return None


def _update_step_persona(persona_id: int, persona_def: dict) -> bool:
    """Update an existing step persona's prompt, description, tools, and labels.

    Compares all mutable fields against the current server state and only
    PATCHes when something actually changed.  Returns True if a PATCH was
    performed, False otherwise.
    """
    resp = api("GET", f"persona/{persona_id}")
    if resp.status_code != 200:
        print(f"  [WARN] Could not fetch persona {persona_id} for update")
        return False

    p = resp.json()

    # ── Compute old vs new for every mutable field ──
    old_prompt = p.get("system_prompt") or ""
    new_prompt = persona_def.get("system_prompt", "")

    old_desc = p.get("description") or ""
    new_desc = persona_def.get("description", old_desc)

    old_tool_ids = sorted(t["id"] for t in p.get("tools", []))
    new_tool_ids = old_tool_ids  # default: keep existing
    tool_names = persona_def.get("tool_names")
    if tool_names and isinstance(tool_names, list):
        new_tool_ids = sorted(resolve_tool_names(tool_names))

    old_label_ids = sorted(l["id"] for l in p.get("labels", []))
    new_label_ids = old_label_ids  # default: keep existing
    label_names = persona_def.get("labels")
    if label_names and isinstance(label_names, list):
        new_label_ids = sorted(get_or_create_labels(label_names))

    # Skip if nothing changed
    if (old_prompt == new_prompt and old_desc == new_desc
            and old_tool_ids == new_tool_ids and old_label_ids == new_label_ids):
        return False

    patch_body = {
        "name": p["name"],
        "description": new_desc,
        "system_prompt": new_prompt,
        "task_prompt": p.get("task_prompt") or "",
        "num_chunks": p.get("num_chunks", 0),
        "is_public": p.get("is_public", True),
        "recency_bias": p.get("recency_bias", "base_decay"),
        "llm_filter_extraction": p.get("llm_filter_extraction", False),
        "llm_relevance_filter": p.get("llm_relevance_filter", False),
        "replace_base_system_prompt": p.get("replace_base_system_prompt", True),
        "datetime_aware": p.get("datetime_aware", True),
        "document_set_ids": p.get("document_set_ids", []),
        "tool_ids": new_tool_ids,
        "label_ids": new_label_ids,
        "starter_messages": p.get("starter_messages", []),
        "users": [], "groups": [], "hierarchy_node_ids": [],
        "document_ids": [], "user_file_ids": [],
    }

    resp = api("PATCH", f"persona/{persona_id}", patch_body)
    if resp.status_code == 200:
        print(f"  [PATCH] Updated {p['name']} (ID={persona_id})")
        return True
    else:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  [WARN] Failed to update {p['name']}: {resp.status_code} {err}")
        return False


def resolve_or_create_persona(step_def: dict) -> int | None:
    """Resolve persona_name to persona_id, auto-creating if needed.

    The step definition should have either:
      - persona_id: int (used directly)
      - persona_name: str (resolved by name, auto-created if missing)
      - persona_def: dict (full persona definition for auto-creation)

    If the persona already exists and a persona_def is provided, the existing
    persona's prompt, description, and tools are updated to match the definition.
    """
    # Direct ID
    if "persona_id" in step_def and step_def["persona_id"]:
        return step_def["persona_id"]

    # By name
    name = step_def.get("persona_name", "")
    if name:
        pid = resolve_persona_id(name)
        if pid is not None:
            # Update the existing persona's prompt if a persona_def is provided
            persona_def = step_def.get("persona_def", {})
            if persona_def and persona_def.get("system_prompt"):
                _update_step_persona(pid, persona_def)
            return pid

    # Auto-create from embedded definition
    persona_def = step_def.get("persona_def", {})
    if not persona_def and name:
        # Minimal auto-creation with just the name and system_prompt
        persona_def = {
            "name": name,
            "description": step_def.get("step_description", f"Agent: {name}"),
            "system_prompt": step_def.get("system_prompt", f"You are {name}."),
        }

    if persona_def:
        return create_step_persona(persona_def)

    print(f"  [WARN] Cannot resolve persona for step: {step_def.get('step_name', '?')}")
    return None
