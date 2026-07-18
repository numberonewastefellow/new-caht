"""rename Persona -> Agent (tables/columns/constraints/indexes/sequences)

Revision ID: 0003_agent_rename
Revises: 0002_workspace_soft_delete
Create Date: 2026-07-18

Pure metadata rename (no data movement). Renames every ``persona*`` DB object to
``agent*`` so the physical schema matches the renamed ORM models. Generated from
the live catalog; ``personal_access_token`` / ``personalization_*`` are excluded.
Columns/constraints/indexes/sequences are renamed before the tables (last) so the
earlier statements resolve against the still-old table names; table renames then
auto-repoint dependent FKs.

Also renames the one persona-related table that is not itself ``persona*``-named:
``assistant__user_specific_config`` -> ``agent__user_specific_config`` (+ column
``assistant_id`` -> ``agent_id`` and its constraints). The broad API wire field
``assistant_id`` is intentionally kept (separate assistant->agent follow-up).

NOTE: the OpenSearch persona-scope field was renamed personas->agents in code
(schema.py PERSONAS_FIELD_NAME/AGENTS_FIELD_NAME); reindex existing docs (dev: fine to drop).
"""

from alembic import op

revision = "0003_agent_rename"
down_revision = "0002_workspace_soft_delete"
branch_labels = None
depends_on = None


