#!/usr/bin/env python3
"""
Set a single agent's LLM model override by name or id — per-agent model escalation.

The workflow deploy's `--update` path syncs prompts/tools but NOT the model override,
so use this to escalate one agent (e.g. gpt-4o-mini -> gpt-4.1) when the small model
fails at extraction/JSON/decision-routing, without touching the other agents.

    python set_agent_model.py --agent "WF Cyber Complaint Extractor" --model gpt-4.1 --key <KEY>
"""
import argparse
import sys

from config import add_common_args, api, apply_common_args


def find_agent(name_or_id: str) -> dict | None:
    if str(name_or_id).isdigit():
        r = api("GET", f"agent/{name_or_id}")
        return r.json() if r.status_code == 200 else None
    r = api("GET", "agent")
    if r.status_code != 200:
        return None
    for a in r.json():
        if a["name"].lower() == str(name_or_id).lower():
            return api("GET", f"agent/{a['id']}").json()
    return None


def main():
    ap = argparse.ArgumentParser(description="Set an agent's LLM model override")
    add_common_args(ap)
    ap.add_argument("--agent", required=True, help="agent name or id")
    ap.add_argument("--model", required=True, help="e.g. gpt-4.1 or gpt-4o-mini")
    ap.add_argument("--provider", default="gpt")
    args = ap.parse_args()
    apply_common_args(args)

    a = find_agent(args.agent)
    if not a:
        print(f"[ERROR] agent '{args.agent}' not found")
        return 1

    body = {
        "name": a["name"],
        "description": a.get("description") or "",
        "system_prompt": a.get("system_prompt") or "",
        "task_prompt": a.get("task_prompt") or "",
        "num_chunks": a.get("num_chunks", 10),
        "is_public": a.get("is_public", True),
        "recency_bias": a.get("recency_bias", "base_decay"),
        "llm_filter_extraction": a.get("llm_filter_extraction", False),
        "llm_relevance_filter": a.get("llm_relevance_filter", False),
        "replace_base_system_prompt": a.get("replace_base_system_prompt", True),
        "datetime_aware": a.get("datetime_aware", True),
        "document_set_ids": a.get("document_set_ids", []),
        "tool_ids": sorted(t["id"] for t in a.get("tools", [])),
        "label_ids": sorted(l["id"] for l in a.get("labels", [])),
        "starter_messages": a.get("starter_messages", []),
        "users": [], "groups": [], "hierarchy_node_ids": [],
        "document_ids": [], "knowledge_file_ids": [],
        "llm_model_provider_override": args.provider,
        "llm_model_version_override": args.model,
    }
    old = a.get("llm_model_version_override")
    r = api("PATCH", f"agent/{a['id']}", body)
    if r.status_code == 200:
        print(f"[OK] {a['name']} (id={a['id']}) model: {old} -> {args.model}")
        return 0
    print(f"[FAIL] PATCH {r.status_code}: {r.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
