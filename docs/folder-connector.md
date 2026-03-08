# Folder Connector — Enterprise-Grade Implementation Plan

## Context

The existing File Connector uploads files to FileStore (Postgres/S3), then reads them back during indexing. We need to index **local filesystem folders** directly — point at one or more directories, recursively scan all supported files, and feed them through the same ingestion pipeline with **full access control** (PUBLIC / PRIVATE / SYNC) matching Google Drive's security model, fully integrated into the search pipeline, document sets, and knowledge base.

---

## Architecture Overview

```text
[Admin UI: Add Folders + Access Control (PUBLIC/PRIVATE/SYNC + UserGroups)]
   -> POST /api/connector (folder_paths, access_type, groups)
   -> PUT /connector/{id}/credential/{id} (access_type, groups stored on CC Pair)
        |
[Celery beat: check-for-indexing every 15s]
        |
[Docfetching task: LocalFolderConnector.poll_source()]
   -> os.walk() recursive scan
   -> parallel file extraction (thread pool, 4 workers)
   -> yield Document batches (with per-doc ExternalAccess when SYNC mode)
        |
[Docprocessing tasks (1 per batch, parallel via Celery)]
   -> chunking -> embedding -> Vespa/OpenSearch insertion (source="folder" stored per doc)
        |
[Search pipeline: source_type filter includes "folder"]
   -> BaseFilters.source_type uses DocumentSource enum -> auto-supports FOLDER
   -> Vespa/OpenSearch queries filter by source field -> auto-supports FOLDER
   -> Document sets containing folder CC pairs -> auto-included in search scope
        |
[Permission sync tasks (when access_type=SYNC, EE only)]
   -> check-for-doc-permissions-sync (every 30s)
   -> check-for-external-group-sync (every 20s)
   -> Reads OS file ACLs -> maps to ExternalAccess -> updates Vespa ACLs
```

Two levels of parallelism:

1. **Within-batch**: `run_functions_tuples_in_parallel()` for file extraction (thread pool)
2. **Across-batches**: Each batch is a separate Celery docprocessing task

---

## Search Pipeline & Document Set Integration

### Why most of the pipeline requires NO code changes

The search and indexing pipeline is **enum-driven**. When a document is indexed, its `source` field is stored as a string (e.g., `"folder"`) in both Vespa and OpenSearch. The search pipeline filters by `DocumentSource` enum values dynamically — no hardcoded source lists. Specifically:

| Component | File | How FOLDER is handled |
| --- | --- | --- |
| **Search filters** | `backend/onyx/context/search/models.py` | `BaseFilters.source_type: list[DocumentSource]` — auto-includes FOLDER |
| **Search pipeline** | `backend/onyx/context/search/pipeline.py` | Source filtering via enum, no hardcoded lists |
| **Source string parsing** | `backend/onyx/secondary_llm_flows/source_filter.py` | `strings_to_document_sources()` auto-converts `"folder"` to enum |
| **Vespa queries** | `backend/onyx/document_index/vespa/shared_utils/vespa_request_builders.py` | Extracts source string from `filters.source_type` — auto-works |
| **OpenSearch queries** | `backend/onyx/document_index/opensearch/opensearch_document_index.py` | `DocumentSource(chunk.source_type)` — auto-converts |
| **Document sets** | `backend/onyx/db/document_set.py` | Links to CC pairs (not source types) — auto-works when folder CC pair is added to a set |
| **Persona/assistant filtering** | `backend/onyx/server/features/persona/models.py` | Filters via document sets which link to CC pairs — auto-works |
| **Knowledge base UI** | `web/src/sections/knowledge/AgentKnowledgePane.tsx` | Shows collections/doc sets — folder CC pairs appear automatically |
| **Connector validation** | `backend/onyx/server/documents/connector.py` | `ENABLED_CONNECTOR_TYPES` env var — FOLDER auto-validated if enabled |
| **Indexing status** | `backend/onyx/server/documents/connector.py` | Uses `cc_pair.connector.source` dynamically — auto-shows FOLDER |
| **Source selector filter UI** | `web/src/components/filters/SourceSelector.tsx` | Pulls available sources from indexed data — auto-includes FOLDER |

