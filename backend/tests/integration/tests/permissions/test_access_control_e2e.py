"""End-to-end access-control integration test against the LIVE running stack.

Proves team / individual-user / public document access control works through the
REAL API + Postgres + OpenSearch (no mocks). It exercises three visibility
dimensions with three ingested documents:

  * PUBLIC   - a public cc_pair            -> ACL {PUBLIC, user_email:<owner>}
  * TEAM     - a private cc_pair scoped to  -> ACL {team:<engineering>, user_email:<owner>}
               team "engineering" (member B)
  * USER-KB  - a private cc_pair whose      -> ACL {user_email:<B>}
               credential is owned by B

Then it verifies, three independent ways:

  1. The ACLs actually stamped into the OpenSearch index (read back by id).
  2. A deterministic DB-side ACL intersection (``get_user_document_access_via_acl``).
  3. REAL vector+keyword search via ``/search/send-search-message`` (no LLM: query
     expansion defaults off) for each principal.

Notes on the harness / environment:
  * ``CCPairManager`` is deliberately NOT imported: its module imports the
    (un-generated) ``generated.onyx_openapi_client``. We associate connector+
    credential ourselves with a direct ``requests.PUT`` to the REST endpoint the
    openapi client wraps (``PUT /nexus/connector/{cid}/credential/{crid}``).
  * There is NO admin search bypass in this build: search visibility is purely
    ACL-driven (``get_acl_for_user`` = own email + PUBLIC + team memberships).
    We therefore assert the admin's ACTUAL, ACL-derived visibility.
"""

import time
import uuid
from types import SimpleNamespace

import requests
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy import pool

from om.db.enums import AccessType
from om.db.engine.sql_engine import build_connection_string
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SYNC_DB_API
from om.db.models import UserRole
from om.db.search_settings import get_current_search_settings
from om.server.documents.models import DocumentSource
from om.server.query_and_chat.models import SendSearchQueryRequest
from om.setup import setup_postgres

from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import GENERAL_HEADERS
from tests.integration.common_utils.constants import MAX_DELAY
from tests.integration.common_utils.document_acl import (
    get_user_document_access_via_acl,
)
from tests.integration.common_utils.document_index import DocumentIndexClient
from tests.integration.common_utils.managers.api_key import APIKeyManager
from tests.integration.common_utils.managers.connector import ConnectorManager
from tests.integration.common_utils.managers.credential import CredentialManager
from tests.integration.common_utils.managers.document import DocumentManager
from tests.integration.common_utils.managers.team import TeamManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.reset import downgrade_postgres
from tests.integration.common_utils.reset import reset_document_index
from tests.integration.common_utils.reset import reset_file_store
from tests.integration.common_utils.test_models import DATestAPIKey
from tests.integration.common_utils.test_models import DATestCCPair
from tests.integration.common_utils.test_models import DATestUser


def _alembic_upgrade_head_sync() -> None:
    """Apply all migrations to head using the SYNC (psycopg2) driver.

    The stock ``reset`` fixture drives ``alembic upgrade`` through env.py's
    default *async* (asyncpg) engine, which rejects the baseline migration's
    multi-statement SQL dump ("cannot insert multiple commands into a prepared
    statement") when run from the host. env.py, however, honors a pre-supplied
    sync connection via ``config.attributes["connection"]`` (its pytest-alembic
    path). We use that hook so DDL runs over the simple-query protocol. This is
    a LOCAL workaround only; no shared source is modified.
    """
    sync_url = build_connection_string(db_api=SYNC_DB_API)
    engine = create_engine(sync_url, poolclass=pool.NullPool)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    cfg.attributes["configure_logger"] = False
    cfg.attributes["connection"] = engine  # -> env.py sync path
    cfg.cmd_opts = SimpleNamespace()  # type: ignore[assignment]
    cfg.cmd_opts.x = ["schema=public"]  # type: ignore[attr-defined]
    try:
        command.upgrade(cfg, "head")
    finally:
        engine.dispose()


