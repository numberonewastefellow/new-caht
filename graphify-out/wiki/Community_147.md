# Community 147

> 87 nodes · cohesion 0.04

## Key Concepts

- **SamlConfigData** (18 connections) — `backend/om/server/sso/config_store.py`
- **sso_audit()** (15 connections) — `backend/om/server/sso/audit.py`
- **process_acs()** (15 connections) — `backend/om/server/sso/service.py`
- **verify_saml_config()** (14 connections) — `backend/om/server/sso/verify.py`
- **test_verify.py** (12 connections) — `backend/tests/unit/om/server/sso/test_verify.py`
- **build_authorize_url()** (10 connections) — `backend/om/server/sso/service.py`
- **_config()** (10 connections) — `backend/tests/unit/om/server/sso/test_verify.py`
- **provision_sso_user()** (9 connections) — `backend/om/server/sso/provisioning.py`
- **process_logout()** (9 connections) — `backend/om/server/sso/service.py`
- **_by_key()** (9 connections) — `backend/tests/unit/om/server/sso/test_verify.py`
- **audit.py** (8 connections) — `backend/om/server/sso/audit.py`
- **build_saml_settings()** (8 connections) — `backend/om/server/sso/saml_settings.py`
- **service.py** (8 connections) — `backend/om/server/sso/service.py`
- **_load_usable_config()** (8 connections) — `backend/om/server/sso/service.py`
- **run_checks()** (8 connections) — `backend/om/server/sso/verify.py`
- **_record_session()** (7 connections) — `backend/om/server/sso/service.py`
- **upsert_saml_session()** (7 connections) — `backend/om/server/sso/session_store.py`
- **build_request_dict()** (6 connections) — `backend/om/server/sso/saml_settings.py`
- **session_store.py** (6 connections) — `backend/om/server/sso/session_store.py`
- **Response** (5 connections) — `backend/om/server/sso/service.py`
- **SsoEvent** (5 connections) — `backend/om/server/sso/audit.py`
- **_reject_assertion()** (5 connections) — `backend/om/server/sso/service.py`
- **expire_saml_sessions_for_user()** (5 connections) — `backend/om/server/sso/session_store.py`
- **get_last_saml_session()** (5 connections) — `backend/om/server/sso/session_store.py`
- **verify.py** (5 connections) — `backend/om/server/sso/verify.py`
- *... and 62 more nodes in this community*

## Relationships

- [[Community 322]] (12 shared connections)
- [[Community 72]] (5 shared connections)
- [[Community 103]] (4 shared connections)
- [[Community 70]] (3 shared connections)
- [[Community 137]] (3 shared connections)
- [[Community 888]] (2 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 1192]] (1 shared connections)
- [[Community 887]] (1 shared connections)
- [[User Roles & Agent Config]] (1 shared connections)

## Source Files

- `backend/om/server/sso/audit.py`
- `backend/om/server/sso/config_store.py`
- `backend/om/server/sso/provisioning.py`
- `backend/om/server/sso/saml_settings.py`
- `backend/om/server/sso/service.py`
- `backend/om/server/sso/session_store.py`
- `backend/om/server/sso/verify.py`
- `backend/tests/unit/om/server/sso/test_verify.py`

## Audit Trail

- EXTRACTED: 260 (74%)
- INFERRED: 93 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*