-- READ-ONLY probes: how much live data depends on strings we might rename.
-- Run against the live DB (psql / docker exec ... psql). SELECTs only.

-- API keys: synthetic users whose email uses the onyx domain (renaming the domain orphans them)
SELECT count(*) AS api_key_users_onyx_domain FROM "user" WHERE email LIKE '%@onyxapikey.ai';
SELECT count(*) AS api_keys_total FROM api_key;

-- PATs: tokens in circulation that start with onyx_pat_ (display form keeps the prefix)
SELECT count(*) AS pats_total,
       count(*) FILTER (WHERE token_display LIKE 'onyx_pat_%') AS pats_onyx_prefix,
       count(*) FILTER (WHERE NOT is_revoked AND (expires_at IS NULL OR expires_at > now())) AS pats_active
FROM personal_access_token;

-- File store: do stored object keys embed the onyx-files prefix? (S3 prefix flip would orphan these)
SELECT count(*) AS files_total,
       count(*) FILTER (WHERE object_key LIKE 'onyx-files/%') AS files_under_onyx_prefix,
       count(*) FILTER (WHERE bucket_name = 'onyx-file-store-bucket') AS files_in_onyx_bucket
FROM file_record;

-- Key/value store rows (Postgres-backed; Redis only caches these)
SELECT count(*) AS kv_rows FROM key_value_store;

-- Chat sessions started from the bot (onyxbot_flow column, renamed in Phase 3)
SELECT count(*) FILTER (WHERE onyxbot_flow) AS bot_sessions, count(*) AS sessions FROM chat_session;

-- Anything else in text columns that embeds the brand (spot check, extend as needed)
SELECT count(*) AS agents_mentioning_onyx FROM agent WHERE system_prompt ILIKE '%onyx%' OR description ILIKE '%onyx%';
