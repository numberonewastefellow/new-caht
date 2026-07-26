# Community 1043

> 12 nodes · cohesion 0.17

## Key Concepts

- **TestClientLifecycle** (8 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **.test_close_closes_session()** (2 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **.test_initialize_creates_session()** (2 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **.test_is_initialized_after_init()** (2 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **.test_is_initialized_before_init()** (2 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **.test_send_message_not_initialized()** (2 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **Tests for API client lifecycle management.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **initialize() creates aiohttp session.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **is_initialized returns False before initialize().** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **is_initialized returns True after initialize().** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **close() closes session and resets is_initialized.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`
- **send_chat_message() before initialize() raises APIConnectionError.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_api_client.py`

## Relationships

- [[Community 200]] (2 shared connections)

## Source Files

- `backend/tests/unit/om/onyxbot/discord/test_api_client.py`

## Audit Trail

- EXTRACTED: 23 (96%)
- INFERRED: 1 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*