### What DOES need explicit changes

These places have **hardcoded lists or maps** that must be updated:

| What | File | Change needed |
| --- | --- | --- |
| `DocumentSourceDescription` dict | `backend/onyx/configs/constants.py` | Add `DocumentSource.FOLDER: "local folder — recursive file indexing from filesystem directories"` |
| `isLoadState()` function | `web/src/lib/connectors/connectors.tsx` | Do NOT add `"folder"` — folder uses PollConnector (not load-only) |
| `_SOURCE_TO_SYNC_CONFIG` (EE) | `backend/ee/onyx/external_permissions/sync_params.py` | Add `DocumentSource.FOLDER` entry with `folder_doc_sync` function |
| `validAutoSyncSources` array | `web/src/lib/types.ts` | Add `ValidSources.Folder` to enable SYNC option in UI |

---

## Security & Access Control Model

### How It Works (Same as Google Drive)

The platform has 3 access modes stored on `ConnectorCredentialPair.access_type`:

| Mode | Behavior | Who Can See Documents |
| --- | --- | --- |
| **PUBLIC** | All documents visible to everyone | All authenticated users |
| **PRIVATE** | Documents scoped to selected user groups | Only users in assigned UserGroups |
| **SYNC** | Per-document permissions synced from source (EE) | Based on OS file ACLs (owner, group, others) |

### Access Control Flow (existing infrastructure, no changes needed)

1. **Frontend**: `AccessTypeForm` (already in `DynamicConnectorCreationForm`) lets admin pick PUBLIC/PRIVATE/SYNC
2. **Frontend**: `AccessTypeGroupSelector` lets admin pick UserGroups when PRIVATE is selected
3. **Backend**: `access_type` + `groups[]` sent via `ConnectorCredentialPairMetadata`
4. **Backend**: Stored on `ConnectorCredentialPair.access_type` + linked via `UserGroup__ConnectorCredentialPair`
5. **Query time**: `apply_document_access_filter()` in `backend/onyx/db/document_access.py` enforces visibility

### SYNC Mode — OS Permission Mapping (New, EE only)

For folders, SYNC mode reads OS-level file permissions and maps to `ExternalAccess`:

```python
# In folder/connector.py
def _get_file_external_access(file_path: str) -> ExternalAccess:
    stat = os.stat(file_path)
    owner_email = _resolve_uid_to_email(stat.st_uid)   # via pwd/LDAP
    group_id = _resolve_gid_to_group(stat.st_gid)      # via grp module
    is_public = bool(stat.st_mode & 0o004)              # world-readable

    return ExternalAccess(
        external_user_emails={owner_email} if owner_email else set(),
        external_user_group_ids={f"folder__{group_id}"} if group_id else set(),
        is_public=is_public,
    )
```

On **Windows**: Uses `win32security` to read file DACLs, maps SIDs to usernames/groups.

Permission sync uses existing infrastructure:

- Initial indexing with `include_permissions=True` (controlled by `backend/onyx/background/indexing/run_docfetching.py`)
- Periodic sync via `RedisConnectorPermissionSync` (runs every 30s for SYNC connectors)
- Tracking via `DocPermissionSyncAttempt` (`backend/onyx/db/models.py`)

### Key Security Files (existing, reused as-is)

| File | Purpose |
| --- | --- |
| `web/src/components/admin/connectors/AccessTypeForm.tsx` | UI for PUBLIC/PRIVATE/SYNC selection |
| `web/src/components/admin/connectors/AccessTypeGroupSelector.tsx` | UI for UserGroup assignment (PRIVATE mode) |
| `backend/onyx/access/models.py` | `ExternalAccess`, `DocExternalAccess`, `DocumentAccess` |
| `backend/onyx/db/enums.py` | `AccessType` enum (PUBLIC/PRIVATE/SYNC) |
| `backend/onyx/db/document_access.py` | Query-time access filtering |
| `backend/onyx/db/connector_credential_pair.py` | CC Pair creation with access_type + groups |
| `backend/onyx/redis/redis_connector_doc_perm_sync.py` | Async permission sync coordination |

