"""Self-cleaning Teams CRUD + OpenSearch-ACL end-to-end test (LIVE stack).

Unlike ``test_access_control_e2e`` this test performs **no destructive reset**:
the operator has real data (e.g. a "Stock" team) that MUST survive. Everything
here is created by the test, verified, and then torn down in a ``finally`` block,
leaving pre-existing data intact. As a guardrail we capture the team count before
touching anything and assert it is restored at the end.

Because there is no reset, "first user is admin" does not apply (real users
already exist). We therefore create a fresh user and ELEVATE it to ADMIN via a
direct DB update (on our own user, reverted at cleanup) to drive the team ops.

Exercised, in order (each an explicit PASS/FAIL):
  1. CREATE users: admin A (elevated), members B, C (BASIC).
  2. CREATE team (enriched response: members/owner/description/tags/is_public,
     member_count/kb_count; creator A is an OWNER member).
  3. ADD members (C as MEMBER).
  4. CHANGE role (C -> ADMIN); assert role in re-GET AND user__team.is_curator DB.
  5. UPDATE settings (description/is_public/tags/default_member_role/guest); re-GET.
  6. REMOVE member (C); B + owner A remain.
  7. OpenSearch ACL: PUBLIC / TEAM / USER-KB docs -> exact index ACL keys +
     REAL search visibility per principal (A/B/C).
  8. DELETE team (async via celery) -> gone from GET /teams.

Harness notes (identical constraints to the reference test):
  * The openapi client is NOT installed; connector<->credential association is a
    direct ``requests.PUT`` to ``/nexus/connector/{cid}/credential/{crid}``.
  * There is no admin search bypass: visibility is purely ACL-driven.
"""

import time
import uuid

import requests

from om.db.enums import AccessType
from om.db.enums import MembershipSource
from om.db.enums import TeamRole
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import User
from om.db.models import User__Team
from om.db.models import UserRole
from om.db.search_settings import get_current_search_settings
from om.server.documents.models import DocumentSource
from om.server.query_and_chat.models import SendSearchQueryRequest

from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import MAX_DELAY
from tests.integration.common_utils.document_index import DocumentIndexClient
from tests.integration.common_utils.managers.api_key import APIKeyManager
from tests.integration.common_utils.managers.connector import ConnectorManager
from tests.integration.common_utils.managers.credential import CredentialManager
from tests.integration.common_utils.managers.document import DocumentManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.test_models import DATestAPIKey
from tests.integration.common_utils.test_models import DATestCCPair
from tests.integration.common_utils.test_models import DATestUser


# Every seeded doc shares this anchor phrase (so one query retrieves all
# *accessible* docs); each carries a unique marker so we can tell which came back.
SEARCH_ANCHOR = "teamscrudacle2e shared corpus reference document"
MARKER_PUBLIC = "publicmarkeralpha"
MARKER_TEAM = "teammarkerbravo"
MARKER_KB = "kbmarkercharlie"


