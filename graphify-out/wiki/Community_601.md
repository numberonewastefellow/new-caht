# Community 601

> 25 nodes · cohesion 0.14

## Key Concepts

- **_perform_external_group_sync()** (23 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **external_perm.py** (12 connections) — `backend/om/db/external_perm.py`
- **Session** (9 connections) — `backend/om/db/external_perm.py`
- **upsert_external_groups()** (9 connections) — `backend/om/db/external_perm.py`
- **fetch_external_teams_for_user()** (7 connections) — `backend/om/db/external_perm.py`
- **mark_all_relevant_cc_pairs_as_external_group_synced()** (7 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **_get_all_cc_pair_ids_to_mark_as_group_synced()** (6 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **fetch_external_teams_for_user_email_and_team_ids()** (5 connections) — `backend/om/db/external_perm.py`
- **_fail_external_group_sync_attempt()** (5 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **User__ExternalTeamId** (3 connections) — `backend/om/db/external_perm.py`
- **UUID** (3 connections) — `backend/om/db/external_perm.py`
- **delete_user__ext_team_for_user__no_commit()** (3 connections) — `backend/om/db/external_perm.py`
- **fetch_public_external_team_ids()** (3 connections) — `backend/om/db/external_perm.py`
- **mark_old_external_groups_as_stale()** (3 connections) — `backend/om/db/external_perm.py`
- **remove_stale_external_groups()** (3 connections) — `backend/om/db/external_perm.py`
- **ConnectorCredentialPair** (2 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **Session** (2 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **delete_public_external_team_for_cc_pair__no_commit()** (2 connections) — `backend/om/db/external_perm.py`
- **delete_user__ext_team_for_cc_pair__no_commit()** (2 connections) — `backend/om/db/external_perm.py`
- **group_sync_utils.py** (2 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **DocumentSource** (1 connections) — `backend/om/db/external_perm.py`
- **Persistence for externally-synced group memberships.  Connectors that sync sou** (1 connections) — `backend/om/db/external_perm.py`
- **Upsert external-team membership (and public-external-team) rows, clearing     t** (1 connections) — `backend/om/db/external_perm.py`
- **For some source types, one successful group sync run should count for all     cc** (1 connections) — `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- **Helper to mark an external group sync attempt as failed with an error message.** (1 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`

## Relationships

- [[Community 533]] (7 shared connections)
- [[Community 218]] (5 shared connections)
- [[Community 59]] (4 shared connections)
- [[Community 320]] (2 shared connections)
- [[Community 217]] (2 shared connections)
- [[Community 443]] (2 shared connections)
- [[Community 120]] (2 shared connections)
- [[Document External Access]] (2 shared connections)
- [[Backend Agent/API Test Fixtures]] (2 shared connections)
- [[Community 802]] (1 shared connections)
- [[Community 362]] (1 shared connections)
- [[Community 304]] (1 shared connections)

## Source Files

- `backend/om/background/celery/tasks/external_group_syncing/group_sync_utils.py`
- `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- `backend/om/db/external_perm.py`

## Audit Trail

- EXTRACTED: 79 (68%)
- INFERRED: 37 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*