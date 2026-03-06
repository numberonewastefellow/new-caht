"""
Generate and deploy starter messages for all agents missing them.

Reads each agent's system_prompt, uses an LLM to generate 3-4 relevant
starter questions, then PATCHes the persona.

Usage:
    python generate_starter_messages.py --list              # Show which agents are missing starters
    python generate_starter_messages.py --all               # Generate & deploy for all missing
    python generate_starter_messages.py --id 325            # Single agent
    python generate_starter_messages.py --preview           # Generate but don't upload
    python generate_starter_messages.py --workflow 53       # Only agents in a specific workflow
    python generate_starter_messages.py --dry-run           # Show what would be generated (no LLM call)

Dependencies:
    pip install openai   (or use any OpenAI-compatible API)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent tests/ dir to path
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from agents_creator.config import api, resolve_api_key  # noqa: E402

# ── LLM Configuration ────────────────────────────────────────────────────

LLM_CONFIG = {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-5-mini",
    "api_key": "",  # Auto-resolved from VirtualAI admin config
}


def _resolve_openai_key():
    """Pull OpenAI API key from env, local file, or VirtualAI admin config."""
    # 1. Environment variable
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        LLM_CONFIG["api_key"] = key
        return

    # 2. Local key file (gpt_key in same directory)
    key_file = Path(__file__).parent / "gpt_key"
    if key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            LLM_CONFIG["api_key"] = key
            return

    # 3. From VirtualAI admin LLM provider config
    try:
        resp = api("GET", "admin/llm/provider")
        if resp.status_code == 200:
            for p in resp.json():
                if p.get("provider") == "openai" and p.get("api_key"):
                    LLM_CONFIG["api_key"] = p["api_key"]
                    LLM_CONFIG["model"] = p.get("default_model_name") or LLM_CONFIG["model"]
                    return
    except Exception:
        pass

GENERATION_PROMPT_TEMPLATE = (
    "You are a UX expert creating starter message buttons for an AI assistant chatbot.\n\n"
    "Given the assistant's system prompt below, generate exactly 4 starter messages that "
    "a user would click to begin a conversation. Each starter message should:\n\n"
    "1. Be a realistic, specific question or request that showcases the assistant's capabilities\n"
    "2. Be concise (under 80 characters for the title, under 150 for the description)\n"
    "3. Cover different aspects of what the assistant can do\n"
    "4. Use natural language as if a real user is asking\n\n"
    'Return ONLY a JSON array with exactly 4 objects, each having:\n'
    '- "name": Short button title (the question/request)\n'
    '- "description": Brief elaboration or context\n'
    '- "message": The actual message sent when clicked (can be same as name or slightly expanded)\n\n'
    "IMPORTANT: Return ONLY the JSON array, no markdown, no explanation.\n\n"
    "---\n\n"
    "ASSISTANT SYSTEM PROMPT:\n"
)


def generate_starters_via_llm(name: str, system_prompt: str) -> list[dict] | None:
    """Call GPT to generate starter messages based on the system prompt."""
    import requests

    if not LLM_CONFIG.get("api_key"):
        print(f"    [ERR] No OpenAI API key configured")
        return None

    prompt_text = GENERATION_PROMPT_TEMPLATE + system_prompt[:3000]

    headers = {
        "Authorization": f"Bearer {LLM_CONFIG['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{LLM_CONFIG['base_url']}/chat/completions",
            json={
                "model": LLM_CONFIG["model"],
                "messages": [{"role": "user", "content": prompt_text}],
                "max_completion_tokens": 4000,
            },
            headers=headers,
            timeout=60,
        )

        if resp.status_code != 200:
            print(f"    [ERR] API {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"    [ERR] API call failed: {e}")
        return None

    if not content:
        return None

    # Parse JSON from response (strip markdown fences if present)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        starters = json.loads(content)
        if isinstance(starters, list) and len(starters) >= 2:
            return starters[:4]
        if isinstance(starters, dict):
            # Model may wrap in an object
            for key in ("starters", "starter_messages", "messages", "data"):
                if key in starters and isinstance(starters[key], list):
                    return starters[key][:4]
        print(f"    [ERR] Invalid format: {content[:200]}")
        return None
    except json.JSONDecodeError as e:
        print(f"    [ERR] JSON parse: {e}")
        print(f"    Raw: {content[:300]}")
        return None


def generate_starters_heuristic(name: str, system_prompt: str) -> list[dict]:
    """Fallback: generate basic starters from prompt analysis without LLM."""
    # Extract key capabilities from the prompt
    prompt_lower = system_prompt.lower()

    # Generic but relevant starters based on name
    clean_name = name.replace("WF ", "").replace("UPS ", "")

    return [
        {
            "name": f"What can you help me with?",
            "description": f"Learn about {clean_name}'s capabilities",
            "message": f"What are your main capabilities and how can you help me?",
        },
        {
            "name": f"Walk me through your process",
            "description": f"Understand the {clean_name} workflow",
            "message": f"Can you walk me through your typical analysis process step by step?",
        },
        {
            "name": f"Analyze a sample case",
            "description": f"See {clean_name} in action with an example",
            "message": f"Can you demonstrate your analysis with a sample case or scenario?",
        },
        {
            "name": f"What data do you need from me?",
            "description": f"Understand required inputs",
            "message": f"What information or data do you need from me to get started?",
        },
    ]


# ── Persona helpers ───────────────────────────────────────────────────────


def get_all_personas() -> list[dict]:
    """Fetch all personas."""
    resp = api("GET", "admin/persona")
    if resp.status_code != 200:
        resp = api("GET", "persona")
    resp.raise_for_status()
    return resp.json()


def get_workflows() -> list[dict]:
    """Fetch all workflows."""
    resp = api("GET", "workflow")
    resp.raise_for_status()
    return resp.json()


def update_persona_starters(persona_id: int, starters: list[dict]) -> bool:
    """PATCH persona with new starter_messages."""
    # Fetch current data
    resp = api("GET", f"persona/{persona_id}")
    if resp.status_code != 200:
        print(f"    [ERR] GET persona {persona_id}: {resp.status_code}")
        return False

    p = resp.json()
    patch = {
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
        "document_set_ids": [ds["id"] for ds in p.get("document_sets", [])],
        "tool_ids": [t["id"] for t in p.get("tools", [])],
        "label_ids": [l["id"] for l in p.get("labels", [])],
        "starter_messages": starters,
        "users": [],
        "groups": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
        "user_file_ids": [],
    }

    resp = api("PATCH", f"persona/{persona_id}", patch)
    if resp.status_code == 200:
        return True
    else:
        print(f"    [ERR] PATCH {resp.status_code}: {resp.text[:200]}")
        return False


def find_missing_starters(
    personas: list[dict],
    workflow_id: int | None = None,
) -> list[dict]:
    """Find personas missing starter messages, optionally filtered by workflow."""
    # Get workflow persona IDs if filtering
    wf_persona_ids = None
    if workflow_id is not None:
        workflows = get_workflows()
        for wf in workflows:
            if wf["id"] == workflow_id:
                wf_persona_ids = set()
                # Add step persona IDs
                for step in wf.get("steps", []):
                    if step.get("persona_id"):
                        wf_persona_ids.add(step["persona_id"])
                # Add wrapper persona (same name)
                for p in personas:
                    if p["name"] == wf["name"]:
                        wf_persona_ids.add(p["id"])
                break

    missing = []
    for p in personas:
        pid = p["id"]
        if pid == 0:
            continue
        if p["name"].startswith("__test"):
            continue
        if wf_persona_ids is not None and pid not in wf_persona_ids:
            continue

        starters = p.get("starter_messages") or []
        if not starters:
            missing.append(p)

    return missing


# ── List command ──────────────────────────────────────────────────────────


def list_missing(personas: list[dict], workflow_id: int | None = None):
    """Show which agents are missing starter messages."""
    missing = find_missing_starters(personas, workflow_id)

    has_prompt = [p for p in missing if (p.get("system_prompt") or "").strip()]
    no_prompt = [p for p in missing if not (p.get("system_prompt") or "").strip()]

    print(f"\nMissing starter messages: {len(missing)}")
    print(f"  With system prompt (can auto-generate): {len(has_prompt)}")
    print(f"  Without prompt (wrapper/empty):         {len(no_prompt)}")

    print(f"\n{'ID':<6} {'Prompt':<8} {'Labels':<30} Name")
    print("-" * 95)
    for p in sorted(missing, key=lambda x: x["id"]):
        prompt = (p.get("system_prompt") or "")
        pflag = f"{len(prompt)}ch" if prompt.strip() else "---"
        labels = ", ".join(l["name"] for l in p.get("labels", []))[:28] or "---"
        print(f"  {p['id']:<6} {pflag:<8} {labels:<30} {p['name']}")


# ── Process command ───────────────────────────────────────────────────────


def process_persona(
    persona: dict,
    upload: bool = True,
    use_llm: bool = True,
    preview_file=None,
) -> bool:
    """Generate starter messages for one persona."""
    pid = persona["id"]
    name = persona["name"]
    prompt = (persona.get("system_prompt") or "").strip()

    print(f"\n  [{pid}] {name}")

    if not prompt:
        print(f"    No system prompt — skipping (wrapper persona)")
        return False

    print(f"    Prompt: {len(prompt)} chars")

    # Generate starters
    starters = None
    if use_llm:
        starters = generate_starters_via_llm(name, prompt)

    if not starters:
        if use_llm:
            print(f"    LLM failed, using heuristic fallback")
        starters = generate_starters_heuristic(name, prompt)

    # Show what was generated (safe print for Windows cp1252)
    for i, s in enumerate(starters):
        try:
            print(f"    [{i+1}] {s['name']}")
        except UnicodeEncodeError:
            safe = s['name'].encode('ascii', 'replace').decode('ascii')
            print(f"    [{i+1}] {safe}")

    # Save to preview file
    if preview_file:
        preview_file.write(f"\n--- {pid}: {name} ---\n")
        preview_file.write(json.dumps(starters, indent=2) + "\n")

    if not upload:
        return True

    # Deploy
    if update_persona_starters(pid, starters):
        print(f"    [OK] Starters set")
        return True
    else:
        print(f"    [FAIL] Could not update")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate & deploy starter messages for agents missing them",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="Show agents missing starters")
    mode.add_argument("--all", action="store_true", help="Generate for ALL missing agents")
    mode.add_argument("--id", type=int, help="Single persona ID")

    parser.add_argument("--workflow", type=int, help="Filter to a specific workflow ID")
    parser.add_argument("--preview", action="store_true", help="Generate but don't upload")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use heuristic only")
    parser.add_argument("--preview-file", default="starter_messages_preview.json",
                        help="File to save preview output")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Pause every N agents to avoid rate limits")

    args = parser.parse_args()
    resolve_api_key()
    _resolve_openai_key()

    print(f"LLM: {LLM_CONFIG['model']} (key={'YES' if LLM_CONFIG['api_key'] else 'MISSING'})")
    print("Fetching personas...")
    personas = get_all_personas()
    print(f"Total: {len(personas)} personas")

    if args.list:
        list_missing(personas, args.workflow)
        return

    if args.id:
        target = next((p for p in personas if p["id"] == args.id), None)
        if not target:
            print(f"Persona {args.id} not found")
            sys.exit(1)
        process_persona(target, upload=not args.preview, use_llm=not args.no_llm)
        return

    # --all
    missing = find_missing_starters(personas, args.workflow)
    # Only process those with system prompts
    targets = [p for p in missing if (p.get("system_prompt") or "").strip()]

    if not targets:
        print("\nNo agents need starter messages!")
        return

    print(f"\nProcessing {len(targets)} agents...")

    preview_file = None
    if args.preview:
        preview_file = open(args.preview_file, "w", encoding="utf-8")
        print(f"Preview mode — saving to {args.preview_file}")

    ok, fail = 0, 0
    for i, persona in enumerate(sorted(targets, key=lambda x: x["id"])):
        if process_persona(
            persona,
            upload=not args.preview,
            use_llm=not args.no_llm,
            preview_file=preview_file,
        ):
            ok += 1
        else:
            fail += 1

        # Rate limit pause
        if not args.no_llm and (i + 1) % args.batch_size == 0 and i + 1 < len(targets):
            print(f"\n  --- Progress: {i+1}/{len(targets)} ({ok} ok, {fail} fail) ---\n")
            time.sleep(1)

    if preview_file:
        preview_file.close()

    print(f"\n{'='*60}")
    print(f"Done: {ok} succeeded, {fail} failed out of {len(targets)}")
    if args.preview:
        print(f"Preview saved to: {args.preview_file}")


if __name__ == "__main__":
    main()
