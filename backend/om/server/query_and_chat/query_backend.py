from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.orm import Session

from om.auth.users import current_curator_or_admin_user
from om.auth.users import current_user
from om.configs.constants import DocumentSource
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.onyxbot.slack.handlers.handle_standard_answers import (
    oneoff_standard_answers,
)
from om.search.admin.service import admin_search as _admin_search_service
from om.search.admin.service import get_valid_tags as _get_valid_tags_service
from om.server.manage.models import StandardAnswer
from om.server.query_and_chat.models import AdminSearchRequest
from om.server.query_and_chat.models import AdminSearchResponse
from om.server.query_and_chat.models import SourceTag
from om.server.query_and_chat.models import TagResponse
from om.server.utils_vector_db import require_vector_db
from om.utils.logger import setup_logger

logger = setup_logger()

admin_router = APIRouter(prefix="/admin")
basic_router = APIRouter(prefix="/query")


# NOTE: these live here rather than in om.server.query_and_chat.models because
# `StandardAnswer` comes from om.server.manage.models, which transitively imports
# om.db.chat -> om.server.query_and_chat.models (circular import at module scope).
class StandardAnswerRequest(BaseModel):
    message: str
    slack_bot_categories: list[str]


class StandardAnswerResponse(BaseModel):
    standard_answers: list[StandardAnswer] = Field(default_factory=list)


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


@basic_router.get("/standard-answer")
def get_standard_answer(
    request: StandardAnswerRequest,
    db_session: Session = Depends(get_session),
    _: User = Depends(current_user),
) -> StandardAnswerResponse:
    try:
        standard_answers = oneoff_standard_answers(
            message=request.message,
            slack_bot_categories=request.slack_bot_categories,
            db_session=db_session,
        )
        return StandardAnswerResponse(standard_answers=standard_answers)
    except Exception as e:
        logger.error(f"Error in get_standard_answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred")
