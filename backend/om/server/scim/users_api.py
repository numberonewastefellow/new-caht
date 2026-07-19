"""SCIM ``/Users`` endpoints (RFC 7644 §3.3–§3.6).

All routes are guarded by ``verify_scim_token`` (bearer auth + tenant binding);
``auth_check.check_router_auth`` recognises that dependency. Responses are
``application/scim+json`` and errors are rendered by :class:`ScimRoute`.

Routes are synchronous ``def`` — FastAPI runs them in a threadpool, so the
blocking SQLAlchemy calls in the service layer never block the event loop. Bodies
are declared as Pydantic params; FastAPI parses ``application/scim+json`` and a
malformed body raises ``RequestValidationError`` which :class:`ScimRoute` renders
as a SCIM ``400 invalidSyntax``.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi.responses import JSONResponse

from om.server.scim.auth import ScimContext
from om.server.scim.auth import verify_scim_token
from om.server.scim.errors import ScimRoute
from om.server.scim.resources import ScimPatchOp
from om.server.scim.resources import ScimUserResource
from om.server.scim.responses import base_url
from om.server.scim.responses import scim_json
from om.server.scim.service import ScimUserService

users_router = APIRouter(prefix="/Users", route_class=ScimRoute)


def _service(ctx: ScimContext, request: Request) -> ScimUserService:
    return ScimUserService(
        ctx.db, actor_user_id=ctx.actor_user_id, base_url=base_url(request)
    )


@users_router.post("")
def create_user(
    resource: ScimUserResource,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).create(resource), status_code=201)


@users_router.get("")
def list_users(
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
    filter: str | None = Query(default=None),
    startIndex: int = Query(default=1),
    count: int | None = Query(default=None),
) -> JSONResponse:
    result = _service(ctx, request).list_users(
        filter_str=filter, start_index=startIndex, count=count
    )
    return scim_json(result)


@users_router.get("/{user_id}")
def get_user(
    user_id: str,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).get(user_id))


@users_router.put("/{user_id}")
def replace_user(
    user_id: str,
    resource: ScimUserResource,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).replace(user_id, resource))


@users_router.patch("/{user_id}")
def patch_user(
    user_id: str,
    patch: ScimPatchOp,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).patch(user_id, patch.operations))


@users_router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> Response:
    _service(ctx, request).deprovision(user_id)
    return Response(status_code=204)
