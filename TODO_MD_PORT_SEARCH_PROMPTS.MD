# TODO — Port: search-scope + answer-completeness prompts (item 14) + separate evidence-selection model (item 6)

**Lane:** L2
**Backlog:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` item 14 (P1) and item 6 (P2)
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5
**Status:** Phase B DONE (2026-10-30) — code + tests green, cross-verification A–D recorded; awaiting user Docker rebuild + manual checks, L4 measurement, and integrator baseline.json regen.

> **Resuming in a new session?** Read the "Progress tracker" (§12). Pick the first unchecked item, and tick it with the date when done.

---

## 1. Scope
- **What users get:**
  - On every turn that used search (internal search, web search, open-URL), the model is told to answer **every part** of the question, to keep **exact figures** (values, limits, dates, names, commands, steps), to say plainly when the documents lack the answer, and to lay out multi-part answers as a list.
  - Search does **not** narrow to one connector just because the question mentions it (e.g. "how much storage does our Google Drive plan include" still searches everything). See §5.1: our fork already behaves this way, so this half of item 14 is a guard test, not a port.
  - Optional: a cheaper model picks which retrieved sections reach the answer model (item 6). This cuts cost per search, because selection runs one LLM call for the whole list plus one per selected section. **Off by default**: with no config, the chat model is used, as today.
- **Upstream commits found** (all after merge-base `fc6a37850`, released in v4.9):

| Commit | PR | Date | What | Port? |
|---|---|---|---|---|
| `ba60745a0b` | #14960 | 2026-09-22 | Per-turn reminder: answer every part of the question and keep exact values; added next to the citation reminder (`UP:om/chat/prompt_utils.py`, `UP:om/prompts/chat_prompts.py`) | **Yes** (our name and wording, §5.0) |
| `a799f07334` | #15067 | 2026-09-24 | System-prompt guidance: lay out multi-part answers as a list and check that the passage matches the question; added after the citation guidance | **Yes** (our name and wording, §5.0) |
| `8ae2902bc2` | #15317 | 2026-10-01 | Scope-decision prompt (`UP:om/prompts/filter_extration.py`): scope only to a source named as WHERE to look, never to the question's SUBJECT | No (feature absent, §5.1) |
| `d1bfaad22f` | #16670 | 2026-10-23 | Passes searched sources to the scope decision so BACKOFF advances (`UP:om/secondary_llm_flows/source_filter.py`) | No (feature absent) |
| `4e221c1e55` | #16079 | 2026-10-16 | Evidence selection routed to its own model: a resolver with a fallback in `UP:om/llm/factory.py`, a lazily resolved per-tool model on the search tool, a factory argument plumbed through `construct_tools`, and an input-budget trimmer `UP:om/secondary_llm_flows/search_prompt_budget.py` | **Yes, re-designed** (§5.2) |
| `623fead396` | #16140 | 2026-10-19 | Removes the unused primary-flow prompt-budget flags that #16079 added | Folded into our design (we never add them) |

  The prerequisite scope feature that #15317 and #16670 tune came in `0cd3294d4c` (#12212), `79afe697da` (#12412), `95b81a3885` (#12897) and `f9060144c3` (#14820). We do **not** have it.
- **Target (our tree):**
  - `backend/om/prompts/chat_prompts.py`: two new constants.
  - `backend/om/chat/prompt_utils.py`: `build_reminder_message`, `build_system_prompt`.
  - `backend/om/prompts/prompt_utils.py`: `replace_citation_guidance_tag` (placeholder branch, §5.1).
  - `backend/om/secondary_llm_flows/evidence_selection_llm.py` (new): resolve the selection model.
  - `backend/om/tools/tool_implementations/search/search_tool.py`: an `evidence_selection_llm` cached property, used at the two selection call sites.
  - `backend/om/configs/app_configs.py`: inside a `# --- search-prompts ---` block only.
