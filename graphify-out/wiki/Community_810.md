# Community 810

> 17 nodes · cohesion 0.18

## Key Concepts

- **get_or_create_discord_service_api_key()** (12 connections) — `backend/om/db/discord_bot.py`
- **delete_discord_service_api_key()** (11 connections) — `backend/om/db/discord_bot.py`
- **get_discord_service_api_key()** (10 connections) — `backend/om/db/discord_bot.py`
- **TestServiceApiKeyAPI** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_create_service_api_key()** (6 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_delete_service_api_key()** (6 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_get_or_create_returns_existing()** (6 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_delete_service_api_key_not_found()** (4 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **ApiKey** (2 connections) — `backend/om/db/discord_bot.py`
- **Delete the Discord service API key for a tenant.      Called when:     - Bot con** (1 connections) — `backend/om/db/discord_bot.py`
- **Get the Discord service API key if it exists.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get existing Discord service API key or create one.      The API key is used by** (1 connections) — `backend/om/db/discord_bot.py`
- **Tests for Discord service API key operations.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Create service API key returns valid key.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **get_or_create_discord_service_api_key regenerates key if exists.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Delete service API key removes it from DB.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Delete when no key exists returns False.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`

## Relationships

- [[Community 469]] (6 shared connections)
- [[Community 235]] (5 shared connections)
- [[Community 445]] (3 shared connections)
- [[Community 428]] (3 shared connections)
- [[User Roles & Agent Config]] (2 shared connections)
- [[Community 273]] (2 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Community 119]] (1 shared connections)

## Source Files

- `backend/om/db/discord_bot.py`
- `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`

## Audit Trail

- EXTRACTED: 41 (56%)
- INFERRED: 32 (44%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*