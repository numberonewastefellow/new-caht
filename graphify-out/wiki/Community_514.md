# Community 514

> 30 nodes · cohesion 0.09

## Key Concepts

- **_split_message()** (15 connections) — `backend/om/onyxbot/discord/handle_message.py`
- **TestSplitMessage** (14 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **test_message_utils.py** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_at_double_newline()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_at_period_space()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_at_single_newline()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_at_space()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_message_at_limit()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_message_over_limit()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_message_under_limit()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_multiple_chunks()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_no_breakpoint()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_preserves_content()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_threshold_50_percent()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **.test_split_with_unicode()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Split content into chunks that fit Discord's message limit.** (1 connections) — `backend/om/onyxbot/discord/handle_message.py`
- **Unit tests for Discord bot message utilities.  Tests for: - Message splitting (_** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **5000 char message splits into 3 chunks.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Concatenated chunks equal original content.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Handles unicode characters correctly.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Tests for _split_message function.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Message under 2000 chars returns single chunk.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Message exactly at 2000 chars returns single chunk.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Message over 2000 chars splits into multiple chunks.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- **Prefers splitting at double newline.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 158]] (2 shared connections)
- [[Community 571]] (1 shared connections)

## Source Files

- `backend/om/onyxbot/discord/handle_message.py`
- `backend/tests/unit/om/onyxbot/discord/test_message_utils.py`

## Audit Trail

- EXTRACTED: 59 (71%)
- INFERRED: 24 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*