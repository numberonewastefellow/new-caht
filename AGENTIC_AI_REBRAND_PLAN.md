# Plan: Rebrand `/admin/workflows` as "Agentic AI" (enterprise dashboard)

> Status: **Approved design, implementation deferred (do tomorrow).**
> Decisions: **Enterprise dashboard** layout + **Full rebrand** terminology + **List page only** (designer redesign deferred — see Future TODO).

## Context
The admin Workflows page reads as a plain list ("Workflows / Create and manage multi-agent workflows"). The system is genuinely a multi-agent **agentic AI** platform (27/36 workflows use autonomous LLM-decision routing). Goal: rebrand the page to **"Agentic AI"** and give it an **enterprise-grade dashboard** look matching 2026 commercial agentic platforms (Agentforce / Copilot Studio / Vertex Agent Builder), using the project's theme system.

Design north-stars from research ("Agent UX" patterns): branding/value-prop hero, an at-a-glance overview (KPIs), mode/status filtering, and cards that make the agent chain + autonomy visible (planning/tool-use disclosure). Sources: [Fuse Lab — UI for AI Agents 2026](https://fuselabcreative.com/ui-design-for-ai-agents/), [Kore.ai — best agentic platforms 2026](https://www.kore.ai/blog/7-best-agentic-ai-platforms), [IBM agentic AI](https://www.ibm.com/think/topics/agentic-ai-vs-generative-ai).

## Scope (explicit)
**In scope:** the list/landing page `/admin/workflows` only. **Out of scope (untouched):** the Visual Builder designer at `/admin/workflows/visual/[id]` (node-graph canvas). The redesigned list keeps both entry points into that designer — the "Visual Builder" header button (`/admin/workflows/visual`) and the per-card "Visual" action (`/admin/workflows/visual/{id}`). The designer redesign is deferred (see **Future TODO** at end).

## Primary file
`web/src/refresh-pages/WorkflowListPage.tsx` — full redesign (currently the whole page lives here; `WorkflowListPage.tsx:113-256`).

### 1. Hero header (replace `SettingsLayouts.Header` title/description, lines 172-186)
- Title **"Agentic AI"** rendered with the `.virtualai-gradient-text` class (defined in globals.css) instead of plain text.
- Subtitle: "Build, orchestrate & manage autonomous multi-agent systems".
- Keep `rightChildren`: **"Visual Builder"** (secondary) + primary button renamed **"New Workflow" → "New Agent"** (`SvgSparkle` leftIcon).
- Icon: keep `SvgSliders` or swap to a sparkle/robot accent icon (verify availability in `@opal/icons`; fall back to `SvgSparkle`).

### 2. KPI overview strip (new, above the search/list)
Four stat tiles computed with `useMemo` from `workflows`:
- **Systems** = `workflows.length`
- **Autonomous** = count `orchestration_mode === "llm_decision"`
- **Sequential** = count `orchestration_mode === "sequential"`
- **Agents** = sum of `w.steps.length`

Render as `Card`/themed tiles; big number (`--text-01`) + label (`--text-03`); accent the value with `var(--virtualai-accent, var(--theme-primary-05))`. Responsive grid (`grid-cols-2 md:grid-cols-4`).

### 3. Filter tabs (new) + search
- Pill toggle: **All / Autonomous / Sequential / Private**; state `activeFilter`, combined with existing `searchQuery` in `filteredWorkflows` (lines 120-128).
- Active pill uses `var(--virtualai-accent)` bg/text; inactive uses `bg-background-tint-02`. Place search input alongside (keep current input, lines 187-198).

### 4. Redesigned `WorkflowCard` (lines 23-111)
- **Mode badge with meaning**: map `llm_decision → "⚡ Autonomous"`, `sequential → "Sequential"` (update `modeLabel`, lines 35-40). Autonomous badge uses accent/`--theme-primary` tint; Sequential uses `--theme-blue-01/05` (current). Keep "Private" badge.
- **Agent-chain visualization**: render the persona chain as connected dots/pills (`◉─◉─◉` + names) instead of plain "A → B → C", with `stepCount` agents. Truncate gracefully.
- Keep **Visual / Edit / Delete** actions. **Run** = optional stretch only — `WorkflowSnapshot` has no persona/launch field, so omit unless a launch route is found.
- Add subtle hover glow with `--virtualai-accent-glow` (per design-system rule 5).

### 5. Empty / loading states (lines 202-235)
Update copy to "agentic system" wording; keep skeletons.

## Full-rebrand terminology (labels only — do NOT change routes/URLs)
- `web/src/components/admin/adminNavItems.ts`: nav item `name: "Workflows"` → **"Agentic AI"** (line 148); breadcrumb label `workflows: "Workflows"` → "Agentic AI" (line 402). Keep `link: "/admin/workflows"` and the `BREADCRUMB_REDIRECT_MAP` entries unchanged.
- `web/src/refresh-pages/AgentsNavigationPage.tsx`: toggle label (line 557) and description (line 598) → "Agentic AI" / "autonomous multi-agent systems".

## Design-system constraints (from CLAUDE.md — must follow)
- **No hardcoded accent colors.** Use `--theme-primary-05/04/06`, `--virtualai-accent`, `--virtualai-accent-glow`, and `.virtualai-gradient-text`. One-offs: `var(--virtualai-accent, var(--theme-primary-05))`.
- If any **new** accent color is introduced, add light **and** dark variants under each `.virtualai-*` / `.dark.virtualai-*` block in `web/src/app/css/colors.css`. (Aim to reuse existing vars and avoid this.)
- This is the **list** page, not an editor — the Wizard/Visual-Builder dual-editor sync rule does **not** apply (no workflow fields/validation/payloads change).

## Verification
1. Run the web app (`web/`); open `/admin/workflows`.
2. Confirm: gradient **"Agentic AI"** hero, KPI numbers match the list (Systems/Autonomous/Sequential/Agents), filter tabs filter correctly and combine with search, cards show ⚡Autonomous/Sequential + agent chain, Visual/Edit/Delete work, delete modal still works.
3. Sidebar nav + breadcrumb read **"Agentic AI"**; route stays `/admin/workflows`.
4. **Theme audit**: toggle dark/light and each accent (Default/Ocean/Emerald/Violet) — verify hero gradient is readable in dark mode and KPI/badge/pill accents adapt (no hardcoded colors leaking).
5. Empty-state (no workflows) and no-search-match states render with new copy.

## Bindings Verification (new design → existing code) — ALL GREEN
Verified each interactive element / data binding the design depends on against live code (2026-06-08):

| Binding | New-design usage | Backed by | Status |
|---|---|---|---|
| Visual Builder btn | `/admin/workflows/visual` | route `visual/page.tsx` exists | OK |
| New Agent btn | `/admin/workflows/create` | route `create/page.tsx` exists | OK |
| Card "Visual" | `/admin/workflows/visual/{id}` | route `visual/[id]/page.tsx` | OK |
| Card "Edit" | `/admin/workflows/edit/{id}` | route `edit/[id]/page.tsx` | OK |
| Card "Delete" | `deleteWorkflow(id)` + modal + `refresh()` | `lib/workflows/api`, `useWorkflows.refresh` | OK |
| Data source | `workflows[]` for KPIs/filters/search | `useWorkflows()` returns `{workflows,isLoading,error,refresh}` | OK |
| KPI: Systems | `workflows.length` | WorkflowSnapshot | OK |
| KPI: Autonomous | `orchestration_mode === "llm_decision"` | field exists | OK |
| KPI: Sequential | `orchestration_mode === "sequential"` | field exists | OK |
| KPI: Agents | sum of `steps.length` | `steps[]` | OK |
| Filter: Private | `is_public === false` | field exists | OK |
| Search | `name` + `description` | fields exist | OK |
| Mode badge | map `llm_decision -> Autonomous`, `sequential -> Sequential` | display-only mapping | OK |
| Sidebar nav rename | label `name:"Workflows" -> "Agentic AI"` | active-state uses `pathname.startsWith(link)`, not name (AdminSidebar.tsx:427) | SAFE |
| AgentsNav toggle rename | label text only | binding key is `viewMode`/`value="workflows"` (unchanged) | SAFE |
| /admin redirect | `/admin/workflows` | route exists | OK |

### MUST-NOT-CHANGE invariants (to keep bindings intact)
- Keep `link: "/admin/workflows"` in `adminNavItems.ts` — rename **only** the `name`/breadcrumb label.
- Keep the `viewMode` literal `"workflows"` and `Tabs.Trigger value="workflows"` in `AgentsNavigationPage.tsx` — change **only** the visible label text.
- Keep `orchestration_mode` value strings `"llm_decision"` / `"sequential"` — rebrand is display-label only.
- Keep all `/admin/workflows/...` route paths (URL-stable rebrand).
- KPI "Agents" = **sum of step counts** (defined agent steps), not distinct personas — label/tooltip should reflect that meaning.

## Dual-version mechanism (IMPLEMENTED — web-only backward-compat)
The Agentic AI page ships as the **default**, with the old list preserved as a one-click fallback. All web-only, no backend/API.
- **Default source**: `DEFAULT_UI_VERSION` env (`new` | `legacy`) — a **plain (non-`NEXT_PUBLIC_`) server env** read in `web/src/app/layout.tsx` (`force-dynamic`) and injected via `web/src/providers/UiConfigProvider.tsx`. Change it + **restart `web_server` (no rebuild)**. Wired into `deployment/docker_compose/docker-compose.yml` `web_server.environment` + `env.template`.
- **Per-user override**: `web/src/hooks/usePageVersion.ts` → URL `?legacy=1|0` → `localStorage["ui-version:<key>"]` → env default → `"new"`.
- **Wrapper**: `web/src/refresh-components/VersionedPage.tsx` (+ `useVersionSwitch()`); `web/src/app/admin/workflows/page.tsx` renders `<VersionedPage versionKey="agentic-ai" current={<WorkflowListPage/>} legacy={<WorkflowListPageLegacy/>} />`.
- **Switch UI**: new page header → "Classic view"; legacy page header → "Try the new Agentic AI view".
- **Reuse**: any page → copy current to `*Legacy.tsx`, wrap its `page.tsx`, add the two switch buttons. One env var governs all keys.

## Legacy cleanup checklist (no dead pages)
Greppable tag on every temporary legacy page: `grep -r "TODO(agentic-ui-cleanup)" web/src`.

| Legacy page | Status | Remove when |
|---|---|---|
| `web/src/refresh-pages/WorkflowListPageLegacy.tsx` | active (backward-compat) | new Agentic AI page verified in production |

Removal steps when retiring a legacy page: (1) delete the `*Legacy.tsx`; (2) render the new page directly in its `page.tsx` (drop `<VersionedPage>`); (3) remove the "Classic view" switch; (4) if no page still uses versioning, delete `usePageVersion.ts`, `VersionedPage.tsx`, `UiConfigProvider.tsx`, the `layout.tsx` wiring, and the `DEFAULT_UI_VERSION` env var.

## Future TODO (deferred — not in this change)
Redesign the **Visual Builder designer** (`/admin/workflows/visual/[id]`) to match the new Agentic AI branding once the list page lands. Likely touch points (per CLAUDE.md dual-editor rule, keep Wizard + Visual Builder in sync):
- `web/src/components/workflow-builder/` — canvas, node styling, `GlobalConfigToolbar.tsx` (the Sequential/LLM-Decision toggle → "Autonomous" wording), `NodeConfigPanel.tsx`.
- Designer page chrome/header: apply gradient "Agentic AI" branding, accent theme variables, and consistent mode terminology ("LLM Decision" → "Autonomous").
- Keep the node-graph UX (START → agents → END, per-node tools/HITL/flags) — it already matches enterprise agentic-AI patterns; this is a styling/terminology pass, not a re-architecture.
- Track as a separate follow-up task/ticket.
