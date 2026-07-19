"""Billing-free, on-demand tenant provisioning (clean-room).

This replaces the Onyx-EE cloud provisioning flow. Everything that reached an external
control plane has been removed — there is **no** Stripe, HubSpot, data-plane token
exchange, control-plane notification, or ``available_tenant`` pre-provision pool. A tenant
is created **synchronously, on demand**, entirely against the local Postgres instance.

A tenant lifecycle here is just three local steps (plus its inverse):

1. ``create_tenant_schema`` — a dedicated Postgres schema (the isolation boundary).
2. ``run_migrations_for_schema`` — the full Alembic chain inside that schema (the baseline
   also seeds the built-in tools / default assistant / search settings).
3. ``setup_onyx`` — per-tenant runtime setup (document index, etc.).
4. ``TenantMappingRepository.assign`` — record the email→tenant login route (public schema).

The public entry point used by the auth layer is :func:`get_or_provision_tenant`; the
tenant-admin API uses :func:`provision_tenant` / :func:`deprovision_tenant` via
:class:`om.tenancy.service.TenantService`.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from om.tenancy.config import MULTI_TENANT
from om.tenancy.config import POSTGRES_DEFAULT_SCHEMA
from om.tenancy.context import get_shared_schema_session
from om.tenancy.context import get_tenant_session
from om.tenancy.events import EVENT_TENANT_CREATED
from om.tenancy.events import EVENT_TENANT_DELETED
from om.tenancy.events import tenant_operation
from om.tenancy.migrations import create_tenant_schema
from om.tenancy.migrations import drop_tenant_schema
from om.tenancy.migrations import run_migrations_for_schema
from om.tenancy.repository import TenantMappingRepository
from om.tenancy.schema import assert_tenant_id
from om.tenancy.schema import new_tenant_id
from om.utils.logger import setup_logger

__all__ = [
    "provision_tenant",
    "get_or_provision_tenant",
    "get_login_tenant_id",
    "deprovision_tenant",
]

logger = setup_logger()


def _seed_default_setup(tenant_id: str) -> None:
    """Run per-tenant runtime setup inside the freshly-migrated tenant schema.

    The baseline migration already seeds the built-in tools, default assistant and search
    settings; this wires up the tenant's document index and any swap bookkeeping. Imported
    lazily so importing this module never drags in the heavy setup dependency graph.
    """
    from om.setup import setup_onyx

    with get_tenant_session(tenant_id=tenant_id) as db_session:
        setup_onyx(db_session, tenant_id)


def provision_tenant(*, admin_email: str, actor_user_id: str | None = None) -> str:
    """Create a brand-new tenant and route ``admin_email`` to it. Returns the tenant id.

    Fully local and idempotent-safe: if any step fails the half-built schema is dropped so
    a retry starts clean. Emits a structured ``tenant.created`` event (Standard 9).
    """
    tenant_id = new_tenant_id()
    with tenant_operation(
        event=EVENT_TENANT_CREATED,
        entity_id=tenant_id,
        action="create",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        admin_email=admin_email,
    ):
        create_tenant_schema(tenant_id)
        try:
            run_migrations_for_schema(tenant_id)
            _seed_default_setup(tenant_id)
            TenantMappingRepository.assign(admin_email, tenant_id, active=True)
        except Exception:
            # Roll back the partially-provisioned schema so we never leave orphans.
            logger.exception(
                f"Provisioning failed for {tenant_id}; rolling back schema"
            )
            drop_tenant_schema(tenant_id)
            raise
    return tenant_id


def _provision_on_demand(email: str) -> str:
    """Serialize concurrent first-logins for one email behind a Postgres advisory lock.

    Two requests for the same never-seen email could otherwise each provision a tenant. A
    transaction-scoped advisory lock (keyed on the email) makes the loser re-read the
    mapping the winner just wrote instead of provisioning a duplicate.
    """
    with get_shared_schema_session() as lock_session:
        lock_session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:email))"),
            {"email": email.lower()},
        )
        existing = TenantMappingRepository.resolve_or_activate(email)
        if existing:
            return existing
        return provision_tenant(admin_email=email)


async def get_or_provision_tenant(
    *,
    email: str,
    referral_source: str | None = None,  # noqa: ARG001 — see note below
    request: object | None = None,  # noqa: ARG001 — see note below
) -> str:
    """Resolve the tenant for ``email`` at login, provisioning one on first sight.

    Awaitable because the auth layer calls it from async code; the blocking DDL/migration
    work runs in a worker thread so the event loop is never stalled.

    ``referral_source`` / ``request`` are accepted only for source-compatibility with the
    auth call sites: in the old EE flow they fed HubSpot / marketing attribution, which has
    been removed. They are intentionally ignored here (no external calls remain).
    """
    if not MULTI_TENANT:
        return POSTGRES_DEFAULT_SCHEMA

    # Existing (or invited) users route to their tenant; only genuinely new emails
    # fall through to on-demand provisioning.
    existing = TenantMappingRepository.resolve_or_activate(email)
    if existing:
        return existing

    return await asyncio.to_thread(_provision_on_demand, email)


def get_login_tenant_id(email: str) -> str | None:
    """Resolve the tenant an email should authenticate into — **without** provisioning.

    Used by the login/authenticate path (which must never create a tenant as a side effect
    of a login attempt). Mirrors the isolation guarantees of the old EE
    ``get_tenant_id_for_email`` so the auth flow can drop the EE dependency:

    * self-hosted (``not MULTI_TENANT``): always the default schema — there is exactly one
      tenant and every user authenticates into it;
    * multi-tenant: the email's active mapping, else an inactive invitation (which is
      activated on first login), else ``None`` for an unknown email.

    Returns ``None`` (never raises) when the email has no mapping, so the caller can treat
    it as an authentication failure.
    """
    if not MULTI_TENANT:
        return POSTGRES_DEFAULT_SCHEMA
    return TenantMappingRepository.resolve_or_activate(email)


def deprovision_tenant(*, tenant_id: str, actor_user_id: str | None = None) -> None:
    """Permanently remove a tenant: drop its schema and every mapping row.

    Strictly validates the id first so this can never target ``public``. Emits a structured
    ``tenant.deleted`` event.
    """
    assert_tenant_id(tenant_id)
    with tenant_operation(
        event=EVENT_TENANT_DELETED,
        entity_id=tenant_id,
        action="delete",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
    ):
        TenantMappingRepository.remove_all_for_tenant(tenant_id)
        drop_tenant_schema(tenant_id)
