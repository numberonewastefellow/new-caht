# SAML SSO (`om.server.sso`) — WS-C

Clean-room SAML 2.0 Service Provider (SP) with just-in-time (JIT) user
provisioning. Replaces the Onyx-EE SAML feature (`db/saml.py`, `server/saml.py`,
the `SamlAccount`/`saml` table, and the `/auth/saml/*` endpoints).

> **Provenance:** written from the WS-C behavior spec, not from Onyx EE source —
> own module layout, own names, own control flow.

---

## 1. Architecture

Layered (services / repositories / models), all tenant-scoped:

| File | Responsibility |
|------|----------------|
| `api.py` | FastAPI routers: `sso_router` (public `/sso/saml/*`) + `admin_sso_router` (`/admin/sso/saml/*`). |
| `service.py` | Orchestration: `build_authorize_url`, `process_acs`, `process_logout`. The only module that drives python3-saml. |
| `provisioning.py` | `provision_sso_user` — JIT via `UserManager.create` (reuses invite-bypass + first-user-admin + verified + tenant provisioning). |
| `config_store.py` | Repository for `sso_saml_config`: decrypted `SamlConfigData` snapshot, masked view, singleton upsert. |
| `session_store.py` | Repository for `sso_saml_session`: cookie↔user ledger (write on login, expire on logout). |
| `saml_settings.py` | Config → python3-saml settings + request dicts. |
| `email.py` | Multi-key email extraction with NameID fallback. |
| `relay_state.py` | RelayState/return-to open-redirect sanitization. |
| `audit.py` | Structured (JSON) audit logging for OpenSearch (Standard 9). |
| `schemas.py` | Pydantic request/response models. |

Models live in `om/db/models.py` under `# === WS-C: SAML SSO models ===`.

### Endpoints

Public (SP-initiated flow; listed in `auth_check.PUBLIC_ENDPOINT_SPECS`):

- `GET  /sso/saml/authorize?next=<path>` → `{ authorization_url }` (IdP redirect).
- `GET|POST /sso/saml/acs` → Assertion Consumer Service (validate → provision → issue cookie).
- `POST /sso/saml/logout` → expire the SAML session ledger + clear the auth cookie.
- `GET  /sso/saml/metadata` → this SP's SAML metadata XML (for IdP registration).

Admin (gated by `current_admin_user`):

- `GET  /admin/sso/saml/config` → `SamlConfigView` (secrets masked).
- `PUT  /admin/sso/saml/config` → upsert config.
- `GET  /admin/sso/saml/verify` → `SamlVerifyResult` — structural diagnostics (see §8).

### Login flow (SP-initiated)

```
Browser → /auth/login  ──(getAuthUrlSS)──▶  GET /sso/saml/authorize?next=…
        ◀── authorization_url ──
Browser ──▶ IdP  ──(SAMLResponse, RelayState)──▶  web /auth/saml/callback route
                                                   └─(proxy)─▶ POST /sso/saml/acs
  ACS: process_response() [strict] → extract email → provision_sso_user
       → auth_backend.login() (Set-Cookie) → write sso_saml_session
  web route reads Set-Cookie → 303 redirect to sanitized RelayState
```

The **public ACS URL stays `{WEB_DOMAIN}/auth/saml/callback`** (the Next.js route,
`web/src/app/auth/saml/callback/route.ts`) so existing IdP registrations keep
working. That route normalizes the HTTP-Redirect (GET) binding to POST and proxies
to the backend `/sso/saml/acs`. The backend builds its python3-saml request dict
from the *configured* ACS URL, so `Destination` validation passes behind the proxy.

---

## 2. Config table & UI

`sso_saml_config` is a **dedicated typed config table** (Standard 5), one row per
tenant. Edited from the admin screen at **`/admin/auth/sso`**
(`web/src/app/admin/auth/sso/`), reachable via the **Governance → "Single Sign-On"**
menu entry (admin-only). The SP private key is stored **encrypted**
(`EncryptedString`) and never returned by the API (the view exposes only
`sp_private_key_set`).

`sso_saml_session` is the cookie↔user session ledger (replaces `saml`), written on
ACS login and expired on logout — SAML sessions are now auditable and revocable.

> `AUTH_TYPE=saml` must be set (env) for the routers to mount. Configure the IdP
> details in the UI, tick **Enable**, and SAML login goes live.

---

## 3. Attribute mapping (email extraction)

IdPs surface email under different keys, so `email.py` probes an ordered,
case-insensitive list (configurable per tenant via `email_attribute_keys`, else the
built-in default), then falls back to the NameID when it is itself an email:

```
http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress   (Entra/ADFS)
http://schemas.microsoft.com/identity/claims/emailaddress            (Entra)
email, emailaddress, mail, user.email                                (Okta/generic)
urn:oid:0.9.2342.19200300.100.1.3                                    (LDAP/Shibboleth)
http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
→ fallback: NameID (emailAddress format)
```

Extracted emails are validated + lowercased. Optional `first_name_attribute_key` /
`last_name_attribute_key` are stored for future display-name use.

---

## 4. Security

