"""Constants for release notes functionality."""

import os

# Raw changelog (mdx) to fetch release notes from. Empty (default) disables
# the feature: no outbound request is made and no notifications are created.
RELEASE_NOTES_CHANGELOG_URL = os.environ.get("OM_RELEASE_NOTES_CHANGELOG_URL", "")

# Base URL for changelog documentation (used for notification links)
DOCS_CHANGELOG_BASE_URL = os.environ.get("OM_DOCS_CHANGELOG_URL", "")

FETCH_TIMEOUT = 60.0

# Redis keys (in shared namespace)
REDIS_KEY_PREFIX = "release_notes:"
REDIS_KEY_FETCHED_AT = f"{REDIS_KEY_PREFIX}fetched_at"
REDIS_KEY_ETAG = f"{REDIS_KEY_PREFIX}etag"

# Cache TTL: 24 hours
REDIS_CACHE_TTL = 60 * 60 * 24

# Auto-refresh threshold: 1 hour
AUTO_REFRESH_THRESHOLD_SECONDS = 60 * 60
