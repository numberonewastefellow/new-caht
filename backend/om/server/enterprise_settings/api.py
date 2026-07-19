"""Custom-OAuth token refresh endpoint.

The enterprise-settings *settings* surface (branding / logo / custom analytics
script) has been replaced by ``om.server.app_settings`` (WS-H), which serves the
same ``/enterprise-settings`` paths consumed by the web app. SCIM token
management moved to ``om.server.scim.admin_api`` (WS-G). The only endpoint that
remains here is the custom-OAuth ``refresh-token`` flow, which is neither a
settings nor a SCIM concern.
"""

from datetime import datetime
from datetime import timezone
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from pydantic import Field

from om.auth.users import current_user_with_expired_token
from om.auth.users import get_user_manager
from om.auth.users import UserManager
from om.db.models import User
from om.utils.logger import setup_logger

basic_router = APIRouter(prefix="/enterprise-settings")

logger = setup_logger()


class RefreshTokenData(BaseModel):
    access_token: str
    refresh_token: str
    session: dict = Field(..., description="Contains session information")
    userinfo: dict = Field(..., description="Contains user information")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if "exp" not in self.session:
            raise ValueError("'exp' must be set in the session dictionary")
        if "userId" not in self.userinfo or "email" not in self.userinfo:
            raise ValueError(
                "'userId' and 'email' must be set in the userinfo dictionary"
            )


@basic_router.post("/refresh-token")
async def refresh_access_token(
    refresh_token: RefreshTokenData,
    user: User = Depends(current_user_with_expired_token),
    user_manager: UserManager = Depends(get_user_manager),
) -> None:
    try:
        logger.debug(f"Received response from Meechum auth URL for user {user.id}")

        # Extract new tokens
        new_access_token = refresh_token.access_token
        new_refresh_token = refresh_token.refresh_token

        new_expiry = datetime.fromtimestamp(
            refresh_token.session["exp"] / 1000, tz=timezone.utc
        )
        expires_at_timestamp = int(new_expiry.timestamp())

        logger.debug(f"Access token has been refreshed for user {user.id}")

        await user_manager.oauth_callback(
            oauth_name="custom",
            access_token=new_access_token,
            account_id=refresh_token.userinfo["userId"],
            account_email=refresh_token.userinfo["email"],
            expires_at=expires_at_timestamp,
            refresh_token=new_refresh_token,
            associate_by_email=True,
        )

        logger.info(f"Successfully refreshed tokens for user {user.id}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"Full authentication required for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Full authentication required",
            )
        logger.error(
            f"HTTP error occurred while refreshing token for user {user.id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error occurred while refreshing token for user {user.id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
