"""Data access for the global ``user_tenant_mapping`` table (email -> tenant routing).

This is the ONE table that lives in the ``public`` schema, so every method here uses the
shared-schema session. The ORM model (``UserTenantMapping``) is defined in the shared
``om.db.models`` module; this repository is the only place that should touch it for
tenant-administration flows.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from om.db.models import User
from om.db.models import UserTenantMapping
from om.tenancy.context import get_shared_schema_session
from om.tenancy.context import get_tenant_session
from om.utils.logger import setup_logger

logger = setup_logger()


class TenantMappingRepository:
    """Repository over the global email->tenant mapping table."""

    @staticmethod
    def get_active_tenant_for_email(email: str) -> str | None:
        """Return the tenant the email is actively bound to, if any."""
        email = email.lower()
        with get_shared_schema_session() as db:
            row = db.execute(
                select(UserTenantMapping.tenant_id).where(
                    UserTenantMapping.email == email,
                    UserTenantMapping.active.is_(True),
                )
            ).first()
            return row[0] if row else None

    @staticmethod
    def resolve_or_activate(email: str) -> str | None:
        """Login routing: return the active tenant, else adopt an invitation.

        If the email has an active mapping, return its tenant. Otherwise, if it has an
        inactive mapping (an invitation created by an admin/assignment), activate the first
        one and return it — so an invited user logs into the tenant they were invited to
        instead of having a brand-new tenant provisioned for them. Returns ``None`` only
        when the email has no mapping at all (a genuinely new user → provision on demand).
        """
        email = email.lower()
        with get_shared_schema_session() as db:
            active = db.execute(
                select(UserTenantMapping.tenant_id).where(
                    UserTenantMapping.email == email,
                    UserTenantMapping.active.is_(True),
                )
            ).first()
            if active is not None:
                return active[0]

            invitation = db.execute(
                select(UserTenantMapping)
                .where(
                    UserTenantMapping.email == email,
                    UserTenantMapping.active.is_(False),
                )
                .with_for_update()
            ).scalars().first()
            if invitation is not None:
                invitation.active = True
                db.commit()
                return invitation.tenant_id
        return None

    @staticmethod
    def email_has_any_mapping(email: str) -> bool:
        email = email.lower()
        with get_shared_schema_session() as db:
            row = db.execute(
                select(UserTenantMapping.tenant_id)
                .where(UserTenantMapping.email == email)
                .limit(1)
            ).first()
            return row is not None

    @staticmethod
    def list_tenant_ids() -> list[str]:
        """Distinct tenant ids that appear in the mapping table."""
        with get_shared_schema_session() as db:
            rows = db.execute(
                select(UserTenantMapping.tenant_id)
                .distinct()
                .order_by(UserTenantMapping.tenant_id)
            ).all()
            return [r[0] for r in rows]

    @staticmethod
    def user_counts_by_tenant() -> dict[str, tuple[int, int]]:
        """Map tenant_id -> (active_count, total_count)."""
        with get_shared_schema_session() as db:
            total_rows = db.execute(
                select(
                    UserTenantMapping.tenant_id,
                    func.count(),  # total
                    func.count().filter(UserTenantMapping.active.is_(True)),  # active
                ).group_by(UserTenantMapping.tenant_id)
            ).all()
        return {tid: (int(active), int(total)) for tid, total, active in total_rows}

    @staticmethod
    def assign(email: str, tenant_id: str, *, active: bool = True) -> None:
        """Idempotently add an (email, tenant_id) mapping."""
        email = email.lower()
        with get_shared_schema_session() as db:
            existing = db.execute(
                select(UserTenantMapping)
                .where(
                    UserTenantMapping.email == email,
                    UserTenantMapping.tenant_id == tenant_id,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if existing is not None:
                if existing.active != active:
                    existing.active = active
                    db.commit()
                return
            db.add(
                UserTenantMapping(email=email, tenant_id=tenant_id, active=active)
            )
            db.commit()

    @staticmethod
    def remove(email: str, tenant_id: str) -> int:
        """Remove a single mapping. Returns rows deleted."""
        email = email.lower()
        with get_shared_schema_session() as db:
            deleted = (
                db.query(UserTenantMapping)
                .filter(
                    UserTenantMapping.email == email,
                    UserTenantMapping.tenant_id == tenant_id,
                )
                .delete()
            )
            db.commit()
            return int(deleted)

    @staticmethod
    def remove_all_for_tenant(tenant_id: str) -> int:
        with get_shared_schema_session() as db:
            deleted = (
                db.query(UserTenantMapping)
                .filter(UserTenantMapping.tenant_id == tenant_id)
                .delete()
            )
            db.commit()
            return int(deleted)

    @staticmethod
    def set_tenant_active(tenant_id: str, active: bool) -> int:
        """Activate/deactivate every mapping for a tenant. Returns rows affected."""
        with get_shared_schema_session() as db:
            affected = (
                db.query(UserTenantMapping)
                .filter(UserTenantMapping.tenant_id == tenant_id)
                .update({"active": active})
            )
            db.commit()
            return int(affected)

    @staticmethod
    def move_user(email: str, from_tenant: str, to_tenant: str) -> None:
        """Deactivate all of a user's mappings and activate them on ``to_tenant``."""
        email = email.lower()
        with get_shared_schema_session() as db:
            db.query(UserTenantMapping).filter(
                UserTenantMapping.email == email
            ).update({"active": False})
            existing = db.execute(
                select(UserTenantMapping).where(
                    UserTenantMapping.email == email,
                    UserTenantMapping.tenant_id == to_tenant,
                )
            ).scalar_one_or_none()
            if existing is not None:
                existing.active = True
            else:
                db.add(
                    UserTenantMapping(email=email, tenant_id=to_tenant, active=True)
                )
            db.commit()
        logger.info(f"Moved user {email} from {from_tenant} to {to_tenant}")

    @staticmethod
    def active_user_count_in_schema(tenant_id: str, emails: list[str]) -> int:
        """Count users that are active *inside the tenant schema* (real seats)."""
        if not emails:
            return 0
        lowered = [e.lower() for e in emails]
        with get_tenant_session(tenant_id=tenant_id) as db:
            return int(
                db.query(User)
                .filter(User.email.in_(lowered), User.is_active.is_(True))
                .count()
            )
