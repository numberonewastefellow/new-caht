# Community 445

> 34 nodes · cohesion 0.11

## Key Concepts

- **api.py** (14 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Session** (11 connections) — `backend/om/server/manage/discord_bot/api.py`
- **User** (11 connections) — `backend/om/server/manage/discord_bot/api.py`
- **get_guild_config_by_internal_id()** (10 connections) — `backend/om/db/discord_bot.py`
- **update_channel_request()** (9 connections) — `backend/om/server/manage/discord_bot/api.py`
- **create_bot_request()** (8 connections) — `backend/om/server/manage/discord_bot/api.py`
- **create_guild_request()** (8 connections) — `backend/om/server/manage/discord_bot/api.py`
- **delete_guild_request()** (8 connections) — `backend/om/server/manage/discord_bot/api.py`
- **list_channel_configs()** (8 connections) — `backend/om/server/manage/discord_bot/api.py`
- **update_guild_request()** (8 connections) — `backend/om/server/manage/discord_bot/api.py`
- **delete_bot_config_endpoint()** (7 connections) — `backend/om/server/manage/discord_bot/api.py`
- **get_guild_config()** (7 connections) — `backend/om/server/manage/discord_bot/api.py`
- **delete_service_api_key_endpoint()** (6 connections) — `backend/om/server/manage/discord_bot/api.py`
- **get_bot_config()** (6 connections) — `backend/om/server/manage/discord_bot/api.py`
- **list_guild_configs()** (6 connections) — `backend/om/server/manage/discord_bot/api.py`
- **DiscordGuildConfigResponse** (3 connections) — `backend/om/server/manage/discord_bot/api.py`
- **DiscordBotConfigResponse** (2 connections) — `backend/om/server/manage/discord_bot/api.py`
- **DiscordChannelConfigResponse** (2 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Get a specific guild config by its ID.** (1 connections) — `backend/om/db/discord_bot.py`
- **Discord bot admin API endpoints.** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Delete Discord bot config.      Also deletes the Discord service API key since t** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Delete the Discord service API key.      This endpoint allows manual deletion of** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- **List all guild configs (pending and registered).** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Create new guild config with registration key. Key shown once.** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- **Get specific guild config.** (1 connections) — `backend/om/server/manage/discord_bot/api.py`
- *... and 9 more nodes in this community*

## Relationships

- [[Community 469]] (8 shared connections)
- [[Community 103]] (8 shared connections)
- [[Community 235]] (7 shared connections)
- [[Community 753]] (3 shared connections)
- [[Community 810]] (3 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 1640]] (1 shared connections)

## Source Files

- `backend/om/db/discord_bot.py`
- `backend/om/server/manage/discord_bot/api.py`

## Audit Trail

- EXTRACTED: 118 (79%)
- INFERRED: 32 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*