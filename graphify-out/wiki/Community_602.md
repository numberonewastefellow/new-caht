# Community 602

> 25 nodes · cohesion 0.12

## Key Concepts

- **make_paginated_slack_api_call()** (16 connections) — `backend/om/connectors/slack/utils.py`
- **slack_group_sync()** (8 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **utils.py** (7 connections) — `backend/om/connectors/slack/utils.py`
- **get_message_link()** (6 connections) — `backend/om/connectors/slack/utils.py`
- **fetch_user_id_to_email_map()** (5 connections) — `backend/om/external_permissions/slack/utils.py`
- **_make_slack_api_call_paginated()** (5 connections) — `backend/om/connectors/slack/utils.py`
- **WebClient** (4 connections) — `backend/om/connectors/slack/utils.py`
- **group_sync.py** (4 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **_get_slack_group_ids()** (4 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **_get_slack_group_members_email()** (4 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **get_base_url()** (4 connections) — `backend/om/connectors/slack/utils.py`
- **Any** (3 connections) — `backend/om/connectors/slack/utils.py`
- **WebClient** (3 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **make_slack_api_call()** (3 connections) — `backend/om/connectors/slack/utils.py`
- **SlackResponse** (3 connections) — `backend/om/connectors/slack/utils.py`
- **ConnectorCredentialPair** (2 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **ExternalUserGroup** (2 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **.__init__()** (2 connections) — `backend/om/connectors/slack/utils.py`
- **MessageType** (1 connections) — `backend/om/connectors/slack/utils.py`
- **utils.py** (1 connections) — `backend/om/external_permissions/slack/utils.py`
- **WebClient** (1 connections) — `backend/om/external_permissions/slack/utils.py`
- **THIS IS NOT USEFUL OR USED FOR PERMISSION SYNCING WHEN USERGROUPS ARE ADDED TO** (1 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **NOTE: not used atm. All channel access is done at the     individual user level** (1 connections) — `backend/om/external_permissions/slack/group_sync.py`
- **Retrieve and cache the base URL of the Slack workspace based on the client token** (1 connections) — `backend/om/connectors/slack/utils.py`
- **Wraps calls to slack API so that they automatically handle pagination** (1 connections) — `backend/om/connectors/slack/utils.py`

## Relationships

- [[Connector Checkpoint & Slim Docs]] (5 shared connections)
- [[Community 665]] (4 shared connections)
- [[Community 320]] (3 shared connections)
- [[Document External Access]] (3 shared connections)
- [[Community 127]] (2 shared connections)
- [[Community 872]] (2 shared connections)
- [[Community 69]] (1 shared connections)

## Source Files

- `backend/om/connectors/slack/utils.py`
- `backend/om/external_permissions/slack/group_sync.py`
- `backend/om/external_permissions/slack/utils.py`

## Audit Trail

- EXTRACTED: 68 (74%)
- INFERRED: 24 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*