---

## Backend Changes

### 1. Add `FOLDER` to DocumentSource enum + description

**File**: `backend/onyx/configs/constants.py`

- Add `FOLDER = "folder"` after `FILE = "file"`
- Add `DocumentSource.FOLDER` to `DocumentSourceRequiringTenantContext`
- Add to `DocumentSourceDescription` dict:

  ```python
  DocumentSource.FOLDER: "local folder — recursive file indexing from filesystem directories",
  ```

### 2. Add config variables

**File**: `backend/onyx/configs/app_configs.py`

```python
# Folder Connector settings
FOLDER_CONNECTOR_ALLOWED_DIRECTORIES = os.environ.get(
    "FOLDER_CONNECTOR_ALLOWED_DIRECTORIES", ""
)  # comma-separated whitelist; empty = all paths allowed
FOLDER_CONNECTOR_MAX_WORKERS = int(os.environ.get("FOLDER_CONNECTOR_MAX_WORKERS", "4"))
FOLDER_CONNECTOR_MAX_FILE_SIZE_MB = int(os.environ.get("FOLDER_CONNECTOR_MAX_FILE_SIZE_MB", "100"))
```

### 3. Extract shared utils from File Connector

**New file**: `backend/onyx/connectors/file/utils.py`

- Move `_process_file()` and `_create_image_section()` from `backend/onyx/connectors/file/connector.py`
- Update imports in `file/connector.py` to use `from onyx.connectors.file.utils import _process_file, _create_image_section`

### 4. Create Folder Connector

**New files**:

- `backend/onyx/connectors/folder/__init__.py` (empty)
- `backend/onyx/connectors/folder/connector.py`

```python
class LocalFolderConnector(LoadConnector, PollConnector, SlimConnector):
    """
    Reads local filesystem folders recursively.
    Supports parallel extraction and OS-level permission syncing.
    """
    def __init__(
        self,
        folder_paths: list[str],
        file_extensions: list[str] | None = None,
        recursive: bool = True,
        follow_symlinks: bool = False,
        exclude_patterns: list[str] | None = None,
        max_file_size_mb: int | None = None,
        batch_size: int = INDEX_BATCH_SIZE,
    )

    def load_credentials(credentials) -> None
    def load_from_state() -> GenerateDocumentsOutput       # full scan
    def poll_source(start, end) -> GenerateDocumentsOutput  # mtime-filtered incremental
    def retrieve_all_slim_docs() -> GenerateSlimDocumentOutput  # for pruning deleted files
    def validate_connector_settings() -> None               # path + security validation
    def _get_file_external_access(file_path) -> ExternalAccess  # OS perms -> ACL
```

**Key implementation details**:

- **Directory walking**: `os.walk()` with `pathlib.Path` for cross-platform
- **Path security**: Validate against `FOLDER_CONNECTOR_ALLOWED_DIRECTORIES` via `os.path.realpath()`
- **File filtering**: Extension check vs `OnyxFileExtensions.ALL_ALLOWED_EXTENSIONS`, `exclude_patterns` via `fnmatch`, size limit
- **mtime filtering**: `os.path.getmtime()` for incremental polling
- **Parallel extraction**: `run_functions_tuples_in_parallel()` from `backend/onyx/utils/threadpool_concurrency.py` with `max_workers=FOLDER_CONNECTOR_MAX_WORKERS`
- **Document ID**: `f"FOLDER_CONNECTOR__{sha256(abs_path)}"` for stable IDs
- **Reuses**: `_process_file()` from `file/utils.py`
- **Error handling**: Per-file try/except, log and continue
- **SlimConnector**: Enables pruning of deleted files from index
- **Permission sync**: Reads OS ACLs when `include_permissions=True`

### 5. Register connector

**File**: `backend/onyx/connectors/registry.py`

```python
DocumentSource.FOLDER: ConnectorMapping(
    module_path="onyx.connectors.folder.connector",
    class_name="LocalFolderConnector",
),
```

