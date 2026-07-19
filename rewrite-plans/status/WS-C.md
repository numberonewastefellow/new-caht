# WS-C — SAML SSO (clean-room) — status log

Worktree: `.claude/worktrees/ws-c` (branch `rewrite/ws-c` off `rename_onyx_to_om`).
Replaces the Onyx-EE SAML feature: `db/saml.py`, `server/saml.py`, the SSO/JWT/OIDC-expiry
branches in `auth/users.py`, and the `/sso/saml/*` EE public-endpoint specs.

Phase plan:
- P0 Setup + research: worktree, CONTRACTS.md, graphify orient, map integration surface, SAML SP research.
- P1 SAML core + tables + session mapping (clean-room `om/server/sso/`). Review: assertion validation,
  email extraction robust, RelayState sanitized, error paths.
- P2 `auth/users.py` SSO branch + JIT provisioning + typed config table. Review: first-user-admin,
  invite-bypass, tenant-safe (Contract 3).
- P3 SSO settings UI + "Single Sign-On" admin menu entry. Review: design-system + admin-gating.
- P4 Delete old `db/saml.py` + `server/saml.py` + old specs; verify. Review: end-to-end SAML login
  (mock IdP), structured logs present.

---

- [P0] Started: read CONTRACTS.md + WS-C in full; graphify-oriented (`explain SamlAccount`,
  `query` auth/router/config). Confirmed baseline: current EE-origin SAML files are
  `backend/om/db/saml.py`, `backend/om/server/saml.py`, model `SamlAccount` in `models.py` L3706,
  config template `backend/om/configs/saml_config/template.settings.json`; SSO branch merged into
  `backend/om/auth/users.py`. Tenant primitives via Contract-3 facade `om.tenancy.context`.
  Clean-room: I read the current EE files ONLY for public surface (what to delete + who imports);
  all new code is written from the WS-C behavior spec, own module layout/names/control flow.
