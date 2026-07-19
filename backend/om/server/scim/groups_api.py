"""SCIM ``/Groups`` endpoints (RFC 7644), mapped to internal Teams (Contract 1).

Guarded by ``verify_scim_token``. Group ``PATCH`` returns ``204 No Content`` (per
Microsoft Entra's documented preference not to echo the member list); ``POST``,
``GET`` and ``PUT`` return the resource as ``application/scim+json``. Reads honor
``excludedAttributes=members`` (Entra sends it on Group queries). Routes are
synchronous so blocking DB work runs in a threadpool, not the event loop.
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
from om.server.scim.resources import ScimGroupResource
from om.server.scim.resources import ScimPatchOp
from om.server.scim.responses import base_url
from om.server.scim.responses import scim_json
from om.server.scim.service import ScimGroupService

groups_router = APIRouter(prefix="/Groups", route_class=ScimRoute)


def _service(ctx: ScimContext, request: Request) -> ScimGroupService:
    return ScimGroupService(
        ctx.db, actor_user_id=ctx.actor_user_id, base_url=base_url(request)
    )


@groups_router.post("")
def create_group(
    resource: ScimGroupResource,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).create(resource), status_code=201)


@groups_router.get("")
def list_groups(
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
    filter: str | None = Query(default=None),
    startIndex: int = Query(default=1),
    count: int | None = Query(default=None),
    excludedAttributes: str | None = Query(default=None),
) -> JSONResponse:
    result = _service(ctx, request).list_groups(
        filter_str=filter,
        start_index=startIndex,
        count=count,
        excluded_attributes=excludedAttributes,
    )
    return scim_json(result)


@groups_router.get("/{group_id}")
def get_group(
    group_id: str,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
    excludedAttributes: str | None = Query(default=None),
) -> JSONResponse:
    return scim_json(
        _service(ctx, request).get(group_id, excluded_attributes=excludedAttributes)
    )


@groups_router.put("/{group_id}")
def replace_group(
    group_id: str,
    resource: ScimGroupResource,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> JSONResponse:
    return scim_json(_service(ctx, request).replace(group_id, resource))


@groups_router.patch("/{group_id}", status_code=204)
def patch_group(
    group_id: str,
    patch: ScimPatchOp,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> Response:
    _service(ctx, request).patch(group_id, patch.operations)
    return Response(status_code=204)


@groups_router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: str,
    request: Request,
    ctx: ScimContext = Depends(verify_scim_token),
) -> Response:
    _service(ctx, request).delete(group_id)
    return Response(status_code=204)
