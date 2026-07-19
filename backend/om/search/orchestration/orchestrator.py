"""Search orchestration.

Flow (per request):
  1. Expand the query (Phase-1 ``QueryExpander``).
  2. Run the original query + every expansion variant against the index **in
     parallel**, each with the same access filters (Contract 2).
  3. Fuse the ranked chunk lists via weighted reciprocal-rank fusion.
  4. Merge fused chunks into per-document sections -> result documents.
  5. Optionally ask the LLM which documents are relevant.
  6. Emit typed packets as each stage completes (progressive SSE rendering).

Multi-tenant + streaming notes:
  * The request-scoped DB session is closed before a StreamingResponse body runs,
    so every DB touch here opens a FRESH tenant-bound session
    (``get_current_tenant_session``). The tenant contextvar itself is still set
    during response streaming.
  * Parallel retrieval threads receive a COPY of the current context
    (``contextvars.copy_context``) so the tenant contextvar propagates; each
    worker opens its own session (SQLAlchemy sessions are not thread-safe).
  * ACL is always applied via Contract-2 access filters (``build_index_filters``
    -> ``build_user_only_filters``) — never reimplemented here, fail-closed.
"""

import contextvars
from collections.abc import Iterator
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from om.context.search.models import BaseFilters
from om.context.search.models import ChunkIndexRequest
from om.context.search.models import IndexFilters
from om.context.search.models import InferenceChunk
from om.context.search.retrieval.search_runner import search_chunks
from om.db.models import User
from om.db.search_settings import get_current_search_settings
from om.document_index.factory import get_default_document_index
from om.document_index.interfaces_new import DocumentIndex
from om.llm.factory import get_default_llm
from om.search.expansion.config import SearchFlowConfig
from om.search.expansion.expander import QueryExpander
from om.search.expansion.models import HistoryTurn
from om.search.expansion.models import QueryExpansionResult
from om.search.filters import build_index_filters
from om.search.log_events import ACTION_EXECUTE
from om.search.log_events import timed_search_event
from om.search.orchestration.fusion import merge_chunks_into_sections
from om.search.orchestration.fusion import RankedList
from om.search.orchestration.fusion import weighted_reciprocal_rank_fusion
from om.search.orchestration.packets import LLMSelectedDocsPacket
from om.search.orchestration.packets import QueryExpansionsPacket
from om.search.orchestration.packets import SearchDocsPacket
from om.search.orchestration.packets import SearchErrorPacket
from om.search.orchestration.packets import SearchStreamPacket
from om.search.orchestration.section_selection import select_relevant_documents
from om.search.results import SearchDocWithContent
from om.tenancy.context import get_current_tenant_session
from om.utils.logger import setup_logger

logger = setup_logger()

_MAX_PARALLEL_RETRIEVALS = 8


class HistoryRecorder(Protocol):
    """Persists a search into history and returns the new row id (or None)."""

    def record(self, *, query: str, expansions: list[str]) -> str | None: ...


