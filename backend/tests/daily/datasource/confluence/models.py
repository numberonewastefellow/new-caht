from pydantic import BaseModel

from om.db.external_perm import ExternalUserGroup


class ExternalUserGroupSet(BaseModel):
    """A version of ExternalUserGroup that uses a set for user_emails to avoid order-dependent comparisons."""

    id: str
    user_emails: set[str]
    gives_anyone_access: bool

    @classmethod
    def from_model(
        cls, external_team: ExternalUserGroup
    ) -> "ExternalUserGroupSet":
        """Convert from ExternalUserGroup to ExternalUserGroupSet."""
        return cls(
            id=external_team.id,
            user_emails=set(external_team.user_emails),
            gives_anyone_access=external_team.gives_anyone_access,
        )
