"""Standard answers — clean-room reimplementation (WS-D).

Keyword/regex canned answers with category tagging for the Slack bot, plus a
stateless query endpoint. See ``README.md`` for architecture, the matching model,
the per-tenant config table, structured-log events, and extension points.

Public sub-modules:
- ``safe_regex``  — ReDoS-resistant pattern validation + bounded matching.
- ``matching``    — the keyword/regex matching engine (pure, persistence-free).
- ``repository``  — SQLAlchemy data-access for answers/categories/config.
- ``service``     — CRUD business logic + structured logging.
- ``config``      — per-tenant feature-toggle config accessors.
- ``blocks``      — Slack Block Kit rendering for matched answers.
- ``slack_handler`` — incoming-message handler + stateless ``oneoff`` variant.
- ``api``         — FastAPI admin CRUD router + query endpoint router.
"""