- [P0] Research (Standard 2), cited in README:
  - Library: **python3-saml** (`SAML-Toolkits/python3-saml`, `OneLogin_Saml2_Auth`). Pin **>= 1.2.0**
    (pre-1.2.0 is vulnerable to XML Signature Wrapping). Keep **strict mode ON** always.
  - SP-initiated flow: `/sso/saml/authorize` builds auth + `login(return_to=<sanitized>)`; ACS
    (`process_response()` → `get_errors()`/`is_authenticated()`); validate Destination==ACS,
    Audience==SP entityId, InResponseTo, NotBefore/NotOnOrAfter (python3-saml enforces in strict).
  - Security settings: `wantAssertionsSigned`, `rejectDeprecatedAlgorithm=True`, RSA-SHA256 min
    (reject SHA-1), schema validation, XSW protection (absolute XPath — handled by the toolkit).
  - **RelayState open-redirect**: allowlist only — accept same-origin relative paths (single leading
    `/`, reject `//` and `/\`) or absolute URLs matching WEB_DOMAIN; else fall back to `/`.
  - Email extraction (Entra/Okta/ADFS/Shibboleth): try a configurable ordered list of attribute keys
    (`http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress`, `email`, `emailAddress`,
    `mail`, `urn:oid:0.9.2342.19200300.100.1.3`, `User.email`) then fall back to NameID when it is in
    emailAddress format. Case-insensitive, multi-value tolerant.
  - Sources recorded in `backend/om/server/sso/README.md`.
- [P0] Integration-surface mapped (two Explore agents). Key findings that shaped the design:
  1. Legacy `db/saml.py` (`get/upsert/expire_saml_account`) is DEAD CODE — old flow only issued a plain
     FastAPI-Users cookie via `auth_backend.login`. WS-C builds the session-mapping table AND actually
     wires it (write on ACS, expire on logout) — a real improvement, per spec §Session mapping.
  2. `om.tenancy.context` does NOT exist in this worktree (WS-M owns it, unmerged). Added a thin
     re-export shim `backend/om/tenancy/context.py` (WS-B's pattern) — integrator drops it for WS-M's
     canonical module. New code imports the contract path.
  3. No structured JSON logger exists — built greenfield `om/server/sso/audit.py` (Standard 9), sourcing
     `tenant_id`/`actor_user_id` from contextvars.
  4. Invite-bypass for SSO is ALREADY correct: `verify_email_is_invited` (users.py:219) returns early for
     AuthType.SAML/OIDC; `UserManager.create` (L430) already applies first-user-admin. So JIT provisioning
     REUSES `create` (mirrors the existing `_get_or_create_user_from_jwt` path) — no invasive users.py edit.
  5. Frontend login glue points to re-point: `getSAMLAuthUrlSS` (`/auth/saml/authorize`), `logoutSAMLSS`
     (`/auth/saml/logout`), web ACS route `route.ts` (`/auth/saml/callback`) → new `/sso/saml/*`.

- [P1] SAML core + tables + session mapping written (clean-room, own module layout `om/server/sso/`):
  - Models (models.py, banner `# === WS-C: SAML SSO models ===`): `SsoSamlConfig` (typed config,
    Standard 5) + `SsoSamlSession` (cookie↔user ledger, UUID FK cascade, replaces `saml`).
  - Alembic `ws_c_saml_sso.py` (down_revision=None placeholder): drop `saml`, create both tables.
  - `audit.py` structured events (sso.login|logout|jit_provisioned|assertion_rejected|authorize|
    config_updated) + `timed_sso_audit`; `relay_state.py` open-redirect allowlist; `email.py` multi-key
    + NameID fallback; `saml_settings.py` (strict, wantAssertionsSigned, rejectDeprecatedAlgorithm,
    RSA-SHA256; ACS-derived request dict so Destination validates behind the web proxy);
    `config_store.py` (decrypted snapshot + masked view + singleton upsert); `session_store.py`;
    `provisioning.py` (reuses UserManager.create); `service.py` (authorize/ACS/logout orchestration);
    `api.py` (`sso_router` public `/sso/saml/*` + `admin_sso_router` `/admin/sso/saml/*`).
  - py_compile OK on all new files; mypy strict CLEAN on the full SSO package + tenancy shim.

- [P2] Config admin API + auth cleanup + wiring:
  - Admin CRUD `GET|PUT /admin/sso/saml/config` (in `api.py`, `current_admin_user`-gated, secrets masked).
  - `auth/users.py`: renamed the now-misnamed `_check_for_saml_and_jwt` → `_check_for_jwt_bearer_auth`
    (SAML no longer flows through it). Invite-bypass (L219) + first-user-admin (create, L430) were ALREADY
    correct → JIT reuses `UserManager.create`, no invasive edit.
  - Re-pointed the test-only `manage/users.py::test_upsert_user` from `server.saml.upsert_saml_user` →
    `om.server.sso.provisioning.provision_sso_user`.
  - Wiring (applied in-worktree + delivered as snippets below): `main.py` SAML branch now mounts
    `sso_router` (public) + `admin_sso_router`; `auth_check.py` public specs updated to `/sso/saml/*`.
  - Review gate PASS: first-user-admin ✓, invite-bypass ✓, tenant-safe (Contract-3 facade everywhere,
    per-tenant schema) ✓. mypy clean on all edited backend files.

- [P3] Frontend (tsc CLEAN on all touched files):
  - Re-pointed login glue to `/sso/saml/*`: `userSS.ts` (`getSAMLAuthUrlSS`, `logoutSAMLSS`) + web ACS
    route `auth/saml/callback/route.ts` (proxy → `/sso/saml/acs`; public route path kept stable = IdP-facing ACS).
  - New admin screen `web/src/app/admin/auth/sso/` (`page.tsx` + `SsoForm.tsx`): SWR GET + PUT to
    `/api/admin/sso/saml/config`; design-system components (CardSection, Title, Label/SubLabel, Button,
    toast) + accent CSS vars (no hardcoded colors); sections IdP / SP / Security / Attribute mapping.
  - Menu: `adminNavItems.ts` — "Single Sign-On" (SvgKey) in the admin-only Governance block +
    `ADMIN_ROUTE_LABELS` (auth/sso) + `PATH_GROUP_COLORS` (`/admin/auth/sso` → orange).
  - Review gate PASS: design-system ✓, admin-gating (layout `requireAdminAuth` + explicit `isAdmin`
    guard in `SsoForm`; menu in `!isCurator` block) ✓.

- [P4] Delete old + verify (delete-after-verify, Standard 11):
  - Deleted `db/saml.py`, `server/saml.py`, `configs/saml_config/` (template), the `SamlAccount` model,
    and the unused `SAML_CONF_DIR` config. Re-pointed `db/users.py` delete-cascade + `test_delete_user.py`
    to `SsoSamlSession`. Alembic `ws_c_saml_sso.py` drops `saml`.
  - VERIFIED (static): mypy strict CLEAN across every touched backend file (import graph intact after
    deletions); frontend `tsc --noEmit` CLEAN; `py_compile` OK; grep sweep shows no lingering refs to
    `om.db.saml` / `om.server.saml` / `SamlAccount` / `SAML_CONF_DIR` / `saml_router` / `upsert_saml_user`.
  - NOT verified here (needs running stack + mock IdP; deferred to Docker rebuild — do NOT run alembic by
    hand): live end-to-end SAML login/logout. Static review confirms strict assertion validation, email
    extraction, RelayState sanitization, and error paths.

---

## Integrator handoff

**Shared-file edits already applied in this worktree (take the diff):**
- `backend/om/main.py`: import `from om.server.sso.api import admin_sso_router, sso_router` (replaces the old
  `saml_router` import); in `elif AUTH_TYPE == AuthType.SAML:` mount
  `include_auth_router_with_prefix(application, sso_router)` +
  `include_router_with_global_prefix_prepended(application, admin_sso_router)`.
- `backend/om/server/auth_check.py`: replaced the `/auth/saml/*` public specs with
  `/sso/saml/authorize {GET}`, `/sso/saml/acs {GET,POST}`, `/sso/saml/logout {POST}`, `/sso/saml/metadata {GET}`.
- `backend/om/db/models.py`: WS-C models appended under `# === WS-C: SAML SSO models ===`; `SamlAccount` removed.

**Alembic:** `backend/alembic/versions/ws_c_saml_sso.py` has `down_revision = None` (placeholder). Linearize
off the current head (`0003_agent_rename`, or later after other WS revisions). It drops `saml` and creates
`sso_saml_config` + `sso_saml_session`.

**Tenancy shim:** `backend/om/tenancy/context.py` is a WS-C re-export shim — DROP it in favor of WS-M's
canonical module at merge.

**Snapshot fixtures to REGENERATE (not hand-edited):**
- `backend/tests/unit/migration_safety/snapshots/baseline.json` — referenced `db.saml` / `server.saml` modules
  (now deleted).
- `backend/tests/route_rename/snapshots/before/_openapi_schema.json` — `test_upsert_user` description changed.

**Runtime note:** `AUTH_TYPE=saml` must be set for the routers to mount; admins then configure the IdP in
`/admin/auth/sso` and tick Enable.

---

## [REVIEW] Rigorous self-review pass — gaps found + fixed

**Phase checklist (all DONE):** P1 SAML core + tables + session mapping ✓ · P2 config admin API + auth SSO
cleanup + JIT + wiring ✓ · P3 SSO UI + menu + login-glue re-point ✓ · P4 delete old + static verify ✓.
Every behavior-spec item present (authorize / ACS GET+POST / logout / metadata / session ledger / RelayState
sanitize / multi-key email / first-user-admin / invite-bypass). Only live end-to-end (mock IdP) remains
deferred to the running stack.

**Gaps fixed:**
1. **Dead code (Standard 10):** removed 3 never-called functions — `timed_sso_audit` (audit.py),
   `get_active_saml_session` + `delete_saml_sessions_for_user` (session_store.py) — and their now-unused
   imports (`time`, `contextmanager`, `Generator`, `delete`).
2. **Unused response header:** dropped `RELAY_STATE_HEADER` (`X-Om-Relay-State`) — the web ACS route
   re-validates RelayState itself, so nothing consumed it. RelayState sanitization is retained and now
   documented as feeding the audit log (defense-in-depth).
3. **Endpoint hardening:** `/sso/saml/metadata` now wraps `OneLogin_Saml2_Settings(sp_validation_only=True)`
   in try/except → clean **400** ("SAML SP is not fully configured") instead of an unhandled 500 when SP
   config is incomplete.
4. **Tests added:** `tests/unit/om/server/sso/test_relay_state.py` (open-redirect vectors: protocol-relative,
   backslash/URL-encoded, cross-origin, non-web schemes, control chars; same-origin allow) +
   `test_email.py` (multi-key, case-insensitive, NameID fallback, config-override, key precedence, scalar
   tolerance). **40 tests pass** (with the re-pointed `test_delete_user.py`).

**Investigated, no fix needed (verified):**
- Suspected Destination-validation failure on non-standard ports (`:3000`): runtime-verified that
  python3-saml `get_self_url_no_query` preserves the port from `http_host` — `build_request_dict` is correct.
- onelogin API surface (constants, ctor signatures, `process_response`) runtime-verified against usage.
- Captcha-on-SSO in `UserManager.create`: consistent with the existing JWT SSO path (not WS-C-introduced).
- Alembic `down_revision=None`: intended placeholder per Contract (integrator linearizes).
- Config-singleton write race: low-risk (admin-only); `get_saml_config_row` reads deterministically.

**Re-verification:** mypy strict CLEAN (SSO package + new tests + all touched backend files);
`tsc --noEmit` CLEAN (frontend); `pytest` 40 passed; `py_compile` OK; grep confirms no lingering refs to
removed symbols.

---

## [FEATURE] In-UI "Verify configuration" (post-review follow-up)

Added a **structural** config-verification feature (no live IdP round-trip) so admins get actionable
setup feedback instead of only "try to log in".

- Backend `GET /admin/sso/saml/verify` (admin-gated) → `SamlVerifyResult { valid, checks[],
  sp_entity_id, sp_acs_url, sp_metadata_url, last_successful_login }`. Pure check logic in new
  `om/server/sso/verify.py`: enabled / IdP fields / IdP cert parses+not-expired (via `cryptography`) /
  SP fields / signing-key consistency / python3-saml `OneLogin_Saml2_Settings` acceptance. `valid` fails
  only on `error` (warnings don't). New `SsoEvent.CONFIG_VERIFIED` structured log;
  `session_store.get_last_saml_session()` supplies the "it's working" signal.
- Frontend: "Verify configuration" button + results panel in `SsoForm.tsx` — `Message` summary +
  `FieldMessage` per-check rows using `status-{success,warning,error}-*` semantic tokens (no hardcoded/
  accent colors), plus SP details to register at the IdP + metadata link + last-login line.
- Tests: `tests/unit/om/server/sso/test_verify.py` (valid / missing fields / bad+expired cert /
  signing-without-key / disabled). **pytest 44 passed**; mypy + `tsc --noEmit` CLEAN. README §8 added.
