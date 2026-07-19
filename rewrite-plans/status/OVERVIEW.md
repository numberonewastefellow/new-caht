# EE-Rewrite — Progress Overview

Live roll-up of all workstreams. Individual agents append to `status/<WS-ID>.md` in this folder.
Open this folder in any editor/session to monitor. The orchestrator updates this table as
notifications arrive.

**Execution model: user-driven separate sessions (see `rewrite-plans/HANDOFF.md`).** The first
background-agent attempt was killed by a VSCode restart; we switched to durable separate sessions.

| WS | Wave | Status | Notes |
|----|------|--------|-------|
| WS-M Multi-tenant | 0 | 🟡 partial — RESUME | Contract 3 done; partial `backend/om/tenancy/` in worktree `agent-aa85bc62ad66a2e0c` |
| WS-B Team/RBAC | 0 | ⬜ start fresh | orphan worktree removed |
| WS-A Purge | 0 | ⬜ start fresh | orphan worktree removed |
| WS-C SAML | 1 | ⬜ ready | contracts concrete in CONTRACTS.md |
| WS-D Standard answers | 1 | ⬜ ready | — |
| WS-E Search | 1 | ⬜ ready | — |
| WS-F Rate limits | 1 | ⬜ ready | — |
| WS-G SCIM | 1 | ⬜ ready | — |
| WS-H Analytics | 1 | ⬜ ready | — |

Legend: ⬜ ready/not started · 🟡 partial · ⏳ running · ✅ done · ❌ needs attention

## Contracts status
- **Contract 3 (Tenant):** ✅ FINALIZED in `CONTRACTS.md` (`get_current_tenant_id()`, `user_tenant_mapping` global).
- **Contracts 1 & 2 (Team + Access):** concrete in `CONTRACTS.md`; WS-B confirms/finalizes.

## Notes
- Nothing is auto-committed. Each session works in its own git worktree.
- See `rewrite-plans/HANDOFF.md` for exact worktree commands + per-WS prompts + launch order.