### 6. Add SYNC config (EE — permission sync registration)

**New file**: `backend/onyx/connectors/folder/doc_sync.py`

```python
def folder_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: FetchAllDocumentsFunction,
    fetch_all_existing_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: IndexingHeartbeatInterface | None,
) -> Generator[DocExternalAccess, None, None]:
    """Re-read OS file permissions for docs and yield updated ACLs."""
```

**File to modify**: `backend/ee/onyx/external_permissions/sync_params.py`

```python
DocumentSource.FOLDER: SyncConfig(
    doc_sync_config=DocSyncConfig(
        doc_sync_frequency=DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY,
        doc_sync_func=folder_doc_sync,
        initial_index_should_sync=True,
    ),
    # No group_sync_config — OS groups mapped directly per-doc
),
```

### Reference patterns

- `backend/onyx/connectors/blob/connector.py` — `BlobStorageConnector` (Load + Poll with mtime)
- `backend/onyx/connectors/google_drive/connector.py` — Permission syncing with `include_permissions` flag
- `backend/ee/onyx/external_permissions/sync_params.py` — SyncConfig registration pattern

---

## Frontend Changes

### 7. Add `Folder` to ValidSources enum

**File**: `web/src/lib/types.ts`

- Add `Folder = "folder"` after `File = "file"`
- Add `ValidSources.Folder` to `validAutoSyncSources` array — enables SYNC option in AccessTypeForm

### 8. Add source metadata

**File**: `web/src/lib/sources.ts`

```typescript
folder: {
    icon: SvgFolder,
    displayName: "Local Folder",
    category: SourceCategory.Storage,
    docs: `${DOCS_ADMINS_PATH}/connectors/official/folder`,
    isPopular: false,
},
```

### 9. Add connector form configuration

**File**: `web/src/lib/connectors/connectors.tsx`

```typescript
folder: {
    description: "Configure Local Folder connector",
    values: [
        {
            type: "list",
            label: "Folder Paths",
            name: "folder_paths",
            optional: false,
            description: "Absolute paths to directories (e.g., /data/docs, /mnt/shared)",
        },
        {
            type: "checkbox",
            label: "Recursive Scan",
            name: "recursive",
            optional: true,
            default: true,
        },
    ],
    advanced_values: [
        { type: "list", label: "File Extensions Filter", name: "file_extensions", optional: true,
          description: "e.g., .pdf, .docx, .md (empty = all supported)" },
        { type: "list", label: "Exclude Patterns", name: "exclude_patterns", optional: true,
          description: "Glob patterns (e.g., *.tmp, __pycache__, .git)" },
        { type: "checkbox", label: "Follow Symlinks", name: "follow_symlinks", default: false, optional: true },
        { type: "number", label: "Max File Size (MB)", name: "max_file_size_mb", default: 100, optional: true },
    ],
    overrideDefaultFreq: 3600,
},
```

Note: Do NOT add `"folder"` to `isLoadState()` — folder uses PollConnector (incremental), not load-only.

### 10. Add credential template

**File**: `web/src/lib/connectors/credentials.ts`

```typescript
folder: null,  // dummy credential (same as file connector)
```

### 11. Source colors

**File**: `web/src/lib/sourceColors.ts` — category-based, auto-handled via `SourceCategory.Storage` (emerald palette). No changes needed.

---

## Complete File Change Summary