# --------------------------------------------------------------------------- #
# Local helpers (copied from the reference test per task constraints)
# --------------------------------------------------------------------------- #
def _associate_credential_to_connector(
    connector_id: int,
    credential_id: int,
    name: str,
    access_type: AccessType,
    groups: list[int],
    user_performing_action: DATestUser,
) -> int:
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
    connector = ConnectorManager.create(
        name=name,
        source=DocumentSource.INGESTION_API,
        access_type=access_type,
        groups=groups,
        user_performing_action=connector_owner,
    )
    credential = CredentialManager.create(
        name=name,
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
    start = time.time()
    last: set[str] | None = None
    while time.time() - start < timeout:
        last = _index_acl(client, doc_id)
        if last == expected:
            return last
        time.sleep(3)
    raise AssertionError(f"Doc {doc_id} ACL never reached {expected}; last seen: {last}")


def _search_doc_ids(query: str, user: DATestUser) -> set[str]:
    """REAL search via /search/send-search-message, query expansion OFF (no LLM)."""
    request = SendSearchQueryRequest(
        search_query=query,
        filters=None,
        run_query_expansion=False,
        stream=False,
    )
    resp = requests.post(
        url=f"{API_SERVER_URL}/search/send-search-message",
        json=request.model_dump(),
        headers=user.headers,
    )
    resp.raise_for_status()
    return {doc["document_id"] for doc in resp.json()["search_docs"]}


# --------------------------------------------------------------------------- #
# Thin REST wrappers for the enriched /teams contract (full control over the
# request body + direct access to the enriched response fields).
# --------------------------------------------------------------------------- #
def _teams_get(actor: DATestUser) -> list[dict]:
    resp = requests.get(f"{API_SERVER_URL}/teams", headers=actor.headers)
    resp.raise_for_status()
    return resp.json()


def _team_get(actor: DATestUser, team_id: int) -> dict:
    team = next((t for t in _teams_get(actor) if t["id"] == team_id), None)
    if team is None:
        raise AssertionError(f"Team {team_id} not found in GET /teams")
    return team


def _team_create(actor: DATestUser, body: dict) -> dict:
    resp = requests.post(f"{API_SERVER_URL}/teams", json=body, headers=actor.headers)
    resp.raise_for_status()
    return resp.json()


def _team_add_users(actor: DATestUser, team_id: int, body: dict) -> dict:
    resp = requests.post(
        f"{API_SERVER_URL}/teams/{team_id}/add-users", json=body, headers=actor.headers
    )
    resp.raise_for_status()
    return resp.json()


def _team_set_role(actor: DATestUser, team_id: int, body: dict) -> None:
    resp = requests.post(
        f"{API_SERVER_URL}/teams/{team_id}/set-role", json=body, headers=actor.headers
    )
    resp.raise_for_status()


def _team_set_curator(actor: DATestUser, team_id: int, body: dict) -> None:
    resp = requests.post(
        f"{API_SERVER_URL}/teams/{team_id}/set-curator",
        json=body,
        headers=actor.headers,
    )
    resp.raise_for_status()


def _team_patch(actor: DATestUser, team_id: int, body: dict) -> dict:
    resp = requests.patch(
        f"{API_SERVER_URL}/teams/{team_id}", json=body, headers=actor.headers
    )
    resp.raise_for_status()
    return resp.json()


def _team_delete(actor: DATestUser, team_id: int) -> None:
    resp = requests.delete(f"{API_SERVER_URL}/teams/{team_id}", headers=actor.headers)
    resp.raise_for_status()


def _member(team: dict, user_id: str) -> dict | None:
    return next((m for m in team["members"] if m["id"] == str(user_id)), None)


def _elevate_to_admin(user: DATestUser) -> None:
    """Elevate our own created user to ADMIN via a direct DB update (there is no
    reset, so first-user-is-admin does not apply). Reverted at cleanup."""
    with get_session_with_current_tenant() as db:
        db_user = db.query(User).filter(User.id == user.id).one()
        db_user.role = UserRole.ADMIN
        db.add(db_user)
        db.commit()
    user.role = UserRole.ADMIN


def _db_deactivate_and_basic(user: DATestUser) -> None:
    """Neutralize our created admin at cleanup (cannot self-deactivate via REST):
    flip is_active=False and role back to BASIC directly in the DB."""
    with get_session_with_current_tenant() as db:
        db_user = db.query(User).filter(User.id == user.id).one_or_none()
        if db_user is None:
            return
        db_user.is_active = False
        db_user.role = UserRole.BASIC
        db.add(db_user)
        db.commit()


def _db_is_curator(team_id: int, user_id: str) -> bool | None:
    with get_session_with_current_tenant() as db:
        row = (
            db.query(User__Team)
            .filter(User__Team.team_id == team_id, User__Team.user_id == user_id)
            .one_or_none()
        )
        return None if row is None else row.is_curator


def _wait_team_absent(actor: DATestUser, team_id: int, timeout: int = MAX_DELAY) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if all(t["id"] != team_id for t in _teams_get(actor)):
            return
        time.sleep(3)
    raise AssertionError(f"Team {team_id} still present after {timeout}s (async delete)")


# --------------------------------------------------------------------------- #
# The test
# --------------------------------------------------------------------------- #
def test_teams_crud_acl_e2e() -> None:
    run = uuid.uuid4().hex[:8]
    results: dict[str, str] = {}

    admin_a: DATestUser | None = None
    user_b: DATestUser | None = None
    user_c: DATestUser | None = None
    api_key: DATestAPIKey | None = None
    team_id: int | None = None
    team_deleted = False
    created_cc_pairs: list[DATestCCPair] = []
    baseline_team_count: int | None = None

    with get_session_with_current_tenant() as db:
        index_name = get_current_search_settings(db).index_name
    doc_index = DocumentIndexClient(index_name=index_name)

    try:
        # -- 1. users -------------------------------------------------------- #
        admin_a = UserManager.create(name=f"tc_admin_a_{run}")
        _elevate_to_admin(admin_a)
        assert UserManager.is_role(admin_a, UserRole.ADMIN), "A must be ADMIN"
        user_b = UserManager.create(name=f"tc_user_b_{run}")
        user_c = UserManager.create(name=f"tc_user_c_{run}")
        assert user_b.role == UserRole.BASIC
        assert user_c.role == UserRole.BASIC
        results["1_create_users"] = "PASS"

        # Guardrail baseline (as admin) BEFORE creating anything team-related.
        baseline_team_count = len(_teams_get(admin_a))
        print(f"Baseline pre-existing team count: {baseline_team_count}")

        # -- 2. CREATE team -------------------------------------------------- #
        team_name = f"tc-eng-{run}"
        created = _team_create(
            admin_a,
            {
                "name": team_name,
                "description": "engineering team",
                "is_public": False,
                "tags": ["Engineering"],
                "user_ids": [user_b.id],
                "cc_pair_ids": [],
            },
        )
        team_id = created["id"]
        assert created["name"] == team_name
        assert created["description"] == "engineering team"
        assert created["is_public"] is False
        assert created["tags"] == ["Engineering"]
        # owner == A
        assert created["owner"] is not None and created["owner"]["id"] == str(
            admin_a.id
        ), created["owner"]
        # creator A is an OWNER member
        mem_a = _member(created, admin_a.id)
        assert mem_a is not None and mem_a["role"] == TeamRole.OWNER.value, mem_a
        # B is a MEMBER with joined_at + source set
        mem_b = _member(created, user_b.id)
        assert mem_b is not None, "B should be a member"
        assert mem_b["role"] == TeamRole.MEMBER.value, mem_b
        assert mem_b["joined_at"] is not None, "joined_at should be set"
        assert mem_b["source"] == MembershipSource.MANUAL.value, mem_b
        # counts present + coherent
        assert created["member_count"] == len(created["members"]) == 2, created
        assert created["kb_count"] == 0, created
        results["2_create_team"] = "PASS"

        # -- 3. ADD members (C as MEMBER) ------------------------------------ #
        added = _team_add_users(
            admin_a, team_id, {"user_ids": [user_c.id], "role": "MEMBER"}
        )
        mem_c = _member(added, user_c.id)
        assert mem_c is not None and mem_c["role"] == TeamRole.MEMBER.value, added
        assert added["member_count"] == 3, added
        results["3_add_member"] = "PASS"

        # -- 4. CHANGE role (C -> ADMIN) + is_curator DB sync ---------------- #
        # NOTE: the /set-role endpoint returns 200 with an empty body, so we
        # verify the effect via a re-GET (role) and a direct DB read (is_curator).
        _team_set_role(admin_a, team_id, {"user_id": user_c.id, "role": "ADMIN"})
        reget = _team_get(admin_a, team_id)
        mem_c = _member(reget, user_c.id)
        assert mem_c is not None and mem_c["role"] == TeamRole.ADMIN.value, mem_c
        c_is_curator = _db_is_curator(team_id, user_c.id)
        assert c_is_curator is True, f"user__team.is_curator for C should be True, got {c_is_curator}"
        # curator_ids in the enriched response should also list C
        assert str(user_c.id) in {str(x) for x in reget["curator_ids"]}, reget[
            "curator_ids"
        ]
        results["4_change_role"] = "PASS"

        # -- 5. UPDATE settings ---------------------------------------------- #
        _team_patch(
            admin_a,
            team_id,
            {
                "description": "updated",
                "is_public": True,
                "tags": ["Eng", "Platform"],
                "default_member_role": "MEMBER",
                "allow_guest_access": True,
            },
        )
        after = _team_get(admin_a, team_id)
        assert after["description"] == "updated", after
        assert after["is_public"] is True, after
        assert after["tags"] == ["Eng", "Platform"], after
        assert after["default_member_role"] == TeamRole.MEMBER.value, after
        assert after["allow_guest_access"] is True, after
        results["5_update_settings"] = "PASS"

        # -- 6. REMOVE member (C); B + owner A remain ------------------------ #
        current_cc_ids = [cc["id"] for cc in after["cc_pairs"]]
        removed = _team_patch(
            admin_a,
            team_id,
            {"user_ids": [user_b.id], "cc_pair_ids": current_cc_ids},
        )
        assert _member(removed, user_c.id) is None, "C should be removed"
        assert _member(removed, user_b.id) is not None, "B should remain"
        assert _member(removed, admin_a.id) is not None, "owner A must remain"
        assert (
            _member(removed, admin_a.id)["role"] == TeamRole.OWNER.value
        ), "A must still be OWNER"
        results["6_remove_member"] = "PASS"

        # -- 6b. promote B to curator so B can own the USER-KB credential ---- #
        # (credential creation requires curator/admin; B is otherwise a MEMBER)
        _team_set_curator(admin_a, team_id, {"user_id": user_b.id, "is_curator": True})
        assert _db_is_curator(team_id, user_b.id) is True

        # -- 7. OpenSearch ACL ---------------------------------------------- #
        api_key = APIKeyManager.create(user_performing_action=admin_a)

        public_cc = _make_cc_pair(
            name=f"tc-public-{run}",
            access_type=AccessType.PUBLIC,
            groups=[],
            connector_owner=admin_a,
            credential_owner=admin_a,
        )
        team_cc = _make_cc_pair(
            name=f"tc-team-{run}",
            access_type=AccessType.PRIVATE,
            groups=[team_id],
            connector_owner=admin_a,
            credential_owner=admin_a,
        )
        kb_cc = _make_cc_pair(
            name=f"tc-kb-{run}",
            access_type=AccessType.PRIVATE,
            groups=[],
            connector_owner=admin_a,
            credential_owner=user_b,  # B owns the credential => user_email:<B>
        )
        created_cc_pairs = [public_cc, team_cc, kb_cc]

        public_doc = DocumentManager.seed_doc_with_content(
            cc_pair=public_cc, content=f"{SEARCH_ANCHOR} {MARKER_PUBLIC}", api_key=api_key
        )
        team_doc = DocumentManager.seed_doc_with_content(
            cc_pair=team_cc, content=f"{SEARCH_ANCHOR} {MARKER_TEAM}", api_key=api_key
        )
        kb_doc = DocumentManager.seed_doc_with_content(
            cc_pair=kb_cc, content=f"{SEARCH_ANCHOR} {MARKER_KB}", api_key=api_key
        )
        public_cc.documents = [public_doc]
        team_cc.documents = [team_doc]
        kb_cc.documents = [kb_doc]

        email_a = f"user_email:{admin_a.email}"
        email_b = f"user_email:{user_b.email}"
        team_key = f"team:{team_name}"

        acl_public = _wait_for_index_acl(doc_index, public_doc.id, {"PUBLIC", email_a})
        acl_team = _wait_for_index_acl(doc_index, team_doc.id, {team_key, email_a})
        acl_kb = _wait_for_index_acl(doc_index, kb_doc.id, {email_b})
        print(f"ACL public_doc={sorted(acl_public)}")
        print(f"ACL team_doc={sorted(acl_team)}")
        print(f"ACL kb_doc={sorted(acl_kb)}")

        all_ids = {public_doc.id, team_doc.id, kb_doc.id}
        seen_a = _search_doc_ids(SEARCH_ANCHOR, admin_a) & all_ids
        seen_b = _search_doc_ids(SEARCH_ANCHOR, user_b) & all_ids
        seen_c = _search_doc_ids(SEARCH_ANCHOR, user_c) & all_ids
        print(f"search A={sorted(seen_a)} B={sorted(seen_b)} C={sorted(seen_c)}")

        # B (team member + KB owner): public + team + own
        assert seen_b == {public_doc.id, team_doc.id, kb_doc.id}, seen_b
        # C (non-member now): public only
        assert seen_c == {public_doc.id}, seen_c
        # A (admin/owner; owns public+team creds, not KB): public + team
        assert seen_a == {public_doc.id, team_doc.id}, seen_a
        results["7_opensearch_acl"] = "PASS"

        # -- 8. DELETE team (async via celery) ------------------------------ #
        _team_delete(admin_a, team_id)
        _wait_team_absent(admin_a, team_id)
        team_deleted = True
        results["8_delete_team"] = "PASS"

        print("PER-STEP RESULTS:", results)

    finally:
        # ------------------------------------------------------------------ #
        # Cleanup — always runs. Order: cc_pairs (docs) -> connectors/creds ->
        # api key -> team -> users. Each step best-effort so one failure does not
        # strand the rest.
        # ------------------------------------------------------------------ #
        admin = admin_a

        # cc_pairs (deletion-attempt removes the cc_pair + its indexed docs)
        for cc in created_cc_pairs:
            try:
                requests.post(
                    url=f"{API_SERVER_URL}/nexus/admin/deletion-attempt",
                    json={
                        "connector_id": cc.connector_id,
                        "credential_id": cc.credential_id,
                    },
                    headers=admin.headers if admin else {},
                ).raise_for_status()
            except Exception as e:
                print(f"[cleanup] cc_pair {cc.id} deletion-attempt failed: {e}")

        # wait for cc_pair deletions to finish so connector/credential deletes
        # do not 400 on an attached-cc_pair
        for cc in created_cc_pairs:
            deadline = time.time() + MAX_DELAY
            while time.time() < deadline:
                try:
                    r = requests.post(
                        f"{API_SERVER_URL}/nexus/admin/connector/indexing-status",
                        headers=admin.headers if admin else {},
                        json={"get_all_connectors": True},
                    )
                    r.raise_for_status()
                    present = any(
                        conn["cc_pair_id"] == cc.id
                        for grp in r.json()
                        for conn in grp["indexing_statuses"]
                    )
                    if not present:
                        break
                except Exception as e:
                    print(f"[cleanup] indexing-status poll failed: {e}")
                    break
                time.sleep(3)

        # connectors + credentials
        for cc in created_cc_pairs:
            try:
                requests.delete(
                    f"{API_SERVER_URL}/nexus/admin/connector/{cc.connector_id}",
                    headers=admin.headers if admin else {},
                )
            except Exception as e:
                print(f"[cleanup] connector {cc.connector_id} delete failed: {e}")
            try:
                requests.delete(
                    f"{API_SERVER_URL}/nexus/credential/{cc.credential_id}",
                    headers=admin.headers if admin else {},
                )
            except Exception as e:
                print(f"[cleanup] credential {cc.credential_id} delete failed: {e}")

        # api key
        if api_key is not None and admin is not None:
            try:
                APIKeyManager.delete(api_key, user_performing_action=admin)
            except Exception as e:
                print(f"[cleanup] api key delete failed: {e}")

        # team (if still present)
        if team_id is not None and not team_deleted and admin is not None:
            try:
                _team_delete(admin, team_id)
                _wait_team_absent(admin, team_id)
            except Exception as e:
                print(f"[cleanup] team {team_id} delete failed: {e}")

        # users: B, C via REST (deactivate then delete); A via DB (cannot self)
        for u in (user_b, user_c):
            if u is None or admin is None:
                continue
            try:
                requests.patch(
                    f"{API_SERVER_URL}/nexus/admin/deactivate-user",
                    json={"user_email": u.email},
                    headers=admin.headers,
                ).raise_for_status()
                requests.delete(
                    f"{API_SERVER_URL}/nexus/admin/delete-user",
                    json={"user_email": u.email},
                    headers=admin.headers,
                ).raise_for_status()
            except Exception as e:
                print(f"[cleanup] user {u.email} delete failed: {e}")
        if admin_a is not None:
            try:
                _db_deactivate_and_basic(admin_a)
            except Exception as e:
                print(f"[cleanup] admin A neutralize failed: {e}")

        # ------------------------------------------------------------------ #
        # Guardrail: pre-existing team count preserved (nothing clobbered).
        # ------------------------------------------------------------------ #
        if baseline_team_count is not None:
            with get_session_with_current_tenant() as db:
                from om.db.team import fetch_teams

                final_count = len(fetch_teams(db, only_up_to_date=False))
            print(
                f"GUARDRAIL: baseline_team_count={baseline_team_count} "
                f"final_team_count={final_count}"
            )
            assert final_count == baseline_team_count, (
                f"Pre-existing team count changed: {baseline_team_count} -> "
                f"{final_count} (data may have been clobbered)"
            )
