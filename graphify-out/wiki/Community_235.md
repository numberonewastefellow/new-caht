# Community 235

> 57 nodes · cohesion 0.08

## Key Concepts

- **Session** (30 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **generate_discord_registration_key()** (25 connections) — `backend/om/server/manage/discord_bot/utils.py`
- **create_guild_config()** (21 connections) — `backend/om/db/discord_bot.py`
- **delete_guild_config()** (19 connections) — `backend/om/db/discord_bot.py`
- **.test_channel_agent_override_in_api_call()** (11 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **test_discord_bot_db.py** (10 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_guild_agent_used_in_api_call()** (10 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **TestChannelConfigAPI** (10 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **update_guild_config()** (9 connections) — `backend/om/db/discord_bot.py`
- **.test_sync_channels_updates_renamed()** (9 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_update_guild_agent()** (9 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_list_channels_for_guild()** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_sync_channels_adds_new()** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_sync_channels_removes_deleted()** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_update_channel_enabled()** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_update_channel_thread_only_mode()** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **TestGuildConfigAPI** (8 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **_create_test_agent()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **TestAgentConfigurationAPI** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_no_agent_uses_default()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_get_guild_config()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_list_guilds()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_update_guild_enabled()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **TestRegistrationKeyAPI** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_delete_registration_key()** (7 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- *... and 32 more nodes in this community*

## Relationships

- [[Community 469]] (25 shared connections)
- [[Community 445]] (7 shared connections)
- [[User Roles & Agent Config]] (6 shared connections)
- [[Community 119]] (6 shared connections)
- [[Community 753]] (6 shared connections)
- [[Community 473]] (6 shared connections)
- [[Community 810]] (5 shared connections)
- [[Backend Agent/API Test Fixtures]] (3 shared connections)

## Source Files

- `backend/om/db/discord_bot.py`
- `backend/om/server/manage/discord_bot/utils.py`
- `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`

## Audit Trail

- EXTRACTED: 172 (54%)
- INFERRED: 144 (46%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*