| Action | File | What |
| --- | --- | --- |
| **Create** | `backend/onyx/connectors/folder/__init__.py` | Package init (empty) |
| **Create** | `backend/onyx/connectors/folder/connector.py` | `LocalFolderConnector` (Load + Poll + Slim + Permissions) |
| **Create** | `backend/onyx/connectors/folder/doc_sync.py` | Permission sync function for SYNC mode |
| **Create** | `backend/onyx/connectors/file/utils.py` | Shared `_process_file` + `_create_image_section` |
| **Modify** | `backend/onyx/connectors/file/connector.py` | Update imports to use `file/utils.py` |
| **Modify** | `backend/onyx/configs/constants.py` | Add `FOLDER` enum + `DocumentSourceDescription` + tenant context |
| **Modify** | `backend/onyx/configs/app_configs.py` | Add 3 env vars |
| **Modify** | `backend/onyx/connectors/registry.py` | Add FOLDER mapping |
| **Modify** | `backend/ee/onyx/external_permissions/sync_params.py` | Add FOLDER to `_SOURCE_TO_SYNC_CONFIG` |
| **Modify** | `web/src/lib/types.ts` | Add `Folder` to `ValidSources` + `validAutoSyncSources` |
| **Modify** | `web/src/lib/sources.ts` | Add folder source metadata |
| **Modify** | `web/src/lib/connectors/connectors.tsx` | Add folder form config |
| **Modify** | `web/src/lib/connectors/credentials.ts` | Add `folder: null` |

### Files that need NO changes (auto-handled via enum)

| File | Why no change needed |
| --- | --- |
| `backend/onyx/context/search/models.py` | `BaseFilters.source_type` uses `list[DocumentSource]` |
| `backend/onyx/context/search/pipeline.py` | Source filtering via enum |
| `backend/onyx/secondary_llm_flows/source_filter.py` | `strings_to_document_sources()` auto-converts |
| `backend/onyx/document_index/vespa/` | Source stored as string, filtered dynamically |
| `backend/onyx/document_index/opensearch/` | `DocumentSource(chunk.source_type)` auto-converts |
| `backend/onyx/db/document_set.py` | Links to CC pairs, not source types |
| `backend/onyx/server/features/persona/` | Filters via document sets -> CC pairs |
| `backend/onyx/server/documents/connector.py` | Indexing status uses `cc_pair.connector.source` dynamically |
| `backend/onyx/db/document_access.py` | Access filtering via `access_type`, not source |
| `web/src/components/filters/SourceSelector.tsx` | Pulls sources from indexed data dynamically |
| `web/src/sections/knowledge/` | Shows document sets, auto-includes folder CC pairs |
| `web/src/lib/sourceColors.ts` | Category-based color system, inherits from `SourceCategory.Storage` |

---

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `FOLDER_CONNECTOR_ALLOWED_DIRECTORIES` | `""` (all allowed) | Comma-separated whitelist of allowed root directories |
| `FOLDER_CONNECTOR_MAX_WORKERS` | `4` | Thread pool workers for parallel file extraction |
| `FOLDER_CONNECTOR_MAX_FILE_SIZE_MB` | `100` | Max single file size in MB (skips larger files) |
| `ENABLED_CONNECTOR_TYPES` | `""` (all enabled) | If set, must include `folder` to allow this connector |

---

## Implementation Order

1. **Phase 1 — Shared utils**: Extract `_process_file` into `file/utils.py`, update `file/connector.py` imports, verify file connector still works
2. **Phase 2 — Backend core**: Add `FOLDER` enum + description + env vars, create `folder/connector.py`, register in `registry.py`
3. **Phase 3 — Frontend**: Add types, sources, form config, credentials, auto-sync source
4. **Phase 4 — Permission sync (EE)**: Add `doc_sync.py`, register in `_SOURCE_TO_SYNC_CONFIG`
5. **Phase 5 — Testing**: End-to-end with all 3 access modes

---

## Verification

1. **File connector regression**: After `utils.py` extraction, create a file connector via UI and verify indexing works unchanged
2. **Folder connector — PUBLIC mode**: Add folder connector with PUBLIC access, verify all files indexed and visible to all users
3. **Folder connector — PRIVATE mode**: Add with PRIVATE access + specific user group, verify only group members see documents in search results
4. **Folder connector — SYNC mode (EE)**: Add with SYNC access, verify OS file permissions read and mapped to `ExternalAccess` — documents respect file-level ACLs at query time
5. **Search pipeline**: Verify folder documents appear in search results, source filter shows "Local Folder" in SourceSelector
6. **Document sets**: Add folder CC pair to a document set, verify documents from folder appear when querying that document set scope
7. **Persona/assistant**: Assign document set containing folder CC pair to a persona, verify persona can access folder documents
8. **Incremental polling**: Modify a file (changes mtime), wait for poll cycle, verify only that file re-indexed
9. **File deletion pruning**: Delete a file from folder, wait for prune cycle, verify document removed from index (via SlimConnector)
10. **Parallel extraction**: Test with 1000+ files, verify thread pool concurrent processing
11. **Security**: Attempt folder path outside `FOLDER_CONNECTOR_ALLOWED_DIRECTORIES` — verify rejection
12. **UI flow**: Admin -> Add Connector -> Local Folder -> add paths -> select access type -> select groups -> Create -> verify indexing status page shows progress

