# rewrite-plans — clean-room reimplementation of the Onyx-EE-origin code

This folder is the execution package for removing all **Onyx Enterprise-Licensed** code from
`backend/om/**` by clean-room reimplementing (or deleting) each feature. Each workstream runs in its
own Claude Code session + git worktree; `CONTRACTS.md` is the only cross-workstream coupling.

## Why
Code merged in by commits `c26724925` + `77ed3c9c2` originated under Onyx's Enterprise License (not
MIT) — it may not be copied/merged/sublicensed/sold. We re-create the **functionality** with our
**own original code** (behavior spec only; never copy Onyx source). Not legal advice — IP-review the
result before selling.

## Read first
- **`CONTRACTS.md`** — Team-model, Access-API, and Tenant-context contracts; shared-file ownership
  rules; Alembic linearization; and the 12 mandatory engineering standards.

## Workstreams (one plan file each)
| File | What | Wave |
|------|------|------|
| `WS-A-purge.md` | DELETE license paywall + billing (keep multi-tenant) | 0 |
| `WS-M-multitenant.md` | KEEP + refactor multi-tenant data isolation, strip billing; owns Tenant contract | 0 (foundation) |
| `WS-B-team-rbac.md` | Enterprise RBAC → **Team**; owns Team + Access-API contracts | 0 (foundation) |
| `WS-C-saml.md` | SAML SSO clean-room | 1 |
| `WS-D-standard-answers.md` | Standard answers clean-room | 1 |
| `WS-E-search.md` | Search / query-expansion clean-room | 1 |
| `WS-F-rate-limits.md` | Rate limiter redesign + full observability | 1 |
| `WS-G-scim.md` | SCIM 2.0 (RFC 7643/7644) redesign | 1 |
| `WS-H-analytics.md` | Analytics / history / reporting with recharts | 1 |

## Launch order
1. **Wave 0:** start **WS-M** + **WS-B** (they publish contract specifics into `CONTRACTS.md`) and
   **WS-A** (pure deletes). WS-A holds its `main.py` tenant-middleware snippet until WS-M defines it.
2. **Wave 1:** once contracts are published, start **WS-C, WS-D, WS-E, WS-F, WS-G, WS-H** in parallel.
3. **Integrate:** one integrator session merges worktrees → applies shared-file snippets → linearizes
   Alembic → boots multi-tenant/no-billing → runs `check_ee_router_auth` + tenant-isolation smoke test
   → IP-review against `c26724925` + `77ed3c9c2`.

## How to run (point-and-implement)
Each `WS-*.md` starts with a self-contained **"▶ AGENT INSTRUCTIONS — START HERE"** block. Just open a
new Claude Code chat session in this repo and say:
> Implement `rewrite-plans/<WS-file>` — follow its AGENT INSTRUCTIONS block.

The agent self-isolates in its own git worktree, works in phases with review gates, logs progress to
`status/<WS-ID>.md`, and does not commit. No git commands or long prompts needed from you. See
`HANDOFF.md` for full details and the integrate step.

**Note:** `WS-M` RESUMES the existing worktree `.claude/worktrees/agent-aa85bc62ad66a2e0c` (partial
work); all others create a fresh worktree.

## Every workstream must (from CONTRACTS.md standards)
Phased execution + self-review gates · TodoWrite · web-research best practices first · clean-room
(no Onyx copying) · multi-tenant-safe · per-feature config table + UI · VertualAI design system ·
menu update · structured OpenSearch logs on every CRUD (try/except) · full OOP + strict typing ·
delete old tables/code only after verify · module README.
