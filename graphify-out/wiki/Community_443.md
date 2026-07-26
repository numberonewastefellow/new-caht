# Community 443

> 34 nodes · cohesion 0.13

## Key Concepts

- **get_user_by_email()** (19 connections) — `backend/om/db/users.py`
- **users.py** (15 connections) — `backend/om/db/users.py`
- **User** (11 connections) — `backend/om/db/users.py`
- **Session** (10 connections) — `backend/om/db/users.py`
- **delete_user_from_db()** (9 connections) — `backend/om/db/users.py`
- **test_delete_user.py** (7 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **batch_add_ext_perm_user_if_not_exists()** (7 connections) — `backend/om/db/users.py`
- **_mock_user()** (6 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **add_slack_user_if_not_exists()** (6 connections) — `backend/om/db/users.py`
- **_get_accepted_user_where_clause()** (6 connections) — `backend/om/db/users.py`
- **get_page_of_filtered_users()** (6 connections) — `backend/om/db/users.py`
- **UserRole** (5 connections) — `backend/om/db/users.py`
- **test_delete_user_commits_and_removes_invited()** (5 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **test_delete_user_deletes_oauth_accounts()** (5 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **fetch_user_by_id()** (5 connections) — `backend/om/db/users.py`
- **get_total_filtered_users_count()** (5 connections) — `backend/om/db/users.py`
- **_get_users_by_emails()** (5 connections) — `backend/om/db/users.py`
- **validate_user_role_update()** (5 connections) — `backend/om/db/users.py`
- **Any** (4 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **_make_query_chain()** (4 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **test_delete_user_cleans_up_join_tables()** (4 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **test_delete_user_nulls_out_document_set_ownership()** (4 connections) — `backend/tests/unit/om/db/test_delete_user.py`
- **get_all_users()** (4 connections) — `backend/om/db/users.py`
- **UUID** (3 connections) — `backend/om/db/users.py`
- **_generate_ext_permissioned_user()** (3 connections) — `backend/om/db/users.py`
- *... and 9 more nodes in this community*

## Relationships

- [[Community 137]] (9 shared connections)
- [[User Roles & Agent Config]] (5 shared connections)
- [[Community 127]] (4 shared connections)
- [[Community 601]] (2 shared connections)
- [[Community 275]] (2 shared connections)
- [[Community 83]] (1 shared connections)
- [[Community 303]] (1 shared connections)
- [[Community 362]] (1 shared connections)
- [[Community 599]] (1 shared connections)
- [[Community 70]] (1 shared connections)
- [[Community 143]] (1 shared connections)
- [[Community 291]] (1 shared connections)

## Source Files

- `backend/om/db/users.py`
- `backend/tests/unit/om/db/test_delete_user.py`

## Audit Trail

- EXTRACTED: 138 (78%)
- INFERRED: 38 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*