class SearchOrchestrator:
    """Runs one expanded + fused search flow, emitting typed packets."""

    def __init__(
        self,
        user: User,
        config: SearchFlowConfig | None = None,
        history_recorder: HistoryRecorder | None = None,
    ) -> None:
        self._user = user
        self._config = config
        self._history_recorder = history_recorder

    # -- public streaming API ------------------------------------------------

    def stream_packets(
        self,
        query: str,
        history: list[HistoryTurn] | None = None,
        user_filters: BaseFilters | None = None,
        include_content: bool = False,
    ) -> Iterator[SearchStreamPacket]:
        history = history or []
        try:
            with timed_search_event(
                event="search.executed",
                action=ACTION_EXECUTE,
                actor_user_id=self._user.id,
            ) as fields:
                # Resolve config, index + access filters on a fresh session.
                with get_current_tenant_session() as session:
                    config = self._config or SearchFlowConfig.load(session)
                    search_settings = get_current_search_settings(session)
                    document_index = get_default_document_index(search_settings, None)
                    index_filters = build_index_filters(
                        self._user, session, user_filters
                    )

                # 1. Expand. Executed queries = original + expansion variants.
                expansion = QueryExpander(config.expansion).expand(query, history)
                variants = expansion.retrieval_variants()
                executed_queries = [query] + [variant.text for variant in variants]
                yield QueryExpansionsPacket(executed_queries=executed_queries)

                # 2 + 3. Retrieve variants in parallel and RRF-fuse.
                fused = self._retrieve_and_fuse(
                    query, expansion, index_filters, document_index, config
                )

                # 4. Merge into per-document sections -> result docs.
                sections = merge_chunks_into_sections(fused, config.fusion.num_results)
                documents = SearchDocWithContent.from_sections(
                    sections, include_content
                )
                fields["num_results"] = len(documents)
                fields["num_variants"] = len(variants)
                yield SearchDocsPacket(search_docs=documents)

                # 5. Optional LLM relevance selection (emitted after docs so the
                #    UI can render results first, then apply relevance).
                if config.fusion.enable_llm_section_selection and documents:
                    selected_ids = select_relevant_documents(
                        expansion.effective_query,
                        documents,
                        get_default_llm(temperature=0.0),
                        max_to_judge=config.fusion.llm_selection_num_docs,
                    )
                    yield LLMSelectedDocsPacket(llm_selected_doc_ids=selected_ids)

                # 6. Persist history (if a recorder was wired in). Fire-and-forget.
                if self._history_recorder is not None:
                    self._history_recorder.record(
                        query=query, expansions=expansion.expansion_texts
                    )
        except Exception as exc:
            logger.exception("search flow failed")
            yield SearchErrorPacket(error=f"{type(exc).__name__}: {exc}")

    # -- retrieval + fusion --------------------------------------------------

    def _retrieve_and_fuse(
        self,
        original_query: str,
        expansion: QueryExpansionResult,
        index_filters: IndexFilters,
        document_index: DocumentIndex,
        config: SearchFlowConfig,
    ) -> list[tuple[InferenceChunk, float]]:
        fusion_cfg = config.fusion
        # (request, weight) specs: original query first, then expansion variants.
        specs: list[tuple[ChunkIndexRequest, float]] = [
            (
                self._chunk_request(original_query, index_filters, fusion_cfg.num_retrieved_per_query),
                fusion_cfg.original_query_weight,
            )
        ]
        for variant in expansion.retrieval_variants():
            weight = (
                fusion_cfg.keyword_variant_weight
                if variant.is_keyword
                else fusion_cfg.semantic_variant_weight
            )
            specs.append(
                (
                    self._chunk_request(
                        variant.text, index_filters, fusion_cfg.num_retrieved_per_query
                    ),
                    weight,
                )
            )

        results = self._parallel_search([spec[0] for spec in specs], document_index)
        ranked_lists = [
            RankedList(chunks=results[i], weight=specs[i][1])
            for i in range(len(specs))
        ]
        return weighted_reciprocal_rank_fusion(ranked_lists, k=fusion_cfg.rrf_k)

    @staticmethod
    def _chunk_request(
        query: str, filters: IndexFilters, limit: int
    ) -> ChunkIndexRequest:
        return ChunkIndexRequest(query=query, filters=filters, limit=limit)

    def _parallel_search(
        self, requests: list[ChunkIndexRequest], document_index: DocumentIndex
    ) -> list[list[InferenceChunk]]:
        user_id = self._user.id

        def worker(request: ChunkIndexRequest) -> list[InferenceChunk]:
            try:
                with get_current_tenant_session() as session:
                    return search_chunks(request, user_id, document_index, session)
            except Exception as exc:
                logger.warning(
                    "variant retrieval failed for query=%r: %s", request.query, exc
                )
                return []

        if len(requests) == 1:
            return [worker(requests[0])]

        results: list[list[InferenceChunk]] = [[] for _ in requests]
        max_workers = min(len(requests), _MAX_PARALLEL_RETRIEVALS)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {}
            for index, request in enumerate(requests):
                # Copy the current context so the tenant contextvar propagates
                # into the worker thread.
                ctx = contextvars.copy_context()
                future_to_index[executor.submit(ctx.run, worker, request)] = index
            for future in as_completed(future_to_index):
                results[future_to_index[future]] = future.result()
        return results
