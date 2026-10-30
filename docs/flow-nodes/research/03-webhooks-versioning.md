# Reference study 3 — webhook triggers and node/workflow versioning

Sources are in `D:/llm/reference-frameworks/`, checked out 2026-10-30.
- **Read-only, patterns only:** n8n (SUL), Windmill (AGPL), Dify main.
- **Reference:** Activepieces (MIT core), Langflow (MIT), graphon (Apache).

Everything below is in our own words. Some checkouts are partial (the n8n body-parser constants, Windmill's `http_trigger_auth.rs`, Langflow's validator source), so those few points are not verified in code.

## Webhooks — per repo
**n8n** (`packages/cli/src/webhooks/`)
- **Path lookup:** static paths sit in a cache keyed by method and path, falling back to the DB. Dynamic paths are prefixed with the node's UUID, and the most specific match wins. The DB primary key is (path, method), so two workflows can't claim the same path.
- **Production** runs the published `activeVersion`.
- **Test mode:** a listener is stored in a cache hash with a TTL and expiry, and is removed after one execution. In multi-main setups it is relayed to the editor's process over pubsub.
- **Response modes:** onReceived, lastNode, responseNode and streaming. GET always uses onReceived. If no response comes back the caller gets 504.
- **Before handling:** a method allowlist and CORS checks run first, n8n's own auth cookies are stripped, and oversized multipart uploads return 413.
- **Webhook node** (v1–2.2): IP allowlist and bot filter (403), a raw-body option, and basic/header/JWT auth compared in constant time.

**Windmill** (`backend/windmill-api/src/`)
- **Routes:** `run/p` (by path), `run/h` (by hash), `run/f` (flow), `run/fv` (pinned flow version). Each comes in three flavours: async (201 + job id), `run_wait_result` (sync) and `run_and_stream` (SSE).
- **Disabled native triggers still return 200**, so the provider doesn't drop the hook.
- **Tokens** can be scoped to a single runnable (`jobs:run:flows:<path>`).
- **HTTP triggers:**
  - An in-memory router per method, and a 10 s scope cache.
  - Jobs run as the trigger's owner, not the caller.
  - The raw body is kept for signature or custom-script auth, with the signature resource cached for 60 s. ⚠ It parses the body *before* verifying the signature.
  - Modes: Sync, Async, SyncSse and Suspended.
  - Payload args are scrubbed so they can't be used to inject resource or variable references.

**Activepieces** (`packages/server/api/src/app/webhooks/`)
- **Routes:** `/:flowId` is async, `/:flowId/sync` is sync, `/draft` runs the draft, and `/test` only captures a sample and doesn't run.
- **Versions:** production uses the published version, falling back to latest.
- **Status codes:**
  - 410 for an unknown flow; 404 for a disabled one;
  - 413 for oversized bodies, ⚠ checked after parsing;
  - 402 when credits run out; 408 on sync timeout.
- **Handshake strategies:** a header, a query parameter, a body parameter, or HEAD.
- **Queueing:** async requests become a BullMQ job with a random id, so there is **no deduplication**.

**Dify** (`api/controllers/trigger`, `api/services/trigger`, `api/core/trigger`)
- **Routes:** `/webhook/<id>` runs the published workflow. `/webhook-debug/<id>` works only while the editor is listening; debug events are kept in Redis for 300 s.
- **Auth:** only the unguessable 24-character id plus required-header checks. **No HMAC.**
- **Limits:** Content-Length is checked *before* parsing, and the content type must match.
- **Parameters:** coerced to types and mapped to `webhook_body`, `webhook_headers` and `webhook_query_params`.
- **Quota:** reserved first, then committed or refunded. A workflow can have at most 5 webhook nodes.
- **Plugin triggers** (`/plugin/<uuid>`): the plugin verifies and extracts the payload using decrypted credentials, then the run is dispatched asynchronously.

**Langflow** (`src/backend/base/langflow/api/v1/endpoints.py`)
- **Route:** `POST /webhook/{flow}` returns 202 and runs as the flow's owner. An API key is optional, behind `WEBHOOK_AUTH_ENABLE`.
- ⚠ The **body has no size cap**, and the run is an in-process asyncio task, so it is **lost on restart**.
- **CVE-2025-3248:**
  - The cause: `/validate/code` was unauthenticated and *executed* function definitions while validating them. Decorators and default arguments run at definition time, which gave remote code execution.
  - The fix: the endpoint now requires authentication, and in restricted modes submitted code must hash-match a server template, with the trusted server copy validated instead.
  - **Lesson: never execute or evaluate user content while validating it.**

| | URL scheme | Auth | Test mode | Response | Dedup | Limits | Queue |
|---|---|---|---|---|---|---|---|
| n8n | `/webhook/<path>` | none/basic/header/JWT + IP | cache-TTL listener, single run | received/lastNode/responseNode/stream | ✗ | 404/403/413/504 | in-proc or queue |
| Windmill | p/h/f/fv + custom | scoped token, signature, script | previews | async/sync/SSE | ✗ | 201; 200 when disabled | DB queue |
| Activepieces | `/:flowId[/sync\|/draft\|/test]` | per-piece signature on raw body | `/test` captures only | async/sync | ✗ | 410/404/413/402/408 | BullMQ |
| Dify | `/webhook/<id>` + debug | secret id + headers | Redis listener (300 s) | static response | ✗ | Content-Length, quota | Celery |
| Langflow | `/webhook/{flow}` | optional API key | SSE to UI | 202 | ✗ | none | asyncio (not durable) |

