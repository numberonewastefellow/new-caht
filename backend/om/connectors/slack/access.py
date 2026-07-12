from collections.abc import Callable
from typing import cast

from slack_sdk import WebClient

from om.access.models import ExternalAccess
from om.connectors.models import BasicExpertInfo
from om.connectors.slack.models import ChannelType


def get_channel_access(
    client: WebClient,
    channel: ChannelType,
    user_cache: dict[str, BasicExpertInfo | None],
) -> ExternalAccess | None:
    """
    Get channel access permissions for a Slack channel.
    This functionality requires Enterprise Edition.

    Args:
        client: Slack WebClient instance
        channel: Slack channel object containing channel info
        user_cache: Cache of user IDs to BasicExpertInfo objects. May be updated in place.

    Returns:
        ExternalAccess object for the channel. None if EE is not enabled.
    """
    # Check if EE is enabled
    from om.external_permissions.slack.channel_access import get_channel_access as _impl_get_channel_access

    # Fetch the EE implementation
    ee_get_channel_access = cast(
        Callable[
            [WebClient, ChannelType, dict[str, BasicExpertInfo | None]],
            ExternalAccess,
        ],
        _impl_get_channel_access,
    )

    return ee_get_channel_access(client, channel, user_cache)
