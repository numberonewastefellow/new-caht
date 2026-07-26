# Community 143

> 89 nodes · cohesion 0.04

## Key Concepts

- **redis_pool.py** (15 connections) — `backend/om/redis/redis_pool.py`
- **onyx_redis.py** (14 connections) — `backend/scripts/debugging/onyx_redis.py`
- **get_redis_replica_client()** (14 connections) — `backend/om/redis/redis_pool.py`
- **Redis** (13 connections) — `backend/om/redis/redis_pool.py`
- **RedisPool** (11 connections) — `backend/om/redis/redis_pool.py`
- **utils.py** (11 connections) — `backend/om/server/features/release_notes/utils.py`
- **ensure_release_notes_fresh_and_notify()** (11 connections) — `backend/om/server/features/release_notes/utils.py`
- **Redis** (9 connections) — `backend/scripts/debugging/onyx_redis.py`
- **onyx_redis()** (9 connections) — `backend/scripts/debugging/onyx_redis.py`
- **get_shared_redis_client()** (9 connections) — `backend/om/redis/redis_pool.py`
- **redis_lock_dump()** (9 connections) — `backend/om/redis/redis_pool.py`
- **TenantRedis** (8 connections) — `backend/om/redis/redis_pool.py`
- **get_user_id()** (7 connections) — `backend/scripts/debugging/onyx_redis.py`
- **redis_shared_lock()** (7 connections) — `backend/om/redis/lock_context.py`
- **parse_mdx_to_release_note_entries()** (7 connections) — `backend/om/server/features/release_notes/utils.py`
- **OmRedisCommand** (6 connections) — `backend/scripts/debugging/onyx_redis.py`
- **delete_user_token_from_redis()** (5 connections) — `backend/scripts/debugging/onyx_redis.py`
- **get_user_token_from_redis()** (5 connections) — `backend/scripts/debugging/onyx_redis.py`
- **purge_by_match_and_type()** (5 connections) — `backend/scripts/debugging/onyx_redis.py`
- **get_raw_redis_client()** (5 connections) — `backend/om/redis/redis_pool.py`
- **.create_pool()** (5 connections) — `backend/om/redis/redis_pool.py`
- **.get_client()** (5 connections) — `backend/om/redis/redis_pool.py`
- **.get_replica_client()** (5 connections) — `backend/om/redis/redis_pool.py`
- **get_last_fetch_time()** (5 connections) — `backend/om/server/features/release_notes/utils.py`
- **parse_version_tuple()** (5 connections) — `backend/om/server/features/release_notes/utils.py`
- *... and 64 more nodes in this community*

## Relationships

- [[Document Indexing Adapter]] (7 shared connections)
- [[Community 161]] (4 shared connections)
- [[Community 69]] (3 shared connections)
- [[Community 73]] (3 shared connections)
- [[Community 120]] (3 shared connections)
- [[Community 70]] (2 shared connections)
- [[Community 72]] (2 shared connections)
- [[Community 106]] (2 shared connections)
- [[Community 148]] (2 shared connections)
- [[Community 199]] (2 shared connections)
- [[Community 61]] (2 shared connections)
- [[Community 59]] (2 shared connections)

## Source Files

- `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- `backend/om/background/celery/tasks/docprocessing/utils.py`
- `backend/om/redis/lock_context.py`
- `backend/om/redis/redis_pool.py`
- `backend/om/server/features/release_notes/utils.py`
- `backend/om/server/runtime/onyx_runtime.py`
- `backend/scripts/debugging/onyx_redis.py`

## Audit Trail

- EXTRACTED: 280 (85%)
- INFERRED: 48 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*