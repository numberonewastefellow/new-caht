from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from om.auth.users import current_curator_or_admin_user
from om.auth.users import current_user
from om.configs.constants import DocumentSource
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.search.admin.service import admin_search as _admin_search_service
from om.search.admin.service import get_valid_tags as _get_valid_tags_service
from om.server.query_and_chat.models import AdminSearchRequest
from om.server.query_and_chat.models import AdminSearchResponse
from om.server.query_and_chat.models import SourceTag
from om.server.query_and_chat.models import TagResponse
from om.server.utils_vector_db import require_vector_db
from om.utils.logger import setup_logger

logger = setup_logger()

admin_router = APIRouter(prefix="/admin")
basic_router = APIRouter(prefix="/query")


@admin_router.post("/search", dependencies=[Depends(require_vector_db)])
def admin_search(
    question: AdminSearchRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> AdminSearchResponse:
    # Clean-room implementation lives in WS-E (om.search.admin.service).
    documents = _admin_search_service(
        query=question.query,
        filters=question.filters,
        user=user,
        db_session=db_session,
    )
    return AdminSearchResponse(documents=documents)


@basic_router.get("/valid-tags")
def get_tags(
    match_pattern: str | None = None,
    # If this is empty or None, then tags for all sources are considered
    sources: list[DocumentSource] | None = None,
    allow_prefix: bool = True,  # This is currently the only option
    limit: int = 50,
    _: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> TagResponse:
    if not allow_prefix:
        raise NotImplementedError("Cannot disable prefix match for now")

    # Clean-room implementation lives in WS-E (om.search.admin.service).
    db_tags = _get_valid_tags_service(
        db_session=db_session,
        match_pattern=match_pattern,
        sources=sources,
        limit=limit,
    )
    server_tags = [
        SourceTag(
            tag_key=db_tag.tag_key, tag_value=db_tag.tag_value, source=db_tag.source
        )
        for db_tag in db_tags
    ]
    return TagResponse(tags=server_tags)


# The standard-answer query endpoint moved to om.standard_answers.api.query_router
# (GET /query/standard-answer) as part of the WS-D clean-room rewrite.
