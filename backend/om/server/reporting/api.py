"""Admin usage-reporting API (clean-room rewrite).

Generate a usage report (synchronously), list generated reports, and download the
CSV. All endpoints are admin-gated and tenant-scoped via ``get_session``.
"""

from http import HTTPStatus

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.reporting.models import GenerateReportRequest
from om.server.reporting.models import UsageReportSchema
from om.server.reporting.service import log_report_downloaded
from om.server.reporting.service import UsageReportService

router = APIRouter(prefix="/admin/reports")


@router.post("/usage")
def generate_usage_report(
    body: GenerateReportRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> UsageReportSchema:
    if (
        body.period_from is not None
        and body.period_to is not None
        and body.period_from >= body.period_to
    ):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST,
            "period_from must be strictly before period_to.",
        )
    return UsageReportService(db_session).generate(
        requestor_user_id=user.id,
        period_from=body.period_from,
        period_to=body.period_to,
    )


@router.get("/usage")
def list_usage_reports(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[UsageReportSchema]:
    return UsageReportService(db_session).list_reports()


@router.get("/usage/{report_id}/download")
def download_usage_report(
    report_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> StreamingResponse:
    service = UsageReportService(db_session)
    try:
        filename, handle = service.get_report_file(report_id)
    except ValueError as exc:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(exc))

    log_report_downloaded(report_id=report_id, actor_user_id=str(user.id))
    return StreamingResponse(
        service.iter_file(handle),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
