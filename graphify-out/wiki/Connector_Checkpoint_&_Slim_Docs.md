# Connector Checkpoint & Slim Docs

> 395 nodes · cohesion 0.02

## Key Concepts

- **ConnectorValidationError** (335 connections) — `backend/om/connectors/exceptions.py`
- **CredentialExpiredError** (214 connections) — `backend/om/connectors/exceptions.py`
- **InsufficientPermissionsError** (204 connections) — `backend/om/connectors/exceptions.py`
- **UnexpectedValidationError** (162 connections) — `backend/om/connectors/exceptions.py`
- **ConnectorMissingCredentialError** (75 connections) — `backend/om/connectors/models.py`
- **NormalizationResult** (71 connections) — `backend/om/connectors/interfaces.py`
- **CredentialsProviderInterface** (70 connections) — `backend/om/connectors/interfaces.py`
- **CredentialsConnector** (59 connections) — `backend/om/connectors/interfaces.py`
- **SlackConnector** (33 connections) — `backend/om/connectors/slack/connector.py`
- **connector.py** (29 connections) — `backend/om/connectors/slack/connector.py`
- **OmRedisSlackRetryHandler** (29 connections) — `backend/om/connectors/slack/onyx_retry_handler.py`
- **OmSlackWebClient** (29 connections) — `backend/om/connectors/slack/onyx_slack_web_client.py`
- **WebClient** (28 connections) — `backend/om/connectors/slack/connector.py`
- **ChannelType** (26 connections) — `backend/om/connectors/slack/connector.py`
- **CodaConnector** (25 connections) — `backend/om/connectors/coda/connector.py`
- **GithubConnector** (24 connections) — `backend/om/connectors/github/connector.py`
- **SlackMessageFilterReason** (24 connections) — `backend/om/connectors/slack/connector.py`
- **MessageType** (23 connections) — `backend/om/connectors/slack/connector.py`
- **BitbucketConnector** (22 connections) — `backend/om/connectors/bitbucket/connector.py`
- **BlobStorageConnector** (22 connections) — `backend/om/connectors/blob/connector.py`
- **SlackCheckpoint** (22 connections) — `backend/om/connectors/slack/connector.py`
- **ExternalAccess** (20 connections) — `backend/om/connectors/slack/connector.py`
- **SlackTextCleaner** (20 connections) — `backend/om/connectors/slack/connector.py`
- **connector.py** (20 connections) — `backend/om/connectors/web/connector.py`
- **BasicExpertInfo** (19 connections) — `backend/om/connectors/slack/connector.py`
- *... and 370 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (488 shared connections)
- [[Connectors (Airtable/Asana)]] (210 shared connections)
- [[Document External Access]] (93 shared connections)
- [[Confluence Connector]] (67 shared connections)
- [[Community 212]] (42 shared connections)
- [[Community 142]] (38 shared connections)
- [[Community 111]] (37 shared connections)
- [[Community 139]] (36 shared connections)
- [[Community 88]] (32 shared connections)
- [[Salesforce Connector]] (32 shared connections)
- [[Google Drive Connector]] (23 shared connections)
- [[Community 167]] (22 shared connections)

## Source Files

- `backend/om/connectors/bitbucket/connector.py`
- `backend/om/connectors/blob/connector.py`
- `backend/om/connectors/bookstack/connector.py`
- `backend/om/connectors/coda/connector.py`
- `backend/om/connectors/confluence/connector.py`
- `backend/om/connectors/dropbox/connector.py`
- `backend/om/connectors/drupal_wiki/connector.py`
- `backend/om/connectors/exceptions.py`
- `backend/om/connectors/github/connector.py`
- `backend/om/connectors/github/rate_limit_utils.py`
- `backend/om/connectors/google_drive/connector.py`
- `backend/om/connectors/interfaces.py`
- `backend/om/connectors/jira/connector.py`
- `backend/om/connectors/models.py`
- `backend/om/connectors/notion/connector.py`
- `backend/om/connectors/outline/connector.py`
- `backend/om/connectors/sharepoint/connector.py`
- `backend/om/connectors/slack/connector.py`
- `backend/om/connectors/slack/onyx_retry_handler.py`
- `backend/om/connectors/slack/onyx_slack_web_client.py`

## Audit Trail

- EXTRACTED: 1332 (36%)
- INFERRED: 2397 (64%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*