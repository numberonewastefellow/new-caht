# Community 753

> 19 nodes · cohesion 0.16

## Key Concepts

- **create_discord_bot_config()** (10 connections) — `backend/om/db/discord_bot.py`
- **delete_discord_bot_config()** (9 connections) — `backend/om/db/discord_bot.py`
- **get_discord_bot_config()** (9 connections) — `backend/om/db/discord_bot.py`
- **TestBotConfigAPI** (9 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_delete_bot_config()** (6 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_get_bot_config()** (6 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_create_bot_config()** (5 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_create_bot_config_already_exists()** (5 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **.test_delete_bot_config_not_found()** (4 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **DiscordBotConfig** (3 connections) — `backend/om/db/discord_bot.py`
- **Get the Discord bot config for this tenant (at most one).** (1 connections) — `backend/om/db/discord_bot.py`
- **Create the Discord bot config. Raises ValueError if already exists.      The che** (1 connections) — `backend/om/db/discord_bot.py`
- **Delete the Discord bot config. Returns True if deleted.** (1 connections) — `backend/om/db/discord_bot.py`
- **Delete bot config removes it from DB.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Delete when no config exists returns False.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Tests for bot config API operations.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Create bot config succeeds with valid token.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Creating config twice raises ValueError.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`
- **Get bot config returns config with masked token.** (1 connections) — `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`

## Relationships

- [[Community 469]] (6 shared connections)
- [[Community 235]] (6 shared connections)
- [[Community 445]] (3 shared connections)
- [[User Roles & Agent Config]] (2 shared connections)
- [[Community 826]] (1 shared connections)
- [[Community 119]] (1 shared connections)

## Source Files

- `backend/om/db/discord_bot.py`
- `backend/tests/integration/tests/discord_bot/test_discord_bot_db.py`

## Audit Trail

- EXTRACTED: 46 (61%)
- INFERRED: 29 (39%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*