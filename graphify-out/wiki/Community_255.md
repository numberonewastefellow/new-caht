# Community 255

> 54 nodes · cohesion 0.05

## Key Concepts

- **create_pat()** (11 connections) — `backend/om/db/pat.py`
- **pat.py** (8 connections) — `backend/om/auth/pat.py`
- **create_token()** (8 connections) — `backend/om/server/pat/api.py`
- **pat.py** (7 connections) — `backend/om/db/pat.py`
- **get_hashed_api_key_from_request()** (6 connections) — `backend/om/auth/api_key.py`
- **get_hashed_pat_from_request()** (6 connections) — `backend/om/auth/pat.py`
- **list_user_pats()** (6 connections) — `backend/om/db/pat.py`
- **delete_token()** (6 connections) — `backend/om/server/pat/api.py`
- **list_tokens()** (6 connections) — `backend/om/server/pat/api.py`
- **extract_tenant_from_auth_header()** (5 connections) — `backend/om/auth/utils.py`
- **get_hashed_bearer_token_from_request()** (5 connections) — `backend/om/auth/utils.py`
- **fetch_user_for_pat()** (5 connections) — `backend/om/db/pat.py`
- **revoke_pat()** (5 connections) — `backend/om/db/pat.py`
- **calculate_expiration()** (4 connections) — `backend/om/auth/pat.py`
- **utils.py** (4 connections) — `backend/om/auth/utils.py`
- **_extract_tenant_from_bearer_token()** (4 connections) — `backend/om/auth/utils.py`
- **UUID** (4 connections) — `backend/om/db/pat.py`
- **api.py** (4 connections) — `backend/om/server/pat/api.py`
- **build_displayable_pat()** (3 connections) — `backend/om/auth/pat.py`
- **generate_pat()** (3 connections) — `backend/om/auth/pat.py`
- **hash_pat()** (3 connections) — `backend/om/auth/pat.py`
- **Request** (3 connections) — `backend/om/auth/utils.py`
- **Session** (3 connections) — `backend/om/db/pat.py`
- **Session** (3 connections) — `backend/om/server/pat/api.py`
- **User** (3 connections) — `backend/om/server/pat/api.py`
- *... and 29 more nodes in this community*

## Relationships

- [[Community 70]] (3 shared connections)
- [[Community 62]] (2 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 103]] (2 shared connections)
- [[Community 428]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 91]] (1 shared connections)
- [[User Roles & Agent Config]] (1 shared connections)

## Source Files

- `backend/om/auth/api_key.py`
- `backend/om/auth/pat.py`
- `backend/om/auth/utils.py`
- `backend/om/db/pat.py`
- `backend/om/server/pat/api.py`

## Audit Trail

- EXTRACTED: 130 (83%)
- INFERRED: 27 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*