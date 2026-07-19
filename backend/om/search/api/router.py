"""Search API router.

Endpoints (all authenticated):
  POST /search/search-flow-classification  - classify a query as search vs chat
  POST /search/send-search-message         - run a search (SSE stream OR full)
  GET  /search/search-history              - the caller's search history
  GET  /search/expansion-settings          - read expansion config (admin)
  PUT  /search/expansion-settings          - update expansion config (admin)

The admin document search + tag lookup live on the shared ``/admin`` and
``/query`` routers (see ``om.search.admin.service`` + integrator snippet), not
here, to preserve their existing paths.
"""

from collections.abc import Generator

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.db.models import User
from om.db.search_expansion_settings import get_expansion_settings
from om.db.search_expansion_settings import update_expansion_settings
from om.search.api import schemas
from om.search.classification import classify_search_flow
from om.search.expansion.config import SearchFlowConfig
from om.search.history.service import list_search_history
from om.search.history.service import SearchHistoryService
from om.search.log_events import ACTION_UPDATE
from om.search.log_events import emit_search_event
from om.search.log_events import STATUS_SUCCESS
from om.search.orchestration.orchestrator import SearchOrchestrator
from om.search.orchestration.packets import LLMSelectedDocsPacket
from om.search.orchestration.packets import QueryExpansionsPacket
from om.search.orchestration.packets import SearchDocsPacket
from om.search.orchestration.packets import SearchErrorPacket
from om.server.rate_limits.dependencies import enforce_rate_limits
from om.server.utils import get_json_line
from om.server.utils_vector_db import require_vector_db
from om.tenancy.context import get_tenant_session_dependency

router = APIRouter(prefix="/search")

# Hard cap on requested result count to bound retrieval cost.
_MAX_NUM_HITS = 100
# Hard cap on history rows returned in one call.
_MAX_HISTORY_LIMIT = 1000


@router.post("/search-flow-classification")
def search_flow_classification(
    request: schemas.SearchFlowClassificationRequest,
    _: User = Depends(current_user),
) -> schemas.SearchFlowClassificationResponse:
    return schemas.SearchFlowClassificationResponse(
        is_search_flow=classify_search_flow(request.user_query)
    )


@router.post(
    "/send-search-message",
    response_model=None,
    # Rate-limit the token-consuming search path (query expansion runs LLM calls),
    # mirroring the enforcement on the chat send endpoint. 429 on over-budget.
    dependencies=[Depends(require_vector_db), Depends(enforce_rate_limits)],
)
def send_search_message(
    request: schemas.SendSearchQueryRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> StreamingResponse | schemas.SearchFullResponse:
    config = _effective_config(db_session, request)
    orchestrator = SearchOrchestrator(
        user=user,
        config=config,
        history_recorder=SearchHistoryService(user.id),
    )

    if request.stream:

        def packet_generator() -> Generator[str, None, None]:
            for packet in orchestrator.stream_packets(
                query=request.search_query,
                history=request.history,
                user_filters=request.filters,
                include_content=request.include_content,
            ):
                yield get_json_line(packet.model_dump())

        return StreamingResponse(
            packet_generator(), media_type="text/event-stream"
        )

    return _collect_full_response(orchestrator, request)


@router.get("/search-history")
def get_search_history(
    limit: int = 100,
    filter_days: int | None = None,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> schemas.SearchHistoryResponse:
    rows = list_search_history(
        db_session,
        user.id,
        limit=min(max(1, limit), _MAX_HISTORY_LIMIT),
        filter_days=filter_days,
    )
    return schemas.SearchHistoryResponse(
        search_queries=[schemas.SearchQueryResponse.from_row(row) for row in rows]
    )


@router.get("/expansion-settings")
def read_expansion_settings(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> schemas.ExpansionSettingsResponse:
    return schemas.ExpansionSettingsResponse.from_row(
        get_expansion_settings(db_session)
    )


@router.put("/expansion-settings")
def write_expansion_settings(
    request: schemas.ExpansionSettingsUpdateRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> schemas.ExpansionSettingsResponse:
    updates = request.model_dump(exclude_none=True)
    row = update_expansion_settings(db_session, updates)
    emit_search_event(
        event="search.config_updated",
        action=ACTION_UPDATE,
        status=STATUS_SUCCESS,
        entity="search_expansion_settings",
        entity_id=row.id,
        actor_user_id=user.id,
        updated_fields=sorted(updates.keys()),
    )
    return schemas.ExpansionSettingsResponse.from_row(row)


# -- helpers -----------------------------------------------------------------


def _effective_config(
    db_session: Session, request: schemas.SendSearchQueryRequest
) -> SearchFlowConfig:
    """Tenant config with per-request overrides applied."""
    config = SearchFlowConfig.load(db_session).model_copy(deep=True)
    if not request.run_query_expansion:
        config.expansion.enable_expansion = False
    num_hits = min(max(request.num_hits, 1), _MAX_NUM_HITS)
    config.fusion.num_results = num_hits
    config.fusion.num_retrieved_per_query = max(
        config.fusion.num_retrieved_per_query, num_hits
    )
    if request.num_docs_fed_to_llm_selection is not None:
        config.fusion.enable_llm_section_selection = True
        config.fusion.llm_selection_num_docs = max(
            1, request.num_docs_fed_to_llm_selection
        )
    return config


def _collect_full_response(
    orchestrator: SearchOrchestrator, request: schemas.SendSearchQueryRequest
) -> schemas.SearchFullResponse:
    """Consume the packet stream into a single non-streaming response."""
    executed_queries: list[str] = []
    documents: list[schemas.SearchDocWithContent] = []
    selected_ids: list[str] | None = None
    error: str | None = None

    for packet in orchestrator.stream_packets(
        query=request.search_query,
        history=request.history,
        user_filters=request.filters,
        include_content=request.include_content,
    ):
        if isinstance(packet, QueryExpansionsPacket):
            executed_queries = packet.executed_queries
        elif isinstance(packet, SearchDocsPacket):
            documents = packet.search_docs
        elif isinstance(packet, LLMSelectedDocsPacket):
            selected_ids = packet.llm_selected_doc_ids
        elif isinstance(packet, SearchErrorPacket):
            error = packet.error

    if selected_ids:
        selected_set = set(selected_ids)
        for doc in documents:
            doc.is_relevant = doc.document_id in selected_set

    return schemas.SearchFullResponse(
        all_executed_queries=executed_queries,
        search_docs=documents,
        llm_selected_doc_ids=selected_ids,
        error=error,
    )
