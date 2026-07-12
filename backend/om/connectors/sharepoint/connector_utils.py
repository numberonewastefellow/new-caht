from typing import Any

from office365.graph_client import GraphClient  # type: ignore[import-untyped]
from office365.onedrive.driveitems.driveItem import DriveItem  # type: ignore[import-untyped]
from office365.sharepoint.client_context import ClientContext  # type: ignore[import-untyped]

from om.connectors.models import ExternalAccess


def get_sharepoint_external_access(
    ctx: ClientContext,
    graph_client: GraphClient,
    drive_item: DriveItem | None = None,
    drive_name: str | None = None,
    site_page: dict[str, Any] | None = None,
    add_prefix: bool = False,
) -> ExternalAccess:
    from om.external_permissions.sharepoint.permission_utils import (
        get_external_access_from_sharepoint as _impl_get_external_access_from_sharepoint,
    )
    if drive_item and drive_item.id is None:
        raise ValueError("DriveItem ID is required")

    # Get external access using the EE implementation
    def noop_fallback(*args: Any, **kwargs: Any) -> ExternalAccess:  # noqa: ARG001
        return ExternalAccess.empty()

    get_external_access_func = _impl_get_external_access_from_sharepoint

    external_access = get_external_access_func(
        ctx, graph_client, drive_name, drive_item, site_page, add_prefix
    )

    return external_access
