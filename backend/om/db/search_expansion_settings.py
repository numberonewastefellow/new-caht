"""Data access for the per-tenant search-expansion settings singleton.

The session passed in is already tenant-bound (Contract 3), so every query here
runs inside the caller's Postgres schema; there is no tenant column.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import SearchExpansionSettings

# Columns an admin may edit from the UI / API.
EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "enable_expansion",
        "enable_keyword_expansion",
        "enable_semantic_rephrase",
        "enable_keyword_history_expansion",
        "max_variants",
        "num_results",
        "num_retrieved_per_query",
        "rrf_k",
        "original_query_weight",
        "semantic_variant_weight",
        "keyword_variant_weight",
        "enable_llm_section_selection",
    }
)


def get_expansion_settings(db_session: Session) -> SearchExpansionSettings:
    """Return the singleton row for the current tenant, creating defaults if absent."""
    settings = db_session.scalar(
        select(SearchExpansionSettings).where(
            SearchExpansionSettings.singleton.is_(True)
        )
    )
    if settings is None:
        settings = SearchExpansionSettings(singleton=True)
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
    return settings


def update_expansion_settings(
    db_session: Session, updates: dict[str, object]
) -> SearchExpansionSettings:
    """Apply a partial update to the singleton. Unknown/None fields are ignored."""
    settings = get_expansion_settings(db_session)
    for key, value in updates.items():
        if key in EDITABLE_FIELDS and value is not None:
            setattr(settings, key, value)
    db_session.commit()
    db_session.refresh(settings)
    return settings