---

## Phase 2 — Folder Management UI/UX Plan

### Overview

The folder connector is functionally complete for ingestion, pruning, permissions, and deletion.
What's missing is **post-creation management UI** — the ability to view, add, remove folder paths
and see indexed documents from the connector detail page.

### Existing Infrastructure We Leverage (NO backend changes needed)

| What | Endpoint | How we use it |
| --- | --- | --- |
| **Update connector config** | `PATCH /api/manage/admin/connector/{id}` | Update `connector_specific_config.folder_paths` |
| **Trigger prune** | `POST /api/manage/admin/cc-pair/{id}/prune` | After removing a folder path, prune removes orphan docs from Vespa |
| **Path validation** | `LocalFolderConnector.validate_connector_settings()` | Already validates paths on creation (called by indexing pipeline) |
| **Connector deletion** | `POST /api/manage/admin/deletion-attempt` | Full cc_pair + Vespa + DB cleanup, already works |
| **Prune cycle** | Celery `connector_pruning_generator_task` | Compares `retrieve_all_slim_docs()` vs DB → deletes stale docs from Vespa |

### Key Insight: How Folder Removal + Index Cleanup Works

The deletion flow for **removing a specific folder path** (not the whole connector):

```
1. Admin removes "/data/reports" from folder_paths in UI
2. UI calls PATCH /api/manage/admin/connector/{id}
   → connector_specific_config.folder_paths = ["/data/docs"]  (without /data/reports)
3. UI calls POST /api/manage/admin/cc-pair/{id}/prune
   → Triggers immediate pruning
4. Pruning runs: retrieve_all_slim_docs() only returns files from /data/docs
   → All /data/reports docs are in DB but NOT in slim docs
   → doc_ids_to_remove = indexed_ids - current_ids
   → Each stale doc → DOCUMENT_BY_CC_PAIR_CLEANUP_TASK
   → Vespa deletion + DB cleanup
```

This is **exactly how Google Drive handles folder deletion** — pruning detects missing docs and cleans up.
No new backend endpoint needed.

---

### Implementation Plan

#### Task 1: Backend — Path Validation Endpoint (NEW)

**File**: `backend/onyx/server/documents/connector.py`

Add a lightweight endpoint for pre-creation validation:

```python
@router.post("/admin/connector/folder/validate-paths")
def validate_folder_paths(
    paths: list[str],
    user: User = Depends(current_curator_or_admin_user),
) -> dict:
    """Validate folder paths exist, are directories, and are in allowlist."""
    results = {}
    for path in paths:
        real_path = os.path.realpath(path)
        if not _is_path_allowed(real_path):
            results[path] = {"valid": False, "error": "Not in allowed directories"}
        elif not os.path.exists(real_path):
            results[path] = {"valid": False, "error": "Path does not exist"}
        elif not os.path.isdir(real_path):
            results[path] = {"valid": False, "error": "Not a directory"}
        else:
            file_count = sum(1 for _ in os.scandir(real_path))
            results[path] = {"valid": True, "file_count": file_count}
    return {"results": results}
```

**Why**: Gives immediate feedback in UI before connector creation or path addition.
Reuses same validation logic from `LocalFolderConnector.validate_connector_settings()`.

---

#### Task 2: Frontend — InlineFolderManagement Component (NEW)

**New file**: `web/src/app/admin/connector/[ccPairId]/InlineFolderManagement.tsx`

Modeled after `InlineFileManagement.tsx` (415 lines) but for folder paths:

