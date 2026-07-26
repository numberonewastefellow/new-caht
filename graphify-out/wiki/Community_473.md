# Community 473

> 32 nodes · cohesion 0.08

## Key Concepts

- **parse_discord_registration_key()** (15 connections) — `backend/om/server/manage/discord_bot/utils.py`
- **TestParseRegistrationKey** (9 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **TestGenerateRegistrationKey** (5 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_registration_key_encodes_correct_tenant()** (4 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **.test_registration_key_tenant_mismatch()** (4 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **.test_generate_registration_key()** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_generate_registration_key_special_tenant()** (4 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **utils.py** (3 connections) — `backend/om/server/manage/discord_bot/utils.py`
- **.test_generate_registration_key_unique()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_empty_token()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_invalid()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_missing_dot()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_missing_prefix()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_special_chars()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_url_encoded_tenant()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **.test_parse_registration_key_valid()** (3 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Key created in tenant 1 cannot be used in tenant 2 context.** (1 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **Key format discord_<tenant_id>.<token> encodes correct tenant.** (1 connections) — `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- **Discord registration key generation and parsing.** (1 connections) — `backend/om/server/manage/discord_bot/utils.py`
- **Parse registration key to extract tenant_id.      Returns tenant_id or None if i** (1 connections) — `backend/om/server/manage/discord_bot/utils.py`
- **Key with empty token part returns None.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Tenant ID with URL encoding is decoded correctly.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Key with special characters in tenant ID.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Tests for generate_discord_registration_key function.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- **Generated key has correct format.** (1 connections) — `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`
- *... and 7 more nodes in this community*

## Relationships

- [[Community 235]] (6 shared connections)
- [[Community 134]] (2 shared connections)
- [[Community 826]] (2 shared connections)
- [[Community 219]] (1 shared connections)
- [[Community 469]] (1 shared connections)

## Source Files

- `backend/om/server/manage/discord_bot/utils.py`
- `backend/tests/integration/multitenant_tests/discord_bot/test_discord_bot_multitenant.py`
- `backend/tests/unit/om/onyxbot/discord/test_discord_utils.py`

## Audit Trail

- EXTRACTED: 59 (67%)
- INFERRED: 29 (33%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*