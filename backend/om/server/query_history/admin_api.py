"""Admin query-history API (clean-room rewrite).

Lists past chat sessions, shows a full session, and streams a CSV export of
question/answer pairs. All endpoints are admin-gated and tenant-scoped via the
``get_session`` dependency. CSV export streams synchronously (paged internally),
so there is no Celery task or file-store round-trip.
"""

import datetime
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.configs.constants import QAFeedbackType
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.analytics.structured_logging import log_structured_event
from om.server.query_history.schemas import ChatSessionDetail
from om.server.query_history.schemas import PaginatedSessions
from om.server.query_history.service import QueryHistoryService
from om.server.query_history.service import stream_query_history_csv
from shared_configs.contextvars import get_current_tenant_id

router = APIRouter(prefix="/admin/query-history")


@router.get("/sessions")
def list_sessions(
    page_num: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=200),
    feedback_type: QAFeedbackType | None = None,
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> PaginatedSessions:
    return QueryHistoryService(db_session).list_sessions(
        page_num=page_num,
        page_size=page_size,
        feedback=feedback_type,
        start=start_time,
        end=end_time,
    )


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: UUID,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> ChatSessionDetail:
    detail = QueryHistoryService(db_session).get_detail(session_id)
    if detail is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Chat session '{session_id}' does not exist.",
        )
    return detail


@router.get("/export")
def export_csv(
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    user: User = Depends(current_admin_user),
) -> StreamingResponse:
    # Capture the tenant id inside the request context; the streaming body runs
    # after the handler returns and opens its own tenant-bound session (see
    # stream_query_history_csv) rather than relying on the request session.
    tenant_id = get_current_tenant_id()
    filename = (
        "query_history_"
        f"{datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    )
    log_structured_event(
        event="report_exported",
        entity="query_history",
        action="export",
        actor_user_id=str(user.id),
        filename=filename,
    )
    return StreamingResponse(
        stream_query_history_csv(tenant_id, start_time, end_time),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
