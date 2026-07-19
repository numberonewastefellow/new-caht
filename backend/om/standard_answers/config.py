"""Per-tenant standard-answers feature config (dedicated typed table, Standard 5).

Reads/writes the singleton :class:`~om.db.models.StandardAnswerConfig` row (id=1)
inside the caller's tenant-scoped session. A missing row is treated as defaults and
lazily created on first write, so the feature is safe to call before any admin has
visited the settings screen.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.db.models import StandardAnswerConfig

SINGLETON_ID = 1

DEFAULT_ENABLED = True
DEFAULT_MAX_MATCHES_PER_MESSAGE = 3
DEFAULT_MATCH_INPUT_CHAR_LIMIT = 8000


@dataclass(frozen=True, slots=True)
class StandardAnswerConfigView:
    """Immutable snapshot of the config, safe to pass around after the session closes."""

    enabled: bool
    max_matches_per_message: int
    match_input_char_limit: int

    @classmethod
    def from_model(cls, model: StandardAnswerConfig) -> "StandardAnswerConfigView":
        return cls(
            enabled=model.enabled,
            max_matches_per_message=model.max_matches_per_message,
            match_input_char_limit=model.match_input_char_limit,
        )


DEFAULT_CONFIG = StandardAnswerConfigView(
    enabled=DEFAULT_ENABLED,
    max_matches_per_message=DEFAULT_MAX_MATCHES_PER_MESSAGE,
    match_input_char_limit=DEFAULT_MATCH_INPUT_CHAR_LIMIT,
)


def _fetch(db_session: Session) -> StandardAnswerConfig | None:
    return db_session.get(StandardAnswerConfig, SINGLETON_ID)


def load_config(db_session: Session) -> StandardAnswerConfigView:
    """Return the tenant's config as an immutable view; defaults if unset."""

    row = _fetch(db_session)
    return StandardAnswerConfigView.from_model(row) if row else DEFAULT_CONFIG


def get_or_create_config(db_session: Session) -> StandardAnswerConfig:
    """Return the singleton config row, creating it with defaults if absent.

    The caller owns the transaction (commit/rollback).
    """

    row = _fetch(db_session)
    if row is not None:
        return row

    # Insert the singleton inside a SAVEPOINT so a lost race (another request created
    # id=1 first) rolls back just this insert, not the caller's transaction; then
    # re-fetch the row the winner committed.
    try:
        with db_session.begin_nested():
            row = StandardAnswerConfig(
                id=SINGLETON_ID,
                enabled=DEFAULT_ENABLED,
                max_matches_per_message=DEFAULT_MAX_MATCHES_PER_MESSAGE,
                match_input_char_limit=DEFAULT_MATCH_INPUT_CHAR_LIMIT,
            )
            db_session.add(row)
            db_session.flush()
        return row
    except IntegrityError:
        existing = _fetch(db_session)
        if existing is None:
            raise
        return existing


def is_enabled(db_session: Session) -> bool:
    """Fast gate for the Slack handler — True when matching should run."""

    return load_config(db_session).enabled
