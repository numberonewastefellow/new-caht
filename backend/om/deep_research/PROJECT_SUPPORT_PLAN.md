# Deep Research for Workspaces — Support Notes

## Status: IMPLEMENTED (Option A — workspace-scoped search)

Deep Research previously threw `RuntimeError("Deep research is not supported for workspaces")` for any chat
inside a workspace (formerly "project"). It is now enabled: a workspace Deep-Research run retrieves the
workspace's own documents via **workspace-scoped OpenSearch search**, iteratively, with citations.

## Why it was only a stub (not an architectural limit)
- Deep Research already retrieves from the index — the internal `SearchTool` is whitelisted alongside
  web-search / open-url in `deep_research/dr_loop.py:231`
  (`allowed_tool_names = {SearchTool.NAME, WebSearchTool.NAME, OpenURLTool.NAME}`). It is not LLM-only.
- `SearchTool` already supports workspace-scoped retrieval: `workspace_id`
  (`tools/tool_implementations/search/search_tool.py:238,252`) is applied to the query
  (`search_tool.py:454`, into `search_pipeline`).

The only missing wiring was (a) the guard and (b) ensuring the workspace-scoped `SearchTool` survives into
the DR branch — the search-availability policy would otherwise strip it for the common
"default persona + files fit in context" case.

## What changed (all in `backend/om/chat/`)
1. **Removed the guard** — `message_handler.py`, the `elif new_msg_req.deep_research:` branch no longer
   raises on `chat_session.workspace_id`.
2. **Search-availability carve-out** — `_get_workspace_search_availability` (`message_handler.py`) takes a
   new `deep_research: bool` param; when `deep_research and workspace_id`, it returns
   `WorkspaceSearchConfig(search_usage=ENABLED, disable_forced_tool=False)` instead of the `DISABLED`
   branch that fires when workspace files fit in context. Call site passes
   `deep_research=bool(new_msg_req.deep_research)`.
3. **Force workspace scoping** — the `SearchToolConfig.workspace_id` in `construct_tools(...)` is now set
   for DR even when `workspace_as_filter` is False (files fit), so the search tool filters to the
   workspace.

`SearchToolUsage.ENABLED` force-adds the `SearchTool` (with `search_tool_config.workspace_id`) in
`tools/tool_constructor.py:431-458`, gated on `not DISABLE_VECTOR_DB` — so with no vector DB the carve-out
gracefully no-ops (DR falls back to web / LLM, no crash).

**No changes** to `dr_loop.py` / `research_agent.py`: retrieval flows through the already-scoped
`SearchTool` in `tools`. **No frontend change**: the DR toggle already shows in workspace chats
(`web/src/sections/input/AppInputBar.tsx:458-464` gates only on the global DR setting + assistant having
search tools) and `deep_research` is sent unconditionally
(`web/src/app/app/services/lib.tsx:153`). **No Alembic migration** (no schema change).

## Design decision: search-scoped RAG, not context injection
DR is an iterative multi-cycle flow (clarification → plan → orchestrator cycles → sub-agents → report).
Injecting all workspace files as forced context into every `construct_message_history` call across cycles +
sub-agents would duplicate large payloads and defeat DR's retrieval design. Option A instead forces
workspace-scoped search on, mirroring the normal "files overflow context" path.

## Deferred follow-up (Option B — hybrid, not built)
Additionally thread `workspace_files`/`workspace_id` into `run_deep_research_llm_loop`
(`dr_loop.py:189-202`) and the 6 `construct_message_history` calls (`dr_loop.py:143,261,325,489`;
`tools/fake_tools/research_agent.py:123,338` — currently `workspace_files=None`), injecting a bounded subset
at the clarification/plan stage only, gated by the same token budget the normal path uses
(`max_llm_context_percentage`). Only worth it if product wants small workspace files always in-context in
addition to search.

## Verification
1. Start a DR run in a workspace with indexed files → no `RuntimeError`; sub-agent `SearchTool` calls fire
   with `workspace_id=<id>` and return chunks scoped to that workspace.
2. Results/citations limited to that workspace's documents; ids resolve in OpenSearch.
3. Default persona + small workspace files (previously `DISABLED`) → DR still searches; a non-DR chat in the
   same workspace is unchanged (files as context, no search).
4. Non-workspace DR and normal workspace chat both unchanged.

Per project rules: migrations apply on container restart (never run `alembic upgrade` directly); user
reviews and rebuilds Docker before anything is committed.
