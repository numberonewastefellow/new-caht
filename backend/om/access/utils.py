"""Encoders for document-ACL principals.

The document index stores each document's ACL as a flat list of opaque,
type-prefixed principal strings (the ``access_control_list`` keyword field). A
document is visible to a user iff at least one of the user's principal strings
(from :func:`om.access.access.get_acl_for_user`) is present in that list. The
prefixes below are the *only* place that encoding is defined — write-side
(``DocumentAccess.to_acl``) and read-side must both route through here so they
stay byte-for-byte identical.

Team rename (Contract 2): the internal group principal is now ``team:`` and the
external group principal ``external_team:``. ``user_email:`` is unchanged.
"""

from om.configs.constants import DocumentSource

# Principal type tags. Distinct prefixes guarantee a user email can never collide
# with a team name or an external group id in the flat ACL list.
USER_EMAIL_PREFIX = "user_email:"
TEAM_PREFIX = "team:"
EXTERNAL_TEAM_PREFIX = "external_team:"


def prefix_user_email(user_email: str) -> str:
    """Encode an internal-or-external user email as an ACL principal."""
    return f"{USER_EMAIL_PREFIX}{user_email}"


def prefix_team(team_name: str) -> str:
    """Encode an internal team name as an ACL principal."""
    return f"{TEAM_PREFIX}{team_name}"


def prefix_external_team(external_team_name: str) -> str:
    """Encode an external (source-synced) group id as an ACL principal."""
    return f"{EXTERNAL_TEAM_PREFIX}{external_team_name}"


def build_ext_team_name_for_om(external_group_name: str, source: DocumentSource) -> str:
    """Namespace an external group id by its source so ids from different
    connectors cannot collide. Lower-cased for case-insensitive matching."""
    return f"{source.value}_{external_group_name}".lower()
