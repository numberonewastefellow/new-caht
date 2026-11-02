"""Database operations for User Library (CRAFT_FILE connector).

Handles storage quota queries and connector/credential setup for the
User Library feature in Craft.
"""

from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import cast
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.configs.constants import DocumentSource
from om.datasource.models import InputType
from om.db.connector import create_connector
from om.db.connector import fetch_connectors
from om.db.connector_credential_pair import add_credential_to_connector
from om.db.connector_credential_pair import (
    get_connector_credential_pairs_for_user,
)
from om.db.credentials import create_credential
from om.db.credentials import fetch_credentials_for_user
from om.db.enums import AccessType
from om.db.enums import ProcessingMode
from om.db.models import Datasource
from om.db.models import DatasourceCredentialPair
from om.db.models import Document as DbDocument
from om.db.models import DocumentByDatasourceCredentialPair
from om.db.models import User
from om.server.documents.models import ConnectorBase
from om.server.documents.models import CredentialBase
from om.server.features.build.configs import USER_LIBRARY_CONNECTOR_NAME
from om.server.features.build.configs import USER_LIBRARY_CREDENTIAL_NAME
from om.utils.logger import setup_logger

logger = setup_logger()


def get_user_storage_bytes(db_session: Session, user_id: UUID) -> int:
    """Get total storage usage for a user's library files.

    Uses SQL aggregation to sum file_size from doc_metadata JSONB for all
    CRAFT_FILE documents owned by this user, avoiding loading all documents
    into Python memory.
    """
    stmt = (
        select(
            func.coalesce(
                func.sum(
                    cast(
                        DbDocument.doc_metadata["file_size"].as_string(),
                        Integer,
                    )
                ),
                0,
            )
        )
        .join(
            DocumentByDatasourceCredentialPair,
            DbDocument.id == DocumentByDatasourceCredentialPair.id,
        )
        .join(
            DatasourceCredentialPair,
            and_(
                DocumentByDatasourceCredentialPair.datasource_id
                == DatasourceCredentialPair.datasource_id,
                DocumentByDatasourceCredentialPair.credential_id
                == DatasourceCredentialPair.credential_id,
            ),
        )
        .join(
            Datasource,
            DatasourceCredentialPair.datasource_id == Datasource.id,
        )
        .where(Datasource.source == DocumentSource.CRAFT_FILE)
        .where(DatasourceCredentialPair.creator_id == user_id)
        .where(DbDocument.doc_metadata["is_directory"].as_boolean().is_not(True))
    )
    result = db_session.execute(stmt).scalar()
    return int(result or 0)


def get_or_create_craft_connector(db_session: Session, user: User) -> tuple[int, int]:
    """Get or create the CRAFT_FILE connector for a user.

    Returns:
        Tuple of (connector_id, credential_id)

    Note: We need to create a credential even though CRAFT_FILE doesn't require
    authentication. This is because VertualAI's connector-credential pair system
    requires a credential for all connectors. The credential is empty ({}).

    This function handles recovery from partial creation failures by detecting
    orphaned connectors (connectors without cc_pairs) and completing their setup.
    """
    # Check if user already has a complete CRAFT_FILE cc_pair
    cc_pairs = get_connector_credential_pairs_for_user(
        db_session=db_session,
        user=user,
        get_editable=False,
        eager_load_connector=True,
        eager_load_credential=True,
        processing_mode=ProcessingMode.RAW_BINARY,
    )

    for cc_pair in cc_pairs:
        if cc_pair.datasource.source == DocumentSource.CRAFT_FILE:
            return cc_pair.datasource.id, cc_pair.credential.id

    # Check for orphaned connector (created but cc_pair creation failed previously)
    existing_connectors = fetch_connectors(
        db_session, sources=[DocumentSource.CRAFT_FILE]
    )
    orphaned_connector = None
    for conn in existing_connectors:
        if conn.name != USER_LIBRARY_CONNECTOR_NAME:
            continue
        if not conn.credentials:
            orphaned_connector = conn
            break

    if orphaned_connector:
        connector_id = orphaned_connector.id
        logger.info(
            f"Found orphaned User Library connector {connector_id}, completing setup"
        )
    else:
        connector_data = ConnectorBase(
            name=USER_LIBRARY_CONNECTOR_NAME,
            source=DocumentSource.CRAFT_FILE,
            input_type=InputType.LOAD_STATE,
            connector_specific_config={"disabled_paths": []},
            refresh_freq=None,
            prune_freq=None,
        )
        connector_response = create_connector(
            db_session=db_session,
            connector_data=connector_data,
        )
        connector_id = connector_response.id

    # Try to reuse an existing User Library credential for this user
    existing_credentials = fetch_credentials_for_user(
        db_session=db_session,
        user=user,
    )
    credential = None
    for cred in existing_credentials:
        if (
            cred.source == DocumentSource.CRAFT_FILE
            and cred.name == USER_LIBRARY_CREDENTIAL_NAME
        ):
            credential = cred
            break

    if credential is None:
        credential_data = CredentialBase(
            credential_json={},
            admin_public=False,
            source=DocumentSource.CRAFT_FILE,
            name=USER_LIBRARY_CREDENTIAL_NAME,
        )
        credential = create_credential(
            credential_data=credential_data,
            user=user,
            db_session=db_session,
        )

    # Link them with RAW_BINARY processing mode
    add_credential_to_connector(
        db_session=db_session,
        connector_id=connector_id,
        credential_id=credential.id,
        user=user,
        cc_pair_name=USER_LIBRARY_CONNECTOR_NAME,
        access_type=AccessType.PRIVATE,
        groups=None,
        processing_mode=ProcessingMode.RAW_BINARY,
    )

    db_session.commit()
    return connector_id, credential.id
