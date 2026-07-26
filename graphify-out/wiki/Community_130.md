# Community 130

> 96 nodes · cohesion 0.04

## Key Concepts

- **slack_retrieval()** (22 connections) — `backend/om/context/search/federated/slack_search.py`
- **DocumentSource** (21 connections) — `backend/om/db/document.py`
- **slack_search.py** (19 connections) — `backend/om/context/search/federated/slack_search.py`
- **ThreadContextResult** (16 connections) — `backend/om/context/search/federated/slack_search.py`
- **_fetch_thread_context()** (14 connections) — `backend/om/context/search/federated/slack_search.py`
- **_create_mock_message()** (14 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **fetch_thread_contexts_with_rate_limit_handling()** (13 connections) — `backend/om/context/search/federated/slack_search.py`
- **SlackRateLimitError** (13 connections) — `backend/om/context/search/federated/slack_search.py`
- **fetch_and_cache_channel_metadata()** (12 connections) — `backend/om/context/search/federated/slack_search.py`
- **query_slack()** (10 connections) — `backend/om/context/search/federated/slack_search.py`
- **WebClient** (9 connections) — `backend/om/context/search/federated/slack_search.py`
- **TestFetchThreadContext** (9 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **TestFetchThreadContextsWithRateLimitHandling** (8 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **Any** (7 connections) — `backend/om/context/search/federated/slack_search.py`
- **ChannelMetadata** (7 connections) — `backend/om/context/search/federated/slack_search.py`
- **SlackMessage** (7 connections) — `backend/om/context/search/federated/slack_search.py`
- **test_slack_thread_context.py** (7 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **TestMaxMessagesLimit** (7 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **TestThreadContextResult** (7 connections) — `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`
- **_build_thread_text()** (6 connections) — `backend/om/context/search/federated/slack_search.py`
- **_should_skip_channel()** (6 connections) — `backend/om/context/search/federated/slack_search.py`
- **_extract_channel_data_from_entities()** (5 connections) — `backend/om/context/search/federated/slack_search.py`
- **get_cached_user_profile()** (5 connections) — `backend/om/context/search/federated/slack_search.py`
- **merge_slack_messages()** (5 connections) — `backend/om/context/search/federated/slack_search.py`
- **.error()** (5 connections) — `backend/om/context/search/federated/slack_search.py`
- *... and 71 more nodes in this community*

## Relationships

- [[Community 102]] (11 shared connections)
- [[Document Indexing Adapter]] (11 shared connections)
- [[Community 140]] (8 shared connections)
- [[Community 361]] (6 shared connections)
- [[Community 83]] (5 shared connections)
- [[Community 266]] (3 shared connections)
- [[Agent Chat Packets & Citations]] (3 shared connections)
- [[Community 69]] (2 shared connections)
- [[Document External Access]] (1 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 85]] (1 shared connections)

## Source Files

- `backend/om/context/search/federated/slack_search.py`
- `backend/om/db/document.py`
- `backend/tests/external_dependency_unit/slack_bot/test_slack_bot_federated_search.py`
- `backend/tests/unit/om/context/search/federated/test_slack_thread_context.py`

## Audit Trail

- EXTRACTED: 278 (70%)
- INFERRED: 122 (30%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*