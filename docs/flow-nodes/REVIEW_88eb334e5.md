# Flow nodes: code review of commit 88eb334e5

**Reviewed:** commit `88eb334e5` "flow-wise" (parallel, loop and code nodes, workflow versioning, sandbox hardening), merged locally in `3b2074ed3`.
**Date:** 2026-10-31.
**Companion docs:** [DESIGN.md](DESIGN.md), [REFERENCE_STUDY.md](REFERENCE_STUDY.md), [HANDOVER.md](HANDOVER.md), [PROGRESS.md](PROGRESS.md).

## Verdict

**The architecture is sound, but the feature is not enterprise-grade yet.**

- **What is good:** the coordinator and branch-worker design matches graphon and LangGraph. The node registry is clean and modular. Backward compatibility is well guarded by the golden fixtures, and the sandbox hardening is real.
- **What blocks enterprise use:**
  - saves can lose edits;
  - stopping a branch doesn't stop the agents running in it;
  - there are no budgets, retries or per-tenant limits;
  - chat-started runs don't survive a restart.
- **What users can't do yet:** build Parallel or Loop steps in either editor. Containers can only be created through the API or JSON. Webhooks (P4) are not started.

## How this review was done

This was a static review. **No tests, load tests or live runs were executed for it**, so failure scenarios come from reading the code and have not been reproduced.

Each finding is tagged with its evidence:
- **[Direct]:** the code was read directly during this review.
- **[Reviewer]:** reported by one independent read-only reviewer, and not re-checked unless noted.

Line numbers refer to commit `88eb334e5`. The working tree may already differ: the "dedicated agents" fix was in progress, uncommitted, when this was written (`nodes/agent.py`, `agent_tools.py`, `base.py`, `workflow_engine.py`, `agent_tool.py`, `stepAgents.ts`, plus tests). That work was not reviewed.

## How it is built, and where the ideas came from

