# Community 70

> 148 nodes · cohesion 0.04

## Key Concepts

- **RecordType** (92 connections) — `backend/om/utils/telemetry.py`
- **users.py** (53 connections) — `backend/om/auth/users.py`
- **UserCreate** (51 connections) — `backend/om/auth/schemas.py`
- **User** (46 connections) — `backend/om/auth/users.py`
- **SQLAlchemyUserAdminDB** (33 connections) — `backend/om/db/auth.py`
- **CaptchaVerificationError** (32 connections) — `backend/om/auth/captcha.py`
- **AuthBackend** (31 connections) — `backend/om/auth/schemas.py`
- **UserUpdateWithRole** (30 connections) — `backend/om/auth/schemas.py`
- **.create()** (23 connections) — `backend/om/auth/users.py`
- **Request** (17 connections) — `backend/om/auth/users.py`
- **_get_or_create_user_from_jwt()** (16 connections) — `backend/om/auth/users.py`
- **SingleTenantJWTStrategy** (16 connections) — `backend/om/auth/users.py`
- **TenantAwareRedisStrategy** (15 connections) — `backend/om/auth/users.py`
- **.oauth_callback()** (14 connections) — `backend/om/auth/users.py`
- **RefreshableDatabaseStrategy** (12 connections) — `backend/om/auth/users.py`
- **AuthenticationBackend** (12 connections) — `backend/om/auth/users.py`
- **get_oauth_router()** (11 connections) — `backend/om/auth/users.py`
- **RefreshableStrategy** (11 connections) — `backend/om/auth/users.py`
- **Any** (11 connections) — `backend/om/auth/users.py`
- **APIRouter** (11 connections) — `backend/om/auth/users.py`
- **AsyncSession** (11 connections) — `backend/om/auth/users.py`
- **UUID** (11 connections) — `backend/om/auth/users.py`
- **SecretType** (11 connections) — `backend/om/auth/users.py`
- **double_check_user()** (10 connections) — `backend/om/auth/users.py`
- **FastAPIUserWithLogoutRouter** (10 connections) — `backend/om/auth/users.py`
- *... and 123 more nodes in this community*

## Relationships

- [[Community 137]] (30 shared connections)
- [[User Roles & Agent Config]] (29 shared connections)
- [[Document Indexing Adapter]] (16 shared connections)
- [[Community 505]] (12 shared connections)
- [[Community 402]] (9 shared connections)
- [[Community 599]] (9 shared connections)
- [[Community 99]] (9 shared connections)
- [[Community 199]] (9 shared connections)
- [[Community 91]] (7 shared connections)
- [[Community 809]] (7 shared connections)
- [[Community 256]] (7 shared connections)
- [[Community 127]] (7 shared connections)

## Source Files

- `backend/om/auth/captcha.py`
- `backend/om/auth/schemas.py`
- `backend/om/auth/users.py`
- `backend/om/db/auth.py`
- `backend/om/db/engine/async_sql_engine.py`
- `backend/om/main.py`
- `backend/om/redis/redis_pool.py`
- `backend/om/server/manage/get_state.py`
- `backend/om/server/utils.py`
- `backend/om/utils/telemetry.py`
- `backend/om/utils/timing.py`
- `backend/tests/unit/om/auth/test_verify_email_domain.py`

## Audit Trail

- EXTRACTED: 527 (48%)
- INFERRED: 580 (52%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*