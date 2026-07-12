from collections.abc import Callable
from typing import Any
from typing import cast

from om.access.models import ExternalAccess
from om.connectors.confluence.onyx_confluence import OmConfluence


def get_page_restrictions(
    confluence_client: OmConfluence,
    page_id: str,
    page_restrictions: dict[str, Any],
    ancestors: list[dict[str, Any]],
) -> ExternalAccess | None:
    """
    Get page access restrictions for a Confluence page.
    This functionality requires Enterprise Edition.

    Note: This wrapper is only called from permission sync path. Group IDs are
    left unprefixed here because upsert_document_external_perms handles prefixing.

    Args:
        confluence_client: OnyxConfluence client instance
        page_id: The ID of the page
        page_restrictions: Dictionary containing page restriction data
        ancestors: List of ancestor pages with their restriction data

    Returns:
        ExternalAccess object for the page. None if EE is not enabled or no restrictions found.
    """
    # Check if EE is enabled
    from om.external_permissions.confluence.page_access import get_page_restrictions as _impl_get_page_restrictions

    # Fetch the EE implementation
    ee_get_all_page_restrictions = cast(
        Callable[
            [OmConfluence, str, dict[str, Any], list[dict[str, Any]], bool],
            ExternalAccess | None,
        ],
        _impl_get_page_restrictions,
    )

    # add_prefix=False: permission sync path - upsert_document_external_perms handles prefixing
    return ee_get_all_page_restrictions(
        confluence_client, page_id, page_restrictions, ancestors, False
    )


def get_all_space_permissions(
    confluence_client: OmConfluence,
    is_cloud: bool,
) -> dict[str, ExternalAccess]:
    """
    Get access permissions for all spaces in Confluence.
    This functionality requires Enterprise Edition.

    Note: This wrapper is only called from permission sync path. Group IDs are
    left unprefixed here because upsert_document_external_perms handles prefixing.

    Args:
        confluence_client: OnyxConfluence client instance
        is_cloud: Whether this is a Confluence Cloud instance

    Returns:
        Dictionary mapping space keys to ExternalAccess objects. Empty dict if EE is not enabled.
    """
    # Check if EE is enabled
    from om.external_permissions.confluence.space_access import get_all_space_permissions as _impl_get_all_space_permissions

    # Fetch the EE implementation
    ee_get_all_space_permissions = cast(
        Callable[
            [OmConfluence, bool, bool],
            dict[str, ExternalAccess],
        ],
        _impl_get_all_space_permissions,
    )

    # add_prefix=False: permission sync path - upsert_document_external_perms handles prefixing
    return ee_get_all_space_permissions(confluence_client, is_cloud, False)
