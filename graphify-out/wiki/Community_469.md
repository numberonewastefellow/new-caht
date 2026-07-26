# Community 469

> 32 nodes · cohesion 0.11

## Key Concepts

- **Session** (23 connections) — `backend/om/db/discord_bot.py`
- **discord_bot.py** (23 connections) — `backend/om/db/discord_bot.py`
- **bulk_create_channel_configs()** (12 connections) — `backend/om/db/discord_bot.py`
- **sync_channel_configs()** (9 connections) — `backend/om/db/discord_bot.py`
- **get_channel_configs()** (8 connections) — `backend/om/db/discord_bot.py`
- **update_discord_channel_config()** (8 connections) — `backend/om/db/discord_bot.py`
- **DiscordGuildConfig** (8 connections) — `backend/om/db/discord_bot.py`
- **create_channel_config()** (7 connections) — `backend/om/db/discord_bot.py`
- **get_guild_configs()** (7 connections) — `backend/om/db/discord_bot.py`
- **DiscordChannelConfig** (7 connections) — `backend/om/db/discord_bot.py`
- **get_guild_config_by_registration_key()** (6 connections) — `backend/om/db/discord_bot.py`
- **register_guild()** (6 connections) — `backend/om/db/discord_bot.py`
- **.test_guild_list_returns_only_own_tenant()** (6 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **get_channel_config_by_internal_ids()** (5 connections) — `backend/om/db/discord_bot.py`
- **DiscordChannelView** (4 connections) — `backend/om/db/discord_bot.py`
- **get_channel_config_by_discord_ids()** (4 connections) — `backend/om/db/discord_bot.py`
- **get_guild_config_by_discord_id()** (4 connections) — `backend/om/db/discord_bot.py`
- **delete_discord_channel_config()** (3 connections) — `backend/om/db/discord_bot.py`
- **CRUD operations for Discord bot models.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get all guild configs for this tenant.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get a guild config by Discord guild ID.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get a guild config by its registration key.** (1 connections) — `backend/om/db/discord_bot.py`
- **Complete registration by setting guild_id and guild_name.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get all channel configs for a guild.** (1 connections) — `backend/om/db/discord_bot.py`
- **Get a specific channel config by guild_id and channel_id.** (1 connections) — `backend/om/db/discord_bot.py`
- *... and 7 more nodes in this community*

## Relationships

- [[Community 235]] (25 shared connections)
- [[Community 445]] (8 shared connections)
- [[Community 753]] (6 shared connections)
- [[Community 810]] (6 shared connections)
- [[User Roles & Agent Config]] (4 shared connections)
- [[Backend Agent/API Test Fixtures]] (2 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 473]] (1 shared connections)
- [[Community 134]] (1 shared connections)

## Source Files

- `backend/om/db/discord_bot.py`
- `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`

## Audit Trail

- EXTRACTED: 130 (79%)
- INFERRED: 34 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*