"""Post-query censoring — the fail-closed safety net over the sync staleness window.

Some sources (e.g. Salesforce) enforce access by *censoring* retrieved results at
query time rather than by an indexed ACL. After retrieval, every chunk from such a
source is re-checked against the authenticated caller and dropped if they may not
see it. Censoring runs per-source, is authoritative and server-side, and **fails
closed** — if a source's check errors, all of that source's chunks are discarded
rather than leaked. The original result ordering is preserved for survivors.

Kept function names (`_post_query_chunk_censoring`) match the search-pipeline
caller; the implementation is a WS-B clean-room rewrite.
"""

from collections.abc import Iterable

from om.configs.constants import DocumentSource
from om.context.search.pipeline import InferenceChunk
from om.db.connector_credential_pair import get_all_auto_sync_cc_pairs
from om.db.models import User
from om.external_permissions.sync_params import get_all_censoring_enabled_sources
from om.external_permissions.sync_params import get_source_perm_sync_config
from om.tenancy.context import get_current_tenant_session
from om.utils.logger import setup_logger

logger = setup_logger()


def _censoring_sources() -> set[DocumentSource]:
    """Sources whose results must pass a query-time censoring check: those that
    both declare a censoring config AND have at least one auto-sync cc-pair.

    Censoring is decided at *source* granularity (a single sync cc-pair censors
    every chunk of that source) to avoid a per-chunk cc-pair lookup.
    """
    censoring_capable = get_all_censoring_enabled_sources()
    if not censoring_capable:
        return set()
    with get_current_tenant_session() as db_session:
        return {
            cc_pair.connector.source
            for cc_pair in get_all_auto_sync_cc_pairs(db_session)
            if cc_pair.connector.source in censoring_capable
        }


def _censor_source_chunks(
    source: DocumentSource,
    chunks: list[InferenceChunk],
    user_email: str,
) -> Iterable[InferenceChunk]:
    """Run a single source's censoring callback. Fail closed: on any error, yield
    nothing (drop every chunk of this source) rather than risk a leak."""
    sync_config = get_source_perm_sync_config(source)
    if sync_config is None or sync_config.censoring_config is None:
        raise ValueError(f"No censoring config found for source {source}")
    try:
        return sync_config.censoring_config.chunk_censoring_func(chunks, user_email)
    except Exception:
        logger.exception(
            "Censoring failed for source %s — dropping all %d of its chunks",
            source,
            len(chunks),
        )
        return []


def _post_query_chunk_censoring(
    chunks: list[InferenceChunk],
    user: User | None,
) -> list[InferenceChunk]:
    """Drop retrieved chunks the user may not see for censoring-enforced sources,
    preserving the input ordering of the survivors."""
    if user is None:
        # Auth disabled — nothing to censor against.
        return chunks

    sources_to_censor = _censoring_sources()
    if not sources_to_censor:
        return chunks

    # Anonymous callers can only ever see non-censored (public) content.
    if user.is_anonymous:
        return [c for c in chunks if c.source_type not in sources_to_censor]

    # Group the chunks that need a per-source check; pass the rest straight
    # through. Censored survivors are keyed by the object the censoring function
    # RETURNS (it may redact, not merely filter) so any redaction is preserved.
    output_by_id: dict[str, InferenceChunk] = {}
    pending: dict[DocumentSource, list[InferenceChunk]] = {}
    for chunk in chunks:
        if chunk.source_type in sources_to_censor:
            pending.setdefault(chunk.source_type, []).append(chunk)
        else:
            output_by_id[chunk.unique_id] = chunk

    for source, source_chunks in pending.items():
        for kept in _censor_source_chunks(source, source_chunks, user.email):
            output_by_id[kept.unique_id] = kept

    # Rebuild in the original order, keeping only survivors.
    return [
        output_by_id[chunk.unique_id]
        for chunk in chunks
        if chunk.unique_id in output_by_id
    ]
