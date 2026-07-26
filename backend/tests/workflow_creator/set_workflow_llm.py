"""
Set the LLM provider/model for workflow agents.

Pins every workflow STEP-agent (name starts with --agent-prefix, default "WF ")
to a given provider/model via its own llm override, and re-points every
llm_decision workflow ORCHESTRATOR whose provider == --orchestrator-from
(default "v") to --provider. This makes workflows run on a capable model
regardless of the global default LLM (which stays as-is for normal chat).

Usage:
    python set_workflow_llm.py --provider gpt --model gpt-4.1 --key <admin-key>
    python set_workflow_llm.py --provider gpt --model gpt-4.1 --dry-run --key ...

Notes:
    - The target model must be VISIBLE on the provider, else the backend coerces
      the override to a visible model. Un-hide it first if needed.
    - Full-body PATCH preserves all existing agent fields; only the two llm
      override fields change. Idempotent (skips agents already set).
"""

import argparse

from config import add_common_args, api, apply_common_args


def _full_agent_patch_body(a: dict, provider: str, model: str) -> dict:
    """Rebuild the AgentUpsertRequest from the current agent, changing only the
    llm override fields. Preserves prompts, tools, labels, starter messages, icon."""
    return {
        "name": a["name"],
        "description": a.get("description") or "",
        "system_prompt": a.get("system_prompt") or "",
        "task_prompt": a.get("task_prompt") or "",
        "num_chunks": a.get("num_chunks", 0),
        "is_public": a.get("is_public", True),
        "recency_bias": a.get("recency_bias", "base_decay"),
        "llm_filter_extraction": a.get("llm_filter_extraction", False),
        "llm_relevance_filter": a.get("llm_relevance_filter", False),
        "replace_base_system_prompt": a.get("replace_base_system_prompt", True),
        "datetime_aware": a.get("datetime_aware", True),
        "document_set_ids": a.get("document_set_ids", []),
        "tool_ids": [t["id"] for t in a.get("tools", [])],
        "label_ids": [l["id"] for l in a.get("labels", [])],
        "starter_messages": a.get("starter_messages") or [],
        "icon_name": a.get("icon_name"),
        "max_output_tokens": a.get("max_output_tokens"),
        "users": [],
        "groups": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
        "knowledge_file_ids": [],
        "llm_model_provider_override": provider,
        "llm_model_version_override": model,
    }


def pin_step_agents(prefix: str, provider: str, model: str, dry: bool) -> int:
    resp = api("GET", "agent")
    resp.raise_for_status()
    agents = [a for a in resp.json() if a.get("name", "").startswith(prefix)]
    print(f"\nStep-agents: {len(agents)} match prefix '{prefix}'")
    ok = skip = fail = 0
    for a in agents:
        if (
            a.get("llm_model_provider_override") == provider
            and a.get("llm_model_version_override") == model
        ):
            skip += 1
            continue
        if dry:
            print(f"  [DRY] would pin {a['name']} (ID={a['id']})")
            ok += 1
            continue
        full = api("GET", f"agent/{a['id']}").json()
        r = api("PATCH", f"agent/{a['id']}", _full_agent_patch_body(full, provider, model))
        if r.status_code == 200:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {a['name']} (ID={a['id']}): {r.status_code} {r.text[:160]}")
    print(f"  -> {ok} pinned, {skip} already set, {fail} failed")
    return fail


def repoint_orchestrators(from_prov: str, provider: str, dry: bool) -> int:
    resp = api("GET", "workflow")
    resp.raise_for_status()
    # All modes: the wrapper agent's llm override is derived from
    # orchestrator_llm_provider regardless of mode, so re-point any workflow on
    # the old provider (harmless for sequential; clears its dangling override).
    wfs = [w for w in resp.json() if w.get("orchestrator_llm_provider") == from_prov]
    print(f"\nOrchestrators: {len(wfs)} workflows point at '{from_prov}'")
    ok = fail = 0
    for w in wfs:
        if dry:
            print(f"  [DRY] would re-point wf {w['id']} '{w['name']}'")
            ok += 1
            continue
        r = api(
            "PATCH",
            f"admin/workflow/{w['id']}",
            {"orchestrator_llm_provider": provider},
        )
        if r.status_code == 200:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] wf {w['id']}: {r.status_code} {r.text[:160]}")
    print(f"  -> {ok} re-pointed, {fail} failed")
    return fail


def main() -> None:
    ap = argparse.ArgumentParser(description="Pin workflow agents to an LLM model")
    ap.add_argument("--provider", default="gpt", help="LLM provider name (must exist)")
    ap.add_argument("--model", default="gpt-4.1", help="model version (must be visible)")
    ap.add_argument("--agent-prefix", default="WF ", help="step-agent name prefix")
    ap.add_argument("--orchestrator-from", default="v", help="old orchestrator provider to replace")
    ap.add_argument("--dry-run", action="store_true")
    add_common_args(ap)
    args = ap.parse_args()
    apply_common_args(args)

    print(f"Target: provider='{args.provider}' model='{args.model}'"
          + (" (DRY RUN)" if args.dry_run else ""))
    fails = pin_step_agents(args.agent_prefix, args.provider, args.model, args.dry_run)
    fails += repoint_orchestrators(args.orchestrator_from, args.provider, args.dry_run)
    print("\nDone." if not fails else f"\nDone with {fails} failure(s).")
    if fails:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
