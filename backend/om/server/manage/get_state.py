import concurrent.futures
import re

import requests
from fastapi import APIRouter

from om import __version__
from om.auth.users import anonymous_user_enabled
from om.auth.users import user_needs_to_be_verified
from om.configs.app_configs import AUTH_TYPE
from om.configs.app_configs import OAUTH_ENABLED
from om.configs.app_configs import PASSWORD_MIN_LENGTH
from om.configs.constants import AuthType
from om.configs.constants import DEV_VERSION_PATTERN
from om.configs.constants import PUBLIC_API_TAGS
from om.configs.constants import STABLE_VERSION_PATTERN
from om.db.auth import get_user_count
from om.server.manage.models import AllVersions
from om.server.manage.models import AuthTypeResponse
from om.server.manage.models import ContainerVersions
from om.server.manage.models import VersionResponse
from om.server.models import StatusResponse

router = APIRouter()


@router.get("/heartbeat", tags=PUBLIC_API_TAGS)
async def healthcheck() -> StatusResponse:
    return StatusResponse(success=True, message="ok")


@router.get("/auth/type", tags=PUBLIC_API_TAGS)
async def get_auth_type() -> AuthTypeResponse:
    # NOTE: This endpoint is critical for the multi-tenant flow and is hit before there is a tenant context
    # The reason is this is used during the login flow, but we don't know which tenant the user is supposed to be
    # associated with until they auth.
    has_users = True
    if AUTH_TYPE != AuthType.CLOUD:
        user_count = await get_user_count()
        has_users = user_count > 0

    return AuthTypeResponse(
        auth_type=AUTH_TYPE,
        requires_verification=user_needs_to_be_verified(),
        anonymous_user_enabled=anonymous_user_enabled(),
        password_min_length=PASSWORD_MIN_LENGTH,
        has_users=has_users,
        oauth_enabled=OAUTH_ENABLED,
    )


@router.get("/version", tags=PUBLIC_API_TAGS)
def get_version() -> VersionResponse:
    return VersionResponse(backend_version=__version__)


@router.get("/versions", tags=PUBLIC_API_TAGS)
def get_versions() -> AllVersions:
    """
    Fetches the latest stable and beta versions of Onyx Docker images.
    Since DockerHub does not explicitly flag stable and beta images,
    this endpoint can be used to programmatically check for new images.
    """
    # Fetch the latest tags from DockerHub for each image component.
    dockerhub_repos = [
        "om/om-model-server",
        "om/om-backend",
        "om/om-web-server",
    ]

    # For good measure, we fetch 10 pages of tags.
    # Fault-tolerant: if the registry is unreachable or the repo is unpublished
    # (e.g. this fork does not push public images), return whatever we collected
    # (usually nothing) instead of raising -- the caller falls back to __version__.
    def get_dockerhub_tags(repo: str, pages: int = 10) -> list[str]:
        url: str | None = f"https://hub.docker.com/v2/repositories/{repo}/tags"
        tags: list[str] = []
        for _ in range(pages):
            if not url:
                break
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError):
                break
            tags.extend(
                [
                    tag["name"]
                    for tag in data.get("results", [])
                    if re.match(r"^v\d", tag["name"])
                ]
            )
            url = data.get("next")
        return tags

    # Get tags for all repos in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_tags = list(
            executor.map(lambda repo: set(get_dockerhub_tags(repo)), dockerhub_repos)
        )

    # Find common tags across all repos
    common_tags = set.intersection(*all_tags)

    # Filter tags by strict version patterns
    dev_tags = [tag for tag in common_tags if DEV_VERSION_PATTERN.match(tag)]
    stable_tags = [tag for tag in common_tags if STABLE_VERSION_PATTERN.match(tag)]

    # Sort common tags and get the latest one
    def version_key(version: str) -> tuple[int, int, int, int]:
        """Extract major, minor, patch, beta as integers for sorting"""
        # Remove 'v' prefix
        clean_version = version[1:]

        # Check if it's a beta version
        if "-beta." in clean_version:
            # Split on '-beta.' to separate version and beta number
            base_version, beta_num = clean_version.split("-beta.")
            parts = base_version.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]), int(beta_num))
        else:
            # Stable version - no beta number
            parts = clean_version.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]), 0)

    # Fall back to the running version when no published tags were found (e.g. the
    # registry was unreachable or this fork does not publish public images) so the
    # endpoint degrades to a 200 with the current version instead of failing.
    latest_dev_version = (
        sorted(dev_tags, key=version_key, reverse=True)[0] if dev_tags else __version__
    )
    latest_stable_version = (
        sorted(stable_tags, key=version_key, reverse=True)[0]
        if stable_tags
        else __version__
    )

    return AllVersions(
        stable=ContainerVersions(
            onyx=latest_stable_version,
            relational_db="postgres:15.2-alpine",
            index="vespaengine/vespa:8.277.17",
            nginx="nginx:1.25.5-alpine",
        ),
        dev=ContainerVersions(
            onyx=latest_dev_version,
            relational_db="postgres:15.2-alpine",
            index="vespaengine/vespa:8.277.17",
            nginx="nginx:1.25.5-alpine",
        ),
        migration=ContainerVersions(
            onyx="airgapped-intfloat-nomic-migration",
            relational_db="postgres:15.2-alpine",
            index="vespaengine/vespa:8.277.17",
            nginx="nginx:1.25.5-alpine",
        ),
    )
