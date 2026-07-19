# HANDOFF — how to run the workstreams (point-and-implement)

Each `WS-*.md` is now **self-contained**: it opens with a **"▶ AGENT INSTRUCTIONS — START HERE"**
block that tells the agent everything (self-isolate in its own worktree, read CONTRACTS.md, clean-room
rule, phases + review gates, research, standards, status logging, no commit). So your workflow is:

## Your entire action per workstream
1. Open a **new Claude Code chat session** in this repo (`d:\llm\danswer20022026`).
2. Say: **"Implement `rewrite-plans/<WS-file>` — follow its AGENT INSTRUCTIONS block."**
3. That's it. The agent creates its own git worktree, works in phases, logs progress to
   `rewrite-plans/status/<WS-ID>.md`, and reports at each gate. It does NOT commit.

No git commands from you. No copy-pasting long prompts. Each session self-isolates, so multiple can run
in parallel without colliding on shared files.

## Which files, in what order
- **First (foundations):**
  - `WS-M-multitenant.md` — **RESUMES** existing worktree `.claude/worktrees/agent-aa85bc62ad66a2e0c`
    (has partial `backend/om/tenancy/` work). Contract 3 already published.
  - `WS-B-team-rbac.md` — owns Team + Access-API contracts (confirms/finalizes them).
  - `WS-A-purge.md` — deletes license paywall + billing.
- **Then (any time — contracts are already concrete in `CONTRACTS.md`):**
  `WS-C-saml.md`, `WS-D-standard-answers.md`, `WS-E-search.md`, `WS-F-rate-limits.md`,
  `WS-G-scim.md`, `WS-H-analytics.md`.

You can launch all of them; WS-B landing first just reduces churn on the Team model.

## Monitoring
Open the `rewrite-plans/status/` folder in any editor — each session appends its progress to
`status/<WS-ID>.md`; `status/OVERVIEW.md` is the roll-up.

## Contract-sync rule
`CONTRACTS.md` (main tree) is the frozen source of truth. A workstream implements to it as written. If
one genuinely must change a contract, it STOPS and tells you; you edit the **main-tree** `CONTRACTS.md`,
and other sessions pick it up (they branch from the main tree). Only WS-B may finalize Contracts 1 & 2;
only WS-M may finalize Contract 3.

## When workstreams are done — integrate
Come back to a session and say **"integrate the rewrite-plans worktrees"**. The integrator will:
merge the worktrees → apply the shared-file snippets (`main.py`, `models.py`, `auth_check.py`, menu) →
linearize the Alembic chain off `0003_agent_rename` → boot multi-tenant/no-billing → run
`check_ee_router_auth` + tenant-isolation smoke test → IP-review against commits
`c26724925` + `77ed3c9c2`. Nothing is committed until you say so.

## Cleanup (after integration)
Worktrees live under `.claude/worktrees/`. Remove with `git worktree remove <path>` and delete merged
`rewrite/ws-*` branches.
