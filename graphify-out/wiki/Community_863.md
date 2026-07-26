# Community 863

> 16 nodes · cohesion 0.12

## Key Concepts

- **TestReplyChainContextBuilder** (9 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_deep_chain()** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_max_depth()** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_single_reply()** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_deleted_message()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_http_exception()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_missing_reference_data()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **.test_build_reply_chain_no_reply()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **Tests for _build_reply_chain_context function.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **Message replies to one message returns 1 message in chain.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **A → B → C → D reply chain returns full chain in chronological order.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **Chain depth > MAX_CONTEXT_MESSAGES stops at limit.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **Message is not a reply returns None.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **Reply to deleted message handles gracefully with partial chain.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **message.reference.message_id is None returns None.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`
- **discord.HTTPException on fetch stops chain.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`

## Relationships

- [[Community 158]] (7 shared connections)
- [[Community 305]] (4 shared connections)

## Source Files

- `backend/tests/unit/om/onyxbot/discord/test_context_builders.py`

## Audit Trail

- EXTRACTED: 31 (76%)
- INFERRED: 10 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*