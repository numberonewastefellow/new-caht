"""Constants for license enforcement.

This file is the single source of truth for:
1. Paths that bypass license enforcement (always accessible)
2. Paths that require an EE license (EE-only features)

Import these constants in both production code and tests to ensure consistency.
"""

# Paths that are ALWAYS accessible, even when license is expired/gated.
# These enable users to:
#   /auth - Log in/out (users can't fix billing if locked out of auth)
#   /license - Fetch, upload, or check license status
#   /heartbeat - Health checks for load balancers/orchestrators
#   /me - Basic user info needed for UI rendering
#   /settings, /enterprise-settings - View app status and branding
#   /billing - Unified billing API
#   /proxy - Self-hosted proxy endpoints (have own license-based auth)
#   /tenants/billing-* - Legacy billing endpoints (backwards compatibility)
#   /nexus/users, /users - User management (needed for seat limit resolution)
#   /signals - Needed for UI to load properly
LICENSE_ENFORCEMENT_ALLOWED_PREFIXES: frozenset[str] = frozenset(
    {
        "/auth",
        "/license",
        "/heartbeat",
        "/me",
        "/settings",
        "/enterprise-settings",
        # Billing endpoints (unified API for both MT and self-hosted)
        "/billing",
        "/admin/billing",
        # Proxy endpoints for self-hosted billing (no tenant context)
        "/proxy",
        # Legacy tenant billing endpoints (kept for backwards compatibility)
        "/tenants/billing-information",
        "/tenants/create-customer-portal-session",
        "/tenants/create-subscription-session",
        # User management - needed to remove users when seat limit exceeded
        "/nexus/users",
        "/nexus/admin/users",
        "/nexus/admin/valid-domains",
        "/nexus/admin/deactivate-user",
        "/nexus/admin/delete-user",
        "/users",
        # Notifications - needed for UI to load properly
        "/signals",
    }
)

# EE-only paths that require a valid license.
# Users without a license (community edition) cannot access these.
# These are blocked even when user has never subscribed (no license).
EE_ONLY_PATH_PREFIXES: frozenset[str] = frozenset(
    {
        # User groups and access control
        "/nexus/admin/user-group",
        # Analytics and reporting
        "/analytics",
        # Query history (admin chat session endpoints)
        "/admin/chat-sessions",
        "/admin/chat-session-history",
        "/admin/query-history",
        # Usage reporting/export
        "/admin/usage-report",
        # Standard answers (canned responses)
        "/nexus/admin/standard-answer",
        # Token rate limits
        "/admin/token-rate-limits",
        # Evals
        "/evals",
    }
)
