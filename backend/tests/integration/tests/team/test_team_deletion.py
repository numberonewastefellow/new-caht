"""
This tests the deletion of a user group with the following foreign key constraints:
- connector_credential_pair
- user
- credential
- llm_provider
- document_set
- token_rate_limit (Not Implemented)
- agent
"""



from om.server.documents.models import DocumentSource
from tests.integration.common_utils.document_index import DocumentIndexClient
from tests.integration.common_utils.managers.cc_pair import CCPairManager
from tests.integration.common_utils.managers.credential import CredentialManager
from tests.integration.common_utils.managers.document_set import DocumentSetManager
from tests.integration.common_utils.managers.llm_provider import LLMProviderManager
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.team import TeamManager
from tests.integration.common_utils.test_models import DATestCredential
from tests.integration.common_utils.test_models import DATestDocumentSet
from tests.integration.common_utils.test_models import DATestLLMProvider
from tests.integration.common_utils.test_models import DATestAgent
from tests.integration.common_utils.test_models import DATestUser
from tests.integration.common_utils.test_models import DATestTeam


def test_team_deletion(
    reset: None, document_index_client: DocumentIndexClient  # noqa: ARG001
) -> None:
    # Creating an admin user (first user created is automatically an admin)
    admin_user: DATestUser = UserManager.create(name="admin_user")

    # create connectors
    cc_pair = CCPairManager.create_from_scratch(
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )

    # Create user group with a cc_pair and a user
    team: DATestTeam = TeamManager.create(
        user_ids=[admin_user.id],
        cc_pair_ids=[cc_pair.id],
        user_performing_action=admin_user,
    )
    cc_pair.groups = [team.id]

    TeamManager.wait_for_sync(
        teams_to_check=[team], user_performing_action=admin_user
    )
    TeamManager.verify(
        team=team,
        user_performing_action=admin_user,
    )
    CCPairManager.verify(
        cc_pair=cc_pair,
        user_performing_action=admin_user,
    )

    # Create other objects that are related to the user group
    credential: DATestCredential = CredentialManager.create(
        groups=[team.id],
        user_performing_action=admin_user,
    )
    document_set: DATestDocumentSet = DocumentSetManager.create(
        cc_pair_ids=[cc_pair.id],
        groups=[team.id],
        user_performing_action=admin_user,
    )
    llm_provider: DATestLLMProvider = LLMProviderManager.create(
        groups=[team.id],
        user_performing_action=admin_user,
    )
    agent: DATestAgent = AgentManager.create(
        groups=[team.id],
        user_performing_action=admin_user,
    )

    TeamManager.wait_for_sync(
        teams_to_check=[team], user_performing_action=admin_user
    )
    TeamManager.verify(
        team=team,
        user_performing_action=admin_user,
    )

    # Delete the user group
    TeamManager.delete(
        team=team,
        user_performing_action=admin_user,
    )

    TeamManager.wait_for_deletion_completion(
        teams_to_check=[team], user_performing_action=admin_user
    )

    # Set our expected local representations to empty
    credential.groups = []
    document_set.groups = []
    llm_provider.groups = []
    agent.groups = []

    # Verify that the local representations were updated
    CredentialManager.verify(
        credential=credential,
        user_performing_action=admin_user,
    )

    DocumentSetManager.verify(
        document_set=document_set,
        user_performing_action=admin_user,
    )

    LLMProviderManager.verify(
        llm_provider=llm_provider,
        user_performing_action=admin_user,
    )

    AgentManager.verify(
        agent=agent,
        user_performing_action=admin_user,
    )
