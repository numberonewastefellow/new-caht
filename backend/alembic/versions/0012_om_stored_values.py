"""rename stored upstream-branded values to om (synthetic emails, web crawler type, confluence group)

Revision ID: 0012_om_stored_values
Revises: 0011_pulse_updated_by
Create Date: 2026-10-27

Data-only. Every statement is guarded by an existence check, so the revision is a no-op on
databases that never stored the old value, and it runs per schema (public and tenant schemas).

* Synthetic user identities: API-key users (``...onyxapikey.ai`` -> ``...omapikey.ai``) and the
  anonymous / no-auth placeholder users (``@onyx.app`` -> ``@omapikey.ai``), in ``user`` and in the
  public ``user_tenant_mapping``. The new domain deliberately has a normal TLD: special-use TLDs
  (``.invalid``) are rejected by the email validation that serializes users.
* ``internet_content_provider.provider_type``: ``onyx_web_crawler`` -> ``om_web_crawler``
  (the application raises on an unknown stored value, so this is required, not cosmetic).
* The Confluence "all users" group id (stored lower-cased and source-prefixed) in the document /
  hierarchy ACL arrays and the external-team tables. OpenSearch ACL fields catch up on the next
  external group sync.

Downgrade restores the old values.
"""

from alembic import op
from sqlalchemy import text

revision = "0012_om_stored_values"
down_revision = "0011_pulse_updated_by"
branch_labels = None
depends_on = None

_OLD_CONF = "confluence_all_confluence_users_found_by_onyx"
_NEW_CONF = "confluence_all_confluence_users_found_by_om"

# (table, column, old, new) pairs applied with replace()/equality; ``like`` rows use suffix match.
_EMAIL_SUFFIX = ("onyxapikey.ai", "omapikey.ai")
_EXACT_EMAILS = (
    ("anonymous@onyx.app", "anonymous@omapikey.ai"),
    ("no-auth-placeholder@onyx.app", "no-auth-placeholder@omapikey.ai"),
)
_EMAIL_TABLES = ("user", "user_tenant_mapping")


def _has_column(table: str, column: str) -> bool:
    return (
        op.get_bind()
        .execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
                "AND table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        .first()
        is not None
    )


def _rewrite_emails(old_suffix: str, new_suffix: str, exact: tuple[tuple[str, str], ...]) -> None:
    for table in _EMAIL_TABLES:
        if not _has_column(table, "email"):
            continue
        # Exact placeholder addresses first: on downgrade they also end with the API-key suffix.
        for old_email, new_email in exact:
            op.execute(
                text(f'UPDATE "{table}" SET email = :new WHERE email = :old').bindparams(
                    old=old_email, new=new_email
                )
            )
        op.execute(
            text(
                f'UPDATE "{table}" SET email = left(email, length(email) - length(:old)) || :new '
                "WHERE email LIKE '%' || :old"
            ).bindparams(old=old_suffix, new=new_suffix)
        )


def _rewrite_provider(old: str, new: str) -> None:
    if _has_column("internet_content_provider", "provider_type"):
        op.execute(
            text("UPDATE internet_content_provider SET provider_type = :new WHERE provider_type = :old").bindparams(
                old=old, new=new
            )
        )


def _rewrite_group(old: str, new: str) -> None:
    for table in ("document", "hierarchy_node"):
        if _has_column(table, "external_team_ids"):
            op.execute(
                text(
                    f"UPDATE {table} SET external_team_ids = array_replace(external_team_ids, :old, :new) "
                    "WHERE external_team_ids @> ARRAY[CAST(:old AS varchar)]"
                ).bindparams(old=old, new=new)
            )
    for table, column in (("public_external_team", "external_team_id"), ("user__external_team_id", "external_team_id")):
        if _has_column(table, column):
            op.execute(text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old").bindparams(old=old, new=new))


def upgrade() -> None:
    _rewrite_emails(_EMAIL_SUFFIX[0], _EMAIL_SUFFIX[1], _EXACT_EMAILS)
    _rewrite_provider("onyx_web_crawler", "om_web_crawler")
    _rewrite_group(_OLD_CONF, _NEW_CONF)


def downgrade() -> None:
    _rewrite_emails(_EMAIL_SUFFIX[1], _EMAIL_SUFFIX[0], tuple((n, o) for o, n in _EXACT_EMAILS))
    _rewrite_provider("om_web_crawler", "onyx_web_crawler")
    _rewrite_group(_NEW_CONF, _OLD_CONF)
