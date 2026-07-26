# Community 826

> 17 nodes · cohesion 0.14

## Key Concepts

- **get_bot_token()** (10 connections) — `backend/om/onyxbot/discord/utils.py`
- **TestGetBotToken** (6 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **test_discord_utils.py** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_bot_token_from_env_only_in_cloud()** (3 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **.test_get_token_env_priority()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_get_token_from_db()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_get_token_from_env()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_get_token_none()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **utils.py** (2 connections) — `backend/om/onyxbot/discord/utils.py`
- **Bot token comes from env var in cloud mode, ignores DB.** (1 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **Unit tests for Discord bot utilities.  Tests for: - Token management (get_bot_to** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Tests for get_bot_token function.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **When env var is set, returns env var.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **When no env var and DB config exists, returns DB token.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **When no env var and no DB config, returns None.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **When both env var and DB exist, env var takes priority.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Get Discord bot token from env var or database.      Priority:     1. DISCORD_BO** (1 connections) — `backend/om/onyxbot/discord/utils.py`

## Relationships

- [[Community 473]] (2 shared connections)
- [[Community 134]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 753]] (1 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 672]] (1 shared connections)

## Source Files

- `backend/om/onyxbot/discord/utils.py`
- `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`

## Audit Trail

- EXTRACTED: 32 (71%)
- INFERRED: 13 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*