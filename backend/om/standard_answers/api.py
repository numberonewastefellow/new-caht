"""FastAPI routers for standard answers.

- ``admin_router`` (prefix ``/nexus``, admin-gated) — CRUD for answers + categories
  and the per-tenant feature config. Path shape preserves the existing frontend
  contract (``/api/nexus/admin/standard-answer...``).
- ``query_router`` (prefix ``/query``, user-gated) — the stateless match endpoint
  ``GET /query/standard-answer`` that replaces the one on ``query_backend.py``.

Thin transport layer: validation/logging/tenancy live in the service + session
dependency (Contract 3). Domain errors are mapped to HTTP status codes here.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.db.models import User
from om.standard_answers.schemas import StandardAnswer as StandardAnswerDTO
from om.standard_answers.schemas import StandardAnswerCategory as StandardAnswerCategoryDTO
from om.standard_answers.schemas import StandardAnswerCategoryCreationRequest
from om.standard_answers.schemas import StandardAnswerConfigResponse
from om.standard_answers.schemas import StandardAnswerConfigUpdateRequest
from om.standard_answers.schemas import StandardAnswerCreationRequest
from om.standard_answers.schemas import StandardAnswerQueryRequest
from om.standard_answers.schemas import StandardAnswerQueryResponse
from om.standard_answers.service import InvalidStandardAnswerError
from om.standard_answers.service import StandardAnswerNotFoundError
from om.standard_answers.service import StandardAnswerService
from om.tenancy.context import get_tenant_session_dependency

admin_router = APIRouter(prefix="/nexus")
query_router = APIRouter(prefix="/query")


def _actor_id(user: User | None) -> str | None:
    return str(user.id) if user is not None else None


def _duplicate_keyword_detail() -> str:
    return (
        "An active standard answer with this keyword already exists. "
        "Deactivate the existing one or use a different keyword."
    )


# --- admin: answers -------------------------------------------------------------


@admin_router.post("/admin/standard-answer", response_model=StandardAnswerDTO)
def create_standard_answer(
    request: StandardAnswerCreationRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> StandardAnswerDTO:
    service = StandardAnswerService(db_session)
    try:
        answer = service.create_answer(
            keyword=request.keyword,
            answer=request.answer,
            category_ids=request.categories,
            match_regex=request.match_regex,
            match_any_keywords=request.match_any_keywords,
            actor_user_id=_actor_id(user),
        )
    except InvalidStandardAnswerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=_duplicate_keyword_detail()) from exc
    return StandardAnswerDTO.from_model(answer)


@admin_router.get("/admin/standard-answer", response_model=list[StandardAnswerDTO])
def list_standard_answers(
    db_session: Session = Depends(get_tenant_session_dependency),
    _: User = Depends(current_admin_user),
) -> list[StandardAnswerDTO]:
    service = StandardAnswerService(db_session)
    return [StandardAnswerDTO.from_model(a) for a in service.list_answers()]


@admin_router.patch(
    "/admin/standard-answer/{standard_answer_id}", response_model=StandardAnswerDTO
)
def patch_standard_answer(
    standard_answer_id: int,
    request: StandardAnswerCreationRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> StandardAnswerDTO:
    service = StandardAnswerService(db_session)
    try:
        answer = service.update_answer(
            standard_answer_id,
            keyword=request.keyword,
            answer=request.answer,
            category_ids=request.categories,
            match_regex=request.match_regex,
            match_any_keywords=request.match_any_keywords,
            actor_user_id=_actor_id(user),
        )
    except StandardAnswerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStandardAnswerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=_duplicate_keyword_detail()) from exc
    return StandardAnswerDTO.from_model(answer)


@admin_router.delete("/admin/standard-answer/{standard_answer_id}")
def delete_standard_answer(
    standard_answer_id: int,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> None:
    service = StandardAnswerService(db_session)
    try:
        service.delete_answer(standard_answer_id, actor_user_id=_actor_id(user))
    except StandardAnswerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- admin: categories ----------------------------------------------------------


@admin_router.post(
    "/admin/standard-answer/category", response_model=StandardAnswerCategoryDTO
)
def create_standard_answer_category(
    request: StandardAnswerCategoryCreationRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> StandardAnswerCategoryDTO:
    service = StandardAnswerService(db_session)
    try:
        category = service.create_category(request.name, actor_user_id=_actor_id(user))
    except InvalidStandardAnswerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=400,
            detail="A category with this name already exists.",
        ) from exc
    return StandardAnswerCategoryDTO.from_model(category)


@admin_router.get(
    "/admin/standard-answer/category",
    response_model=list[StandardAnswerCategoryDTO],
)
def list_standard_answer_categories(
    db_session: Session = Depends(get_tenant_session_dependency),
    _: User = Depends(current_admin_user),
) -> list[StandardAnswerCategoryDTO]:
    service = StandardAnswerService(db_session)
    return [
        StandardAnswerCategoryDTO.from_model(c) for c in service.list_categories()
    ]


@admin_router.patch(
    "/admin/standard-answer/category/{standard_answer_category_id}",
    response_model=StandardAnswerCategoryDTO,
)
def patch_standard_answer_category(
    standard_answer_category_id: int,
    request: StandardAnswerCategoryCreationRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> StandardAnswerCategoryDTO:
    service = StandardAnswerService(db_session)
    try:
        category = service.update_category(
            standard_answer_category_id,
            request.name,
            actor_user_id=_actor_id(user),
        )
    except StandardAnswerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStandardAnswerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=400,
            detail="A category with this name already exists.",
        ) from exc
    return StandardAnswerCategoryDTO.from_model(category)


@admin_router.delete(
    "/admin/standard-answer/category/{standard_answer_category_id}"
)
def delete_standard_answer_category(
    standard_answer_category_id: int,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> None:
    service = StandardAnswerService(db_session)
    try:
        service.delete_category(
            standard_answer_category_id, actor_user_id=_actor_id(user)
        )
    except StandardAnswerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStandardAnswerError as exc:
        # In-use or default category → 400 with a clear, actionable message.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        # A reference was added between the check and the delete (FK backstop).
        raise HTTPException(
            status_code=400,
            detail="Category is now in use and can no longer be deleted.",
        ) from exc


# --- admin: feature config ------------------------------------------------------


@admin_router.get(
    "/admin/standard-answer/config", response_model=StandardAnswerConfigResponse
)
def get_standard_answer_config(
    db_session: Session = Depends(get_tenant_session_dependency),
    _: User = Depends(current_admin_user),
) -> StandardAnswerConfigResponse:
    config = StandardAnswerService(db_session).get_config()
    return StandardAnswerConfigResponse(
        enabled=config.enabled,
        max_matches_per_message=config.max_matches_per_message,
        match_input_char_limit=config.match_input_char_limit,
    )


@admin_router.put(
    "/admin/standard-answer/config", response_model=StandardAnswerConfigResponse
)
def update_standard_answer_config(
    request: StandardAnswerConfigUpdateRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    user: User = Depends(current_admin_user),
) -> StandardAnswerConfigResponse:
    config = StandardAnswerService(db_session).update_config(
        enabled=request.enabled,
        max_matches_per_message=request.max_matches_per_message,
        match_input_char_limit=request.match_input_char_limit,
        actor_user_id=_actor_id(user),
    )
    return StandardAnswerConfigResponse(
        enabled=config.enabled,
        max_matches_per_message=config.max_matches_per_message,
        match_input_char_limit=config.match_input_char_limit,
    )


# --- stateless query endpoint ---------------------------------------------------


@query_router.get("/standard-answer", response_model=StandardAnswerQueryResponse)
def get_standard_answer(
    request: StandardAnswerQueryRequest,
    db_session: Session = Depends(get_tenant_session_dependency),
    _: User = Depends(current_user),
) -> StandardAnswerQueryResponse:
    """Stateless match: return active answers whose triggers fire on ``message``,
    scoped to the given category names. No Slack side effects, no chat records."""

    service = StandardAnswerService(db_session)
    matches = service.match_by_category_names(
        request.message, request.slack_bot_categories
    )
    return StandardAnswerQueryResponse(
        standard_answers=[StandardAnswerDTO.from_model(a) for a in matches]
    )