| Piece | Our files | Main inspiration |
|---|---|---|
| Node registry, pinned `(type, version)`, opt-in upgrades | `nodes/base.py`, `registry.py`, `builtin.py` | n8n `typeVersion`; Activepieces pinned pieces and flow migrations |
| One coordinator thread owns the DB, trace and checkpoints | `sequential.py`, `blocks.py` | graphon dispatcher (Dify's engine); LangGraph Pregel |
| Parallel: bounded pool, isolated branch state, merge in declared order | `branches.py`, `nodes/parallel.py` | graphon iteration window; LangGraph ordered writes |
| Loop: mandatory `max_iterations`, `$loop.item/index/previous` | `nodes/loop.py` | Dify/graphon Loop and Iteration; Langflow's iteration guard |
| Code step: base64 source, nonce result frame, strict output limits | `nodes/code.py`, `code_harness.py` | Dify code node and graphon limits; n8n task runner |
| Immutable versions, runs pinned by content hash | `versioning.py`, `agent_workflow_version` | Windmill hashed versions; Temporal pinned runs |
| Sandbox hardening and warm pool | `code-interpreter/` | Windmill nsjail; dify-sandbox; Activepieces warm engine |

[REFERENCE_STUDY.md](REFERENCE_STUDY.md) and [HANDOVER.md](HANDOVER.md) have the full source map and licence rules.

## Findings

### High

1. **Saves can lose edits, and a save is not atomic.** [Direct: `saving.py`, `versioning.py`. Reviewer: the commit in `db/workflow.py:140`]
   - **Where:** `saving.py:221-239`, `db/workflow.py:140`, `versioning.py:47-64`.
   - **Problem:** `expected_version` is checked without a row lock, and the steps commit in a different transaction from the version row.
   - **Impact:** two concurrent saves can lose one edit with no 409. Or the second save returns a 500 after its steps are already committed, and the live definition no longer matches its version.
   - **Fix:** `SELECT … FOR UPDATE`, compare after taking the lock, use one transaction, and map a leftover IntegrityError to 409.

2. **The first save of a pre-migration workflow keeps no "before" snapshot, and `version` stays 1.** [Direct]
   - **Where:** `versioning.py:47`.
   - **Impact:** the pre-edit definition can't be restored. A second admin holding `expected_version=1` also passes the check and silently overwrites the first admin's edit.
   - **Fix:** pin the current graph before applying the edit, and use `next = max(latest, workflow.version) + 1`.

3. **Cancelling a branch doesn't stop the agents running in it.** [Direct]
   - **Where:** `agent_streaming.py:134`, `nodes/agent.py` (passes `ctx.is_connected`), `branches.py:219-226`.
   - **Problem:** the agent stream checks `is_connected`, not the branch's `cancel_event`.
   - **Impact:** after `first_success` picks a winner, losing branches keep calling the LLM and tools until the current agent finishes, and their tokens are never counted. A stop from the user does reach them through `is_connected`.
   - **Fix:** pass `ctx.stop_requested` to `stream_agent_packets`, and account for abandoned branches.

4. **The sandbox's admission queue can starve its own threadpool.** [Direct: limits and sync routes. Reviewer: the failure chain. Not load-tested]
   - **Where:** `code-interpreter/.../app_configs.py:60-61`, `routes.py:243,331`, `security.py:219-228`, `main.py:140-144`.
   - **Problem:** 8 workers + 32 queued = 40, which equals AnyIO's default threadpool size, and waiting requests hold threads.
   - **Impact:** under load `/health` can hang, the K8s liveness probe kills the pod, and running code steps die. The "503 when full" rule doesn't fire.
   - **Fix:** do the admission check on the event loop, make `/health` async, and keep the limits below the threadpool size.

5. **Design delta C5 is not implemented: there are no per-tenant or global sandbox limits in the backend.** [Reviewer]
   - **Where:** `nodes/code.py:298-309`.
   - **Impact:** one tenant's parallel or loop workflow can take all the sandbox slots, so other tenants' code steps and chat Python tool get 503s.
   - **Fix:** add per-tenant and global bounded semaphores, and per-tenant fairness in `ExecutionLimiter`.

### Medium

6. **`on_branch_error=fail` is not fail-fast.** [Direct] The runner waits for every branch before checking for failures (`parallel.py:164`), so healthy branches keep spending after the run is already doomed. The `drop_failed` mode from delta E4 is also missing.
7. **A loop inside a parallel branch loses the branch's cancel signal.** [Direct] `loop.py:_scoped()` builds a `ScopedRunContext` without passing `cancel_event`, so it gets a fresh one. The losing branch's loop keeps iterating after `first_success`.
8. **The run timeout is only checked between nodes.** [Direct] `blocks.py:74` checks after a node finishes, and the wait loop in `branches.py:203-217` checks only for a stop. A hung LLM call inside a branch therefore holds the run past its timeout.
9. **No global run budget or global concurrency limit.** [Direct]
   - Delta E7's step budget and E1's `WORKFLOW_MAX_CONCURRENCY` don't exist.
   - Three nested loops allow up to 50³ = 125,000 agent calls, bounded only by the run timeout.
   - `max_concurrency` is per container, and each branch opens its own DB session for its whole duration (`branches.py:161`), which can tie up pooled connections during LLM calls. The pool impact was not measured.
10. **Duplicate `output_key` is not rejected at save, though E3 says it is.** [Direct] `_check_unique` checks only `node_key` and `step_order` (`saving.py:123-129`). `loop` isn't reserved as an output key either, so it can collide with `$loop.*`.
11. **No save-time data-flow check.** [Direct] A reference to a sibling branch's output or to a later step isn't caught at save. What happens at run time depends on the step type:
    - **Agent steps:** the literal text `$name` goes into the prompt, with no error (`inputs.py:58-61`).
    - **Code steps and `for_each` items:** the run fails with `UnresolvedReferenceError`.
12. **`schema_version` 2 and the safe tokenizer are not implemented.** [Direct] The field is stored, but no engine code branches on it, so new workflows also get the legacy substring substitution (`inputs.py:51-62`). This now affects loops:
    - `$loop.item.title` in an agent mapping becomes the whole item followed by the literal `.title`, with no error. Field paths only work in code steps.
    - A step with output key `l` or `loop` corrupts `$loop.item`.
    - Substituted text is re-expanded, so an item or LLM output containing `$other_key` pulls in that step's output.
13. **Version snapshots leave out workflow-level settings.** [Reviewer] The orchestrator prompt and LLM, `max_steps`, `max_calls_per_agent`, description, `is_public` and icon aren't in the definition. Edits to them create no version, the 409 doesn't protect them, and restore can't bring them back.
14. **Run pinning only exists in sequential v2.** [Reviewer] `llm_decision` runs and the legacy engine don't record `workflow_version_id` (`workflow_engine.py:1283,1297`), so their paused runs resume against the edited workflow. 29 of the live workflows are `llm_decision`.
15. **Both editors silently upgrade router v1 to v2.** [Reviewer] `serializer.ts routerStepFields` forces the version on every save, which contradicts the opt-in, diffed upgrade rule.
16. **Migration `0002` risks.** [Reviewer]
    - `node_key` is NOT NULL with no server default, which breaks rolling deploys while old pods still insert steps.
    - `parent_step_id` and `workflow_execution.workflow_version_id` have no index.
    - Downgrade leaves container rows that old code would misrun.
17. **Code step issues.** [Reviewer]
    - The CPU limit is fixed at 5s, so CPU-bound code never reaches a 30s timeout and gets a misleading "timed out after 30s" error.
    - A valid result near 1 MB can fail as "truncated", because the cap counts bytes while the frame also carries up to 64K of logs.
    - Falling back from `run_function` to `/v1/execute` silently loses protections: output isn't bounded while reading, workspace files are kept, error kinds are lost, and K8s pods have no pids limit or deadline.
    - Captured logs and tracebacks are never shown.
18. **No authorization check on the agent a step references.** [Direct] The save path only checked that the agent exists, not that the admin saving the workflow may use it, such as another team's private agent. The in-progress "dedicated agents" fix adds default-Assistant and wrapper-agent rules, but the part of it seen here does not add an ownership check.

### Low

All from the independent reviewer unless tagged.

- Negative `step_order` returns a 500; `node_key` has no length or charset check.
- The container check resolves the latest spec instead of the parent's pinned version (`saving.py:149`).
- Restore returns a 500 for an unknown node type or definition format.
- Version history exposes old prompt overrides and author UUIDs to anyone who can view a public workflow.
- Runs can bump `version` when the hash drifts, causing spurious 409s attributed to the chat user.
- [Direct] A branch's `timed_out` isn't merged (`merge_branch`). The top-level timeout check catches it at the next node, but the parallel step reports success with partial output.
- A forged result frame can raise an uncaught `ValueError` or `RecursionError` in the backend (only admins write code).
- Sandboxes run with `--cgroupns host`; a new `requests.Session` is created per code run and never closed.
- [Direct] Token usage is a word count, not provider usage (`nodes/agent.py`, "Rough token estimate"). This was already the case, but parallel and loop multiply the cost it fails to measure.

### Checked and correct

From the independent reviewers, not re-checked unless tagged:

- **Tenant binding:** `X-OM-Tenant` comes only from the tenant context variable and is copied into branch threads ([Direct] for the copy).
- **Sandbox auth:** fails closed, with constant-time compare.
- **Code harness:** the single-frame rule and strict output validation hold. User code can forge its own frame, but validation is the real boundary, as the design says.
- **Warm pool:** containers are single-use, taken under a lock.
- **Docker flags and K8s NetworkPolicy:** flags are as designed, and the selector matches the executor pods.
- **Content hash:** stable across saves.
- **Upsert by `node_key`:** kept children are detached before a removed container is deleted.
- **Resume:** sequential v2 uses the pinned definition.
- **Editors:** both use one serializer, all fields round-trip without flattening containers, and both send `expected_version` and handle 409.

## Gaps against the plan

| Promised | Status |
|---|---|
| E1 global `WORKFLOW_MAX_CONCURRENCY` | Not built; the limit is per container |
| E3 duplicate `output_key` rejected at save | Not enforced |
| E4 three error modes | `fail` and `continue` only, and `fail` isn't fail-fast |
| E5 progress saved inside a container | Not built (DESIGN.md defers it to after v1); a crash re-runs the whole container, including side-effecting tools |
| E6 throttled checkpoints | Not built; one checkpoint per completed top-level node |
| E7 step budget, break checked before and after, explicit break | Only `max_iterations`, checked before each iteration |
| E9 retry with backoff | There is no node retry at all |
| C3 typed error kinds | Free-text errors |
| C5 per-tenant and global semaphores | Missing |
| V3 opt-in, audited upgrades | Routers auto-upgrade; no audit event |
| `schema_version` 2 safe tokenizer | Field only |
| Pinning in every mode | Sequential v2 only |
| Every save bumps the version | Only when step content changes, and not on a legacy workflow's first save |
| Container UI in both editors | Not built |
| P4 webhooks | Not started |
| `research/00-platform-survey.md` | Not written |

## What enterprise platforms have that we don't

This comparison is based on general knowledge of Temporal, LangGraph, Copilot Studio/Power Automate, Bedrock AgentCore and n8n, plus a short web search whose results were mostly vendor guides. It is a direction check, not a feature-by-feature audit of those products.

The common view is that the orchestration layer should own state, retries and timeouts, with the model call as one step inside it.

**Must-have**

1. **Durable execution for every run.**
   - Pulse already runs on Celery with a heartbeat and a reaper, but a reaped run is marked `interrupted` and not retried (`pulse/scheduler.py:304-324`).
   - Chat-started runs stream through the request's generator. A restart kills them, and only paused runs can resume. No reaper for them was found in the workflow or Pulse code, so they appear to stay `running`.
   - **Needed:** runs on a worker queue, a lease and heartbeat for all runs, and resume of crashed runs from the last checkpoint.
2. **Per-node retry policy and timeout.** Attempts, backoff, retry-on rules (LLM 429/5xx, sandbox 503), and a timeout that can interrupt a stuck node.
3. **Idempotency for side-effecting tools.** Keys such as `(execution, node_key, attempt)`, so a retry or resume doesn't repeat an external action. LangGraph's docs make the same point: on resume a node starts again from its beginning, so side effects must be idempotent.
4. **Cost and quota governance.** Real provider token usage, budgets per run, workflow and tenant with a hard stop, and tenant-level concurrency limits.
5. **Human approval gates inside containers.** Pausing inside parallel and loop is banned today, which rules out "approve this branch's result".
6. **Observability.** OpenTelemetry spans per run, node and LLM call; live per-branch trace progress (trace calls are buffered until the join today); metrics for queue depth, latency and failure rate.
7. **Audit and RBAC.** Audit events for save, restore, upgrade and run; separate edit, publish and run permissions; owner checks on restore; limits on which agents and tools a workflow may use.
8. **Release safety.** Draft and publish, so an edit doesn't immediately change what production users run. History-only was a deliberate user decision on 2026-10-30, and is worth revisiting for enterprise customers.
9. **Data governance.** PII redaction and retention limits, because checkpoints and traces store full prompts and outputs.

**Nice to have:** node-result caching, sub-workflow nodes, branch lanes in the timeline, and evaluation gates before publishing.

## Recommended fix order

One module at a time, each finished and tested before the next.

| # | Work | Findings | Main files |
|---|---|---|---|
| 1 | Save and version transaction, snapshot completeness, migration follow-up | 1, 2, 13, 16 | `saving.py`, `versioning.py`, `db/workflow.py`, `graph.py`, new migration |
| 2 | Cancel, fail-fast and timeout in the engine | 3, 6, 7, 8 | `agent_streaming.py`, `branches.py`, `nodes/loop.py` |
| 3 | Save-time validation and safe references | 10, 11, 12, 18 | `saving.py`, `inputs.py`, `nodes/agent.py` |
| 4 | Budgets and concurrency limits | 5, 9 | `app_configs.py`, `branches.py`, `nodes/code.py` |
| 5 | Sandbox admission and code step fixes | 4, 17 | `code-interpreter/.../api/`, `main.py`, `nodes/code.py`, `code_harness.py` |
| 6 | Pin `llm_decision` runs; opt-in router upgrade | 14, 15 | `workflow_engine.py`, `serializer.ts` |
| 7 | Enterprise items, each with its own TODO and plan doc first | Section above | To be planned |

Item 3 needs care: changing substitution semantics must stay behind `schema_version`, so existing workflows keep their exact behaviour.

**Verification for each step:**
- Backend unit tests and the golden suite with `ENGINE_IMPL=v2` and `legacy`.
- DB tests in `tests/external_dependency_unit/workflow/` on `flow_dev`.
- Live E2E scripts on the isolated preview.
- For web changes: `npx tsc --noEmit` and the workflow jest suites.
- Add a new regression test for each finding fixed. Findings 1, 3, 4 and 7 especially need tests that reproduce them, since this review did not run them.

## Sources

- [LangGraph: durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- [Temporal: LangGraph integration](https://docs.temporal.io/develop/python/integrations/langgraph)
- [DevOps.com: The missing runtime for long-running AI agents](https://devops.com/the-missing-runtime-for-long-running-ai-agents/)
- [IntuitionLabs: Agentic AI workflows and Temporal](https://intuitionlabs.ai/articles/agentic-ai-temporal-orchestration)
- [Context Studios: AI agent orchestration tools 2026](https://www.contextstudios.ai/guides/ai-agent-orchestration-tools-2026.md)
- [TechTrends KE: WSO2Con Africa 2026 on durable workflows](https://techtrendske.co.ke/2026/09/22/wso2con-africa-2026-durable-workflows/)
