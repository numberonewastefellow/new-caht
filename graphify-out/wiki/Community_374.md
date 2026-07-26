# Community 374

> 40 nodes · cohesion 0.12

## Key Concepts

- **slack_bot.py** (12 connections) — `backend/om/server/manage/slack_bot.py`
- **Session** (11 connections) — `backend/om/server/manage/slack_bot.py`
- **patch_slack_channel_config()** (11 connections) — `backend/om/server/manage/slack_bot.py`
- **Session** (10 connections) — `backend/om/db/slack_channel_config.py`
- **User** (10 connections) — `backend/om/server/manage/slack_bot.py`
- **slack_channel_config.py** (10 connections) — `backend/om/db/slack_channel_config.py`
- **create_slack_channel_agent()** (10 connections) — `backend/om/db/slack_channel_config.py`
- **create_bot()** (10 connections) — `backend/om/server/manage/slack_bot.py`
- **create_slack_channel_config()** (9 connections) — `backend/om/server/manage/slack_bot.py`
- **_form_channel_config()** (8 connections) — `backend/om/server/manage/slack_bot.py`
- **SlackChannelConfig** (7 connections) — `backend/om/db/slack_channel_config.py`
- **fetch_slack_channel_configs()** (6 connections) — `backend/om/db/slack_channel_config.py`
- **insert_slack_channel_config()** (6 connections) — `backend/om/db/slack_channel_config.py`
- **remove_slack_channel_config()** (6 connections) — `backend/om/db/slack_channel_config.py`
- **patch_bot()** (6 connections) — `backend/om/server/manage/slack_bot.py`
- **fetch_slack_channel_config_for_channel_or_default()** (5 connections) — `backend/om/db/slack_channel_config.py`
- **update_slack_channel_config()** (5 connections) — `backend/om/db/slack_channel_config.py`
- **get_bot_by_id()** (5 connections) — `backend/om/server/manage/slack_bot.py`
- **list_bot_configs()** (5 connections) — `backend/om/server/manage/slack_bot.py`
- **list_bots()** (5 connections) — `backend/om/server/manage/slack_bot.py`
- **list_slack_channel_configs()** (5 connections) — `backend/om/server/manage/slack_bot.py`
- **ChannelConfig** (4 connections) — `backend/om/db/slack_channel_config.py`
- **SlackBot** (4 connections) — `backend/om/server/manage/slack_bot.py`
- **SlackChannelConfig** (4 connections) — `backend/om/server/manage/slack_bot.py`
- **_cleanup_relationships()** (4 connections) — `backend/om/db/slack_channel_config.py`
- *... and 15 more nodes in this community*

## Relationships

- [[User Roles & Agent Config]] (6 shared connections)
- [[Agent Chat Packets & Citations]] (6 shared connections)
- [[Community 1259]] (5 shared connections)
- [[Community 195]] (3 shared connections)
- [[Community 127]] (3 shared connections)
- [[Community 103]] (3 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 168]] (1 shared connections)
- [[Community 361]] (1 shared connections)
- [[Community 111]] (1 shared connections)

## Source Files

- `backend/om/db/slack_channel_config.py`
- `backend/om/server/manage/slack_bot.py`
- `backend/tests/unit/om/onyxbot/test_slack_channel_config.py`

## Audit Trail

- EXTRACTED: 166 (77%)
- INFERRED: 49 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*