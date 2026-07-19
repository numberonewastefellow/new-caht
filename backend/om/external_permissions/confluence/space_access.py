"""Resolve a Confluence space's view permissions into an :class:`ExternalAccess`.

Confluence exposes space permissions differently on Cloud vs Server/Data-Center,
so each has its own reader; both collapse to the same shape — the set of allowed
user emails, the set of allowed group names, and whether the space is anonymously
public. WS-B clean-room rewrite (public entrypoints preserved).
"""

from typing import Any

from om.access.models import ExternalAccess
from om.access.utils import build_ext_team_name_for_om
from om.configs.app_configs import CONFLUENCE_ANONYMOUS_ACCESS_IS_PUBLIC
from om.configs.constants import DocumentSource
from om.connectors.confluence.onyx_confluence import (
    get_user_email_from_username__server,
)
from om.connectors.confluence.onyx_confluence import OmConfluence
from om.external_permissions.confluence.constants import ALL_CONF_EMAILS_GROUP_NAME
from om.external_permissions.confluence.constants import REQUEST_PAGINATION_LIMIT
from om.external_permissions.confluence.constants import VIEWSPACE_PERMISSION_TYPE
from om.utils.logger import setup_logger

logger = setup_logger()


def _resolve_server_emails(
    confluence_client: OmConfluence, usernames: set[str]
) -> set[str]:
    """Map Server usernames to emails, skipping any that can't be resolved."""
    emails: set[str] = set()
    for username in usernames:
        email = get_user_email_from_username__server(confluence_client, username)
        if email:
            emails.add(email)
        else:
            logger.warning(f"Email for user {username} not found in Confluence")
    return emails


def _get_server_space_permissions(
    confluence_client: OmConfluence, space_key: str
) -> ExternalAccess:
    raw_categories = confluence_client.get_all_space_permissions_server(
        space_key=space_key
    )

    # Only the "view space" grants determine who can read the space.
    view_grants: list[dict[str, Any]] = []
    for category in raw_categories:
        if category.get("type") == VIEWSPACE_PERMISSION_TYPE:
            view_grants.extend(category.get("spacePermissions", []))

    usernames: set[str] = set()
    group_names: set[str] = set()
    is_public = False
    for grant in view_grants:
        username = grant.get("userName")
        group_name = grant.get("groupName")
        if username:
            usernames.add(username)
        if group_name:
            group_names.add(group_name)
        # A grant naming neither a user nor a group is an anonymous-access grant.
        # Server can't be probed for this behind a paywall, so it is opt-in:
        # either treat the space as public, or fold in the "all Confluence users"
        # pseudo-group so every known user still matches.
        if username is None and group_name is None:
            if CONFLUENCE_ANONYMOUS_ACCESS_IS_PUBLIC:
                is_public = True
            else:
                group_names.add(ALL_CONF_EMAILS_GROUP_NAME)

    user_emails = _resolve_server_emails(confluence_client, usernames)

    if not user_emails and not group_names:
        logger.warning(
            "No user emails or group names found in Confluence space permissions"
            f"\nSpace key: {space_key}\nSpace permissions: {raw_categories}"
        )

    return ExternalAccess(
        external_user_emails=user_emails,
        external_team_ids=group_names,
        is_public=is_public,
    )


def _first_result_field(subjects: dict[str, Any], subject_type: str, field: str) -> Any:
    """Pull ``subjects[subject_type].results[0][field]`` defensively."""
    results = subjects.get(subject_type, {}).get("results") or [{}]
    return results[0].get(field)


def _get_cloud_space_permissions(
    confluence_client: OmConfluence, space_key: str
) -> ExternalAccess:
    space = confluence_client.get_space(space_key=space_key, expand="permissions")
    grants = space.get("permissions", [])

    user_emails: set[str] = set()
    group_names: set[str] = set()
    is_public = False
    for grant in grants:
        subjects = grant.get("subjects")
        if subjects:
            # Explicit user/group grant.
            email = _first_result_field(subjects, "user", "email")
            if email:
                user_emails.add(email)
            group_name = _first_result_field(subjects, "group", "name")
            if group_name:
                group_names.add(group_name)
        elif (
            grant.get("operation", {}).get("operation") == "read"
            and grant.get("anonymousAccess", False)
        ):
            # A subject-less read grant with anonymous access => publicly readable.
            is_public = True

    return ExternalAccess(
        external_user_emails=user_emails,
        external_team_ids=group_names,
        is_public=is_public,
    )


def _prefix_groups(access: ExternalAccess) -> ExternalAccess:
    """Namespace the raw group names by source (indexing path only)."""
    return ExternalAccess(
        external_user_emails=access.external_user_emails,
        external_team_ids={
            build_ext_team_name_for_om(group, DocumentSource.CONFLUENCE)
            for group in access.external_team_ids
        },
        is_public=access.is_public,
    )


def get_space_permission(
    confluence_client: OmConfluence,
    space_key: str,
    is_cloud: bool,
    add_prefix: bool = False,
) -> ExternalAccess:
    reader = _get_cloud_space_permissions if is_cloud else _get_server_space_permissions
    access = reader(confluence_client, space_key)

    if not access.is_public and not access.external_user_emails and not access.external_team_ids:
        logger.warning(
            f"No permissions found for space '{space_key}'. This is very unlikely "
            "to be correct and usually means the access token lacks Admin "
            f"permissions for space '{space_key}'."
        )

    if add_prefix and access.external_team_ids:
        return _prefix_groups(access)
    return access


def get_all_space_permissions(
    confluence_client: OmConfluence,
    is_cloud: bool,
    add_prefix: bool = False,
) -> dict[str, ExternalAccess]:
    """Per-space :class:`ExternalAccess` for every space in the instance.

    ``add_prefix``: True on the indexing path (namespace group ids per source);
    False on the permission-sync path (leave raw).
    """
    space_keys = [
        key
        for space in confluence_client.retrieve_confluence_spaces(
            limit=REQUEST_PAGINATION_LIMIT
        )
        if (key := space.get("key"))
    ]
    logger.debug(f"Resolving permissions for {len(space_keys)} Confluence spaces")

    return {
        space_key: get_space_permission(
            confluence_client, space_key, is_cloud, add_prefix
        )
        for space_key in space_keys
    }