**None of them deduplicate. We will.**

## Versioning — per repo
- **n8n:**
  - Each saved node keeps its `typeVersion`.
  - A versioned node type maps each version number to its implementation.
  - New nodes get the default version, and an unknown version is a hard error.
  - Which properties appear is controlled per version.
- **Activepieces:**
  - **Flow schema:** each flow version has a `schemaVersion`. A **migration chain (v0→v27)** of `{targetSchemaVersion, migrate}` steps runs **lazily whenever a flow version is read**. It backs up the old JSON, writes the migrated version back, and pages on-call if it fails.
  - **Pieces:** each step is **pinned to an exact piece version**. Upgrades are explicit, with a minor/major warning. ADR 000005 freezes the resolved versions when a flow version is locked. Upgrades can be reverted, and every upgrade or revert is recorded as an audit event.
- **graphon:** node data carries `version` (default "1"). A registry maps type → version → class, with a `latest` pointer. Legacy DSL without versions is recognised by its shape.
- **Langflow:** flows store each component's code. At build time, built-in components whose code has drifted are swapped for the server copy; this is configurable. The "Update available" badge does not apply to custom components.
- **Windmill:** script and flow versions are immutable, identified by hash or version id, and callers can pin them (`fv`, `h`).

## Recommendations adopted
**Pulse webhooks — request handling, cheapest checks first**
1. **Method and token shape:** method must be POST, otherwise 405. Token shape and length are checked by regex, with 404 on failure and no DB call.
2. **Size:** if `Content-Length` is over 1 MB, return 413. Then read the body with a hard 1 MB cap, which also covers chunked uploads.
3. **Tenant:** parse the tenant from the token and validate the schema name.
4. **Rate limit:** a Redis token bucket per IP and per token-hash prefix. Return 429 with `Retry-After`.
5. **Token lookup:** hash the token and look it up in the tenant schema. Cache hits and misses for 30–60 s. Unknown and disabled tokens both get a uniform 404.
6. **Auth:**
   - **Standard Webhooks:** the `webhook-id`, `webhook-timestamp` and `webhook-signature` headers must be present, and the timestamp within ±5 min. Then compute HMAC-SHA256 over `id.timestamp.` plus the **raw body bytes** and compare in constant time against every `v1,` signature, which allows key rotation. Failure returns 401.
   - **Header-token mode:** compare in constant time.
7. **Only then parse the JSON**, with depth and key limits. This avoids the parse-before-verify mistake of Windmill and Activepieces.

**Tokens and secrets**
- Tokens use the SCIM pattern: `whk_<tenant>.<32-byte secret>`, stored as SHA-256, with only the last 4 characters shown. Two hashes can be active at once during rotation.
- The HMAC secret (`whsec_…`) has to be kept usable for verification, so it is stored **encrypted**, not hashed.

**Dedup**
- The key is `webhook-id`, a configured header, or a JSON path, stored as `PulseRun.dedup_key`.
- A partial unique index on (schedule_id, dedup_key) WHERE trigger='webhook', with inserts using ON CONFLICT DO NOTHING.
- A duplicate returns **202 with the original run id**.

**Concurrency**
- Per-token and per-tenant buckets, plus the existing active-run caps.
- **Don't** reuse run-now's "409 if a run is already active" rule. Instead queue up to N pending runs, then return 429.

**Response, test mode and payload**
- **v1 is async only:** 202 `{run_id}`, sent through the existing outbox sweeper. Sync and last-node responses are deferred.
- **Test mode:** `POST /hooks/test/{token}` works only while the owner has "Listen" open (Redis TTL 120–300 s), otherwise 409. It captures the payload for the mapping UI and does not run the workflow. It never consumes production dedup keys.
- **Payload mapping:** `{{payload.a.b}}` in `render_input_message`. Values are substituted as strings only, length-capped, and **never re-expanded**. The payload goes in a delimited "untrusted" block, because the LLM runs with the owner's tools.

**Security pitfalls**
- Verify the signature over the raw `request.body()`, never over re-serialized JSON.
- Redact tokens in access logs and never log signatures.
- Strip Authorization, Cookie and signature headers before storing the payload.
- No CORS on `/hooks`.
- Re-check the owner and workflow access at run time (`resolve_run_context`).
- A deleted workflow disables its webhooks.

**Versioning**
- **Per node:** `type` + integer `type_version`. The registry maps (type, version) to an implementation and schema, with a default version for new nodes. Old versions are kept while any row uses them, deprecated versions are hidden from the palette, and an **unknown version is a hard error**.
- **Per workflow:** `schema_version`. A chain of pure, idempotent N→N+1 steps, tested against fixtures. **Migrate lazily in memory on read; write back only on save** or from a locked background job, keeping the pre-migration JSON as a backup. If migration fails, refuse to run and alert.
- **Two kinds of change:**
  - Schema migrations are structural and automatic.
  - Node-type upgrades change behaviour and are **opt-in**. Each one has an optional `upgrade(params)`; without one, the upgrade is marked breaking.
- **Pinning in-flight runs:** an immutable `workflow_version` table, with each run storing `workflow_version_id` and a content hash. Production and scheduled runs use the published version; test runs use the draft.
- **UX:**
  - an "Upgrade available" badge per node and a banner per workflow;
  - a diff dialog with a warning on breaking changes;
  - revert, plus an audit event for every upgrade and revert;
  - custom nodes are exempt from the badge.
