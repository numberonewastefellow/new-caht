# Community 672

> 22 nodes · cohesion 0.11

## Key Concepts

- **OmDiscordClient** (15 connections) — `backend/om/onyxbot/discord/client.py`
- **TestBotLifecycle** (5 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **main()** (4 connections) — `backend/om/onyxbot/discord/client.py`
- **.test_close_closes_api_client()** (3 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **.test_setup_hook_initializes_api_client()** (3 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **.test_setup_hook_initializes_cache()** (3 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **client.py** (3 connections) — `backend/om/onyxbot/discord/client.py`
- **.on_ready()** (3 connections) — `backend/om/onyxbot/discord/client.py`
- **._periodic_cache_refresh()** (3 connections) — `backend/om/onyxbot/discord/client.py`
- **.setup_hook()** (3 connections) — `backend/om/onyxbot/discord/client.py`
- **Tests for bot lifecycle management.** (1 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **setup_hook calls cache.refresh_all().** (1 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **setup_hook calls api_client.initialize().** (1 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **close() calls api_client.close().** (1 connections) — `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`
- **.close()** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **.__init__()** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Discord bot client with integrated message handling.** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Main entry point for Discord bot.** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Discord bot client with integrated cache, API client, and message handling.** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Called before on_ready. Initialize components.** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Background task to refresh cache periodically.** (1 connections) — `backend/om/onyxbot/discord/client.py`
- **Bot connected and ready.** (1 connections) — `backend/om/onyxbot/discord/client.py`

## Relationships

- [[Community 219]] (2 shared connections)
- [[Community 826]] (1 shared connections)
- [[Community 119]] (1 shared connections)
- [[Community 200]] (1 shared connections)
- [[Community 134]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)

## Source Files

- `backend/om/onyxbot/discord/client.py`
- `backend/tests/external_dependency_unit/discord_bot/test_discord_events.py`

## Audit Trail

- EXTRACTED: 46 (81%)
- INFERRED: 11 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*