```
┌─────────────────────────────────────────────────────┐
│ Managed Folders                            [Edit]   │
├─────────────────────────────────────────────────────┤
│ ✓  /data/docs                          [x Remove]  │
│ ✓  /data/reports                       [x Remove]  │
│ ✓  /mnt/shared/knowledge-base          [x Remove]  │
│                                                     │
│ [+ Add Folder Path]                                 │
│                                                     │
│ ┌─ Add new path ─────────────────────────────────┐  │
│ │ /data/new-folder                    [Validate] │  │
│ │ ✓ Path valid (142 files found)                 │  │
│ └────────────────────────────────────────────────┘  │
│                                                     │
│ ⚠ Removing a folder will delete its indexed         │
│   documents from the search index.                  │
│                                                     │
│                          [Cancel]  [Save Changes]   │
└─────────────────────────────────────────────────────┘
```

**Component behavior**:
1. **Display mode**: Shows current `folder_paths` as a list (read-only)
2. **Edit mode** (toggle via Edit button):
   - Each path has a Remove (x) button with strikethrough on click
   - "Add Folder Path" opens a text input + Validate button
   - Validate calls `POST /api/manage/admin/connector/folder/validate-paths`
   - Shows validation result inline (valid + file count, or error)
3. **Save flow**:
   - Confirmation modal: "Removing folders will delete X indexed documents. Continue?"
   - Calls `PATCH /api/manage/admin/connector/{connectorId}` with updated `connector_specific_config`
   - If paths were removed: calls `POST /api/manage/admin/cc-pair/{ccPairId}/prune` to trigger cleanup
   - Calls `onRefresh()` to reload page data
4. **Validation rules**:
   - Cannot remove all paths (at least one required)
   - New paths validated before save
   - Duplicate path detection

**Key imports to reuse**:
- `updateConnector()` from `web/src/lib/connector.ts` — for PATCH
- `Button`, `IconButton`, `Text` from `@opal/*` — consistent styling
- `ConfirmEntityModal` — for removal confirmation

---

#### Task 3: Frontend — Wire InlineFolderManagement into Detail Page

**File**: `web/src/app/admin/connector/[ccPairId]/page.tsx`

Add folder management alongside the existing file management block (~line 694):

```tsx
{/* Inline file management for file connectors */}
{ccPair.connector.source === "file" &&
  ccPair.is_editable_for_current_user && (
    <div className="mt-6">
      <InlineFileManagement connectorId={ccPair.connector.id} onRefresh={refresh} />
    </div>
  )}

{/* Inline folder management for folder connectors */}
{ccPair.connector.source === "folder" &&
  ccPair.is_editable_for_current_user && (
    <div className="mt-6">
      <InlineFolderManagement
        connectorId={ccPair.connector.id}
        ccPairId={ccPair.id}
        currentPaths={ccPair.connector.connector_specific_config.folder_paths || []}
        connectorSpecificConfig={ccPair.connector.connector_specific_config}
        onRefresh={refresh}
      />
    </div>
  )}
```

---

#### Task 4: Frontend — "Prune Now" Button on Connector Detail

**File**: `web/src/app/admin/connector/[ccPairId]/page.tsx`

Add a "Sync & Prune" action to the existing Manage dropdown menu (around line 500):

```tsx
// In the dropdown menu, add after Re-Index:
{
  label: "Prune Deleted Files",
  icon: SvgTrash,
  onClick: async () => {
    const res = await fetch(`/api/manage/admin/cc-pair/${ccPair.id}/prune`, {
      method: "POST",
    });
    if (res.ok) {
      showToast("Pruning triggered. Deleted files will be removed from index.", "success");
    }
  },
  disabled: ccPair.status === "DELETING" || ccPair.status === "PAUSED",
}
```

**Why**: Manual prune is critical for folder connector — if files are deleted from disk,
admin shouldn't have to wait for the next scheduled prune cycle.

---

#### Task 5: Frontend — Indexed Documents Browser (Optional Enhancement)

**New file**: `web/src/app/admin/connector/[ccPairId]/IndexedDocumentsList.tsx`

