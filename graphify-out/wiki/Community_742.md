# Community 742

> 19 nodes · cohesion 0.14

## Key Concepts

- **auth.py** (11 connections) — `backend/om/server/scim/auth.py`
- **verify_scim_token()** (11 connections) — `backend/om/server/scim/auth.py`
- **ScimContext** (5 connections) — `backend/om/server/scim/auth.py`
- **Request** (4 connections) — `backend/om/server/scim/auth.py`
- **hash_scim_token()** (4 connections) — `backend/om/server/scim/auth.py`
- **build_scim_token_display()** (3 connections) — `backend/om/server/scim/auth.py`
- **_extract_bearer_token()** (3 connections) — `backend/om/server/scim/auth.py`
- **generate_scim_token()** (3 connections) — `backend/om/server/scim/auth.py`
- **parse_tenant_from_token()** (3 connections) — `backend/om/server/scim/auth.py`
- **tokens_match()** (3 connections) — `backend/om/server/scim/auth.py`
- **SCIM bearer-token generation, hashing and request authentication.  Tokens are** (1 connections) — `backend/om/server/scim/auth.py`
- **FastAPI dependency: authenticate a SCIM request and bind its tenant.      Yiel** (1 connections) — `backend/om/server/scim/auth.py`
- **# NOTE: the broad try only guards pre-yield auth work; exceptions** (1 connections) — `backend/om/server/scim/auth.py`
- **Authenticated SCIM request context handed to every provisioning route.** (1 connections) — `backend/om/server/scim/auth.py`
- **Mint a new raw SCIM token (CSPRNG). Tenant is embedded in MT mode.** (1 connections) — `backend/om/server/scim/auth.py`
- **SHA-256 hex digest of a raw token (the DB lookup key).      No salt is needed:** (1 connections) — `backend/om/server/scim/auth.py`
- **Masked, last-4 form for the admin UI, e.g. ``scim_****ab12``.** (1 connections) — `backend/om/server/scim/auth.py`
- **Recover the tenant schema embedded in a token (or the default schema).** (1 connections) — `backend/om/server/scim/auth.py`
- **Constant-time hash comparison (defence in depth over the DB lookup).** (1 connections) — `backend/om/server/scim/auth.py`

## Relationships

- [[Community 252]] (6 shared connections)
- [[Community 506]] (2 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 884]] (1 shared connections)

## Source Files

- `backend/om/server/scim/auth.py`

## Audit Trail

- EXTRACTED: 49 (83%)
- INFERRED: 10 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*