- **python3-saml `>= 1.2.0`** (repo ships `1.15.0`) — pre-1.2.0 is vulnerable to XML
  Signature Wrapping (XSW). **`strict=True` always** — never disabled.
- Strict mode validates signature, XML schema, `Destination`, `AudienceRestriction`,
  and `NotBefore`/`NotOnOrAfter`. Defaults: `wantAssertionsSigned=True`,
  `rejectDeprecatedAlgorithm=True`, RSA-SHA256 signature / SHA-256 digest (reject SHA-1).
- **RelayState open-redirect protection** (`relay_state.py`): only same-origin
  relative paths or absolute URLs whose host matches `WEB_DOMAIN` are honored;
  protocol-relative (`//host`, backslash/encoded variants), foreign origins, and
  non-`http(s)` schemes collapse to `/`. Applied at both `authorize` (return_to) and
  `acs` (RelayState); the web route re-validates (`validateInternalRedirect`).
- **IdP-initiated SSO** is accepted (`process_response(request_id=None)`); we do not
  enforce `InResponseTo` because the SP is stateless behind the web proxy. Replay is
  bounded by strict `NotOnOrAfter`; a persistent request-id/assertion-id replay cache
  is a documented future extension.
- Non-web-login / deactivated accounts are rejected (403).

### Research informing the design (Standard 2)

- OWASP SAML Security Cheat Sheet — validation checklist, XSW, RelayState allowlisting.
- python3-saml (`SAML-Toolkits/python3-saml`) README — `OneLogin_Saml2_Auth` API,
  settings/security keys.
- Microsoft Entra & Okta SAML claim/NameID mapping docs — email attribute keys.

---

## 5. Structured log events (Standard 9)

`audit.py` emits one JSON record (`sso_audit …`) per event with fields:
`event, entity, entity_id, tenant_id, actor_user_id, action, status, duration_ms,
error`. Emission is wrapped in try/except (never breaks auth). Events:

| `event` | `entity` | when |
|---------|----------|------|
| `sso.authorize` | `saml_config` | authorize URL built |
| `sso.login` | `user` | successful ACS login |
| `sso.jit_provisioned` | `user` | new user created on first login |
| `sso.logout` | `user` | SP logout |
| `sso.assertion_rejected` | `saml_session` / `saml_config` | validation failure / unconfigured |
| `sso.config_updated` | `saml_config` | admin PUT |

`tenant_id`/`actor_user_id` come from the request contextvars.

---

## 6. Multi-tenant readiness (Contract 3)

Every DB access uses the Contract-3 tenancy facade (`om.tenancy.context`); both
tables live inside the per-tenant schema (no `{"schema": "public"}`). Tenant
resolution for a login is delegated to `UserManager` (email→tenant); in
multi-tenant, the host/subdomain → tenant routing that selects *which* tenant's
SAML config to load is owned by **WS-M** (login-time tenant middleware).

> The tenancy facade module `om/tenancy/context.py` in this worktree is a thin
> re-export **shim** for coherence; the integrator replaces it with WS-M's canonical
> module.

---

## 7. Extending

- **New IdP attribute for email:** add its key to `email_attribute_keys` in the
  admin UI (no code change) — or to `DEFAULT_EMAIL_ATTRIBUTE_KEYS` in `email.py`.
- **Display name / group claims:** `first_name_attribute_key` /
  `last_name_attribute_key` are already stored; read them in `service.process_acs`
  and pass through to provisioning.
- **SP-signed requests:** set an SP cert + private key and tick "Sign AuthnRequests".
- **Replay cache:** persist `auth.get_last_assertion_id()` per tenant and reject
  duplicates within the assertion lifetime.

---

## 8. In-UI verification (`GET /admin/sso/saml/verify`)

A **structural** diagnostic of the *saved* config — it does NOT contact the IdP
(a live round-trip is still "just log in"). `verify.py::verify_saml_config` runs
ordered checks and returns `SamlVerifyResult { valid, checks[], sp_entity_id,
sp_acs_url, sp_metadata_url, last_successful_login }`:

- `enabled` — SAML turned on (warning if off).
- `idp_fields` — Entity ID / Sign-On URL / certificate present (error).
- `idp_cert` — the IdP cert parses as X.509 via `cryptography` (error) and is not
  expired (warning). `OneLogin_Saml2_Utils.format_cert` only normalizes, so real
  parsing is done here.
- `sp_fields` — SP Entity ID / ACS URL present (error).
- `signing` — if "Sign AuthnRequests" is on, an SP private key must be set (error).
- `settings` — the generated python3-saml settings are accepted by
  `OneLogin_Saml2_Settings(...)` (error surfaces the toolkit's error codes).

`valid` is False iff any check is an `error` (warnings do not fail it). The result
also returns the SP details to register at the IdP, a link to `/sso/saml/metadata`,
and the most-recent SAML session (from `sso_saml_session`) as an "it's working"
signal. Emits the `sso.config_verified` structured-log event.

The admin screen (`web/src/app/admin/auth/sso/SsoForm.tsx`) renders this as a
**"Verify configuration"** button + a results panel (`Message` summary +
`FieldMessage` per-check rows, using `status-{success,warning,error}-*` tokens).