def _reset_live_stack() -> None:
    """Full clean slate against the live stack (Postgres drop+remigrate via the
    sync path, OpenSearch index wipe, FileStore wipe). USER HAS ACCEPTED THIS
    DATA LOSS."""
    # Drop + recreate the public schema (psycopg2 / autocommit -> works fine).
    downgrade_postgres(revision="base", clear_data=True)
    # Re-migrate to head over the sync driver.
    _alembic_upgrade_head_sync()
    # Seed built-in tools / default assistant / default search settings.
    with get_session_with_current_tenant() as db_session:
        setup_postgres(db_session)
    # Wipe + recreate the OpenSearch index and the FileStore.
    reset_document_index()
    reset_file_store()


# A phrase shared by every seeded doc so a single query retrieves all
# *accessible* docs; each doc then carries a unique marker token so we can tell
# which docs a principal actually got back.
SEARCH_ANCHOR = "accesscontrole2e shared corpus reference document"
MARKER_PUBLIC = "publicmarkeralpha"
MARKER_TEAM = "teammarkerbravo"
MARKER_KB = "kbmarkercharlie"


# --------------------------------------------------------------------------- #
# Local helpers (kept in-file per task constraints)
# --------------------------------------------------------------------------- #
def _associate_credential_to_connector(
    connector_id: int,
    credential_id: int,
    name: str,
    access_type: AccessType,
    groups: list[int],
    user_performing_action: DATestUser,
) -> int:
    """Direct REST call standing in for the openapi client's
    ``associate_credential_to_connector``. Returns the new cc_pair id."""
    resp = requests.put(
        url=f"{API_SERVER_URL}/nexus/connector/{connector_id}/credential/{credential_id}",
        json={
            "name": name,
            "access_type": access_type.value,
            "groups": groups,
        },
        headers=user_performing_action.headers,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def _make_cc_pair(
    name: str,
    access_type: AccessType,
    groups: list[int],
    connector_owner: DATestUser,
    credential_owner: DATestUser,
) -> DATestCCPair:
    """Replicates ``CCPairManager.create_from_scratch`` without importing it:
    create connector + credential, then associate them. ``credential_owner``
    determines the ``user_email:`` ACL stamped onto docs seeded into this pair."""
    connector = ConnectorManager.create(
        name=name,
        source=DocumentSource.INGESTION_API,
        access_type=access_type,
        groups=groups,
        user_performing_action=connector_owner,
    )
    credential = CredentialManager.create(
        name=name,
        # NOT_APPLICABLE is in CREDENTIAL_PERMISSIONS_TO_IGNORE, so a non-admin
        # curator may own a group-less private credential (needed for the USER-KB
        # doc). INGESTION_API is fine for admin-owned credentials.
        source=(
            DocumentSource.NOT_APPLICABLE
            if credential_owner.role != UserRole.ADMIN
            else DocumentSource.INGESTION_API
        ),
        curator_public=(access_type == AccessType.PUBLIC),
        groups=groups,
        user_performing_action=credential_owner,
    )
    cc_pair_id = _associate_credential_to_connector(
        connector_id=connector.id,
        credential_id=credential.id,
        name=name,
        access_type=access_type,
        groups=groups,
        user_performing_action=connector_owner,
    )
    return DATestCCPair(
        id=cc_pair_id,
        name=name,
        connector_id=connector.id,
        credential_id=credential.id,
        access_type=access_type,
        groups=groups,
    )


def _index_acl(client: DocumentIndexClient, doc_id: str) -> set[str] | None:
    """Return the ACL-key set for a doc from the live OpenSearch index, or None
    if the doc has not been indexed yet."""
    docs = client.get_documents_by_id([doc_id])["documents"]
    if not docs:
        return None
    return set(docs[0]["fields"]["access_control_list"].keys())


def _wait_for_index_acl(
    client: DocumentIndexClient,
    doc_id: str,
    expected: set[str],
    timeout: int = MAX_DELAY,
) -> set[str]:
    """Poll until the indexed ACL for ``doc_id`` equals ``expected`` (indexing +
    permission stamping are asynchronous)."""
    start = time.time()
    last: set[str] | None = None
    while time.time() - start < timeout:
        last = _index_acl(client, doc_id)
        if last == expected:
            return last
        time.sleep(3)
    raise AssertionError(
        f"Doc {doc_id} ACL never reached {expected}; last seen: {last}"
    )


def _search_doc_ids(query: str, user: DATestUser | None) -> set[str]:
    """REAL search via /search/send-search-message with query expansion OFF (no
    LLM). Returns the set of returned document ids."""
    request = SendSearchQueryRequest(
        search_query=query,
        filters=None,
        run_query_expansion=False,
        stream=False,
    )
    resp = requests.post(
        url=f"{API_SERVER_URL}/search/send-search-message",
        json=request.model_dump(),
        headers=user.headers if user else GENERAL_HEADERS,
    )
    resp.raise_for_status()
    return {doc["document_id"] for doc in resp.json()["search_docs"]}


# --------------------------------------------------------------------------- #
# The test
# --------------------------------------------------------------------------- #
def test_access_control_e2e() -> None:
    # -- 0. clean slate (local sync-migration reset; accepted data loss) ----- #
    _reset_live_stack()
    with get_session_with_current_tenant() as db:
        index_name = get_current_search_settings(db).index_name
    document_index_client = DocumentIndexClient(index_name=index_name)

    # -- 1. users ----------------------------------------------------------- #
    admin_a = UserManager.create(name="acl_admin_a")
    assert UserManager.is_role(admin_a, UserRole.ADMIN)
    user_b = UserManager.create(name="acl_user_b")
    user_c = UserManager.create(name="acl_user_c")
    assert user_b.role == UserRole.BASIC
    assert user_c.role == UserRole.BASIC

    # -- 2. team "engineering" with B (not C) ------------------------------- #
    team = TeamManager.create(
        name="engineering",
        user_ids=[user_b.id],
        user_performing_action=admin_a,
    )
    TeamManager.wait_for_sync(teams_to_check=[team], user_performing_action=admin_a)

    all_teams = TeamManager.get_all(admin_a)
    eng = next(t for t in all_teams if t.id == team.id)
    member_ids = {u.id for u in eng.users}
    assert user_b.id in member_ids, "B should be a member of engineering"
    assert user_c.id not in member_ids, "C must NOT be a member of engineering"

    # Make B a curator of engineering so B can OWN a credential (curator-or-admin
    # only endpoint); this is what yields a user_email:<B> ACL on the KB doc.
    TeamManager.set_curator_status(
        test_team=team,
        user_to_set_as_curator=user_b,
        user_performing_action=admin_a,
    )
    assert UserManager.is_role(user_b, UserRole.CURATOR)

    # -- admin API key (ingestion-endpoint auth only) ----------------------- #
    api_key: DATestAPIKey = APIKeyManager.create(user_performing_action=admin_a)

    # -- 3. three cc_pairs + one uniquely-searchable doc each --------------- #
    run = uuid.uuid4().hex[:8]

    public_cc = _make_cc_pair(
        name=f"acl-public-{run}",
        access_type=AccessType.PUBLIC,
        groups=[],
        connector_owner=admin_a,
        credential_owner=admin_a,
    )
    team_cc = _make_cc_pair(
        name=f"acl-team-{run}",
        access_type=AccessType.PRIVATE,
        groups=[team.id],
        connector_owner=admin_a,
        credential_owner=admin_a,
    )
    kb_cc = _make_cc_pair(
        name=f"acl-kb-{run}",
        access_type=AccessType.PRIVATE,
        groups=[],
        connector_owner=admin_a,
        credential_owner=user_b,  # <- B owns the credential => user_email:<B>
    )

    public_doc = DocumentManager.seed_doc_with_content(
        cc_pair=public_cc,
        content=f"{SEARCH_ANCHOR} {MARKER_PUBLIC}",
        api_key=api_key,
    )
    team_doc = DocumentManager.seed_doc_with_content(
        cc_pair=team_cc,
        content=f"{SEARCH_ANCHOR} {MARKER_TEAM}",
        api_key=api_key,
    )
    kb_doc = DocumentManager.seed_doc_with_content(
        cc_pair=kb_cc,
        content=f"{SEARCH_ANCHOR} {MARKER_KB}",
        api_key=api_key,
    )
    public_cc.documents = [public_doc]
    team_cc.documents = [team_doc]
    kb_cc.documents = [kb_doc]

    team_acl_key = f"team:{team.name}"
    email_a = f"user_email:{admin_a.email}"
    email_b = f"user_email:{user_b.email}"

    # -- 4a. ACLs actually stamped into the OpenSearch index ---------------- #
    _wait_for_index_acl(
        document_index_client, public_doc.id, {"PUBLIC", email_a}
    )
    _wait_for_index_acl(
        document_index_client, team_doc.id, {team_acl_key, email_a}
    )
    _wait_for_index_acl(document_index_client, kb_doc.id, {email_b})

    # Cross-check with the shared harness verifier (exact team-key match).
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=public_cc,
        group_names=[],
        doc_creating_user=admin_a,
    )
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=team_cc,
        group_names=[team.name],
        doc_creating_user=admin_a,
    )
    DocumentManager.verify(
        document_index_client=document_index_client,
        cc_pair=kb_cc,
        group_names=[],
        doc_creating_user=user_b,
    )

    # -- 4b. deterministic DB-side ACL intersection ------------------------- #
    all_doc_ids = [public_doc.id, team_doc.id, kb_doc.id]
    with get_session_with_current_tenant() as db:
        access_a = set(get_user_document_access_via_acl(admin_a, all_doc_ids, db))
        access_b = set(get_user_document_access_via_acl(user_b, all_doc_ids, db))
        access_c = set(get_user_document_access_via_acl(user_c, all_doc_ids, db))

    # admin A owns the public + team credentials (not the KB one) and is not on
    # the team; with no search bypass it reaches public + team (via ownership).
    assert access_a == {public_doc.id, team_doc.id}, access_a
    # B: public (public) + team (membership) + KB (ownership).
    assert access_b == {public_doc.id, team_doc.id, kb_doc.id}, access_b
    # C: only the public doc.
    assert access_c == {public_doc.id}, access_c

    # -- 5. REAL search (no LLM: expansion off) ----------------------------- #
    seen_a = _search_doc_ids(SEARCH_ANCHOR, admin_a) & set(all_doc_ids)
    seen_b = _search_doc_ids(SEARCH_ANCHOR, user_b) & set(all_doc_ids)
    seen_c = _search_doc_ids(SEARCH_ANCHOR, user_c) & set(all_doc_ids)

    assert seen_a == {public_doc.id, team_doc.id}, seen_a
    assert seen_b == {public_doc.id, team_doc.id, kb_doc.id}, seen_b
    assert seen_c == {public_doc.id}, seen_c

    # Exercise the shared DocumentSearchManager too (blurb-based), and confirm B
    # sees the team + KB markers a non-member (C) does not.
    from tests.integration.common_utils.managers.document_search import (
        DocumentSearchManager,
    )

    blurbs_b = " ".join(
        DocumentSearchManager.search_documents(SEARCH_ANCHOR, user_b)
    )
    blurbs_c = " ".join(
        DocumentSearchManager.search_documents(SEARCH_ANCHOR, user_c)
    )
    assert MARKER_PUBLIC in blurbs_b
    assert MARKER_TEAM in blurbs_b
    assert MARKER_KB in blurbs_b
    assert MARKER_PUBLIC in blurbs_c
    assert MARKER_TEAM not in blurbs_c
    assert MARKER_KB not in blurbs_c

    # Anonymous / unauthenticated: best-effort (may be disabled -> skip).
    try:
        anon_seen = _search_doc_ids(SEARCH_ANCHOR, None) & set(all_doc_ids)
    except requests.HTTPError:
        anon_seen = None
    if anon_seen is not None:
        assert anon_seen == {public_doc.id}, anon_seen

    print(
        "ACCESS-CONTROL E2E OK | "
        f"A={sorted(seen_a)} B={sorted(seen_b)} C={sorted(seen_c)} "
        f"anon={sorted(anon_seen) if anon_seen is not None else 'skipped'}"
    )
