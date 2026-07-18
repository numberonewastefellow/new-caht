"""rename Project->Workspace and UserFile->KnowledgeFile

Revision ID: 0002_workspace_rename
Revises: 0001_baseline_schema
Create Date: 2026-07-18

Pure metadata rename (no data movement). Renames the ``user_project`` table to
``workspace`` and the ``user_file`` table to ``knowledge_file``, plus every
dependent column / FK / PK / index / sequence, so the physical schema matches
the renamed ORM models.

Notes:
- ``user_project`` was historically ``ALTER TABLE user_folder RENAME TO
  user_project``; Postgres kept the original constraint/sequence names, so the
  PK is ``user_folder_pkey``, the owner FK is ``user_folder_user_id_fkey`` and
  the identity sequence is ``user_folder_id_seq`` (all verified against
  0001_baseline_schema.sql).
- The workspace AI column ``instructions`` -> ``workspace_instructions``.
- ``UserFileStatus`` is a non-native (VARCHAR) enum -> no DB type to rename.
- The Celery/Redis task/queue/lock string VALUES are intentionally NOT renamed
  (operational safety); only ORM/table/column names change here.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_workspace_rename"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


# (old_sql, reverse_sql) pairs, applied top-to-bottom on upgrade and
# bottom-to-top on downgrade. Tables are renamed before their columns/
# constraints/indexes so the later statements can reference the new table name.
_RENAMES = [
    # --- Project -> Workspace (table user_project -> workspace) ---
    ("ALTER TABLE user_project RENAME TO workspace",
     "ALTER TABLE workspace RENAME TO user_project"),
    ("ALTER TABLE workspace RENAME CONSTRAINT user_folder_pkey TO workspace_pkey",
     "ALTER TABLE user_project RENAME CONSTRAINT workspace_pkey TO user_folder_pkey"),
    ("ALTER SEQUENCE user_folder_id_seq RENAME TO workspace_id_seq",
     "ALTER SEQUENCE workspace_id_seq RENAME TO user_folder_id_seq"),
    ("ALTER TABLE workspace RENAME CONSTRAINT user_folder_user_id_fkey TO workspace_user_id_fkey",
     "ALTER TABLE user_project RENAME CONSTRAINT workspace_user_id_fkey TO user_folder_user_id_fkey"),
    ("ALTER TABLE workspace RENAME COLUMN instructions TO workspace_instructions",
     "ALTER TABLE user_project RENAME COLUMN workspace_instructions TO instructions"),
    # chat_session.project_id -> workspace_id (+ fk + index)
    ("ALTER TABLE chat_session RENAME COLUMN project_id TO workspace_id",
     "ALTER TABLE chat_session RENAME COLUMN workspace_id TO project_id"),
    ("ALTER TABLE chat_session RENAME CONSTRAINT fk_chat_session_project_id TO fk_chat_session_workspace_id",
     "ALTER TABLE chat_session RENAME CONSTRAINT fk_chat_session_workspace_id TO fk_chat_session_project_id"),
    ("ALTER INDEX ix_chat_session_project_id RENAME TO ix_chat_session_workspace_id",
     "ALTER INDEX ix_chat_session_workspace_id RENAME TO ix_chat_session_project_id"),

    # --- UserFile -> KnowledgeFile (table user_file -> knowledge_file) ---
    ("ALTER TABLE user_file RENAME TO knowledge_file",
     "ALTER TABLE knowledge_file RENAME TO user_file"),
    ("ALTER TABLE knowledge_file RENAME CONSTRAINT user_file_pkey TO knowledge_file_pkey",
     "ALTER TABLE user_file RENAME CONSTRAINT knowledge_file_pkey TO user_file_pkey"),
    ("ALTER TABLE knowledge_file RENAME COLUMN needs_project_sync TO needs_workspace_sync",
     "ALTER TABLE user_file RENAME COLUMN needs_workspace_sync TO needs_project_sync"),
    ("ALTER TABLE knowledge_file RENAME COLUMN last_project_sync_at TO last_workspace_sync_at",
     "ALTER TABLE user_file RENAME COLUMN last_workspace_sync_at TO last_project_sync_at"),

    # --- persona__user_file -> persona__knowledge_file ---
    ("ALTER TABLE persona__user_file RENAME TO persona__knowledge_file",
     "ALTER TABLE persona__knowledge_file RENAME TO persona__user_file"),
    ("ALTER TABLE persona__knowledge_file RENAME COLUMN user_file_id TO knowledge_file_id",
     "ALTER TABLE persona__user_file RENAME COLUMN knowledge_file_id TO user_file_id"),
    ("ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__user_file_pkey TO persona__knowledge_file_pkey",
     "ALTER TABLE persona__user_file RENAME CONSTRAINT persona__knowledge_file_pkey TO persona__user_file_pkey"),
    ("ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__user_file_user_file_id_fkey TO persona__knowledge_file_knowledge_file_id_fkey",
     "ALTER TABLE persona__user_file RENAME CONSTRAINT persona__knowledge_file_knowledge_file_id_fkey TO persona__user_file_user_file_id_fkey"),
    ("ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__user_file_persona_id_fkey TO persona__knowledge_file_persona_id_fkey",
     "ALTER TABLE persona__user_file RENAME CONSTRAINT persona__knowledge_file_persona_id_fkey TO persona__user_file_persona_id_fkey"),

    # --- project__user_file -> workspace__knowledge_file (compound rename) ---
    ("ALTER TABLE project__user_file RENAME TO workspace__knowledge_file",
     "ALTER TABLE workspace__knowledge_file RENAME TO project__user_file"),
    ("ALTER TABLE workspace__knowledge_file RENAME COLUMN project_id TO workspace_id",
     "ALTER TABLE project__user_file RENAME COLUMN workspace_id TO project_id"),
    ("ALTER TABLE workspace__knowledge_file RENAME COLUMN user_file_id TO knowledge_file_id",
     "ALTER TABLE project__user_file RENAME COLUMN knowledge_file_id TO user_file_id"),
    ("ALTER TABLE workspace__knowledge_file RENAME CONSTRAINT project__user_file_pkey TO workspace__knowledge_file_pkey",
     "ALTER TABLE project__user_file RENAME CONSTRAINT workspace__knowledge_file_pkey TO project__user_file_pkey"),
    ("ALTER TABLE workspace__knowledge_file RENAME CONSTRAINT fk_project__user_file_project_id TO fk_workspace__knowledge_file_workspace_id",
     "ALTER TABLE project__user_file RENAME CONSTRAINT fk_workspace__knowledge_file_workspace_id TO fk_project__user_file_project_id"),
    ("ALTER TABLE workspace__knowledge_file RENAME CONSTRAINT fk_project__user_file_user_file_id TO fk_workspace__knowledge_file_knowledge_file_id",
     "ALTER TABLE project__user_file RENAME CONSTRAINT fk_workspace__knowledge_file_knowledge_file_id TO fk_project__user_file_user_file_id"),
    ("ALTER INDEX idx_project__user_file_user_file_id RENAME TO idx_workspace__knowledge_file_knowledge_file_id",
     "ALTER INDEX idx_workspace__knowledge_file_knowledge_file_id RENAME TO idx_project__user_file_user_file_id"),
    ("ALTER INDEX ix_project__user_file_project_id_created_at RENAME TO ix_workspace__knowledge_file_workspace_id_created_at",
     "ALTER INDEX ix_workspace__knowledge_file_workspace_id_created_at RENAME TO ix_project__user_file_project_id_created_at"),
]


def upgrade() -> None:
    for forward_sql, _ in _RENAMES:
        op.execute(forward_sql)


def downgrade() -> None:
    for _, reverse_sql in reversed(_RENAMES):
        op.execute(reverse_sql)
