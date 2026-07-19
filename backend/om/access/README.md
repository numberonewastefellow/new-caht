# Access — document ACL resolution (Contract 2)

This module turns "who may access this document?" into the concrete data the
search index filters on. It is the load-bearing bridge between the RBAC layer
(`rbac/README.md`) and search.

## How access is enforced (early-binding + set-intersection)

Each document is indexed with a flat, multi-valued `access_control_list` field
(plus an `is_public` boolean). At query time a user is expanded into their set of
**principal strings**; a document is returned iff its ACL shares **at least one**
principal with the user's set. This is the enterprise-standard model (Elastic
DLS, Amazon Kendra, Microsoft Graph connectors) and **early-binding** — the
security filter is applied inside the query, not by post-filtering results, so
pagination and facet counts stay correct.

Two directions, one encoding (`utils.py`):

```
write-side:  DocumentAccess.build(...).to_acl()   -> stamped into the index
read-side:   get_acl_for_user(user, db)           -> query access filter
```

Both MUST use the same encoders or matching silently fails.

## Principal encoding (team rename — Contract 2)

| principal | encoder | string |
|-----------|---------|--------|
| internal user / external user email | `prefix_user_email` | `user_email:<email>` |
| internal **team** | `prefix_team` | `team:<name>` |
| external (source-synced) group | `prefix_external_team` | `external_team:<id>` |
| public | — | `PUBLIC` (`PUBLIC_DOC_PAT`) |

The old `group:` / `external_group:` encodings are gone. External group ids are
namespaced per source by `build_ext_team_name_for_om` so ids can't collide across
connectors. Because the DB and index are **fresh** (greenfield), this rename
needs **no reindex** — see `DO_NOT_RENAME.md`.

## Public API (frozen — Contract 2)

WS-D / WS-E and the indexing/search pipeline import ONLY these; bodies are the
WS-B clean-room rewrite:

- `get_access_for_document(document_id, db_session) -> DocumentAccess`
- `get_access_for_documents(document_ids, db_session) -> dict[str, DocumentAccess]`
- `get_acl_for_user(user, db_session=None) -> set[str]`
- `get_access_for_knowledge_files(knowledge_file_ids, db_session) -> dict[str, DocumentAccess]`
- `source_should_fetch_permissions_during_indexing(source) -> bool`
- `om.context.search.preprocessing.access_filters.build_access_filters_for_user(user, session) -> list[str]`

`DocumentAccess` / `ExternalAccess` (frozen dataclasses) carry `teams` and
`external_team_ids` (renamed from `user_groups` / `external_user_group_ids`).

## Resolution logic

`get_access_for_documents` composes a document's principals from:
1. the always-on subset (owner emails + public flag) from `get_access_info_for_documents`;
2. internal **teams** granted via non-SYNC connectors (`om.db.team.fetch_teams_for_documents`);
3. externally-synced principals stored on the document (`external_user_emails`,
   `external_team_ids`) plus public-external-team overlap;
4. a "public during search" flag for **censoring-only** sources (their access is
   enforced afterwards by post-query censoring, so retrieval must not hide them).

Documents not yet indexed fall back to `get_null_document_access()`
(least-permissive) so the flow never fails on a missing row.

## Index field

`om/document_index/opensearch/schema.py`: `ACCESS_CONTROL_LIST_FIELD_NAME =
"access_control_list"` (keyword list) + `is_public`. Field **names** are
unchanged; only the prefixes *inside* the list changed to team-based. The
per-document group columns `document.external_team_ids` /
`hierarchy_node.external_team_ids` were renamed from `external_user_group_ids`.

## Circular-import note

`get_acl_for_user` / `_resolve_access_for_documents` import `om.db.team` and
`om.external_permissions.sync_params` **lazily (at call time)** on purpose: both
transitively import back into this module, and a top-level import is a hard cycle
that takes down every celery worker at autodiscovery. Keep those imports inside
the functions.

## Multi-tenant readiness

Every function takes a caller-supplied tenant-bound `Session`; no global tenant
reads, no cross-tenant access. See Contract 3.

## Tests

- `tests/unit/om/access/test_acl_parity.py` — write-side/read-side round-trip,
  team-based prefixes, and the allow/deny matrix on a fixed corpus.
- `tests/unit/om/access/test_rbac.py` — the RBAC matrix + PDP.

## Research

Document-ACL + early-binding + external-group sync/censoring references:
https://www.elastic.co/docs/reference/search-connectors/es-dls-overview ·
https://docs.aws.amazon.com/kendra/latest/dg/user-context-filter.html ·
https://www.sinequa.com/resources/blog/data-access-security-management-the-enterprise-search-challenge/ ·
https://learn.microsoft.com/en-us/azure/search/search-query-access-control-rbac-enforcement
