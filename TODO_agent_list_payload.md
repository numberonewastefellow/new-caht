# TODO: Shrink the `GET /api/agent` list payload (chat page agent list)

> Status: **Planned — not started.** Do later. Big item: needs backend and frontend changes.

## Context

After login, the chat page fetches `GET /api/agent` (backend `list_agents`,
[api.py:449](backend/om/server/features/agent/api.py#L449) →
`get_minimal_agent_snapshots_for_user`, [agent.py:410](backend/om/db/agent.py#L410)), which returns
`list[MinimalAgentSnapshot]` ([models.py:148](backend/om/server/features/agent/models.py#L148)) for
**every** agent the user can see. Measured on 2026-10-25 (admin user, local stack):

| Metric | Value |
|---|---|
| Agents returned | **456** (47 workflow wrappers; all `is_visible = true`) |
| Payload, raw JSON | **949 kB** |
| Payload, gzip | **~147 kB** (nginx gzip for `application/json` on `/api`, enabled 2026-10-25) |
| Server time / DB queries | 0.45 s / 10 queries (no N+1 at this size; the cost is size, not the DB) |

Where the bytes go:

| Field | Share | Notes |
|---|---|---|
| `starter_messages` | **29%** (277 kB) | one agent alone has 36 kB of starter messages |
| `tools` | **20%** (192 kB) | 366 tool entries but only **96 distinct** tools, repeated per agent |
| `description` | 12% (114 kB) | |
| `owner` | 6% (60 kB) | `{id, email}` per agent |
| `labels`, `name`, … | rest | |

**Trimming fields doesn't help much.** Dropping the unused tool fields (`definition`,
`custom_headers`, `passthrough_auth`, …) and doc-set fields (`users`, `groups`, …) only took
**908 kB to 822 kB (−10%)**. The size comes from the number of agents and from
per-agent content (starter messages, descriptions) that the chat page only needs for the
**selected** agent.

## Options to evaluate (pick one or combine)

1. **Lazy-load per-agent details.** The list returns only what the sidebar and agent picker
   show (id, name, short description, icon, labels, flags, `workflow_id`, owner id). Starter
   messages, tools and document sets come from `GET /agent/{id}` (already exists) when an
   agent is selected, cached with SWR per id.
2. **Paginate or virtualize the picker and sidebar** using the existing paginated endpoint
   ([api.py:469](backend/om/server/features/agent/api.py#L469),
   `get_minimal_agent_snapshots_paginated`), with search done server-side.
3. **De-duplicate tools.** Return `tools` once as a top-level map and `tool_ids` per agent
   (366 entries become 96). This changes the response shape.
4. **Hide workflow step agents.** Leave non-wrapper step agents out of the chat list. Only wrappers
   need to be chat-selectable; check whether step agents should be `is_visible = false`.
5. **SSR/RSC or caching.** Render the initial agent list server-side, or add
   `ETag`/`If-None-Match` and a persisted SWR cache, so repeat page loads don't
   re-download an unchanged list.
6. **DB, for when agent/doc counts grow.** Replace the `attached_documents` and `hierarchy_nodes`
   row loads (only used for `len()` and the source set) with grouped `COUNT` and
   `DISTINCT source` queries in `get_minimal_agent_snapshots_for_user`
   ([agent.py:423-434](backend/om/db/agent.py#L423-L434)) and the paginated variant (~:553).

## Consumers that must be updated

- `web/src/hooks/useAgents.ts` (`useSWR("/api/agent")`, dedupe 60 s) and its users: `AppPage`,
  `AppSidebar`, `ChatButton` (one per sidebar row), `AgentButton`, `useChatSessions`,
  `useChatController`, `useAgentController`, `Suggestions`, `ChatSearchCommandMenu`,
  `usePinnedAgents`, `useCurrentAgent`.
- Type `MinimalAgentSnapshot` in `web/src/app/admin/assistants/interfaces.ts` (`Agent` and
  `FullAgent` extend it).
- Fields the chat page reads today:
  - **Agent:** id, name, description, starter_messages, uploaded_image_id, icon_name, is_default_agent, is_visible,
    is_public, builtin_agent, display_priority, owner, labels, workflow_id, llm overrides,
    max_output_tokens, replace_base_system_prompt, knowledge_sources, hierarchy_node_count,
    attached_document_count.
  - **tools[]:** id, name, display_name, description, in_code_tool_id, mcp_server_id, chat_selectable,
    oauth_config_id.
  - **document_sets[]:** id, name, description, cc_pair / federated sources.
- Scripts in `backend/tests/workflow_creator/*` call `GET /agent` and read `tools[].id` and
  `document_sets[].id`, so keep those or switch the scripts to `/admin/agent`.
- Not affected: the admin agent list (`/admin/agent`, `AgentSnapshot`), the agent editor and
  `/agent/{id}` (`FullAgentSnapshot`).

## Verification (when implemented)

1. Payload for the 456-agent dataset: target well under 100 kB raw for the initial list.
2. Chat page: agent picker, sidebar, pinned agents, starter messages for the selected agent,
   actions popover tools, source filters, and the workflow wrapper agents still work.
3. `backend/tests/workflow_creator` scripts still run.