_RENAMES = [
    ('ALTER TABLE agent_workflow_step RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE agent_workflow_step RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE chat_session RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE chat_session RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE discord_channel_config RENAME COLUMN persona_override_id TO agent_override_id', 'ALTER TABLE discord_channel_config RENAME COLUMN agent_override_id TO persona_override_id'),
    ('ALTER TABLE discord_guild_config RENAME COLUMN default_persona_id TO default_agent_id', 'ALTER TABLE discord_guild_config RENAME COLUMN default_agent_id TO default_persona_id'),
    ('ALTER TABLE llm_provider__persona RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE llm_provider__persona RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__document_set RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__document_set RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__document RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__document RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__hierarchy_node RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__hierarchy_node RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__knowledge_file RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__knowledge_file RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__persona_label RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__persona_label RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__persona_label RENAME COLUMN persona_label_id TO agent_label_id', 'ALTER TABLE persona__persona_label RENAME COLUMN agent_label_id TO persona_label_id'),
    ('ALTER TABLE persona__tool RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__tool RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__user_group RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__user_group RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona__user RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE persona__user RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE persona RENAME COLUMN builtin_persona TO builtin_agent', 'ALTER TABLE persona RENAME COLUMN builtin_agent TO builtin_persona'),
    ('ALTER TABLE persona RENAME COLUMN is_default_persona TO is_default_agent', 'ALTER TABLE persona RENAME COLUMN is_default_agent TO is_default_persona'),
    ('ALTER TABLE slack_channel_config RENAME COLUMN persona_id TO agent_id', 'ALTER TABLE slack_channel_config RENAME COLUMN agent_id TO persona_id'),
    ('ALTER TABLE agent_workflow_step RENAME CONSTRAINT agent_workflow_step_persona_id_fkey TO agent_workflow_step_agent_id_fkey', 'ALTER TABLE agent_workflow_step RENAME CONSTRAINT agent_workflow_step_agent_id_fkey TO agent_workflow_step_persona_id_fkey'),
    ('ALTER TABLE chat_session RENAME CONSTRAINT fk_chat_session_persona_id TO fk_chat_session_agent_id', 'ALTER TABLE chat_session RENAME CONSTRAINT fk_chat_session_agent_id TO fk_chat_session_persona_id'),
    ('ALTER TABLE discord_channel_config RENAME CONSTRAINT discord_channel_config_persona_override_id_fkey TO discord_channel_config_agent_override_id_fkey', 'ALTER TABLE discord_channel_config RENAME CONSTRAINT discord_channel_config_agent_override_id_fkey TO discord_channel_config_persona_override_id_fkey'),
    ('ALTER TABLE discord_guild_config RENAME CONSTRAINT discord_guild_config_default_persona_id_fkey TO discord_guild_config_default_agent_id_fkey', 'ALTER TABLE discord_guild_config RENAME CONSTRAINT discord_guild_config_default_agent_id_fkey TO discord_guild_config_default_persona_id_fkey'),
    ('ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__persona_llm_provider_id_fkey TO llm_provider__agent_llm_provider_id_fkey', 'ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__agent_llm_provider_id_fkey TO llm_provider__persona_llm_provider_id_fkey'),
    ('ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__persona_persona_id_fkey TO llm_provider__agent_agent_id_fkey', 'ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__agent_agent_id_fkey TO llm_provider__persona_persona_id_fkey'),
    ('ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__persona_pkey TO llm_provider__agent_pkey', 'ALTER TABLE llm_provider__persona RENAME CONSTRAINT llm_provider__agent_pkey TO llm_provider__persona_pkey'),
    ('ALTER TABLE persona__document_set RENAME CONSTRAINT persona__document_set_document_set_id_fkey TO agent__document_set_document_set_id_fkey', 'ALTER TABLE persona__document_set RENAME CONSTRAINT agent__document_set_document_set_id_fkey TO persona__document_set_document_set_id_fkey'),
    ('ALTER TABLE persona__document_set RENAME CONSTRAINT persona__document_set_persona_id_fkey TO agent__document_set_agent_id_fkey', 'ALTER TABLE persona__document_set RENAME CONSTRAINT agent__document_set_agent_id_fkey TO persona__document_set_persona_id_fkey'),
    ('ALTER TABLE persona__document_set RENAME CONSTRAINT persona__document_set_pkey TO agent__document_set_pkey', 'ALTER TABLE persona__document_set RENAME CONSTRAINT agent__document_set_pkey TO persona__document_set_pkey'),
    ('ALTER TABLE persona__document RENAME CONSTRAINT persona__document_document_id_fkey TO agent__document_document_id_fkey', 'ALTER TABLE persona__document RENAME CONSTRAINT agent__document_document_id_fkey TO persona__document_document_id_fkey'),
    ('ALTER TABLE persona__document RENAME CONSTRAINT persona__document_persona_id_fkey TO agent__document_agent_id_fkey', 'ALTER TABLE persona__document RENAME CONSTRAINT agent__document_agent_id_fkey TO persona__document_persona_id_fkey'),
    ('ALTER TABLE persona__document RENAME CONSTRAINT persona__document_pkey TO agent__document_pkey', 'ALTER TABLE persona__document RENAME CONSTRAINT agent__document_pkey TO persona__document_pkey'),
    ('ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT persona__hierarchy_node_hierarchy_node_id_fkey TO agent__hierarchy_node_hierarchy_node_id_fkey', 'ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT agent__hierarchy_node_hierarchy_node_id_fkey TO persona__hierarchy_node_hierarchy_node_id_fkey'),
    ('ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT persona__hierarchy_node_persona_id_fkey TO agent__hierarchy_node_agent_id_fkey', 'ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT agent__hierarchy_node_agent_id_fkey TO persona__hierarchy_node_persona_id_fkey'),
    ('ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT persona__hierarchy_node_pkey TO agent__hierarchy_node_pkey', 'ALTER TABLE persona__hierarchy_node RENAME CONSTRAINT agent__hierarchy_node_pkey TO persona__hierarchy_node_pkey'),
    ('ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__knowledge_file_knowledge_file_id_fkey TO agent__knowledge_file_knowledge_file_id_fkey', 'ALTER TABLE persona__knowledge_file RENAME CONSTRAINT agent__knowledge_file_knowledge_file_id_fkey TO persona__knowledge_file_knowledge_file_id_fkey'),
    ('ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__knowledge_file_persona_id_fkey TO agent__knowledge_file_agent_id_fkey', 'ALTER TABLE persona__knowledge_file RENAME CONSTRAINT agent__knowledge_file_agent_id_fkey TO persona__knowledge_file_persona_id_fkey'),
    ('ALTER TABLE persona__knowledge_file RENAME CONSTRAINT persona__knowledge_file_pkey TO agent__knowledge_file_pkey', 'ALTER TABLE persona__knowledge_file RENAME CONSTRAINT agent__knowledge_file_pkey TO persona__knowledge_file_pkey'),
    ('ALTER TABLE persona__persona_label RENAME CONSTRAINT persona__persona_label_persona_id_fkey TO agent__agent_label_agent_id_fkey', 'ALTER TABLE persona__persona_label RENAME CONSTRAINT agent__agent_label_agent_id_fkey TO persona__persona_label_persona_id_fkey'),
    ('ALTER TABLE persona__persona_label RENAME CONSTRAINT persona__persona_label_persona_label_id_fkey TO agent__agent_label_agent_label_id_fkey', 'ALTER TABLE persona__persona_label RENAME CONSTRAINT agent__agent_label_agent_label_id_fkey TO persona__persona_label_persona_label_id_fkey'),
    ('ALTER TABLE persona__persona_label RENAME CONSTRAINT persona__persona_label_pkey TO agent__agent_label_pkey', 'ALTER TABLE persona__persona_label RENAME CONSTRAINT agent__agent_label_pkey TO persona__persona_label_pkey'),
    ('ALTER TABLE persona__tool RENAME CONSTRAINT persona__tool_persona_id_fkey TO agent__tool_agent_id_fkey', 'ALTER TABLE persona__tool RENAME CONSTRAINT agent__tool_agent_id_fkey TO persona__tool_persona_id_fkey'),
    ('ALTER TABLE persona__tool RENAME CONSTRAINT persona__tool_pkey TO agent__tool_pkey', 'ALTER TABLE persona__tool RENAME CONSTRAINT agent__tool_pkey TO persona__tool_pkey'),
    ('ALTER TABLE persona__tool RENAME CONSTRAINT persona__tool_tool_id_fkey TO agent__tool_tool_id_fkey', 'ALTER TABLE persona__tool RENAME CONSTRAINT agent__tool_tool_id_fkey TO persona__tool_tool_id_fkey'),
    ('ALTER TABLE persona__user_group RENAME CONSTRAINT persona__user_group_persona_id_fkey TO agent__user_group_agent_id_fkey', 'ALTER TABLE persona__user_group RENAME CONSTRAINT agent__user_group_agent_id_fkey TO persona__user_group_persona_id_fkey'),
    ('ALTER TABLE persona__user_group RENAME CONSTRAINT persona__user_group_pkey TO agent__user_group_pkey', 'ALTER TABLE persona__user_group RENAME CONSTRAINT agent__user_group_pkey TO persona__user_group_pkey'),
    ('ALTER TABLE persona__user_group RENAME CONSTRAINT persona__user_group_user_group_id_fkey TO agent__user_group_user_group_id_fkey', 'ALTER TABLE persona__user_group RENAME CONSTRAINT agent__user_group_user_group_id_fkey TO persona__user_group_user_group_id_fkey'),
    ('ALTER TABLE persona__user RENAME CONSTRAINT persona__user_persona_id_fkey TO agent__user_agent_id_fkey', 'ALTER TABLE persona__user RENAME CONSTRAINT agent__user_agent_id_fkey TO persona__user_persona_id_fkey'),
    ('ALTER TABLE persona__user RENAME CONSTRAINT persona__user_pkey TO agent__user_pkey', 'ALTER TABLE persona__user RENAME CONSTRAINT agent__user_pkey TO persona__user_pkey'),
    ('ALTER TABLE persona__user RENAME CONSTRAINT persona__user_user_id_fkey TO agent__user_user_id_fkey', 'ALTER TABLE persona__user RENAME CONSTRAINT agent__user_user_id_fkey TO persona__user_user_id_fkey'),
    ('ALTER TABLE persona_label RENAME CONSTRAINT persona_category_name_key TO agent_category_name_key', 'ALTER TABLE persona_label RENAME CONSTRAINT agent_category_name_key TO persona_category_name_key'),
    ('ALTER TABLE persona_label RENAME CONSTRAINT persona_category_pkey TO agent_category_pkey', 'ALTER TABLE persona_label RENAME CONSTRAINT agent_category_pkey TO persona_category_pkey'),
    ('ALTER TABLE persona RENAME CONSTRAINT fk_persona_default_model_configuration_id TO fk_agent_default_model_configuration_id', 'ALTER TABLE persona RENAME CONSTRAINT fk_agent_default_model_configuration_id TO fk_persona_default_model_configuration_id'),
    ('ALTER TABLE persona RENAME CONSTRAINT persona__user_fk TO agent__user_fk', 'ALTER TABLE persona RENAME CONSTRAINT agent__user_fk TO persona__user_fk'),
    ('ALTER TABLE persona RENAME CONSTRAINT persona_pkey TO agent_pkey', 'ALTER TABLE persona RENAME CONSTRAINT agent_pkey TO persona_pkey'),
    ('ALTER TABLE persona RENAME CONSTRAINT persona_workflow_id_fkey TO agent_workflow_id_fkey', 'ALTER TABLE persona RENAME CONSTRAINT agent_workflow_id_fkey TO persona_workflow_id_fkey'),
    ('ALTER TABLE slack_channel_config RENAME CONSTRAINT slack_channel_config_persona_id_fkey TO slack_channel_config_agent_id_fkey', 'ALTER TABLE slack_channel_config RENAME CONSTRAINT slack_channel_config_agent_id_fkey TO slack_channel_config_persona_id_fkey'),
    ('ALTER INDEX _builtin_persona_name_idx RENAME TO _builtin_agent_name_idx', 'ALTER INDEX _builtin_agent_name_idx RENAME TO _builtin_persona_name_idx'),
    ('ALTER INDEX ix_llm_provider__persona_composite RENAME TO ix_llm_provider__agent_composite', 'ALTER INDEX ix_llm_provider__agent_composite RENAME TO ix_llm_provider__persona_composite'),
    ('ALTER INDEX ix_llm_provider__persona_llm_provider_id RENAME TO ix_llm_provider__agent_llm_provider_id', 'ALTER INDEX ix_llm_provider__agent_llm_provider_id RENAME TO ix_llm_provider__persona_llm_provider_id'),
    ('ALTER INDEX ix_llm_provider__persona_persona_id RENAME TO ix_llm_provider__agent_agent_id', 'ALTER INDEX ix_llm_provider__agent_agent_id RENAME TO ix_llm_provider__persona_persona_id'),
    ('ALTER INDEX ix_persona__document_document_id RENAME TO ix_agent__document_document_id', 'ALTER INDEX ix_agent__document_document_id RENAME TO ix_persona__document_document_id'),
    ('ALTER INDEX ix_persona__hierarchy_node_hierarchy_node_id RENAME TO ix_agent__hierarchy_node_hierarchy_node_id', 'ALTER INDEX ix_agent__hierarchy_node_hierarchy_node_id RENAME TO ix_persona__hierarchy_node_hierarchy_node_id'),
    ('ALTER SEQUENCE persona_category_id_seq RENAME TO agent_category_id_seq', 'ALTER SEQUENCE agent_category_id_seq RENAME TO persona_category_id_seq'),
    ('ALTER SEQUENCE persona_id_seq RENAME TO agent_id_seq', 'ALTER SEQUENCE agent_id_seq RENAME TO persona_id_seq'),
    ('ALTER TABLE llm_provider__persona RENAME TO llm_provider__agent', 'ALTER TABLE llm_provider__agent RENAME TO llm_provider__persona'),
    ('ALTER TABLE persona RENAME TO agent', 'ALTER TABLE agent RENAME TO persona'),
    ('ALTER TABLE persona__document RENAME TO agent__document', 'ALTER TABLE agent__document RENAME TO persona__document'),
    ('ALTER TABLE persona__document_set RENAME TO agent__document_set', 'ALTER TABLE agent__document_set RENAME TO persona__document_set'),
    ('ALTER TABLE persona__hierarchy_node RENAME TO agent__hierarchy_node', 'ALTER TABLE agent__hierarchy_node RENAME TO persona__hierarchy_node'),
    ('ALTER TABLE persona__knowledge_file RENAME TO agent__knowledge_file', 'ALTER TABLE agent__knowledge_file RENAME TO persona__knowledge_file'),
    ('ALTER TABLE persona__persona_label RENAME TO agent__agent_label', 'ALTER TABLE agent__agent_label RENAME TO persona__persona_label'),
    ('ALTER TABLE persona__tool RENAME TO agent__tool', 'ALTER TABLE agent__tool RENAME TO persona__tool'),
    ('ALTER TABLE persona__user RENAME TO agent__user', 'ALTER TABLE agent__user RENAME TO persona__user'),
    ('ALTER TABLE persona__user_group RENAME TO agent__user_group', 'ALTER TABLE agent__user_group RENAME TO persona__user_group'),
    ('ALTER TABLE persona_label RENAME TO agent_label', 'ALTER TABLE agent_label RENAME TO persona_label'),
    # assistant__user_specific_config -> agent__user_specific_config (bounded: table+column+constraints only;
    # the broad API wire field `assistant_id` is intentionally kept — separate assistant->agent follow-up).
    ('ALTER TABLE assistant__user_specific_config RENAME COLUMN assistant_id TO agent_id', 'ALTER TABLE assistant__user_specific_config RENAME COLUMN agent_id TO assistant_id'),
    ('ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT assistant__user_specific_config_assistant_id_fkey TO agent__user_specific_config_agent_id_fkey', 'ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT agent__user_specific_config_agent_id_fkey TO assistant__user_specific_config_assistant_id_fkey'),
    ('ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT assistant__user_specific_config_pkey TO agent__user_specific_config_pkey', 'ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT agent__user_specific_config_pkey TO assistant__user_specific_config_pkey'),
    ('ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT assistant__user_specific_config_user_id_fkey TO agent__user_specific_config_user_id_fkey', 'ALTER TABLE assistant__user_specific_config RENAME CONSTRAINT agent__user_specific_config_user_id_fkey TO assistant__user_specific_config_user_id_fkey'),
    ('ALTER TABLE assistant__user_specific_config RENAME TO agent__user_specific_config', 'ALTER TABLE agent__user_specific_config RENAME TO assistant__user_specific_config'),
]


def upgrade() -> None:
    for forward_sql, _ in _RENAMES:
        op.execute(forward_sql)


def downgrade() -> None:
    for _, reverse_sql in reversed(_RENAMES):
        op.execute(reverse_sql)