- **Dropped:** upstream's DB flow type `SEARCH_SELECTION` and admin UI, the cost-limit checks (`UP:om/server/usage_limits.py`; we have no such module), incognito policy plumbing, the federated-Slack-search routing, upstream's enterprise-only search-API changes, and the `.agents/feature-map` docs.
- **Out of scope / related, needs approval (§11):** the `document_filter` LLM call timeout (#12333, `2415cff137`), which our fork lacks; the doubled selection token budget (#14451, `638684efa7`); and moving query expansion or the time filter to the cheaper model.
- **Dependencies:** none for the code. The L4 eval baseline must exist before rollout so this lane can be measured on its own (§8).

## 2. DB migration
None. Item 6 uses env config, not a DB setting. Note on the rejected alternative: adding `SEARCH_SELECTION` to `LLMModelFlowType` (`om/db/enums.py`, stored with `native_enum=False`) **would** need a migration. The column is a VARCHAR sized to the longest current value (`contextual_rag`, 14 chars), and `search_selection` is 16. It would also need admin UI. Deferred (§10, Q2).

## 3. Model mapping
- **New env vars** (all in the `# --- search-prompts ---` block):
  - `ENABLE_COMPLETE_ANSWER_PROMPTS`: default `true`. Set it to `false` to drop both item-14 texts, which gives a baseline run on the same build for L4.
  - `EVIDENCE_SELECTION_LLM_PROVIDER`: provider **name** as shown in Admin → LLM, e.g. `DevEnvPresetOpenAI`. Default unset.
  - `EVIDENCE_SELECTION_LLM_NAME`: model name, e.g. `gpt-4o-mini`. Default unset. Both must be set; if only one is, log a warning and use the chat model.
- **No new dependency.** No API, route, payload, OpenSearch field, Celery task or Redis key changes. No re-index.
- **Prompt texts:** adapted from upstream (validated there on a 500-question paired benchmark) but rewritten in our voice; see §5.0 for the exact text and the identifier names.

## 4. UI
None. The admin selection-model picker is a possible follow-up (Q2).

## 5. Design: reuse and differences from upstream

### 5.0 Naming & structure (ours)
Upstream code is **reference only**. Every folder, file, identifier and env name below is ours and follows our existing conventions: the `*_REMINDER` / `*_GUIDANCE` constants in `om/prompts/chat_prompts.py`, the `ENABLE_*` flags and the `*_LLM_PROVIDER` / `*_LLM_NAME` pairs (cf. `DEFAULT_CONTEXTUAL_RAG_LLM_NAME/_PROVIDER`) in `app_configs.py`. No new folders.

| Upstream reference concept | Ours (folder / file / identifier / config) | Reason |
|---|---|---|
| Per-turn "answer every part, keep exact values" reminder | `COMPLETE_ANSWER_REMINDER` in `om/prompts/chat_prompts.py` | Sits next to `CITATION_REMINDER` / `FILE_REMINDER`, and says what it asks for: a complete answer |
| System-prompt "multi-part layout / passage match" guidance | `MULTI_PART_ANSWER_GUIDANCE` in `om/prompts/chat_prompts.py` | Pairs with `REQUIRE_CITATION_GUIDANCE`; names its main instruction (list the parts) |
| On/off for both texts (upstream has none) | `ENABLE_COMPLETE_ANSWER_PROMPTS` (env, default `true`) in `app_configs.py` | `ENABLE_*` is our flag convention (`ENABLE_CONTEXTUAL_RAG`) |
| DB flow type + per-flow default model for selection | `EVIDENCE_SELECTION_LLM_PROVIDER` + `EVIDENCE_SELECTION_LLM_NAME` (env) | Same `_LLM_PROVIDER` / `_LLM_NAME` pair as contextual RAG; "evidence selection" is our backlog term |
| Selection-model resolver in the LLM factory | `resolve_evidence_selection_llm(chat_llm)` in `om/secondary_llm_flows/evidence_selection_llm.py` | Lives beside its only consumer flow (`document_filter.py`); keeps `om/llm/` (L5) untouched |
| Lazily resolved model on the search tool | `SearchTool.evidence_selection_llm` (cached property) | Matches the module and env name, so a grep finds all three |
| Input-budget trimmer module | none; a private `_fits_evidence_selection_window()` in `search_tool.py` | We fall back to the chat model instead of trimming, so no new module |
| Test files | `test_complete_answer_prompts.py`, `test_llm_loop_complete_answer.py`, `test_evidence_selection_llm.py`, `test_search_tool_evidence_routing.py`, `test_no_source_autonarrow.py` | Named after our identifiers, in the existing `tests/unit/om/<pkg>/` folders |

**Prompt text (ours, adapted from upstream):**
- `COMPLETE_ANSWER_REMINDER`: "Answer each part of the question. Where the documents give a specific number, date, limit, name, command or step that bears on the question, quote it exactly instead of paraphrasing it. Before you finish, re-read the question and check that no part is left unanswered. If the documents do not contain what was asked, say so plainly instead of offering related information that does not answer it."
- `MULTI_PART_ANSWER_GUIDANCE`: "When the answer has several parts, give them as a list rather than one long sentence, and include the secondary details the question asks for, not just its main point. Make sure the passage you rely on matches the full context of the question: a document on a nearby topic usually lacks the details that were asked for."
- Risk: our rewording has not been benchmarked. The L4 run (§8) compares it with the baseline; if it underperforms, fall back to wording closer to the reference and re-measure.

### 5.1 Item 14: prompts
- **Search scope is already right in our fork.** `om/context/search/pipeline.py` only runs `extract_source_filter` when `auto_detect_filters=True`. No caller passes that, and `om/secondary_llm_flows/source_filter.py::extract_source_filter` raises `NotImplementedError`. `om/prompts/filter_extration.py` is an unused legacy prompt. So a question that names a source never narrows search; only explicit user, agent or Slack-channel filters do. **Action:** add a guard test so a future port of the scope feature can't regress this silently, and keep the WHERE-vs-SUBJECT rule from #15317 as the spec if we ever port #12212.
- **`build_reminder_message`** (`om/chat/prompt_utils.py:126`): after `CITATION_REMINDER`, append `COMPLETE_ANSWER_REMINDER` (behind the flag). Same trigger as upstream: `include_citation_reminder`. In our fork that is `should_cite_documents or always_cite_documents` (`llm_loop.py:763`), so workspace turns that cite workspace files get the reminder too (intended: they are document-backed).
- **`build_system_prompt`** (`om/chat/prompt_utils.py:196`): after `REQUIRE_CITATION_GUIDANCE`, append `MULTI_PART_ANSWER_GUIDANCE`.
- **Improvement over upstream:** upstream adds the coverage text only in the fallback branch. If the admin's default prompt contains `{{CITATION_GUIDANCE}}` (allowed by `web/src/app/admin/configuration/default-assistant/page.tsx`), the citation guidance is substituted in place and the coverage text is lost. We substitute `REQUIRE_CITATION_GUIDANCE + MULTI_PART_ANSWER_GUIDANCE` in `replace_citation_guidance_tag` as well, and add an "already present" check so the text is never added twice.
- **Custom agents with "replace base system prompt"** (`llm_loop.py` ~690) skip `build_system_prompt`, so they get the reminder but not the coverage text. That is the same as upstream; we keep it, because those admins own their whole prompt.
- **Token cost:** about 120 extra prompt tokens on cited turns. `prompt_utils.py:84` (the fake system prompt used to reserve tokens) picks this up automatically.

### 5.2 Item 6: selection model
- **New `om/secondary_llm_flows/evidence_selection_llm.py`:** `resolve_evidence_selection_llm(chat_llm: LLM) -> LLM`.
  - If either env var is unset, return `chat_llm` (no DB hit).
  - Otherwise use the **existing** `fetch_llm_provider_view` (`om/db/llm.py:536`) plus `llm_from_provider` (`om/llm/factory.py:212`), the same path `get_llm_for_contextual_rag` already uses. These are **called, not modified**: `om/llm/` belongs to L5.
  - On any error (unknown provider, bad key), log one warning and return `chat_llm`. Selection must never break search.
  - The module is generic: a later "cheap utility model" for query expansion or naming can reuse it with another pair of env vars.
- **`SearchTool.evidence_selection_llm`:** a `functools.cached_property` that calls the resolver once per tool instance. Used at `search_tool.py:778` (`select_sections_for_expansion`) and `:851` (`expand_section_safe` → `classify_section_relevance`). Query expansion and the reranker stay on `self.llm` / Cortex.
- **Why resolve inside the tool, not plumb `selection_llm_factory` through `construct_tools` like upstream:** every path that builds a `SearchTool` (chat `message_handler.py:905`, `agent_tool.py:286` for agents and workflow steps, deep-research `research_agent.py:762`) gets the routing with no signature changes. One code path, one test.
- **Context-window guard** (replaces upstream's `SearchPromptBudget` binary-search trimming): if `evidence_selection_llm.config.max_input_tokens` is smaller than `max_tokens_for_selection` plus a margin for the prompt, use the chat model for that call and log at debug level. This is simpler, and it can't silently drop evidence.
- **Unchanged:** `RERANK_PROTECT_TOP_K` protection (`search_tool.py:785`) still runs after selection, so a weaker selector can't discard the reranker's top sections. This makes a cheap selector safer in our fork than in upstream.
- **Per-agent models:** workflows pin per-step models (see the workflow-build-patterns memory: mini by default, gpt-4.1 for the Extractor). With the env set, selection uses the global cheap model for **every** agent, including ones pinned to a stronger model. Documented as intended (Q3).

## 6. Existing features touched (regression scope)

| Caller / feature | Path | Hit by | Covered by |
|---|---|---|---|
| Web chat (stream + non-stream send) | `server/query_and_chat/chat_backend.py:560,582` → `chat/message_handler.py::stream_chat_message` → `chat/llm_loop.py::run_llm_loop` (713, 759) | 14 + 6 | new loop-level test (mock LLM, assert system + reminder text) in the style of `tests/unit/om/chat/test_llm_loop.py` / `test_message_handler_mock_llm.py` |
| Agents in chat (default prompt / replace-prompt / `task_prompt`) | `llm_loop.py` ~690–765 | 14 | parametrized loop test: three agent shapes |
| Workspace chat (`always_cite_documents`) | `llm_loop.py:647` | 14 | loop test with workspace files set |
| Slack / ombot answers | `ombot/slack/handlers/handle_regular_answer.py:188` → `stream_chat_message` | 14 + 6 | covered by the loop test (same entry point); manual check C |
| Pulse scheduled runs | `pulse/runner.py:373` → `stream_chat_message` | 14 + 6 | loop test; existing `tests/unit/om/pulse` must stay green |
| Workflow steps and agent-as-tool | `tools/tool_implementations/agent_tool.py:286,354,396` (own system prompt, `run_llm_step`) | **6 only** (no chat prompt builders) | new test: `SearchTool` built via `construct_tools` uses the selection model when the env is set; existing `tests/unit/om/workflows` green; manual check D |
| Workflow orchestrator | `workflows/workflow_engine.py:510` (`_build_orchestrator_system_prompt`) | none | existing workflow tests |
| Deep research | `deep_research/dr_loop.py`, `tools/fake_tools/research_agent.py:762` (own prompts) | **6 only** | selection-routing test via `construct_tools` |
| Eval harness (L4) | `evals/eval.py:241,395` → `stream_chat_message` | 14 + 6 | this is the measurement path (§8) |
| Search-tool baseline harness | `tests/search_baseline/test_search_tool_layer.py` | 6 | re-run unchanged; with the env unset, results must be identical |
| Existing prompt-util tests | `tests/unit/om/prompts/test_prompt_utils.py` | 14 (placeholder branch) | extend for the placeholder + coverage case |

**Behaviour changes to be aware of (intended):** answers on search-backed turns get longer and more list-shaped, and say "not in the documents" more often instead of giving adjacent information. Workflow guard-rail tests (`test_<dept>.py`) match on **step outputs** produced via `agent_tool`, which item 14 doesn't touch. Re-run 2–3 of them anyway (manual check D).

## 7. Tests
**New unit tests (planned):**

| File | What it covers |
|---|---|
| `backend/tests/unit/om/chat/test_complete_answer_prompts.py` | reminder and system prompt include or omit the texts per `should_cite_documents` / `always_cite_documents` / last cycle / flag off; `{{CITATION_GUIDANCE}}` placeholder branch; no double insertion |
| `backend/tests/unit/om/chat/test_llm_loop_complete_answer.py` | public entry `run_llm_loop` with a mock LLM: first turn without search has no texts; after a search tool call both are present; replace-prompt agent gets the reminder only |
| `backend/tests/unit/om/secondary_llm_flows/test_evidence_selection_llm.py` | env unset → fallback, no DB call; both set → resolved LLM; one set → warning + fallback; unknown provider / exception → fallback |
| `backend/tests/unit/om/tools/test_search_tool_evidence_routing.py` | `SearchTool` passes `evidence_selection_llm` to `select_sections_for_expansion` and `classify_section_relevance`, and `self.llm` to query expansion; context-window guard; resolver called once per instance; tool built via `construct_tools` (agent/workflow path) is routed too |
| `backend/tests/unit/om/context/test_no_source_autonarrow.py` | guard: `search_pipeline` never calls `extract_source_filter` for default callers; a query naming "Google Drive" keeps `source_type=None` |

**Pre-existing unrelated failures:** record them before starting (e.g. `test_websearch_utils.py`, cp1252 on Windows, per the pdfium doc).

## 8. Metric hook (L4)
- **Should move up:** answer completeness (every sub-part answered), exact-figure correctness (numbers, dates, limits copied verbatim), and the honest "not in the documents" rate on unanswerable questions.
- **Should stay flat (guard):** recall@k and the answer score on questions that **name a source** as their subject. Our fork already doesn't narrow, so a drop here means something else regressed.
- **Item 6:** selection-precision proxy (share of cited docs that the selector kept), LLM cost and latency per search turn. Run with the env unset vs set; completeness must not drop by more than an agreed tolerance (Q4).
- **Isolation:** measure L2 against the **L4 baseline alone** (no L3 ranking or L5 provider changes in the same build). `ENABLE_COMPLETE_ANSWER_PROMPTS=false` gives the A side on the same image.

## 9. Gates and lane boundaries
- [x] Naming grep on new and changed files (no upstream product name). (2026-10-30, see §12 "Gates")
- [x] `pytest backend/tests/unit/migration_safety` (2026-10-30: only the expected added module; baseline regenerated at integration) (the new module adds a name. **Do not edit** `tests/unit/migration_safety/snapshots/baseline.json` in this lane. If the snapshot check flags `om.secondary_llm_flows.evidence_selection_llm`, report it to the integrator.)
- [x] `backend/tests/route_rename` (no route changes expected). (2026-10-30: 2 pre-existing stale-snapshot failures, unrelated)
- [x] Import check of every caller module in §6, plus `compileall`. (2026-10-30)
- [ ] `python -I rename-audit/build_inventory.py --check`: **not run by this lane** (it rewrites report files); run it at commit time.
- [x] Web `tsc`: not needed (no web changes).
- **Files this lane owns:** `om/prompts/chat_prompts.py`, `om/prompts/prompt_utils.py`, `om/chat/prompt_utils.py`, `om/secondary_llm_flows/evidence_selection_llm.py` (new), `om/tools/tool_implementations/search/search_tool.py` (selection call sites only), and the new tests above.
- **Shared hot files:** `om/configs/app_configs.py`, only inside `# --- search-prompts ---`. Must **not** touch: `om/document_index/opensearch/` (L3), `om/llm/` provider/factory modules (L5; read and call only), the migration snapshot, `alembic/`. No new deps, no migration.

## 10. Post-implementation cross-verification (after Phase B)
Goal: show that our behaviour matches the upstream reference wherever we intend it to, and that every difference is one we chose. Rules:
- **Never import upstream code into our repo** and never add it to `sys.path` from our tests.
- The upstream-side runner is a throwaway script **outside the repo** (e.g. under `d:/tmp/l2_xverify/`). It runs in its own venv against the read-only reference checkout and writes JSON.
- Our side is a script in the same folder that imports only `om.*`.
- Both read the same inputs, `d:/tmp/l2_xverify/cases.json`. A `diff` script compares **structure** (which blocks are present, their order, which model was called), not wording, because our text is reworded on purpose.

**Case set A: rendered system prompt** (`build_system_prompt` on our side, its reference counterpart on the other):

| # | Input | Expected vs reference |
|---|---|---|
| A1 | default prompt, no search on the turn | same: no citation block, no multi-part block |
| A2 | default prompt, search ran | same: citation block, then the multi-part block, at the same position relative to the company/user-info sections |
| A3 | custom admin default prompt containing `{{CITATION_GUIDANCE}}`, search ran | **intended difference:** ours inserts citation + multi-part guidance at the placeholder; the reference inserts citation only |
| A4 | A3 but no search | same: placeholder replaced by an empty string |
| A5 | prompt already containing the citation guidance text | same: no duplicate blocks |
| A6 | A2 with `ENABLE_COMPLETE_ANSWER_PROMPTS=false` | equals the pre-L2 output of our tree (no reference counterpart) |

**Case set B: per-turn reminder** (`build_reminder_message`):

| # | Input | Expected vs reference |
|---|---|---|
| B1 | cite on | same: citation reminder, then the complete-answer reminder |
| B2 | cite on + last cycle | same order: last-cycle, citation, complete-answer |
| B3 | cite on + agent `task_prompt` + file reminder | same order, `task_prompt` first, file reminder last |
| B4 | cite off | same: no complete-answer reminder |
| B5 | workspace turn (`always_cite_documents`) without a search call | ours includes the reminder; record the reference's behaviour for the same inputs and note any difference |

**Case set C: selection-model routing** (the reference needs its DB, so compare against its **unit-test cases**: list the scenarios in its search-tool and factory tests, then mirror each scenario as a case in our own tests, without copying the code):

| # | Scenario | Expected (ours) | Reference behaviour |
|---|---|---|---|
| C1 | nothing configured | chat model; no DB lookup | chat model (fallback) |
| C2 | configured, resolves | cheap model for both selection calls; chat model for query expansion | same routing |
| C3 | resolver raises / unknown provider | chat model + one warning | chat model + warning |
| C4 | only one of the two env vars set | chat model + warning | n/a (DB-configured); our own case |
| C5 | cheap model's context smaller than the selection payload | chat model for that call | trims the prompt instead (**intended difference**) |
| C6 | resolver called twice in one tool instance | resolved once (cached) | resolved once |

**Case set D: scope:** a query naming a source as its subject ("how much storage does our Google Drive plan include") has no source filter in ours. Upstream's WHERE-vs-SUBJECT eval cases are the spec. Record which of them would narrow there; none may narrow here.

**Record** every case result (pass, intended difference, unexpected difference) in the tracker. Fix or explain each unexpected difference before rollout.

## 11. Open questions for the user
1. **Default for the item-14 prompts:** on (as upstream) with the `false` off-switch for baseline runs? Recommended: **on**.
2. **Selection model config:** env vars now (recommended, zero migration), with an admin "default model for search selection" later? The later option needs a small migration (VARCHAR length) and UI.
3. **Pinned per-agent models:** when the cheap selector is configured, should agents or workflow steps pinned to a stronger model keep selection on their own model? The plan says no (global cheap model). The alternative is a per-agent opt-out.
4. **Acceptable completeness tolerance** for turning on the cheap selector (e.g. ≤1 pt drop on the L4 set), and which model to try first (`gpt-4o-mini` is already the fallback default in seeding).
5. **Also port the `document_filter` timeout (#12333) and the doubled selection budget (#14451)** in this lane? Both are small and adjacent, and the cheaper selector offsets the budget's cost.
6. **Workflows:** should step agents (via `agent_tool`) also get `COMPLETE_ANSWER_REMINDER` when they search? This is not upstream behaviour and could shift guard-rail outputs, so the plan says **no** for now.

**Decided 2026-10-30 (user):**
1. `ENABLE_COMPLETE_ANSWER_PROMPTS` default **ON** (L4 also measures OFF).
2. Env/config now; admin setting later.
3. Agents pinned to stronger models **also** use the cheap evidence-selection model when it is configured.
4. Completeness threshold / model choice decided by the L4 measurement (try `gpt-4o-mini` first).
5. **Yes** — also port the selection timeout and the doubled selection budget, in our own names.
6. Workflow steps do **not** get the completeness reminder.

## 12. Progress tracker
- [x] 2026-10-30 Research: upstream commits (§1), our prompt builders and callers, search-scope state, LLM factory reuse, test layout
- [x] 2026-10-30 Plan doc written (this file)
- [x] 2026-10-30 User approval of plan + answers to §11 (recorded under §11 "Decided 2026-10-30")
- [x] 2026-10-30 Record pre-existing test failures (baseline run of `tests/unit/om/chat`, `prompts`, `tools`, `workflows`, `pulse`, `migration_safety`, `context` at 2fa6ebfc3): 585 passed, 10 failed, 2 collection errors — all pre-existing/unrelated: `test_chat_utils.py::TestGetCustomAgentPrompt` x2, `test_tool_utils.py::test_explicit_tool_calling_supported` x2 (claude), `test_websearch_utils.py` x6, collection errors `mcp/test_mcp_result_errors.py`, `open_url/test_snippet_finding.py`
- [x] 2026-10-30 Config block in `app_configs.py` — named `# --- complete-answer-prompts ---` (integrator's block name, supersedes `search-prompts`): `ENABLE_COMPLETE_ANSWER_PROMPTS` (default on), `EVIDENCE_SELECTION_LLM_PROVIDER`/`_NAME`, plus Q5 ports `EVIDENCE_SELECTION_LLM_TIMEOUT_S` (60) and `EVIDENCE_SELECTION_BUDGET_MULTIPLIER` (2; set 1 for previous budget)
- [x] 2026-10-30 `COMPLETE_ANSWER_REMINDER` + `MULTI_PART_ANSWER_GUIDANCE` in `chat_prompts.py` (text exactly as §5.0)
- [x] 2026-10-30 Wired via `om/prompts/prompt_utils.py::build_citation_guidance_block` + `complete_answer_prompts_enabled` into `build_reminder_message`, `build_system_prompt` (append path) and `replace_citation_guidance_tag` (placeholder path — note `DEFAULT_SYSTEM_PROMPT` itself uses `{{CITATION_GUIDANCE}}`, so this is the default path)
- [x] 2026-10-30 Tests: `test_complete_answer_prompts.py` (13), `test_llm_loop_complete_answer.py` (7), `test_no_source_autonarrow.py` (6), `prompts/test_prompt_utils.py` +4 — green
- [x] 2026-10-30 `om/secondary_llm_flows/evidence_selection_llm.py` + `SearchTool.evidence_selection_llm` + context-window guard (`_fits_evidence_selection_window`, `_pick_section_selection_llm`); timeout via `timeout_override` in both `document_filter.py` calls
- [x] 2026-10-30 Tests: `secondary_llm_flows/test_evidence_selection_llm.py` (8, incl. timeout), `tools/test_search_tool_evidence_routing.py` (11, incl. `construct_tools` path) — green
- [x] 2026-10-30 Gates (§9): naming grep 0 on all 13 files; ruff + mypy clean; compileall + import of all §6 callers OK; suites 640 passed (final run), same 10 pre-existing failures + 2 collection errors; `migration_safety/test_golden_snapshot` flags only `added=['<root>.secondary_llm_flows.evidence_selection_llm']` (expected — integrator regenerates baseline.json); `tests/route_rename` 2 failed = pre-existing stale snapshots (80 MISSING endpoints, unrelated, no routes touched); `search_baseline/test_search_tool_layer.py` 7 passed (env unset)
- [x] 2026-10-30 Cross-verify (§10): `d:\tmp\upgrade-xverify\complete-answer-prompts\` — `cases.json`, `structure.py`, `run_ours.py` (om.* only), `run_ref.py` (reference checkout in its own py3.13 venv `d:\tmp\upgrade-xverify\venv-ref`), `diff.py`, `run_scope_ours.py`. Nothing imported into our tree. Note: the reference checkout is at its **tip**, which has a later prompt-caching refactor (not one of the §1 commits) that moved citation + coverage guidance from the system prompt into the per-turn reminder and dropped the separate citation reminder; differences that come only from that refactor are marked (R).
- [x] 2026-10-30 Set A: A1 SAME (no blocks); A2 (default prompt, which carries `{{CITATION_GUIDANCE}}`) **intended diff**: ours citation+multi-part at the placeholder, ref citation only (the placeholder gap of §5.1; ref compensates via its reminder (R)); A2b (no placeholder) SAME: company → citation → multi-part; A3 **intended diff** (as planned); A4 SAME (placeholder emptied); A5 SAME (no duplicates); A6/A6b flag off == pre-L2 output (byte-equal). No unexpected differences.
- [x] 2026-10-30 Set B: B4 SAME (cite off → task only). B1/B2/B3/B5: same order of the shared blocks (task → last-cycle → citation → complete-answer → file); the difference is (R) only: ref's reminder carries citation-guidance + coverage text in place of our `CITATION_REMINDER`, while ours keeps those two in the system prompt (the design of the ported commits). B5 (workspace turn): same builder input as B1, so both include the complete-answer reminder → no behaviour difference. Explained, not fixed (porting the caching refactor is out of scope).
- [x] 2026-10-30 Set C (mirrored from ref `test_search_tool_run.py` + `llm/test_factory.py` scenarios, our own code): C1 unset → chat model, no DB (`test_unset_returns_chat_llm_without_db`, `test_unconfigured_uses_chat_llm_everywhere`) PASS; C2 cheap model for both selection calls, chat for query expansion (`test_configured_routes_selection_and_classification`) PASS = ref; C3 resolver error / unknown provider → chat + one warning (`test_unknown_provider…`, `test_builder_exception…`, `test_resolver_failure_keeps_search_on_chat_model`) PASS = ref; C4 one env var → chat + warning PASS (ours only); C5 small context → chat model for the list call (`test_small_context_selection_model_falls_back_for_that_call`) **intended diff** (ref trims); C6 resolved once per instance PASS = ref. Extra ref scenario `test_empty_search_never_resolves_selection_model` → found ours resolved even with 0 sections: **fixed** (resolve only when there are sections) + mirrored test. Ref cost-limit/incognito scenarios: dropped by design (§1).
- [x] 2026-10-30 Set D: ref scope-prompt examples — SUBJECT ("which teams use the Salesforce connector", "how much storage does our Google Drive plan include", HR topic) → ref [] / ours None: SAME. WHERE/COMBINED/BACKOFF ("search Confluence for…", "in Google Drive, find…", "check Jira first, then Confluence…", "look in Slack and Gmail…") would narrow in ref; ours None for all (detector never called): **intended diff** (scope feature absent, §5.1). Nothing narrows here. No unexpected differences remain.
- [ ] User: Docker rebuild; manual checks: A) chat question with 2 sub-parts + a figure → both answered, figure exact; B) "what does our Google Drive plan include" → sources not limited to Drive; C) Slack bot answer; D) 2–3 dept workflow `test_<dept>.py` guard-rail suites; E) with `EVIDENCE_SELECTION_LLM_*` set, `api_server` logs show the selection calls on the cheap model and no fallback warnings
- [ ] L4: baseline vs L2 eval run (flag off/on; selector unset/set); record numbers here
- [ ] User: review + commit (run `build_inventory.py --check` first)
- [ ] Tick items 14 and 6 in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD`
