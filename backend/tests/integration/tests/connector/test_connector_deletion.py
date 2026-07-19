"""
This file contains tests for the following:
- Ensuring deletion of a connector also:
    - deletes the documents in the document index for that connector
    - updates the document sets and user groups to remove the connector
- Ensure that deleting a connector that is part of an overlapping document set and/or user group works as expected
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from om.connectors.models import ConnectorFailure
from om.connectors.models import DocumentFailure
from om.db.engine.sql_engine import get_sqlalchemy_engine
from om.db.enums import IndexingStatus
from om.db.index_attempt import create_index_attempt
from om.db.index_attempt import create_index_attempt_error
from om.db.models import IndexAttempt
from om.db.search_settings import get_current_search_settings
from om.server.documents.models import DocumentSource
from tests.integration.common_utils.constants import NUM_DOCS
from tests.integration.common_utils.document_index import DocumentIndexClient
from tests.integration.common_utils.managers.api_key import APIKeyManager
from tests.integration.common_utils.managers.cc_pair import CCPairManager
from tests.integration.common_utils.managers.document import DocumentManager
from tests.integration.common_utils.managers.document_set import DocumentSetManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.team import TeamManager
from tests.integration.common_utils.test_models import DATestAPIKey
from tests.integration.common_utils.test_models import DATestUser
from tests.integration.common_utils.test_models import DATestTeam


def test_connector_deletion(
    reset: None, document_index_client: DocumentIndexClient  # noqa: ARG001
) -> None:
    team_1: DATestTeam
    team_2: DATestTeam

    is_ee = True

    # Creating an admin user (first user created is automatically an admin)
    admin_user: DATestUser = UserManager.create(name="admin_user")
    # create api key
    api_key: DATestAPIKey = APIKeyManager.create(
        user_performing_action=admin_user,
    )

    # create connectors
    cc_pair_1 = CCPairManager.create_from_scratch(
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )
    cc_pair_2 = CCPairManager.create_from_scratch(
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )

    # seed documents
    cc_pair_1.documents = DocumentManager.seed_dummy_docs(
        cc_pair=cc_pair_1,
        num_docs=NUM_DOCS,
        api_key=api_key,
    )
    cc_pair_2.documents = DocumentManager.seed_dummy_docs(
        cc_pair=cc_pair_2,
        num_docs=NUM_DOCS,
        api_key=api_key,
    )

    # create document sets
    doc_set_1 = DocumentSetManager.create(
        name="Test Document Set 1",
        cc_pair_ids=[cc_pair_1.id],
        user_performing_action=admin_user,
    )
    doc_set_2 = DocumentSetManager.create(
        name="Test Document Set 2",
        cc_pair_ids=[cc_pair_1.id, cc_pair_2.id],
        user_performing_action=admin_user,
    )

    # wait for document sets to be synced
    DocumentSetManager.wait_for_sync(user_performing_action=admin_user)

    print("Document sets created and synced")

    if is_ee:
        # create user groups
        team_1 = TeamManager.create(
            cc_pair_ids=[cc_pair_1.id],
            user_performing_action=admin_user,
        )
        team_2 = TeamManager.create(
            cc_pair_ids=[cc_pair_1.id, cc_pair_2.id],
            user_performing_action=admin_user,
        )
        TeamManager.wait_for_sync(user_performing_action=admin_user)

    # inject a finished index attempt and index attempt error (exercises foreign key errors)
    with Session(get_sqlalchemy_engine()) as db_session:
        primary_search_settings = get_current_search_settings(db_session)
        new_attempt = IndexAttempt(
            connector_credential_pair_id=cc_pair_1.id,
            search_settings_id=primary_search_settings.id,
            from_beginning=False,
            status=IndexingStatus.COMPLETED_WITH_ERRORS,
        )
        db_session.add(new_attempt)
        db_session.commit()

        create_index_attempt_error(
            index_attempt_id=new_attempt.id,
            connector_credential_pair_id=cc_pair_1.id,
            failure=ConnectorFailure(
                failure_message="Test error",
                failed_document=DocumentFailure(
                    document_id=cc_pair_1.documents[0].id,
                    document_link=None,
                ),
                failed_entity=None,
            ),
            db_session=db_session,
        )

    # delete connector 1
    CCPairManager.pause_cc_pair(
        cc_pair=cc_pair_1,
        user_performing_action=admin_user,
    )
    CCPairManager.delete(
        cc_pair=cc_pair_1,
        user_performing_action=admin_user,
    )

    # inject an index attempt and index attempt error (exercises foreign key errors)
    with Session(get_sqlalchemy_engine()) as db_session:
        attempt_id = create_index_attempt(
            connector_credential_pair_id=cc_pair_1.id,
            search_settings_id=1,
            db_session=db_session,
        )
        create_index_attempt_error(
            index_attempt_id=attempt_id,
            connector_credential_pair_id=cc_pair_1.id,
            failure=ConnectorFailure(
                failure_message="Test error",
                failed_document=DocumentFailure(
                    document_id=cc_pair_1.documents[0].id,
                    document_link=None,
                ),
                failed_entity=None,
            ),
            db_session=db_session,
        )

    # Update local records to match the database for later comparison
    doc_set_1.cc_pair_ids = []
    doc_set_2.cc_pair_ids = [cc_pair_2.id]
    cc_pair_1.groups = []
    if is_ee:
        cc_pair_2.groups = [team_2.id]
    else:
        cc_pair_2.groups = []

    CCPairManager.wait_for_deletion_completion(
        cc_pair_id=cc_pair_1.id, user_performing_action=admin_user
    )

    # validate document-index documents
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_1,
        doc_set_names=[],
        group_names=[],
        doc_creating_user=admin_user,
        verify_deleted=True,
    )

    cc_pair_2_group_name_expected = []
    if is_ee:
        cc_pair_2_group_name_expected = [team_2.name]

    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_2,
        doc_set_names=[doc_set_2.name],
        group_names=cc_pair_2_group_name_expected,
        doc_creating_user=admin_user,
        verify_deleted=False,
    )

    # check that only connector 1 is deleted
    CCPairManager.verify(
        cc_pair=cc_pair_2,
        user_performing_action=admin_user,
    )

    # validate document sets
    DocumentSetManager.verify(
        document_set=doc_set_1,
        user_performing_action=admin_user,
    )
    DocumentSetManager.verify(
        document_set=doc_set_2,
        user_performing_action=admin_user,
    )

    if is_ee:
        team_1.cc_pair_ids = []
        team_2.cc_pair_ids = [cc_pair_2.id]

        # validate user groups
        TeamManager.verify(
            team=team_1,
            user_performing_action=admin_user,
        )
        TeamManager.verify(
            team=team_2,
            user_performing_action=admin_user,
        )


def test_connector_deletion_for_overlapping_connectors(
    reset: None, document_index_client: DocumentIndexClient  # noqa: ARG001
) -> None:
    """Checks to make sure that connectors with overlapping documents work properly. Specifically, that the overlapping
    document (1) still exists and (2) has the right document set / group post-deletion of one of the connectors.
    """
    team_1: DATestTeam
    team_2: DATestTeam

    is_ee = True

    # Creating an admin user (first user created is automatically an admin)
    admin_user: DATestUser = UserManager.create(name="admin_user")
    # create api key
    api_key: DATestAPIKey = APIKeyManager.create(
        user_performing_action=admin_user,
    )

    # create connectors
    cc_pair_1 = CCPairManager.create_from_scratch(
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )
    cc_pair_2 = CCPairManager.create_from_scratch(
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )

    doc_ids = [str(uuid4())]
    cc_pair_1.documents = DocumentManager.seed_dummy_docs(
        cc_pair=cc_pair_1,
        document_ids=doc_ids,
        api_key=api_key,
    )
    cc_pair_2.documents = DocumentManager.seed_dummy_docs(
        cc_pair=cc_pair_2,
        document_ids=doc_ids,
        api_key=api_key,
    )

    # verify the document exists in the document index and that it is not in any document sets or groups
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_1,
        doc_set_names=[],
        group_names=[],
        doc_creating_user=admin_user,
    )
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_2,
        doc_set_names=[],
        group_names=[],
        doc_creating_user=admin_user,
    )

    # create document set
    doc_set_1 = DocumentSetManager.create(
        name="Test Document Set 1",
        cc_pair_ids=[cc_pair_1.id],
        user_performing_action=admin_user,
    )
    DocumentSetManager.wait_for_sync(
        document_sets_to_check=[doc_set_1],
        user_performing_action=admin_user,
    )

    print("Document set 1 created and synced")

    # verify document-index document is in the document set
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_1,
        doc_set_names=[doc_set_1.name],
        doc_creating_user=admin_user,
    )
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_2,
        doc_creating_user=admin_user,
    )

    if is_ee:
        # create a user group and attach it to connector 1
        team_1 = TeamManager.create(
            name="Test User Group 1",
            cc_pair_ids=[cc_pair_1.id],
            user_performing_action=admin_user,
        )
        TeamManager.wait_for_sync(
            teams_to_check=[team_1],
            user_performing_action=admin_user,
        )
        cc_pair_1.groups = [team_1.id]

        print("User group 1 created and synced")

        # create a user group and attach it to connector 2
        team_2 = TeamManager.create(
            name="Test User Group 2",
            cc_pair_ids=[cc_pair_2.id],
            user_performing_action=admin_user,
        )
        TeamManager.wait_for_sync(
            teams_to_check=[team_2],
            user_performing_action=admin_user,
        )
        cc_pair_2.groups = [team_2.id]

        print("User group 2 created and synced")

        # verify document-index document is in the user group
        DocumentManager.verify(
            document_index_client=document_index_client,
            cc_pair=cc_pair_1,
            group_names=[team_1.name, team_2.name],
            doc_creating_user=admin_user,
        )
        DocumentManager.verify(
            document_index_client=document_index_client,
            cc_pair=cc_pair_2,
            group_names=[team_1.name, team_2.name],
            doc_creating_user=admin_user,
        )

    # delete connector 1
    CCPairManager.pause_cc_pair(
        cc_pair=cc_pair_1,
        user_performing_action=admin_user,
    )
    CCPairManager.delete(
        cc_pair=cc_pair_1,
        user_performing_action=admin_user,
    )

    # wait for deletion to finish
    CCPairManager.wait_for_deletion_completion(
        cc_pair_id=cc_pair_1.id, user_performing_action=admin_user
    )

    print("Connector 1 deleted")

    # check that only connector 1 is deleted
    # TODO: check for the CC pair rather than the connector once the refactor is done
    CCPairManager.verify(
        cc_pair=cc_pair_1,
        verify_deleted=True,
        user_performing_action=admin_user,
    )
    CCPairManager.verify(
        cc_pair=cc_pair_2,
        user_performing_action=admin_user,
    )

    # verify the document is not in any document sets
    # verify the document is only in user group 2
    group_names_expected = []
    if is_ee:
        group_names_expected = [team_2.name]

    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=cc_pair_2,
        doc_set_names=[],
        group_names=group_names_expected,
        doc_creating_user=admin_user,
        verify_deleted=False,
    )