A collapsible section on the detail page showing documents indexed by this connector:

```
┌─────────────────────────────────────────────────────┐
│ Indexed Documents (1,247 total)          [Refresh]  │
├─────────────────────────────────────────────────────┤
│ File Path                    │ Indexed At │ Chunks  │
│ /data/docs/report.pdf        │ 2h ago     │ 12      │
│ /data/docs/guide.md          │ 2h ago     │ 3       │
│ /data/docs/specs/api.docx    │ 2h ago     │ 8       │
│ ...                                                 │
│                    [< 1  2  3  4  5 >]              │
└─────────────────────────────────────────────────────┘
```

**Backend**: Uses existing `GET /api/manage/admin/cc-pair/{id}` which returns `num_docs_indexed`.
For detailed listing, would need a new endpoint:

```python
@router.get("/admin/cc-pair/{cc_pair_id}/documents")
def get_cc_pair_documents(
    cc_pair_id: int,
    page: int = 0,
    page_size: int = 25,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> PaginatedReturn[DocumentSnapshot]:
    """List documents indexed by this cc_pair with pagination."""
```

Uses `get_document_ids_for_connector_credential_pair()` from `backend/onyx/db/document.py:154`.

---

#### Task 6: Backend — Surface Blocked Path Errors in Index Attempts

**File**: `backend/onyx/connectors/folder/connector.py`

Currently `_is_path_allowed()` silently returns False and `validate_connector_settings()` raises.
But during `_walk_all_files()`, blocked paths may be silently skipped.

**Fix**: In `_walk_all_files()`, log blocked/missing paths as warnings that get captured in `IndexAttempt.error_msg`:

```python
def _walk_all_files(self, start=None, end=None):
    all_files = []
    for folder_path in self.folder_paths:
        real_path = os.path.realpath(folder_path)
        if not _is_path_allowed(real_path):
            logger.warning(f"Skipping blocked path: {folder_path} (not in allowed directories)")
            continue
        if not os.path.exists(real_path):
            logger.warning(f"Skipping missing path: {folder_path}")
            continue
        # ... existing walk logic
```

These warnings already flow into the indexing attempt error/log display in the admin UI.

---

### File Change Summary

| Action | File | What |
| --- | --- | --- |
| **Create** | `web/src/app/admin/connector/[ccPairId]/InlineFolderManagement.tsx` | Folder path management component |
| **Modify** | `web/src/app/admin/connector/[ccPairId]/page.tsx` | Wire in InlineFolderManagement + Prune button |
| **Create** | `backend/onyx/server/documents/connector.py` (add endpoint) | `POST /admin/connector/folder/validate-paths` |
| **Modify** | `backend/onyx/connectors/folder/connector.py` | Better warning logs for blocked/missing paths |
| **Create** | `web/src/app/admin/connector/[ccPairId]/IndexedDocumentsList.tsx` | (Optional) Document browser |
| **Create** | `backend/onyx/server/documents/cc_pair.py` (add endpoint) | (Optional) `GET /admin/cc-pair/{id}/documents` |

### Implementation Order

```
Phase 2a (Core — must have):
  1. Path validation endpoint (backend)
  2. InlineFolderManagement component (frontend)
  3. Wire into detail page (frontend)
  4. Prune Now button (frontend)
  5. Blocked path warning logs (backend)

Phase 2b (Nice to have):
  6. Indexed documents list endpoint (backend)
  7. IndexedDocumentsList component (frontend)
```

### Verification — Phase 2

1. **Add folder path**: Edit connector → add new path → validate → save → re-index runs → new docs appear
2. **Remove folder path**: Edit connector → remove path → save → confirm → prune triggers → docs removed from Vespa
3. **Path validation**: Add invalid path → see inline error before save
4. **Prune Now**: Delete files from disk → click Prune → verify docs removed
5. **Blocked path**: Set `FOLDER_CONNECTOR_ALLOWED_DIRECTORIES` → add out-of-scope path → see error
6. **Cannot remove all**: Try removing last path → blocked with validation message
7. **Indexed docs browser**: View paginated list of indexed documents per connector
