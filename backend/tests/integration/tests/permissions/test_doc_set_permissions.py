
import pytest
from requests.exceptions import HTTPError

from om.db.enums import AccessType
from om.server.documents.models import DocumentSource
from tests.integration.common_utils.managers.cc_pair import CCPairManager
from tests.integration.common_utils.managers.document_set import DocumentSetManager
from tests.integration.common_utils.managers.user import DATestUser
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.team import TeamManager


def test_doc_set_permissions_setup(reset: None) -> None:  # noqa: ARG001
    # Creating an admin user (first user created is automatically an admin)
    admin_user: DATestUser = UserManager.create(name="admin_user")

    # Creating a second user (curator)
    curator: DATestUser = UserManager.create(name="curator")

    # Creating the first user group
    team_1 = TeamManager.create(
        name="curated_team",
        user_ids=[curator.id],
        cc_pair_ids=[],
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team_1], user_performing_action=admin_user
    )

    # Setting the curator as a curator for the first user group
    TeamManager.set_curator_status(
        test_team=team_1,
        user_to_set_as_curator=curator,
        user_performing_action=admin_user,
    )

    # Creating a second user group
    team_2 = TeamManager.create(
        name="uncurated_team",
        user_ids=[curator.id],
        cc_pair_ids=[],
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team_1], user_performing_action=admin_user
    )

    # Admin creates a cc_pair
    private_cc_pair = CCPairManager.create_from_scratch(
        access_type=AccessType.PRIVATE,
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )

    # Admin creates a public cc_pair
    public_cc_pair = CCPairManager.create_from_scratch(
        access_type=AccessType.PUBLIC,
        source=DocumentSource.INGESTION_API,
        user_performing_action=admin_user,
    )

    # END OF HAPPY PATH

    """Tests for things Curators/Admins should not be able to do"""

    # Test that curator cannot create a document set for the group they don't curate
    with pytest.raises(HTTPError):
        DocumentSetManager.create(
            name="Invalid Document Set 1",
            groups=[team_2.id],
            cc_pair_ids=[public_cc_pair.id],
            user_performing_action=curator,
        )

    # Test that curator cannot create a document set attached to both groups
    with pytest.raises(HTTPError):
        DocumentSetManager.create(
            name="Invalid Document Set 2",
            is_public=False,
            cc_pair_ids=[public_cc_pair.id],
            groups=[team_1.id, team_2.id],
            user_performing_action=curator,
        )

    # Test that curator cannot create a document set with no groups
    with pytest.raises(HTTPError):
        DocumentSetManager.create(
            name="Invalid Document Set 3",
            is_public=False,
            cc_pair_ids=[public_cc_pair.id],
            groups=[],
            user_performing_action=curator,
        )

    # Test that curator cannot create a document set with no cc_pairs
    with pytest.raises(HTTPError):
        DocumentSetManager.create(
            name="Invalid Document Set 4",
            is_public=False,
            cc_pair_ids=[],
            groups=[team_1.id],
            user_performing_action=curator,
        )

    # Test that admin cannot create a document set with no cc_pairs
    with pytest.raises(HTTPError):
        DocumentSetManager.create(
            name="Invalid Document Set 4",
            is_public=False,
            cc_pair_ids=[],
            groups=[team_1.id],
            user_performing_action=admin_user,
        )

    """Tests for things Curators should be able to do"""
    # Test that curator can create a document set for the group they curate
    valid_doc_set = DocumentSetManager.create(
        name="Valid Document Set",
        is_public=False,
        cc_pair_ids=[public_cc_pair.id],
        groups=[team_1.id],
        user_performing_action=curator,
    )

    DocumentSetManager.wait_for_sync(
        document_sets_to_check=[valid_doc_set], user_performing_action=admin_user
    )

    # Verify that the valid document set was created
    DocumentSetManager.verify(
        document_set=valid_doc_set,
        user_performing_action=admin_user,
    )

    # Verify that only one document set exists
    all_doc_sets = DocumentSetManager.get_all(user_performing_action=admin_user)
    assert len(all_doc_sets) == 1

    # Add the private_cc_pair to the doc set on our end for later comparison
    valid_doc_set.cc_pair_ids.append(private_cc_pair.id)

    # Confirm the curator can't add the private_cc_pair to the doc set
    with pytest.raises(HTTPError):
        DocumentSetManager.edit(
            document_set=valid_doc_set,
            user_performing_action=curator,
        )
    # Confirm the admin can't add the private_cc_pair to the doc set
    with pytest.raises(HTTPError):
        DocumentSetManager.edit(
            document_set=valid_doc_set,
            user_performing_action=admin_user,
        )

    # Verify the document set has not been updated in the db
    with pytest.raises(ValueError):
        DocumentSetManager.verify(
            document_set=valid_doc_set,
            user_performing_action=admin_user,
        )

    # Add the private_cc_pair to the user group on our end for later comparison
    team_1.cc_pair_ids.append(private_cc_pair.id)

    # Admin adds the cc_pair to the group the curator curates
    TeamManager.edit(
        team=team_1,
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team_1], user_performing_action=admin_user
    )
    TeamManager.verify(
        team=team_1,
        user_performing_action=admin_user,
    )

    # Confirm the curator can now add the cc_pair to the doc set
    DocumentSetManager.edit(
        document_set=valid_doc_set,
        user_performing_action=curator,
    )
    DocumentSetManager.wait_for_sync(
        document_sets_to_check=[valid_doc_set], user_performing_action=admin_user
    )
    # Verify the updated document set
    DocumentSetManager.verify(
        document_set=valid_doc_set,
        user_performing_action=admin_user,
    )
