"""User invitation / seat helpers for multi-tenant user management (clean-room).

These helpers back the admin user-management surface (`om.server.manage.users`) in
multi-tenant mode: inviting emails onto a tenant, removing them, and the read-only
counts/invitation lookups shown in ``/me``. They operate purely on the global
``user_tenant_mapping`` table (public schema) plus the per-tenant ``User`` table — there
is **no** billing, seat-cap, or control-plane coupling (all removed with the EE cloud
flow). This is the self-hosted, clean-room replacement for the old Onyx-EE cloud
tenants invitation / user-mapping helpers (that subsystem has been deleted).
"""

from __future__ import annotations

from om.configs.constants import ANONYMOUS_USER_EMAIL
from om.db.models import User
from om.db.models import UserTenantMapping
from om.server.manage.models import TenantSnapshot
from om.tenancy.context import get_shared_schema_session
from om.tenancy.context import get_tenant_session
from om.utils.logger import setup_logger

__all__ = [
    "invite_emails_to_tenant",
    "remove_emails_from_tenant",
    "get_tenant_invitation",
    "active_user_count_for_tenant",
]

logger = setup_logger()


def invite_emails_to_tenant(emails: list[str], tenant_id: str) -> None:
    """Idempotently map ``emails`` to ``tenant_id``.

    An email that already has an *active* mapping to a different tenant receives an
    **inactive** mapping (an invitation) here, which it can adopt on next login
    (``TenantMappingRepository.resolve_or_activate``); a genuinely new email is mapped
    active immediately. Emails that already have any mapping to this tenant are skipped.
    """
    unique_emails = {e.lower() for e in emails}
    if not unique_emails:
        return

    with get_shared_schema_session() as db_session:
        try:
            # Rows already mapped to THIS tenant — leave untouched.
            existing_here = (
                db_session.query(UserTenantMapping)
                .filter(
                    UserTenantMapping.email.in_(unique_emails),
                    UserTenantMapping.tenant_id == tenant_id,
                )
                .with_for_update()
                .all()
            )
            emails_with_mapping = {m.email for m in existing_here}

            # Emails already active in SOME tenant → new mapping is an invitation.
            active_elsewhere = (
                db_session.query(UserTenantMapping.email)
                .filter(
                    UserTenantMapping.email.in_(unique_emails),
                    UserTenantMapping.active.is_(True),
                )
                .all()
            )
            emails_active_somewhere = {e for (e,) in active_elsewhere}

            for email in unique_emails:
                if email in emails_with_mapping:
                    continue
                db_session.add(
                    UserTenantMapping(
                        email=email,
                        tenant_id=tenant_id,
                        active=email not in emails_active_somewhere,
                    )
                )

            db_session.commit()
            logger.info(f"Invited users {sorted(unique_emails)} to tenant {tenant_id}")
        except Exception:
            logger.exception(f"Failed to invite users to tenant {tenant_id}")
            db_session.rollback()
            raise


def remove_emails_from_tenant(emails: list[str], tenant_id: str) -> None:
    """Delete any mappings of ``emails`` to ``tenant_id`` (best-effort, never raises)."""
    lowered = [e.lower() for e in emails]
    if not lowered:
        return
    with get_shared_schema_session() as db_session:
        try:
            db_session.query(UserTenantMapping).filter(
                UserTenantMapping.email.in_(lowered),
                UserTenantMapping.tenant_id == tenant_id,
            ).delete(synchronize_session=False)
            db_session.commit()
        except Exception as e:
            logger.exception(
                f"Failed to remove users from tenant {tenant_id}: {str(e)}"
            )
            db_session.rollback()


def get_tenant_invitation(email: str) -> TenantSnapshot | None:
    """Return the first pending (inactive) tenant invitation for ``email``, if any."""
    email = email.lower()
    with get_shared_schema_session() as db_session:
        invitation = (
            db_session.query(UserTenantMapping)
            .filter(
                UserTenantMapping.email == email,
                UserTenantMapping.active.is_(False),
            )
            .first()
        )
        if invitation is None:
            return None

        user_count = (
            db_session.query(UserTenantMapping)
            .filter(
                UserTenantMapping.tenant_id == invitation.tenant_id,
                UserTenantMapping.active.is_(True),
            )
            .count()
        )
        return TenantSnapshot(
            tenant_id=invitation.tenant_id, number_of_users=user_count
        )


def active_user_count_for_tenant(tenant_id: str) -> int:
    """Number of real, active seats in a tenant.

    A seat counts when the email has an *active* mapping to the tenant (excluding the
    anonymous system user) **and** the corresponding ``User`` row inside the tenant's
    schema is active. The two-step lookup mirrors the isolation boundary: the mapping
    lives in the public schema, the ``User`` rows live inside the tenant schema.
    """
    with get_shared_schema_session() as db_session:
        active_mapping_emails = (
            db_session.query(UserTenantMapping.email)
            .filter(
                UserTenantMapping.tenant_id == tenant_id,
                UserTenantMapping.active.is_(True),
                UserTenantMapping.email != ANONYMOUS_USER_EMAIL,
            )
            .all()
        )
        emails = [e for (e,) in active_mapping_emails]

    if not emails:
        return 0

    with get_tenant_session(tenant_id=tenant_id) as db_session:
        return int(
            db_session.query(User)
            .filter(User.email.in_(emails), User.is_active.is_(True))
            .count()
        )
