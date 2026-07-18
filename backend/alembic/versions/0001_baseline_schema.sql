-- Baseline schema (squashed). Auto-generated from pg_dump of the migrated DB.
-- pg_trgm is used by KG trigram indexes but pg_dump omits it; add explicitly.
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.2
-- Dumped by pg_dump version 15.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--



--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--



--
-- Name: update_kg_entity_name(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION update_kg_entity_name() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                name text;
                cleaned_name text;
            BEGIN
                -- Set name to semantic_id if document_id is not NULL
                IF NEW.document_id IS NOT NULL THEN
                    SELECT lower(semantic_id) INTO name
                    FROM document
                    WHERE id = NEW.document_id;
                ELSE
                    name = lower(NEW.name);
                END IF;

                -- Clean name and truncate if too long
                cleaned_name = regexp_replace(
                    name,
                    '[^a-z0-9]+', '', 'g'
                );
                IF length(cleaned_name) > 1000 THEN
                    cleaned_name = left(cleaned_name, 1000);
                END IF;

                -- Set name and name trigrams
                NEW.name = name;
                NEW.name_trigrams = public.show_trgm(cleaned_name);
                RETURN NEW;
            END;
            $$;


--
-- Name: update_kg_entity_name_from_doc(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION update_kg_entity_name_from_doc() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                doc_name text;
                cleaned_name text;
            BEGIN
                doc_name = lower(NEW.semantic_id);

                -- Clean name and truncate if too long
                cleaned_name = regexp_replace(
                    doc_name,
                    '[^a-z0-9]+', '', 'g'
                );
                IF length(cleaned_name) > 1000 THEN
                    cleaned_name = left(cleaned_name, 1000);
                END IF;

                -- Set name and name trigrams for all entities referencing this document
                UPDATE kg_entity
                SET
                    name = doc_name,
                    name_trigrams = public.show_trgm(cleaned_name)
                WHERE document_id = NEW.id;
                RETURN NEW;
            END;
            $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accesstoken; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE accesstoken (
    user_id uuid NOT NULL,
    token character varying(43) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: agent_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE agent_workflow (
    id integer NOT NULL,
    name character varying NOT NULL,
    description text,
    user_id uuid,
    orchestration_mode character varying DEFAULT 'llm_decision'::character varying NOT NULL,
    orchestrator_prompt text,
    orchestrator_llm_provider character varying,
    orchestrator_llm_model character varying,
    max_steps integer DEFAULT 10,
    timeout_seconds integer DEFAULT 1800,
    is_public boolean DEFAULT true,
    is_visible boolean DEFAULT true,
    deleted boolean DEFAULT false,
    icon_name character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    max_calls_per_agent integer DEFAULT 2 NOT NULL
);


--
-- Name: agent_workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE agent_workflow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE agent_workflow_id_seq OWNED BY agent_workflow.id;


--
-- Name: agent_workflow_step; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE agent_workflow_step (
    id integer NOT NULL,
    workflow_id integer NOT NULL,
    persona_id integer,
    step_order integer NOT NULL,
    step_name character varying NOT NULL,
    step_description text,
    input_mapping jsonb,
    output_key character varying DEFAULT 'output'::character varying,
    condition jsonb,
    is_terminal boolean DEFAULT false,
    can_request_input boolean DEFAULT false NOT NULL,
    promote_output boolean DEFAULT false NOT NULL,
    llm_provider_override character varying,
    llm_model_override character varying,
    max_output_tokens_override integer,
    system_prompt_override text,
    task_prompt_override text,
    tool_ids_override jsonb,
    document_set_ids_override jsonb,
    replace_base_system_prompt_override boolean,
    step_type character varying DEFAULT 'agent'::character varying NOT NULL
);


--
-- Name: agent_workflow_step_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE agent_workflow_step_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_workflow_step_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE agent_workflow_step_id_seq OWNED BY agent_workflow_step.id;


--
-- Name: api_key; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE api_key (
    id integer NOT NULL,
    hashed_api_key character varying NOT NULL,
    api_key_display character varying NOT NULL,
    user_id uuid NOT NULL,
    owner_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    name character varying,
    use_owner_identity boolean DEFAULT false NOT NULL
);


--
-- Name: api_key_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE api_key_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_key_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE api_key_id_seq OWNED BY api_key.id;


--
-- Name: artifact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE artifact (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    type character varying(8) NOT NULL,
    path character varying NOT NULL,
    name character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assistant__user_specific_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE assistant__user_specific_config (
    assistant_id integer NOT NULL,
    user_id uuid NOT NULL,
    disabled_tool_ids integer[] NOT NULL
);


--
-- Name: background_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE background_error (
    id integer NOT NULL,
    message character varying NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    cc_pair_id integer
);


--
-- Name: background_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE background_error_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: background_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE background_error_id_seq OWNED BY background_error.id;


--
-- Name: build_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE build_message (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    turn_index integer NOT NULL,
    type character varying(9) NOT NULL,
    message_metadata jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: build_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE build_session (
    id uuid NOT NULL,
    user_id uuid,
    name character varying,
    status character varying(6) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_activity_at timestamp with time zone DEFAULT now() NOT NULL,
    nextjs_port integer,
    demo_data_enabled boolean DEFAULT true NOT NULL,
    sharing_scope character varying DEFAULT 'private'::character varying NOT NULL
);


--
-- Name: chat_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chat_feedback (
    id integer NOT NULL,
    is_positive boolean,
    feedback_text text,
    chat_message_id integer,
    required_followup boolean,
    predefined_feedback character varying
);


--
-- Name: chat_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE chat_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE chat_feedback_id_seq OWNED BY chat_feedback.id;


--
-- Name: chat_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chat_message (
    message text NOT NULL,
    message_type character varying(9) NOT NULL,
    time_sent timestamp with time zone DEFAULT now() NOT NULL,
    token_count integer NOT NULL,
    id integer NOT NULL,
    parent_message_id integer,
    latest_child_message_id integer,
    citations jsonb,
    error text,
    files jsonb,
    chat_session_id uuid,
    message_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, message)) STORED,
    reasoning_tokens text,
    is_clarification boolean DEFAULT false NOT NULL,
    processing_duration_seconds double precision,
    last_summarized_message_id integer
);


--
-- Name: chat_message__search_doc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chat_message__search_doc (
    chat_message_id integer NOT NULL,
    search_doc_id integer NOT NULL
);


--
-- Name: chat_message__standard_answer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chat_message__standard_answer (
    chat_message_id integer NOT NULL,
    standard_answer_id integer NOT NULL
);


--
-- Name: chat_message_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE chat_message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE chat_message_id_seq OWNED BY chat_message.id;


--
-- Name: chat_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chat_session (
    user_id uuid,
    description text,
    deleted boolean NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    persona_id integer,
    shared_status character varying(7) NOT NULL,
    llm_override jsonb,
    prompt_override jsonb,
    onyxbot_flow boolean NOT NULL,
    current_alternate_model character varying,
    slack_thread_id character varying,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    temperature_override double precision,
    description_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, COALESCE(description, ''::text))) STORED,
    project_id integer,
    sandbox_session_id character varying
);


--
-- Name: chunk_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE chunk_stats (
    id character varying NOT NULL,
    document_id character varying NOT NULL,
    chunk_in_doc_id integer NOT NULL,
    information_content_boost double precision,
    last_modified timestamp with time zone DEFAULT now() NOT NULL,
    last_synced timestamp with time zone
);


--
-- Name: connector; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE connector (
    id integer NOT NULL,
    name character varying NOT NULL,
    source character varying(50) NOT NULL,
    input_type character varying(10),
    connector_specific_config jsonb NOT NULL,
    refresh_freq integer,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL,
    prune_freq integer,
    indexing_start timestamp without time zone,
    kg_processing_enabled boolean DEFAULT false,
    kg_coverage_days integer
);


--
-- Name: connector_credential_pair_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE connector_credential_pair_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connector_credential_pair; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE connector_credential_pair (
    connector_id integer NOT NULL,
    credential_id integer NOT NULL,
    last_successful_index_time timestamp with time zone,
    total_docs_indexed integer NOT NULL,
    id integer DEFAULT nextval('connector_credential_pair_id_seq'::regclass) NOT NULL,
    name character varying NOT NULL,
    status character varying(16) NOT NULL,
    deletion_failure_message character varying,
    access_type character varying NOT NULL,
    auto_sync_options jsonb,
    last_time_perm_sync timestamp with time zone,
    last_pruned timestamp with time zone,
    last_time_external_group_sync timestamp with time zone,
    creator_id uuid,
    indexing_trigger character varying(7),
    in_repeated_error_state boolean DEFAULT false,
    processing_mode character varying DEFAULT 'REGULAR'::character varying NOT NULL,
    last_time_hierarchy_fetch timestamp with time zone
);


--
-- Name: connector_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE connector_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connector_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE connector_id_seq OWNED BY connector.id;


--
-- Name: credential; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE credential (
    id integer NOT NULL,
    user_id uuid,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL,
    admin_public boolean NOT NULL,
    credential_json bytea,
    source character varying(100),
    name character varying,
    curator_public boolean DEFAULT false NOT NULL
);


--
-- Name: credential__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE credential__user_group (
    credential_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: credential_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE credential_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credential_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE credential_id_seq OWNED BY credential.id;


--
-- Name: discord_bot_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE discord_bot_config (
    id character varying DEFAULT 'SINGLETON'::character varying NOT NULL,
    bot_token bytea NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_discord_bot_config_singleton CHECK (((id)::text = 'SINGLETON'::text))
);


--
-- Name: discord_channel_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE discord_channel_config (
    id integer NOT NULL,
    guild_config_id integer NOT NULL,
    channel_id bigint NOT NULL,
    channel_name character varying NOT NULL,
    channel_type character varying(20) DEFAULT 'text'::character varying NOT NULL,
    is_private boolean DEFAULT false NOT NULL,
    thread_only_mode boolean DEFAULT false NOT NULL,
    require_bot_invocation boolean DEFAULT true NOT NULL,
    persona_override_id integer,
    enabled boolean DEFAULT false NOT NULL
);


--
-- Name: discord_channel_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE discord_channel_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: discord_channel_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE discord_channel_config_id_seq OWNED BY discord_channel_config.id;


--
-- Name: discord_guild_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE discord_guild_config (
    id integer NOT NULL,
    guild_id bigint,
    guild_name character varying,
    registration_key character varying NOT NULL,
    registered_at timestamp with time zone,
    default_persona_id integer,
    enabled boolean DEFAULT true NOT NULL
);


--
-- Name: discord_guild_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE discord_guild_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: discord_guild_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE discord_guild_config_id_seq OWNED BY discord_guild_config.id;


--
-- Name: doc_permission_sync_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doc_permission_sync_attempt (
    id integer NOT NULL,
    connector_credential_pair_id integer NOT NULL,
    status character varying(21) NOT NULL,
    total_docs_synced integer,
    docs_with_permission_errors integer,
    error_message text,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_started timestamp with time zone,
    time_finished timestamp with time zone
);


--
-- Name: doc_permission_sync_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doc_permission_sync_attempt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doc_permission_sync_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doc_permission_sync_attempt_id_seq OWNED BY doc_permission_sync_attempt.id;


--
-- Name: document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document (
    id character varying NOT NULL,
    boost integer NOT NULL,
    hidden boolean NOT NULL,
    semantic_id character varying NOT NULL,
    link character varying,
    doc_updated_at timestamp with time zone,
    primary_owners character varying[],
    secondary_owners character varying[],
    from_ingestion_api boolean,
    last_modified timestamp with time zone DEFAULT now() NOT NULL,
    last_synced timestamp with time zone,
    external_user_emails character varying[],
    external_user_group_ids character varying[],
    is_public boolean,
    chunk_count integer,
    kg_stage character varying,
    kg_processing_time timestamp with time zone,
    doc_metadata jsonb,
    parent_hierarchy_node_id integer
);


--
-- Name: document__tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document__tag (
    document_id character varying NOT NULL,
    tag_id integer NOT NULL
);


--
-- Name: document_by_connector_credential_pair; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_by_connector_credential_pair (
    id character varying NOT NULL,
    connector_id integer NOT NULL,
    credential_id integer NOT NULL,
    has_been_indexed boolean NOT NULL
);


--
-- Name: document_retrieval_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_retrieval_feedback (
    id integer NOT NULL,
    document_id character varying NOT NULL,
    document_rank integer NOT NULL,
    clicked boolean NOT NULL,
    feedback character varying,
    chat_message_id integer
);


--
-- Name: document_retrieval_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE document_retrieval_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_retrieval_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE document_retrieval_feedback_id_seq OWNED BY document_retrieval_feedback.id;


--
-- Name: document_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_set (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying,
    user_id uuid,
    is_up_to_date boolean NOT NULL,
    is_public boolean NOT NULL,
    time_last_modified_by_user timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_set__connector_credential_pair; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_set__connector_credential_pair (
    document_set_id integer NOT NULL,
    connector_credential_pair_id integer NOT NULL,
    is_current boolean NOT NULL
);


--
-- Name: document_set__user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_set__user (
    document_set_id integer NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: document_set__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE document_set__user_group (
    document_set_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: document_set_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE document_set_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE document_set_id_seq OWNED BY document_set.id;


--
-- Name: search_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE search_settings (
    id integer NOT NULL,
    model_name character varying NOT NULL,
    model_dim integer NOT NULL,
    "normalize" boolean NOT NULL,
    query_prefix character varying NOT NULL,
    passage_prefix character varying NOT NULL,
    index_name character varying NOT NULL,
    status character varying,
    provider_type character varying(50),
    multipass_indexing boolean DEFAULT false NOT NULL,
    multilingual_expansion character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    embedding_precision character varying(8) DEFAULT 'FLOAT'::character varying NOT NULL,
    reduced_dimension integer,
    enable_contextual_rag boolean DEFAULT false NOT NULL,
    contextual_rag_llm_name character varying,
    contextual_rag_llm_provider character varying,
    switchover_type character varying(11) DEFAULT 'reindex'::character varying NOT NULL
);


--
-- Name: embedding_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE embedding_model_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: embedding_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE embedding_model_id_seq OWNED BY search_settings.id;


--
-- Name: embedding_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE embedding_provider (
    api_key bytea,
    provider_type character varying(50) NOT NULL,
    api_url character varying,
    api_version character varying,
    deployment_name character varying
);


--
-- Name: external_group_permission_sync_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE external_group_permission_sync_attempt (
    id integer NOT NULL,
    connector_credential_pair_id integer,
    status character varying(21) NOT NULL,
    total_users_processed integer,
    total_groups_processed integer,
    total_group_memberships_synced integer,
    error_message text,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_started timestamp with time zone,
    time_finished timestamp with time zone
);


--
-- Name: external_group_permission_sync_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE external_group_permission_sync_attempt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: external_group_permission_sync_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE external_group_permission_sync_attempt_id_seq OWNED BY external_group_permission_sync_attempt.id;


--
-- Name: federated_connector; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE federated_connector (
    id integer NOT NULL,
    source character varying NOT NULL,
    credentials bytea NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: federated_connector__document_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE federated_connector__document_set (
    id integer NOT NULL,
    federated_connector_id integer NOT NULL,
    document_set_id integer NOT NULL,
    entities jsonb NOT NULL
);


--
-- Name: federated_connector__document_set_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE federated_connector__document_set_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: federated_connector__document_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE federated_connector__document_set_id_seq OWNED BY federated_connector__document_set.id;


--
-- Name: federated_connector_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE federated_connector_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: federated_connector_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE federated_connector_id_seq OWNED BY federated_connector.id;


--
-- Name: federated_connector_oauth_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE federated_connector_oauth_token (
    id integer NOT NULL,
    federated_connector_id integer NOT NULL,
    user_id uuid NOT NULL,
    token bytea NOT NULL,
    expires_at timestamp without time zone
);


--
-- Name: federated_connector_oauth_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE federated_connector_oauth_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: federated_connector_oauth_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE federated_connector_oauth_token_id_seq OWNED BY federated_connector_oauth_token.id;


--
-- Name: file_content; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE file_content (
    file_id character varying NOT NULL,
    lobj_oid bigint NOT NULL,
    file_size bigint DEFAULT '0'::bigint NOT NULL
);


--
-- Name: file_record; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE file_record (
    file_id character varying NOT NULL,
    display_name character varying,
    file_origin character varying DEFAULT 'connector'::character varying NOT NULL,
    file_type character varying DEFAULT 'text/plain'::character varying NOT NULL,
    file_metadata jsonb,
    bucket_name character varying,
    object_key character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: hierarchy_fetch_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE hierarchy_fetch_attempt (
    id uuid NOT NULL,
    connector_credential_pair_id integer NOT NULL,
    status character varying NOT NULL,
    nodes_fetched integer DEFAULT 0,
    nodes_updated integer DEFAULT 0,
    error_msg text,
    full_exception_trace text,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_started timestamp with time zone,
    time_updated timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: hierarchy_node; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE hierarchy_node (
    id integer NOT NULL,
    raw_node_id character varying NOT NULL,
    display_name character varying NOT NULL,
    link character varying,
    source character varying NOT NULL,
    node_type character varying NOT NULL,
    document_id character varying,
    parent_id integer,
    external_user_emails character varying[],
    external_user_group_ids character varying[],
    is_public boolean DEFAULT false NOT NULL
);


--
-- Name: hierarchy_node_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE hierarchy_node_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hierarchy_node_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE hierarchy_node_id_seq OWNED BY hierarchy_node.id;


--
-- Name: image_generation_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE image_generation_config (
    image_provider_id character varying NOT NULL,
    model_configuration_id integer NOT NULL,
    is_default boolean NOT NULL
);


--
-- Name: index_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE index_attempt (
    id integer NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL,
    status character varying NOT NULL,
    error_msg character varying,
    total_docs_indexed integer,
    time_started timestamp with time zone,
    new_docs_indexed integer,
    from_beginning boolean NOT NULL,
    full_exception_trace text,
    docs_removed_from_index integer,
    connector_credential_pair_id integer NOT NULL,
    search_settings_id integer,
    checkpoint_pointer character varying,
    poll_range_start timestamp with time zone,
    poll_range_end timestamp with time zone,
    celery_task_id character varying,
    cancellation_requested boolean DEFAULT false NOT NULL,
    total_batches integer,
    completed_batches integer DEFAULT 0 NOT NULL,
    total_failures_batch_level integer DEFAULT 0 NOT NULL,
    total_chunks integer DEFAULT 0 NOT NULL,
    last_progress_time timestamp with time zone,
    last_batches_completed_count integer DEFAULT 0 NOT NULL,
    heartbeat_counter integer DEFAULT 0 NOT NULL,
    last_heartbeat_value integer DEFAULT 0 NOT NULL,
    last_heartbeat_time timestamp with time zone
);


--
-- Name: index_attempt_errors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE index_attempt_errors (
    id integer NOT NULL,
    index_attempt_id integer NOT NULL,
    connector_credential_pair_id integer NOT NULL,
    document_id character varying,
    document_link character varying,
    entity_id character varying,
    failed_time_range_start timestamp with time zone,
    failed_time_range_end timestamp with time zone,
    failure_message text NOT NULL,
    is_resolved boolean NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: index_attempt_errors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE index_attempt_errors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: index_attempt_errors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE index_attempt_errors_id_seq OWNED BY index_attempt_errors.id;


--
-- Name: index_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE index_attempt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: index_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE index_attempt_id_seq OWNED BY index_attempt.id;


--
-- Name: inputprompt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE inputprompt (
    id integer NOT NULL,
    prompt character varying NOT NULL,
    content character varying NOT NULL,
    active boolean NOT NULL,
    is_public boolean NOT NULL,
    user_id uuid
);


--
-- Name: inputprompt__user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE inputprompt__user (
    input_prompt_id integer NOT NULL,
    user_id uuid NOT NULL,
    disabled boolean NOT NULL
);


--
-- Name: inputprompt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE inputprompt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inputprompt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE inputprompt_id_seq OWNED BY inputprompt.id;


--
-- Name: internet_content_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE internet_content_provider (
    id integer NOT NULL,
    name character varying NOT NULL,
    provider_type character varying NOT NULL,
    api_key bytea,
    config jsonb,
    is_active boolean DEFAULT false NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: internet_content_provider_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE internet_content_provider_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: internet_content_provider_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE internet_content_provider_id_seq OWNED BY internet_content_provider.id;


--
-- Name: internet_search_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE internet_search_provider (
    id integer NOT NULL,
    name character varying NOT NULL,
    provider_type character varying NOT NULL,
    api_key bytea,
    config jsonb,
    is_active boolean DEFAULT false NOT NULL,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    time_updated timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: internet_search_provider_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE internet_search_provider_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: internet_search_provider_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE internet_search_provider_id_seq OWNED BY internet_search_provider.id;


--
-- Name: key_value_store; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE key_value_store (
    key character varying NOT NULL,
    value jsonb,
    encrypted_value bytea
);


--
-- Name: kg_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_entity (
    id_name character varying NOT NULL,
    name character varying NOT NULL,
    entity_key character varying,
    name_trigrams character varying(3)[],
    document_id character varying,
    alternative_names character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    entity_type_id_name character varying NOT NULL,
    description character varying,
    keywords character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    acl character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    boosts jsonb DEFAULT '{}'::jsonb NOT NULL,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    event_time timestamp with time zone,
    time_updated timestamp with time zone DEFAULT now(),
    time_created timestamp with time zone DEFAULT now(),
    parent_key character varying
);


--
-- Name: kg_entity_extraction_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_entity_extraction_staging (
    id_name character varying NOT NULL,
    name character varying NOT NULL,
    document_id character varying,
    alternative_names character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    entity_type_id_name character varying NOT NULL,
    description character varying,
    keywords character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    acl character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    boosts jsonb DEFAULT '{}'::jsonb NOT NULL,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    transferred_id_name character varying,
    entity_key character varying,
    parent_key character varying,
    event_time timestamp with time zone,
    time_created timestamp with time zone DEFAULT now()
);


--
-- Name: kg_entity_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_entity_type (
    id_name character varying NOT NULL,
    description character varying,
    grounding character varying NOT NULL,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    active boolean NOT NULL,
    deep_extraction boolean NOT NULL,
    time_updated timestamp with time zone DEFAULT now(),
    time_created timestamp with time zone DEFAULT now(),
    grounded_source_name character varying,
    entity_values character varying[],
    clustering jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: kg_relationship; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_relationship (
    id_name character varying NOT NULL,
    source_node character varying NOT NULL,
    target_node character varying NOT NULL,
    source_node_type character varying NOT NULL,
    target_node_type character varying NOT NULL,
    source_document character varying NOT NULL,
    type character varying NOT NULL,
    relationship_type_id_name character varying NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    time_updated timestamp with time zone DEFAULT now(),
    time_created timestamp with time zone DEFAULT now()
);


--
-- Name: kg_relationship_extraction_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_relationship_extraction_staging (
    id_name character varying NOT NULL,
    source_node character varying NOT NULL,
    target_node character varying NOT NULL,
    source_node_type character varying NOT NULL,
    target_node_type character varying NOT NULL,
    source_document character varying NOT NULL,
    type character varying NOT NULL,
    relationship_type_id_name character varying NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    transferred boolean DEFAULT false NOT NULL,
    time_created timestamp with time zone DEFAULT now()
);


--
-- Name: kg_relationship_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_relationship_type (
    id_name character varying NOT NULL,
    name character varying NOT NULL,
    source_entity_type_id_name character varying NOT NULL,
    target_entity_type_id_name character varying NOT NULL,
    definition boolean NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    type character varying NOT NULL,
    active boolean NOT NULL,
    time_updated timestamp with time zone DEFAULT now(),
    time_created timestamp with time zone DEFAULT now(),
    clustering jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: kg_relationship_type_extraction_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_relationship_type_extraction_staging (
    id_name character varying NOT NULL,
    name character varying NOT NULL,
    source_entity_type_id_name character varying NOT NULL,
    target_entity_type_id_name character varying NOT NULL,
    definition boolean NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    type character varying NOT NULL,
    active boolean NOT NULL,
    time_created timestamp with time zone DEFAULT now(),
    clustering jsonb DEFAULT '{}'::jsonb NOT NULL,
    transferred boolean DEFAULT false NOT NULL
);


--
-- Name: kg_term; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kg_term (
    id_term character varying NOT NULL,
    entity_types character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    time_updated timestamp with time zone DEFAULT now(),
    time_created timestamp with time zone DEFAULT now()
);


--
-- Name: license; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE license (
    id integer NOT NULL,
    license_data text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: license_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE license_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: license_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE license_id_seq OWNED BY license.id;


--
-- Name: llm_model_flow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE llm_model_flow (
    id integer NOT NULL,
    llm_model_flow_type character varying(20) NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    model_configuration_id integer NOT NULL
);


--
-- Name: llm_model_flow_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE llm_model_flow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_model_flow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE llm_model_flow_id_seq OWNED BY llm_model_flow.id;


--
-- Name: llm_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE llm_provider (
    id integer NOT NULL,
    name character varying NOT NULL,
    api_base character varying,
    api_version character varying,
    custom_config jsonb,
    default_model_name character varying NOT NULL,
    is_default_provider boolean,
    api_key bytea,
    provider character varying,
    is_public boolean DEFAULT true NOT NULL,
    deployment_name character varying,
    is_default_vision_provider boolean DEFAULT false,
    default_vision_model character varying,
    is_auto_mode boolean DEFAULT false NOT NULL
);


--
-- Name: llm_provider__persona; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE llm_provider__persona (
    llm_provider_id integer NOT NULL,
    persona_id integer NOT NULL
);


--
-- Name: llm_provider__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE llm_provider__user_group (
    llm_provider_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: llm_provider_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE llm_provider_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_provider_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE llm_provider_id_seq OWNED BY llm_provider.id;


--
-- Name: mcp_connection_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE mcp_connection_config (
    id integer NOT NULL,
    mcp_server_id integer,
    user_email character varying NOT NULL,
    config bytea NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: mcp_connection_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE mcp_connection_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_connection_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE mcp_connection_config_id_seq OWNED BY mcp_connection_config.id;


--
-- Name: mcp_server; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE mcp_server (
    id integer NOT NULL,
    owner character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    server_url character varying NOT NULL,
    auth_type character varying(9),
    admin_connection_config_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    auth_performer character varying(8),
    transport character varying(15),
    status character varying(14) DEFAULT 'CREATED'::character varying NOT NULL,
    last_refreshed_at timestamp with time zone
);


--
-- Name: mcp_server__user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE mcp_server__user (
    mcp_server_id integer NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: mcp_server__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE mcp_server__user_group (
    mcp_server_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: mcp_server_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE mcp_server_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_server_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE mcp_server_id_seq OWNED BY mcp_server.id;


--
-- Name: memory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE memory (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    memory_text text NOT NULL,
    conversation_id uuid,
    message_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: memory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE memory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE memory_id_seq OWNED BY memory.id;


--
-- Name: model_configuration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE model_configuration (
    id integer NOT NULL,
    llm_provider_id integer NOT NULL,
    name character varying NOT NULL,
    is_visible boolean NOT NULL,
    max_input_tokens integer,
    supports_image_input boolean,
    display_name character varying
);


--
-- Name: model_configuration_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE model_configuration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_configuration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE model_configuration_id_seq OWNED BY model_configuration.id;


--
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE notification (
    id integer NOT NULL,
    notif_type character varying NOT NULL,
    user_id uuid,
    dismissed boolean NOT NULL,
    last_shown timestamp with time zone NOT NULL,
    first_shown timestamp with time zone NOT NULL,
    additional_data jsonb,
    title character varying DEFAULT 'New Notification'::character varying NOT NULL,
    description character varying DEFAULT ''::character varying
);


--
-- Name: notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE notification_id_seq OWNED BY notification.id;


--
-- Name: oauth_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE oauth_account (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    oauth_name character varying(100) NOT NULL,
    access_token text NOT NULL,
    expires_at integer,
    refresh_token text,
    account_id character varying(320) NOT NULL,
    account_email character varying(320) NOT NULL
);


--
-- Name: oauth_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE oauth_config (
    id integer NOT NULL,
    name character varying NOT NULL,
    authorization_url text NOT NULL,
    token_url text NOT NULL,
    client_id bytea NOT NULL,
    client_secret bytea NOT NULL,
    scopes jsonb,
    additional_params jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: oauth_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE oauth_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oauth_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE oauth_config_id_seq OWNED BY oauth_config.id;


--
-- Name: oauth_user_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE oauth_user_token (
    id integer NOT NULL,
    oauth_config_id integer NOT NULL,
    user_id uuid NOT NULL,
    token_data bytea NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: oauth_user_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE oauth_user_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oauth_user_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE oauth_user_token_id_seq OWNED BY oauth_user_token.id;


--
-- Name: persona; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona (
    id integer NOT NULL,
    name character varying NOT NULL,
    deleted boolean NOT NULL,
    description character varying NOT NULL,
    num_chunks integer,
    llm_model_version_override character varying,
    user_id uuid,
    llm_relevance_filter boolean NOT NULL,
    llm_filter_extraction boolean NOT NULL,
    recency_bias character varying NOT NULL,
    is_visible boolean NOT NULL,
    display_priority integer,
    starter_messages jsonb,
    is_public boolean NOT NULL,
    llm_model_provider_override character varying,
    uploaded_image_id character varying,
    chunks_above integer NOT NULL,
    chunks_below integer NOT NULL,
    builtin_persona boolean NOT NULL,
    is_default_persona boolean DEFAULT false NOT NULL,
    search_start_date timestamp with time zone,
    system_prompt character varying(5000000),
    task_prompt character varying(5000000),
    datetime_aware boolean DEFAULT true NOT NULL,
    replace_base_system_prompt boolean DEFAULT false NOT NULL,
    icon_name character varying,
    default_model_configuration_id integer,
    workflow_id integer,
    max_output_tokens integer
);


--
-- Name: persona__document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__document (
    persona_id integer NOT NULL,
    document_id character varying NOT NULL
);


--
-- Name: persona__document_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__document_set (
    persona_id integer NOT NULL,
    document_set_id integer NOT NULL
);


--
-- Name: persona__hierarchy_node; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__hierarchy_node (
    persona_id integer NOT NULL,
    hierarchy_node_id integer NOT NULL
);


--
-- Name: persona__persona_label; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__persona_label (
    persona_id integer NOT NULL,
    persona_label_id integer NOT NULL
);


--
-- Name: persona__tool; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__tool (
    persona_id integer NOT NULL,
    tool_id integer NOT NULL
);


--
-- Name: persona__user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__user (
    persona_id integer NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: persona__user_file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__user_file (
    persona_id integer NOT NULL,
    user_file_id uuid NOT NULL
);


--
-- Name: persona__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona__user_group (
    persona_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: persona_label; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE persona_label (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying
);


--
-- Name: persona_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE persona_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE persona_category_id_seq OWNED BY persona_label.id;


--
-- Name: persona_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE persona_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE persona_id_seq OWNED BY persona.id;


--
-- Name: personal_access_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE personal_access_token (
    id integer NOT NULL,
    name character varying NOT NULL,
    hashed_token character varying(64) NOT NULL,
    token_display character varying NOT NULL,
    user_id uuid NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone,
    is_revoked boolean DEFAULT false NOT NULL
);


--
-- Name: personal_access_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE personal_access_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personal_access_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE personal_access_token_id_seq OWNED BY personal_access_token.id;


--
-- Name: project__user_file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE project__user_file (
    project_id integer NOT NULL,
    user_file_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: public_external_user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public_external_user_group (
    external_user_group_id character varying NOT NULL,
    cc_pair_id integer NOT NULL,
    stale boolean DEFAULT false NOT NULL
);


--
-- Name: saml; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE saml (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    encrypted_cookie text NOT NULL,
    expires_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: saml_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE saml_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: saml_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE saml_id_seq OWNED BY saml.id;


--
-- Name: sandbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE sandbox (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    container_id character varying,
    status character varying(12) DEFAULT 'provisioning'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_heartbeat timestamp with time zone
);


--
-- Name: scim_group_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scim_group_mapping (
    id integer NOT NULL,
    external_id character varying NOT NULL,
    user_group_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scim_group_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scim_group_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scim_group_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scim_group_mapping_id_seq OWNED BY scim_group_mapping.id;


--
-- Name: scim_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scim_token (
    id integer NOT NULL,
    name character varying NOT NULL,
    hashed_token character varying(64) NOT NULL,
    token_display character varying NOT NULL,
    created_by_id uuid NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone
);


--
-- Name: scim_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scim_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scim_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scim_token_id_seq OWNED BY scim_token.id;


--
-- Name: scim_user_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scim_user_mapping (
    id integer NOT NULL,
    external_id character varying NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scim_user_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scim_user_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scim_user_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scim_user_mapping_id_seq OWNED BY scim_user_mapping.id;


--
-- Name: search_doc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE search_doc (
    id integer NOT NULL,
    document_id character varying NOT NULL,
    chunk_ind integer NOT NULL,
    semantic_id character varying NOT NULL,
    link character varying,
    blurb character varying NOT NULL,
    boost integer NOT NULL,
    source_type character varying(50) NOT NULL,
    hidden boolean NOT NULL,
    score double precision NOT NULL,
    match_highlights character varying[] NOT NULL,
    updated_at timestamp with time zone,
    primary_owners character varying[],
    secondary_owners character varying[],
    doc_metadata jsonb NOT NULL,
    is_internet boolean,
    is_relevant boolean,
    relevance_explanation character varying
);


--
-- Name: search_doc_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE search_doc_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: search_doc_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE search_doc_id_seq OWNED BY search_doc.id;


--
-- Name: search_query; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE search_query (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    query character varying NOT NULL,
    query_expansions character varying[],
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: slack_bot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE slack_bot (
    id integer NOT NULL,
    name character varying NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    bot_token bytea NOT NULL,
    app_token bytea NOT NULL,
    user_token bytea
);


--
-- Name: slack_bot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE slack_bot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: slack_bot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE slack_bot_id_seq OWNED BY slack_bot.id;


--
-- Name: slack_channel_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE slack_channel_config (
    id integer NOT NULL,
    slack_bot_id integer NOT NULL,
    persona_id integer,
    channel_config jsonb NOT NULL,
    enable_auto_filters boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL
);


--
-- Name: slack_channel_config__standard_answer_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE slack_channel_config__standard_answer_category (
    slack_channel_config_id integer NOT NULL,
    standard_answer_category_id integer NOT NULL
);


--
-- Name: slack_channel_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE slack_channel_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: slack_channel_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE slack_channel_config_id_seq OWNED BY slack_channel_config.id;


--
-- Name: snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE snapshot (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    storage_path character varying NOT NULL,
    size_bytes bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: standard_answer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE standard_answer (
    id integer NOT NULL,
    keyword character varying NOT NULL,
    answer character varying NOT NULL,
    active boolean NOT NULL,
    match_regex boolean DEFAULT false NOT NULL,
    match_any_keywords boolean DEFAULT false NOT NULL
);


--
-- Name: standard_answer__standard_answer_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE standard_answer__standard_answer_category (
    standard_answer_id integer NOT NULL,
    standard_answer_category_id integer NOT NULL
);


--
-- Name: standard_answer_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE standard_answer_category (
    id integer NOT NULL,
    name character varying NOT NULL
);


--
-- Name: standard_answer_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE standard_answer_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: standard_answer_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE standard_answer_category_id_seq OWNED BY standard_answer_category.id;


--
-- Name: standard_answer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE standard_answer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: standard_answer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE standard_answer_id_seq OWNED BY standard_answer.id;


--
-- Name: sync_record; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE sync_record (
    id integer NOT NULL,
    entity_id integer NOT NULL,
    sync_type character varying(40) NOT NULL,
    sync_status character varying(40) NOT NULL,
    num_docs_synced integer NOT NULL,
    sync_start_time timestamp with time zone NOT NULL,
    sync_end_time timestamp with time zone
);


--
-- Name: sync_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE sync_record_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sync_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE sync_record_id_seq OWNED BY sync_record.id;


--
-- Name: tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tag (
    id integer NOT NULL,
    tag_key character varying NOT NULL,
    tag_value character varying NOT NULL,
    source character varying(50) NOT NULL,
    is_list boolean DEFAULT false NOT NULL
);


--
-- Name: tag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE tag_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE tag_id_seq OWNED BY tag.id;


--
-- Name: task_queue_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE task_queue_jobs (
    id integer NOT NULL,
    task_id character varying NOT NULL,
    task_name character varying NOT NULL,
    status character varying(7) NOT NULL,
    start_time timestamp with time zone,
    register_time timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: task_queue_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE task_queue_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_queue_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE task_queue_jobs_id_seq OWNED BY task_queue_jobs.id;


--
-- Name: tenant_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tenant_usage (
    id integer NOT NULL,
    window_start timestamp with time zone NOT NULL,
    llm_cost_cents double precision DEFAULT '0'::double precision NOT NULL,
    chunks_indexed integer DEFAULT 0 NOT NULL,
    api_calls integer DEFAULT 0 NOT NULL,
    non_streaming_api_calls integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: tenant_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE tenant_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tenant_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE tenant_usage_id_seq OWNED BY tenant_usage.id;


--
-- Name: token_rate_limit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE token_rate_limit (
    id integer NOT NULL,
    enabled boolean NOT NULL,
    token_budget integer NOT NULL,
    period_hours integer NOT NULL,
    scope character varying(10) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: token_rate_limit__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE token_rate_limit__user_group (
    rate_limit_id integer NOT NULL,
    user_group_id integer NOT NULL
);


--
-- Name: token_rate_limit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE token_rate_limit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: token_rate_limit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE token_rate_limit_id_seq OWNED BY token_rate_limit.id;


--
-- Name: tool; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tool (
    id integer NOT NULL,
    name character varying NOT NULL,
    description text,
    in_code_tool_id character varying,
    openapi_schema jsonb,
    user_id uuid,
    display_name character varying,
    custom_headers jsonb,
    passthrough_auth boolean DEFAULT false NOT NULL,
    mcp_server_id integer,
    mcp_input_schema jsonb,
    enabled boolean NOT NULL,
    oauth_config_id integer
);


--
-- Name: tool_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tool_call (
    id integer NOT NULL,
    tool_id integer NOT NULL,
    tool_call_arguments jsonb NOT NULL,
    tool_call_response text NOT NULL,
    parent_chat_message_id integer,
    chat_session_id uuid NOT NULL,
    parent_tool_call_id integer,
    turn_number integer DEFAULT 0 NOT NULL,
    tool_call_id character varying DEFAULT ''::character varying NOT NULL,
    reasoning_tokens text,
    tool_call_tokens integer DEFAULT 0 NOT NULL,
    generated_images jsonb,
    tab_index integer DEFAULT 0 NOT NULL
);


--
-- Name: tool_call__search_doc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tool_call__search_doc (
    tool_call_id integer NOT NULL,
    search_doc_id integer NOT NULL
);


--
-- Name: tool_call_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE tool_call_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_call_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE tool_call_id_seq OWNED BY tool_call.id;


--
-- Name: tool_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE tool_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE tool_id_seq OWNED BY tool.id;


--
-- Name: usage_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE usage_reports (
    id integer NOT NULL,
    report_name character varying NOT NULL,
    requestor_user_id uuid,
    time_created timestamp with time zone DEFAULT now() NOT NULL,
    period_from timestamp with time zone,
    period_to timestamp with time zone
);


--
-- Name: usage_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE usage_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usage_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE usage_reports_id_seq OWNED BY usage_reports.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "user" (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    hashed_password character varying(1024) NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    is_verified boolean NOT NULL,
    role character varying(14) NOT NULL,
    oidc_expiry timestamp with time zone,
    default_model text,
    visible_assistants jsonb DEFAULT '[]'::jsonb NOT NULL,
    hidden_assistants jsonb DEFAULT '[]'::jsonb NOT NULL,
    chosen_assistants jsonb,
    auto_scroll boolean,
    pinned_assistants jsonb,
    shortcut_enabled boolean DEFAULT false NOT NULL,
    temperature_override_enabled boolean DEFAULT false,
    personal_name character varying,
    personal_role character varying,
    use_memories boolean DEFAULT true NOT NULL,
    theme_preference character varying(6),
    chat_background character varying,
    user_preferences text,
    default_app_mode character varying DEFAULT 'CHAT'::character varying NOT NULL,
    enable_memory_tool boolean DEFAULT true NOT NULL,
    font_preference character varying,
    CONSTRAINT ensure_lowercase_email CHECK (((email)::text = lower((email)::text)))
);


--
-- Name: user__external_user_group_id; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user__external_user_group_id (
    user_id uuid NOT NULL,
    external_user_group_id character varying NOT NULL,
    cc_pair_id integer NOT NULL,
    stale boolean DEFAULT false NOT NULL
);


--
-- Name: user__user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user__user_group (
    user_group_id integer NOT NULL,
    user_id uuid NOT NULL,
    is_curator boolean DEFAULT false NOT NULL
);


--
-- Name: user_file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_file (
    user_id uuid,
    link_url character varying,
    token_count integer,
    file_type character varying,
    file_id character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp without time zone,
    content_type character varying,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    status character varying(10) DEFAULT 'PROCESSING'::character varying NOT NULL,
    chunk_count integer,
    last_accessed_at timestamp with time zone,
    needs_project_sync boolean DEFAULT false NOT NULL,
    last_project_sync_at timestamp with time zone
);


--
-- Name: user_project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_project (
    id integer NOT NULL,
    user_id uuid,
    name character varying(255),
    description character varying(255),
    display_priority integer,
    created_at timestamp with time zone DEFAULT now(),
    instructions character varying
);


--
-- Name: user_folder_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_folder_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_folder_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_folder_id_seq OWNED BY user_project.id;


--
-- Name: user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_group (
    id integer NOT NULL,
    name character varying NOT NULL,
    is_up_to_date boolean NOT NULL,
    is_up_for_deletion boolean NOT NULL,
    time_last_modified_by_user timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_group__connector_credential_pair; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_group__connector_credential_pair (
    user_group_id integer NOT NULL,
    cc_pair_id integer NOT NULL,
    is_current boolean NOT NULL
);


--
-- Name: user_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_group_id_seq OWNED BY user_group.id;


--
-- Name: workflow_execution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE workflow_execution (
    id integer NOT NULL,
    workflow_id integer NOT NULL,
    chat_session_id uuid,
    user_id uuid,
    status character varying DEFAULT 'running'::character varying,
    steps_executed jsonb,
    total_tokens integer DEFAULT 0,
    total_duration_ms integer DEFAULT 0,
    error_message text,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    paused_at_step_id integer,
    checkpoint_data jsonb
);


--
-- Name: workflow_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE workflow_execution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workflow_execution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE workflow_execution_id_seq OWNED BY workflow_execution.id;


--
-- Name: agent_workflow id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow ALTER COLUMN id SET DEFAULT nextval('agent_workflow_id_seq'::regclass);


--
-- Name: agent_workflow_step id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow_step ALTER COLUMN id SET DEFAULT nextval('agent_workflow_step_id_seq'::regclass);


--
-- Name: api_key id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key ALTER COLUMN id SET DEFAULT nextval('api_key_id_seq'::regclass);


--
-- Name: background_error id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY background_error ALTER COLUMN id SET DEFAULT nextval('background_error_id_seq'::regclass);


--
-- Name: chat_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_feedback ALTER COLUMN id SET DEFAULT nextval('chat_feedback_id_seq'::regclass);


--
-- Name: chat_message id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message ALTER COLUMN id SET DEFAULT nextval('chat_message_id_seq'::regclass);


--
-- Name: connector id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector ALTER COLUMN id SET DEFAULT nextval('connector_id_seq'::regclass);


--
-- Name: credential id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential ALTER COLUMN id SET DEFAULT nextval('credential_id_seq'::regclass);


--
-- Name: discord_channel_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_channel_config ALTER COLUMN id SET DEFAULT nextval('discord_channel_config_id_seq'::regclass);


--
-- Name: discord_guild_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_guild_config ALTER COLUMN id SET DEFAULT nextval('discord_guild_config_id_seq'::regclass);


--
-- Name: doc_permission_sync_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doc_permission_sync_attempt ALTER COLUMN id SET DEFAULT nextval('doc_permission_sync_attempt_id_seq'::regclass);


--
-- Name: document_retrieval_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_retrieval_feedback ALTER COLUMN id SET DEFAULT nextval('document_retrieval_feedback_id_seq'::regclass);


--
-- Name: document_set id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set ALTER COLUMN id SET DEFAULT nextval('document_set_id_seq'::regclass);


--
-- Name: external_group_permission_sync_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY external_group_permission_sync_attempt ALTER COLUMN id SET DEFAULT nextval('external_group_permission_sync_attempt_id_seq'::regclass);


--
-- Name: federated_connector id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector ALTER COLUMN id SET DEFAULT nextval('federated_connector_id_seq'::regclass);


--
-- Name: federated_connector__document_set id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector__document_set ALTER COLUMN id SET DEFAULT nextval('federated_connector__document_set_id_seq'::regclass);


--
-- Name: federated_connector_oauth_token id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector_oauth_token ALTER COLUMN id SET DEFAULT nextval('federated_connector_oauth_token_id_seq'::regclass);


--
-- Name: hierarchy_node id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_node ALTER COLUMN id SET DEFAULT nextval('hierarchy_node_id_seq'::regclass);


--
-- Name: index_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt ALTER COLUMN id SET DEFAULT nextval('index_attempt_id_seq'::regclass);


--
-- Name: index_attempt_errors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt_errors ALTER COLUMN id SET DEFAULT nextval('index_attempt_errors_id_seq'::regclass);


--
-- Name: inputprompt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt ALTER COLUMN id SET DEFAULT nextval('inputprompt_id_seq'::regclass);


--
-- Name: internet_content_provider id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_content_provider ALTER COLUMN id SET DEFAULT nextval('internet_content_provider_id_seq'::regclass);


--
-- Name: internet_search_provider id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_search_provider ALTER COLUMN id SET DEFAULT nextval('internet_search_provider_id_seq'::regclass);


--
-- Name: license id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY license ALTER COLUMN id SET DEFAULT nextval('license_id_seq'::regclass);


--
-- Name: llm_model_flow id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_model_flow ALTER COLUMN id SET DEFAULT nextval('llm_model_flow_id_seq'::regclass);


--
-- Name: llm_provider id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider ALTER COLUMN id SET DEFAULT nextval('llm_provider_id_seq'::regclass);


--
-- Name: mcp_connection_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_connection_config ALTER COLUMN id SET DEFAULT nextval('mcp_connection_config_id_seq'::regclass);


--
-- Name: mcp_server id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server ALTER COLUMN id SET DEFAULT nextval('mcp_server_id_seq'::regclass);


--
-- Name: memory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY memory ALTER COLUMN id SET DEFAULT nextval('memory_id_seq'::regclass);


--
-- Name: model_configuration id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY model_configuration ALTER COLUMN id SET DEFAULT nextval('model_configuration_id_seq'::regclass);


--
-- Name: notification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY notification ALTER COLUMN id SET DEFAULT nextval('notification_id_seq'::regclass);


--
-- Name: oauth_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_config ALTER COLUMN id SET DEFAULT nextval('oauth_config_id_seq'::regclass);


--
-- Name: oauth_user_token id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_user_token ALTER COLUMN id SET DEFAULT nextval('oauth_user_token_id_seq'::regclass);


--
-- Name: persona id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona ALTER COLUMN id SET DEFAULT nextval('persona_id_seq'::regclass);


--
-- Name: persona_label id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona_label ALTER COLUMN id SET DEFAULT nextval('persona_category_id_seq'::regclass);


--
-- Name: personal_access_token id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY personal_access_token ALTER COLUMN id SET DEFAULT nextval('personal_access_token_id_seq'::regclass);


--
-- Name: saml id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY saml ALTER COLUMN id SET DEFAULT nextval('saml_id_seq'::regclass);


--
-- Name: scim_group_mapping id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_group_mapping ALTER COLUMN id SET DEFAULT nextval('scim_group_mapping_id_seq'::regclass);


--
-- Name: scim_token id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_token ALTER COLUMN id SET DEFAULT nextval('scim_token_id_seq'::regclass);


--
-- Name: scim_user_mapping id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_user_mapping ALTER COLUMN id SET DEFAULT nextval('scim_user_mapping_id_seq'::regclass);


--
-- Name: search_doc id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_doc ALTER COLUMN id SET DEFAULT nextval('search_doc_id_seq'::regclass);


--
-- Name: search_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_settings ALTER COLUMN id SET DEFAULT nextval('embedding_model_id_seq'::regclass);


--
-- Name: slack_bot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_bot ALTER COLUMN id SET DEFAULT nextval('slack_bot_id_seq'::regclass);


--
-- Name: slack_channel_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config ALTER COLUMN id SET DEFAULT nextval('slack_channel_config_id_seq'::regclass);


--
-- Name: standard_answer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer ALTER COLUMN id SET DEFAULT nextval('standard_answer_id_seq'::regclass);


--
-- Name: standard_answer_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer_category ALTER COLUMN id SET DEFAULT nextval('standard_answer_category_id_seq'::regclass);


--
-- Name: sync_record id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY sync_record ALTER COLUMN id SET DEFAULT nextval('sync_record_id_seq'::regclass);


--
-- Name: tag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY tag ALTER COLUMN id SET DEFAULT nextval('tag_id_seq'::regclass);


--
-- Name: task_queue_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY task_queue_jobs ALTER COLUMN id SET DEFAULT nextval('task_queue_jobs_id_seq'::regclass);


--
-- Name: tenant_usage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY tenant_usage ALTER COLUMN id SET DEFAULT nextval('tenant_usage_id_seq'::regclass);


--
-- Name: token_rate_limit id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY token_rate_limit ALTER COLUMN id SET DEFAULT nextval('token_rate_limit_id_seq'::regclass);


--
-- Name: tool id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool ALTER COLUMN id SET DEFAULT nextval('tool_id_seq'::regclass);


--
-- Name: tool_call id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call ALTER COLUMN id SET DEFAULT nextval('tool_call_id_seq'::regclass);


--
-- Name: usage_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY usage_reports ALTER COLUMN id SET DEFAULT nextval('usage_reports_id_seq'::regclass);


--
-- Name: user_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group ALTER COLUMN id SET DEFAULT nextval('user_group_id_seq'::regclass);


--
-- Name: user_project id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_project ALTER COLUMN id SET DEFAULT nextval('user_folder_id_seq'::regclass);


--
-- Name: workflow_execution id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution ALTER COLUMN id SET DEFAULT nextval('workflow_execution_id_seq'::regclass);


--
-- Name: tag _tag_key_value_source_list_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT _tag_key_value_source_list_uc UNIQUE (tag_key, tag_value, source, is_list);


--
-- Name: accesstoken accesstoken_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY accesstoken
    ADD CONSTRAINT accesstoken_pkey PRIMARY KEY (token);


--
-- Name: agent_workflow agent_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow
    ADD CONSTRAINT agent_workflow_pkey PRIMARY KEY (id);


--
-- Name: agent_workflow_step agent_workflow_step_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow_step
    ADD CONSTRAINT agent_workflow_step_pkey PRIMARY KEY (id);


--
-- Name: api_key api_key_api_key_display_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key
    ADD CONSTRAINT api_key_api_key_display_key UNIQUE (api_key_display);


--
-- Name: api_key api_key_hashed_api_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key
    ADD CONSTRAINT api_key_hashed_api_key_key UNIQUE (hashed_api_key);


--
-- Name: api_key api_key_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key
    ADD CONSTRAINT api_key_pkey PRIMARY KEY (id);


--
-- Name: artifact artifact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY artifact
    ADD CONSTRAINT artifact_pkey PRIMARY KEY (id);


--
-- Name: assistant__user_specific_config assistant__user_specific_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY assistant__user_specific_config
    ADD CONSTRAINT assistant__user_specific_config_pkey PRIMARY KEY (assistant_id, user_id);


--
-- Name: background_error background_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY background_error
    ADD CONSTRAINT background_error_pkey PRIMARY KEY (id);


--
-- Name: build_message build_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY build_message
    ADD CONSTRAINT build_message_pkey PRIMARY KEY (id);


--
-- Name: build_session build_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY build_session
    ADD CONSTRAINT build_session_pkey PRIMARY KEY (id);


--
-- Name: chat_feedback chat_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_feedback
    ADD CONSTRAINT chat_feedback_pkey PRIMARY KEY (id);


--
-- Name: chat_message__search_doc chat_message__search_doc_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__search_doc
    ADD CONSTRAINT chat_message__search_doc_pkey PRIMARY KEY (chat_message_id, search_doc_id);


--
-- Name: chat_message__standard_answer chat_message__standard_answer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__standard_answer
    ADD CONSTRAINT chat_message__standard_answer_pkey PRIMARY KEY (chat_message_id, standard_answer_id);


--
-- Name: chat_message chat_message_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message
    ADD CONSTRAINT chat_message_id_key UNIQUE (id);


--
-- Name: chat_session chat_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_session
    ADD CONSTRAINT chat_session_pkey PRIMARY KEY (id);


--
-- Name: chunk_stats chunk_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chunk_stats
    ADD CONSTRAINT chunk_stats_pkey PRIMARY KEY (id);


--
-- Name: connector_credential_pair connector_credential_pair__id__key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector_credential_pair
    ADD CONSTRAINT connector_credential_pair__id__key UNIQUE (id);


--
-- Name: connector_credential_pair connector_credential_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector_credential_pair
    ADD CONSTRAINT connector_credential_pair_pkey PRIMARY KEY (connector_id, credential_id);


--
-- Name: connector connector_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector
    ADD CONSTRAINT connector_pkey PRIMARY KEY (id);


--
-- Name: credential__user_group credential__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential__user_group
    ADD CONSTRAINT credential__user_group_pkey PRIMARY KEY (credential_id, user_group_id);


--
-- Name: credential credential_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential
    ADD CONSTRAINT credential_pkey PRIMARY KEY (id);


--
-- Name: discord_bot_config discord_bot_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_bot_config
    ADD CONSTRAINT discord_bot_config_pkey PRIMARY KEY (id);


--
-- Name: discord_channel_config discord_channel_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_channel_config
    ADD CONSTRAINT discord_channel_config_pkey PRIMARY KEY (id);


--
-- Name: discord_guild_config discord_guild_config_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_guild_config
    ADD CONSTRAINT discord_guild_config_guild_id_key UNIQUE (guild_id);


--
-- Name: discord_guild_config discord_guild_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_guild_config
    ADD CONSTRAINT discord_guild_config_pkey PRIMARY KEY (id);


--
-- Name: discord_guild_config discord_guild_config_registration_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_guild_config
    ADD CONSTRAINT discord_guild_config_registration_key_key UNIQUE (registration_key);


--
-- Name: doc_permission_sync_attempt doc_permission_sync_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doc_permission_sync_attempt
    ADD CONSTRAINT doc_permission_sync_attempt_pkey PRIMARY KEY (id);


--
-- Name: document__tag document__tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document__tag
    ADD CONSTRAINT document__tag_pkey PRIMARY KEY (document_id, tag_id);


--
-- Name: document_by_connector_credential_pair document_by_connector_credential_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_by_connector_credential_pair
    ADD CONSTRAINT document_by_connector_credential_pair_pkey PRIMARY KEY (id, connector_id, credential_id);


--
-- Name: document document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document
    ADD CONSTRAINT document_pkey PRIMARY KEY (id);


--
-- Name: document_retrieval_feedback document_retrieval_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_pkey PRIMARY KEY (id);


--
-- Name: document_set__connector_credential_pair document_set__connector_credential_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__connector_credential_pair
    ADD CONSTRAINT document_set__connector_credential_pair_pkey PRIMARY KEY (document_set_id, connector_credential_pair_id, is_current);


--
-- Name: document_set__user_group document_set__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user_group
    ADD CONSTRAINT document_set__user_group_pkey PRIMARY KEY (document_set_id, user_group_id);


--
-- Name: document_set__user document_set__user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user
    ADD CONSTRAINT document_set__user_pkey PRIMARY KEY (document_set_id, user_id);


--
-- Name: document_set document_set_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set
    ADD CONSTRAINT document_set_name_key UNIQUE (name);


--
-- Name: document_set document_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set
    ADD CONSTRAINT document_set_pkey PRIMARY KEY (id);


--
-- Name: search_settings embedding_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_settings
    ADD CONSTRAINT embedding_model_pkey PRIMARY KEY (id);


--
-- Name: embedding_provider embedding_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY embedding_provider
    ADD CONSTRAINT embedding_provider_pkey PRIMARY KEY (provider_type);


--
-- Name: external_group_permission_sync_attempt external_group_permission_sync_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY external_group_permission_sync_attempt
    ADD CONSTRAINT external_group_permission_sync_attempt_pkey PRIMARY KEY (id);


--
-- Name: federated_connector__document_set federated_connector__document_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector__document_set
    ADD CONSTRAINT federated_connector__document_set_pkey PRIMARY KEY (id);


--
-- Name: federated_connector_oauth_token federated_connector_oauth_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector_oauth_token
    ADD CONSTRAINT federated_connector_oauth_token_pkey PRIMARY KEY (id);


--
-- Name: federated_connector federated_connector_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector
    ADD CONSTRAINT federated_connector_pkey PRIMARY KEY (id);


--
-- Name: file_content file_content_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY file_content
    ADD CONSTRAINT file_content_pkey PRIMARY KEY (file_id);


--
-- Name: file_record file_store_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY file_record
    ADD CONSTRAINT file_store_pkey PRIMARY KEY (file_id);


--
-- Name: hierarchy_fetch_attempt hierarchy_fetch_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_fetch_attempt
    ADD CONSTRAINT hierarchy_fetch_attempt_pkey PRIMARY KEY (id);


--
-- Name: hierarchy_node hierarchy_node_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_node
    ADD CONSTRAINT hierarchy_node_pkey PRIMARY KEY (id);


--
-- Name: image_generation_config image_generation_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY image_generation_config
    ADD CONSTRAINT image_generation_config_pkey PRIMARY KEY (image_provider_id);


--
-- Name: index_attempt_errors index_attempt_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt_errors
    ADD CONSTRAINT index_attempt_errors_pkey PRIMARY KEY (id);


--
-- Name: index_attempt index_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt
    ADD CONSTRAINT index_attempt_pkey PRIMARY KEY (id);


--
-- Name: inputprompt__user inputprompt__user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt__user
    ADD CONSTRAINT inputprompt__user_pkey PRIMARY KEY (input_prompt_id, user_id);


--
-- Name: inputprompt inputprompt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt
    ADD CONSTRAINT inputprompt_pkey PRIMARY KEY (id);


--
-- Name: internet_content_provider internet_content_provider_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_content_provider
    ADD CONSTRAINT internet_content_provider_name_key UNIQUE (name);


--
-- Name: internet_content_provider internet_content_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_content_provider
    ADD CONSTRAINT internet_content_provider_pkey PRIMARY KEY (id);


--
-- Name: internet_search_provider internet_search_provider_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_search_provider
    ADD CONSTRAINT internet_search_provider_name_key UNIQUE (name);


--
-- Name: internet_search_provider internet_search_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY internet_search_provider
    ADD CONSTRAINT internet_search_provider_pkey PRIMARY KEY (id);


--
-- Name: key_value_store key_value_store_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY key_value_store
    ADD CONSTRAINT key_value_store_pkey PRIMARY KEY (key);


--
-- Name: kg_entity_extraction_staging kg_entity_extraction_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity_extraction_staging
    ADD CONSTRAINT kg_entity_extraction_staging_pkey PRIMARY KEY (id_name);


--
-- Name: kg_entity kg_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity
    ADD CONSTRAINT kg_entity_pkey PRIMARY KEY (id_name);


--
-- Name: kg_entity_type kg_entity_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity_type
    ADD CONSTRAINT kg_entity_type_pkey PRIMARY KEY (id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_pkey PRIMARY KEY (id_name, source_document);


--
-- Name: kg_relationship kg_relationship_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_pkey PRIMARY KEY (id_name, source_document);


--
-- Name: kg_relationship_type_extraction_staging kg_relationship_type_extraction_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type_extraction_staging
    ADD CONSTRAINT kg_relationship_type_extraction_staging_pkey PRIMARY KEY (id_name);


--
-- Name: kg_relationship_type kg_relationship_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type
    ADD CONSTRAINT kg_relationship_type_pkey PRIMARY KEY (id_name);


--
-- Name: kg_term kg_term_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_term
    ADD CONSTRAINT kg_term_pkey PRIMARY KEY (id_term);


--
-- Name: license license_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY license
    ADD CONSTRAINT license_pkey PRIMARY KEY (id);


--
-- Name: llm_model_flow llm_model_flow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_model_flow
    ADD CONSTRAINT llm_model_flow_pkey PRIMARY KEY (id);


--
-- Name: llm_provider__persona llm_provider__persona_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__persona
    ADD CONSTRAINT llm_provider__persona_pkey PRIMARY KEY (llm_provider_id, persona_id);


--
-- Name: llm_provider__user_group llm_provider__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__user_group
    ADD CONSTRAINT llm_provider__user_group_pkey PRIMARY KEY (llm_provider_id, user_group_id);


--
-- Name: llm_provider llm_provider_is_default_provider_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider
    ADD CONSTRAINT llm_provider_is_default_provider_key UNIQUE (is_default_provider);


--
-- Name: llm_provider llm_provider_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider
    ADD CONSTRAINT llm_provider_name_key UNIQUE (name);


--
-- Name: llm_provider llm_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider
    ADD CONSTRAINT llm_provider_pkey PRIMARY KEY (id);


--
-- Name: mcp_connection_config mcp_connection_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_connection_config
    ADD CONSTRAINT mcp_connection_config_pkey PRIMARY KEY (id);


--
-- Name: mcp_server__user_group mcp_server__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user_group
    ADD CONSTRAINT mcp_server__user_group_pkey PRIMARY KEY (mcp_server_id, user_group_id);


--
-- Name: mcp_server__user mcp_server__user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user
    ADD CONSTRAINT mcp_server__user_pkey PRIMARY KEY (mcp_server_id, user_id);


--
-- Name: mcp_server mcp_server_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server
    ADD CONSTRAINT mcp_server_pkey PRIMARY KEY (id);


--
-- Name: memory memory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY memory
    ADD CONSTRAINT memory_pkey PRIMARY KEY (id);


--
-- Name: model_configuration model_configuration_llm_provider_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY model_configuration
    ADD CONSTRAINT model_configuration_llm_provider_id_name_key UNIQUE (llm_provider_id, name);


--
-- Name: model_configuration model_configuration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY model_configuration
    ADD CONSTRAINT model_configuration_pkey PRIMARY KEY (id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);


--
-- Name: oauth_account oauth_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_account
    ADD CONSTRAINT oauth_account_pkey PRIMARY KEY (id);


--
-- Name: oauth_config oauth_config_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_config
    ADD CONSTRAINT oauth_config_name_key UNIQUE (name);


--
-- Name: oauth_config oauth_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_config
    ADD CONSTRAINT oauth_config_pkey PRIMARY KEY (id);


--
-- Name: oauth_user_token oauth_user_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_user_token
    ADD CONSTRAINT oauth_user_token_pkey PRIMARY KEY (id);


--
-- Name: persona__document persona__document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document
    ADD CONSTRAINT persona__document_pkey PRIMARY KEY (persona_id, document_id);


--
-- Name: persona__document_set persona__document_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document_set
    ADD CONSTRAINT persona__document_set_pkey PRIMARY KEY (persona_id, document_set_id);


--
-- Name: persona__hierarchy_node persona__hierarchy_node_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__hierarchy_node
    ADD CONSTRAINT persona__hierarchy_node_pkey PRIMARY KEY (persona_id, hierarchy_node_id);


--
-- Name: persona__persona_label persona__persona_label_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__persona_label
    ADD CONSTRAINT persona__persona_label_pkey PRIMARY KEY (persona_id, persona_label_id);


--
-- Name: persona__tool persona__tool_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__tool
    ADD CONSTRAINT persona__tool_pkey PRIMARY KEY (persona_id, tool_id);


--
-- Name: persona__user_file persona__user_file_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_file
    ADD CONSTRAINT persona__user_file_pkey PRIMARY KEY (persona_id, user_file_id);


--
-- Name: persona__user_group persona__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_group
    ADD CONSTRAINT persona__user_group_pkey PRIMARY KEY (persona_id, user_group_id);


--
-- Name: persona__user persona__user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user
    ADD CONSTRAINT persona__user_pkey PRIMARY KEY (persona_id, user_id);


--
-- Name: persona_label persona_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona_label
    ADD CONSTRAINT persona_category_name_key UNIQUE (name);


--
-- Name: persona_label persona_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona_label
    ADD CONSTRAINT persona_category_pkey PRIMARY KEY (id);


--
-- Name: persona persona_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona
    ADD CONSTRAINT persona_pkey PRIMARY KEY (id);


--
-- Name: personal_access_token personal_access_token_hashed_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY personal_access_token
    ADD CONSTRAINT personal_access_token_hashed_token_key UNIQUE (hashed_token);


--
-- Name: personal_access_token personal_access_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY personal_access_token
    ADD CONSTRAINT personal_access_token_pkey PRIMARY KEY (id);


--
-- Name: project__user_file project__user_file_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY project__user_file
    ADD CONSTRAINT project__user_file_pkey PRIMARY KEY (project_id, user_file_id);


--
-- Name: public_external_user_group public_external_user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public_external_user_group
    ADD CONSTRAINT public_external_user_group_pkey PRIMARY KEY (external_user_group_id, cc_pair_id);


--
-- Name: saml saml_encrypted_cookie_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY saml
    ADD CONSTRAINT saml_encrypted_cookie_key UNIQUE (encrypted_cookie);


--
-- Name: saml saml_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY saml
    ADD CONSTRAINT saml_pkey PRIMARY KEY (id);


--
-- Name: saml saml_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY saml
    ADD CONSTRAINT saml_user_id_key UNIQUE (user_id);


--
-- Name: sandbox sandbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sandbox
    ADD CONSTRAINT sandbox_pkey PRIMARY KEY (id);


--
-- Name: sandbox sandbox_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sandbox
    ADD CONSTRAINT sandbox_user_id_key UNIQUE (user_id);


--
-- Name: scim_group_mapping scim_group_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_group_mapping
    ADD CONSTRAINT scim_group_mapping_pkey PRIMARY KEY (id);


--
-- Name: scim_group_mapping scim_group_mapping_user_group_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_group_mapping
    ADD CONSTRAINT scim_group_mapping_user_group_id_key UNIQUE (user_group_id);


--
-- Name: scim_token scim_token_hashed_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_token
    ADD CONSTRAINT scim_token_hashed_token_key UNIQUE (hashed_token);


--
-- Name: scim_token scim_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_token
    ADD CONSTRAINT scim_token_pkey PRIMARY KEY (id);


--
-- Name: scim_user_mapping scim_user_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_user_mapping
    ADD CONSTRAINT scim_user_mapping_pkey PRIMARY KEY (id);


--
-- Name: scim_user_mapping scim_user_mapping_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_user_mapping
    ADD CONSTRAINT scim_user_mapping_user_id_key UNIQUE (user_id);


--
-- Name: search_doc search_doc_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_doc
    ADD CONSTRAINT search_doc_pkey PRIMARY KEY (id);


--
-- Name: search_query search_query_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_query
    ADD CONSTRAINT search_query_pkey PRIMARY KEY (id);


--
-- Name: slack_bot slack_bot_app_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_bot
    ADD CONSTRAINT slack_bot_app_token_key UNIQUE (app_token);


--
-- Name: slack_bot slack_bot_bot_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_bot
    ADD CONSTRAINT slack_bot_bot_token_key UNIQUE (bot_token);


--
-- Name: slack_channel_config__standard_answer_category slack_bot_config__standard_answer_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config__standard_answer_category
    ADD CONSTRAINT slack_bot_config__standard_answer_category_pkey PRIMARY KEY (slack_channel_config_id, standard_answer_category_id);


--
-- Name: slack_bot slack_bot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_bot
    ADD CONSTRAINT slack_bot_pkey PRIMARY KEY (id);


--
-- Name: slack_channel_config slack_channel_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config
    ADD CONSTRAINT slack_channel_config_pkey PRIMARY KEY (id);


--
-- Name: snapshot snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY snapshot
    ADD CONSTRAINT snapshot_pkey PRIMARY KEY (id);


--
-- Name: standard_answer__standard_answer_category standard_answer__standard_answer_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer__standard_answer_category
    ADD CONSTRAINT standard_answer__standard_answer_category_pkey PRIMARY KEY (standard_answer_id, standard_answer_category_id);


--
-- Name: standard_answer_category standard_answer_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer_category
    ADD CONSTRAINT standard_answer_category_name_key UNIQUE (name);


--
-- Name: standard_answer_category standard_answer_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer_category
    ADD CONSTRAINT standard_answer_category_pkey PRIMARY KEY (id);


--
-- Name: standard_answer standard_answer_keyword_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer
    ADD CONSTRAINT standard_answer_keyword_key UNIQUE (keyword);


--
-- Name: standard_answer standard_answer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer
    ADD CONSTRAINT standard_answer_pkey PRIMARY KEY (id);


--
-- Name: sync_record sync_record_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sync_record
    ADD CONSTRAINT sync_record_pkey PRIMARY KEY (id);


--
-- Name: tag tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (id);


--
-- Name: task_queue_jobs task_queue_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY task_queue_jobs
    ADD CONSTRAINT task_queue_jobs_pkey PRIMARY KEY (id);


--
-- Name: tenant_usage tenant_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tenant_usage
    ADD CONSTRAINT tenant_usage_pkey PRIMARY KEY (id);


--
-- Name: token_rate_limit__user_group token_rate_limit__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY token_rate_limit__user_group
    ADD CONSTRAINT token_rate_limit__user_group_pkey PRIMARY KEY (rate_limit_id, user_group_id);


--
-- Name: token_rate_limit token_rate_limit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY token_rate_limit
    ADD CONSTRAINT token_rate_limit_pkey PRIMARY KEY (id);


--
-- Name: tool_call__search_doc tool_call__search_doc_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call__search_doc
    ADD CONSTRAINT tool_call__search_doc_pkey PRIMARY KEY (tool_call_id, search_doc_id);


--
-- Name: tool_call tool_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call
    ADD CONSTRAINT tool_call_pkey PRIMARY KEY (id);


--
-- Name: tool tool_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool
    ADD CONSTRAINT tool_pkey PRIMARY KEY (id);


--
-- Name: chunk_stats uq_chunk_stats_doc_chunk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chunk_stats
    ADD CONSTRAINT uq_chunk_stats_doc_chunk UNIQUE (document_id, chunk_in_doc_id);


--
-- Name: discord_channel_config uq_discord_channel_guild_channel; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_channel_config
    ADD CONSTRAINT uq_discord_channel_guild_channel UNIQUE (guild_config_id, channel_id);


--
-- Name: federated_connector__document_set uq_federated_connector_document_set; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector__document_set
    ADD CONSTRAINT uq_federated_connector_document_set UNIQUE (federated_connector_id, document_set_id);


--
-- Name: hierarchy_node uq_hierarchy_node_raw_id_source; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_node
    ADD CONSTRAINT uq_hierarchy_node_raw_id_source UNIQUE (raw_node_id, source);


--
-- Name: inputprompt uq_inputprompt_prompt_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt
    ADD CONSTRAINT uq_inputprompt_prompt_user_id UNIQUE (prompt, user_id);


--
-- Name: kg_entity uq_kg_entity_name_type_doc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity
    ADD CONSTRAINT uq_kg_entity_name_type_doc UNIQUE (name, entity_type_id_name, document_id);


--
-- Name: kg_relationship_extraction_staging uq_kg_relationship_extraction_staging_source_target_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT uq_kg_relationship_extraction_staging_source_target_type UNIQUE (source_node, target_node, type);


--
-- Name: kg_relationship uq_kg_relationship_source_target_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT uq_kg_relationship_source_target_type UNIQUE (source_node, target_node, type);


--
-- Name: llm_model_flow uq_model_config_per_llm_model_flow_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_model_flow
    ADD CONSTRAINT uq_model_config_per_llm_model_flow_type UNIQUE (llm_model_flow_type, model_configuration_id);


--
-- Name: oauth_user_token uq_oauth_user_token; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_user_token
    ADD CONSTRAINT uq_oauth_user_token UNIQUE (oauth_config_id, user_id);


--
-- Name: tenant_usage uq_tenant_usage_window; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tenant_usage
    ADD CONSTRAINT uq_tenant_usage_window UNIQUE (window_start);


--
-- Name: agent_workflow_step uq_workflow_step_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow_step
    ADD CONSTRAINT uq_workflow_step_order UNIQUE (workflow_id, step_order);


--
-- Name: usage_reports usage_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY usage_reports
    ADD CONSTRAINT usage_reports_pkey PRIMARY KEY (id);


--
-- Name: user__external_user_group_id user__external_user_group_id_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user__external_user_group_id
    ADD CONSTRAINT user__external_user_group_id_pkey PRIMARY KEY (user_id, external_user_group_id, cc_pair_id);


--
-- Name: user__user_group user__user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user__user_group
    ADD CONSTRAINT user__user_group_pkey PRIMARY KEY (user_group_id, user_id);


--
-- Name: user_file user_file_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_file
    ADD CONSTRAINT user_file_pkey PRIMARY KEY (id);


--
-- Name: user_project user_folder_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_project
    ADD CONSTRAINT user_folder_pkey PRIMARY KEY (id);


--
-- Name: user_group__connector_credential_pair user_group__connector_credential_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group__connector_credential_pair
    ADD CONSTRAINT user_group__connector_credential_pair_pkey PRIMARY KEY (user_group_id, cc_pair_id, is_current);


--
-- Name: user_group user_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group
    ADD CONSTRAINT user_group_name_key UNIQUE (name);


--
-- Name: user_group user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group
    ADD CONSTRAINT user_group_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: workflow_execution workflow_execution_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution
    ADD CONSTRAINT workflow_execution_pkey PRIMARY KEY (id);


--
-- Name: _builtin_persona_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX _builtin_persona_name_idx ON persona USING btree (name) WHERE (builtin_persona = true);


--
-- Name: idx_chat_message_tsv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_message_tsv ON chat_message USING gin (message_tsv);


--
-- Name: idx_chat_session_desc_tsv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_session_desc_tsv ON chat_session USING gin (description_tsv);


--
-- Name: idx_document_cc_pair_connector_credential; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_cc_pair_connector_credential ON document_by_connector_credential_pair USING btree (connector_id, credential_id);


--
-- Name: idx_document_cc_pair_counts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_cc_pair_counts ON document_by_connector_credential_pair USING btree (connector_id, credential_id, has_been_indexed);


--
-- Name: idx_kg_entity_clustering_trigrams; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kg_entity_clustering_trigrams ON kg_entity USING gin (name public.gin_trgm_ops);


--
-- Name: idx_kg_entity_normalization_trigrams; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kg_entity_normalization_trigrams ON kg_entity USING gin (name_trigrams);


--
-- Name: idx_license_singleton; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_license_singleton ON license USING btree ((true));


--
-- Name: idx_project__user_file_user_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project__user_file_user_file_id ON project__user_file USING btree (user_file_id);


--
-- Name: ix_accesstoken_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_accesstoken_created_at ON accesstoken USING btree (created_at);


--
-- Name: ix_artifact_session_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_artifact_session_created ON artifact USING btree (session_id, created_at DESC);


--
-- Name: ix_artifact_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_artifact_type ON artifact USING btree (type);


--
-- Name: ix_build_message_session_turn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_build_message_session_turn ON build_message USING btree (session_id, turn_index, created_at);


--
-- Name: ix_build_session_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_build_session_status ON build_session USING btree (status);


--
-- Name: ix_build_session_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_build_session_user_created ON build_session USING btree (user_id, created_at DESC);


--
-- Name: ix_chat_session_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_session_project_id ON chat_session USING btree (project_id);


--
-- Name: ix_chunk_stats_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunk_stats_document_id ON chunk_stats USING btree (document_id);


--
-- Name: ix_chunk_stats_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunk_stats_id ON chunk_stats USING btree (id);


--
-- Name: ix_chunk_stats_last_modified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunk_stats_last_modified ON chunk_stats USING btree (last_modified);


--
-- Name: ix_chunk_stats_last_synced; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunk_stats_last_synced ON chunk_stats USING btree (last_synced);


--
-- Name: ix_chunk_sync_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunk_sync_status ON chunk_stats USING btree (last_modified, last_synced);


--
-- Name: ix_doc_permission_sync_attempt_time_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_doc_permission_sync_attempt_time_created ON doc_permission_sync_attempt USING btree (time_created);


--
-- Name: ix_document__tag_tag_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document__tag_tag_id ON document__tag USING btree (tag_id);


--
-- Name: ix_document_by_connector_credential_pair_pkey__connecto_27dc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_by_connector_credential_pair_pkey__connecto_27dc ON document_by_connector_credential_pair USING btree (connector_id, credential_id);


--
-- Name: ix_document_kg_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_kg_stage ON document USING btree (kg_stage);


--
-- Name: ix_document_last_modified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_last_modified ON document USING btree (last_modified);


--
-- Name: ix_document_last_synced; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_last_synced ON document USING btree (last_synced);


--
-- Name: ix_document_parent_hierarchy_node_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_parent_hierarchy_node_id ON document USING btree (parent_hierarchy_node_id);


--
-- Name: ix_document_sync_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_sync_status ON document USING btree (last_modified, last_synced);


--
-- Name: ix_entity_extraction_staging_acl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_extraction_staging_acl ON kg_entity_extraction_staging USING btree (entity_type_id_name, acl);


--
-- Name: ix_entity_extraction_staging_name_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_extraction_staging_name_search ON kg_entity_extraction_staging USING btree (name, entity_type_id_name);


--
-- Name: ix_entity_name_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_name_search ON kg_entity USING btree (name, entity_type_id_name);


--
-- Name: ix_entity_type_acl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_type_acl ON kg_entity USING btree (entity_type_id_name, acl);


--
-- Name: ix_external_group_permission_sync_attempt_time_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_external_group_permission_sync_attempt_time_created ON external_group_permission_sync_attempt USING btree (time_created);


--
-- Name: ix_group_sync_attempt_cc_pair_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_group_sync_attempt_cc_pair_time ON external_group_permission_sync_attempt USING btree (connector_credential_pair_id, time_created);


--
-- Name: ix_group_sync_attempt_status_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_group_sync_attempt_status_time ON external_group_permission_sync_attempt USING btree (status, time_finished DESC);


--
-- Name: ix_hierarchy_fetch_attempt_cc_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hierarchy_fetch_attempt_cc_pair ON hierarchy_fetch_attempt USING btree (connector_credential_pair_id);


--
-- Name: ix_hierarchy_fetch_attempt_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hierarchy_fetch_attempt_status ON hierarchy_fetch_attempt USING btree (status);


--
-- Name: ix_hierarchy_fetch_attempt_time_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hierarchy_fetch_attempt_time_created ON hierarchy_fetch_attempt USING btree (time_created);


--
-- Name: ix_hierarchy_node_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hierarchy_node_parent_id ON hierarchy_node USING btree (parent_id);


--
-- Name: ix_hierarchy_node_source_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hierarchy_node_source_type ON hierarchy_node USING btree (source, node_type);


--
-- Name: ix_image_generation_config_is_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_image_generation_config_is_default ON image_generation_config USING btree (is_default);


--
-- Name: ix_image_generation_config_model_configuration_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_image_generation_config_model_configuration_id ON image_generation_config USING btree (model_configuration_id);


--
-- Name: ix_index_attempt_active_coordination; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_active_coordination ON index_attempt USING btree (connector_credential_pair_id, search_settings_id, status);


--
-- Name: ix_index_attempt_cc_pair_settings_poll; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_cc_pair_settings_poll ON index_attempt USING btree (connector_credential_pair_id, search_settings_id, status, time_updated DESC);


--
-- Name: ix_index_attempt_ccpair_search_settings_time_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_ccpair_search_settings_time_updated ON index_attempt USING btree (connector_credential_pair_id, search_settings_id, time_updated DESC);


--
-- Name: ix_index_attempt_latest_for_connector_credential_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_latest_for_connector_credential_pair ON index_attempt USING btree (connector_credential_pair_id, time_created);


--
-- Name: ix_index_attempt_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_status ON index_attempt USING btree (status);


--
-- Name: ix_index_attempt_time_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_index_attempt_time_created ON index_attempt USING btree (time_created);


--
-- Name: ix_internet_content_provider_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_internet_content_provider_is_active ON internet_content_provider USING btree (is_active);


--
-- Name: ix_internet_search_provider_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_internet_search_provider_is_active ON internet_search_provider USING btree (is_active);


--
-- Name: ix_kg_entity_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_document_id ON kg_entity USING btree (document_id);


--
-- Name: ix_kg_entity_entity_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_entity_key ON kg_entity USING btree (entity_key);


--
-- Name: ix_kg_entity_entity_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_entity_type_id_name ON kg_entity USING btree (entity_type_id_name);


--
-- Name: ix_kg_entity_extraction_staging_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_document_id ON kg_entity_extraction_staging USING btree (document_id);


--
-- Name: ix_kg_entity_extraction_staging_entity_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_entity_key ON kg_entity_extraction_staging USING btree (entity_key);


--
-- Name: ix_kg_entity_extraction_staging_entity_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_entity_type_id_name ON kg_entity_extraction_staging USING btree (entity_type_id_name);


--
-- Name: ix_kg_entity_extraction_staging_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_id_name ON kg_entity_extraction_staging USING btree (id_name);


--
-- Name: ix_kg_entity_extraction_staging_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_name ON kg_entity_extraction_staging USING btree (name);


--
-- Name: ix_kg_entity_extraction_staging_parent_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_extraction_staging_parent_key ON kg_entity_extraction_staging USING btree (parent_key);


--
-- Name: ix_kg_entity_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_id_name ON kg_entity USING btree (id_name);


--
-- Name: ix_kg_entity_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_name ON kg_entity USING btree (name);


--
-- Name: ix_kg_entity_parent_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_parent_key ON kg_entity USING btree (parent_key);


--
-- Name: ix_kg_entity_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_entity_type_id_name ON kg_entity_type USING btree (id_name);


--
-- Name: ix_kg_relationship_extraction_staging_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_id_name ON kg_relationship_extraction_staging USING btree (id_name);


--
-- Name: ix_kg_relationship_extraction_staging_nodes; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_nodes ON kg_relationship_extraction_staging USING btree (source_node, target_node);


--
-- Name: ix_kg_relationship_extraction_staging_relationship_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_relationship_type_id_name ON kg_relationship_extraction_staging USING btree (relationship_type_id_name);


--
-- Name: ix_kg_relationship_extraction_staging_source_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_source_document ON kg_relationship_extraction_staging USING btree (source_document);


--
-- Name: ix_kg_relationship_extraction_staging_source_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_source_node ON kg_relationship_extraction_staging USING btree (source_node);


--
-- Name: ix_kg_relationship_extraction_staging_source_node_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_source_node_type ON kg_relationship_extraction_staging USING btree (source_node_type);


--
-- Name: ix_kg_relationship_extraction_staging_target_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_target_node ON kg_relationship_extraction_staging USING btree (target_node);


--
-- Name: ix_kg_relationship_extraction_staging_target_node_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_target_node_type ON kg_relationship_extraction_staging USING btree (target_node_type);


--
-- Name: ix_kg_relationship_extraction_staging_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_extraction_staging_type ON kg_relationship_extraction_staging USING btree (type);


--
-- Name: ix_kg_relationship_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_id_name ON kg_relationship USING btree (id_name);


--
-- Name: ix_kg_relationship_nodes; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_nodes ON kg_relationship USING btree (source_node, target_node);


--
-- Name: ix_kg_relationship_relationship_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_relationship_type_id_name ON kg_relationship USING btree (relationship_type_id_name);


--
-- Name: ix_kg_relationship_source_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_source_document ON kg_relationship USING btree (source_document);


--
-- Name: ix_kg_relationship_source_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_source_node ON kg_relationship USING btree (source_node);


--
-- Name: ix_kg_relationship_source_node_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_source_node_type ON kg_relationship USING btree (source_node_type);


--
-- Name: ix_kg_relationship_target_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_target_node ON kg_relationship USING btree (target_node);


--
-- Name: ix_kg_relationship_target_node_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_target_node_type ON kg_relationship USING btree (target_node_type);


--
-- Name: ix_kg_relationship_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type ON kg_relationship USING btree (type);


--
-- Name: ix_kg_relationship_type_extraction_staging_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_extraction_staging_id_name ON kg_relationship_type_extraction_staging USING btree (id_name);


--
-- Name: ix_kg_relationship_type_extraction_staging_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_extraction_staging_name ON kg_relationship_type_extraction_staging USING btree (name);


--
-- Name: ix_kg_relationship_type_extraction_staging_source_entit_11ac; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_extraction_staging_source_entit_11ac ON kg_relationship_type_extraction_staging USING btree (source_entity_type_id_name);


--
-- Name: ix_kg_relationship_type_extraction_staging_target_entit_6684; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_extraction_staging_target_entit_6684 ON kg_relationship_type_extraction_staging USING btree (target_entity_type_id_name);


--
-- Name: ix_kg_relationship_type_extraction_staging_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_extraction_staging_type ON kg_relationship_type_extraction_staging USING btree (type);


--
-- Name: ix_kg_relationship_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_id_name ON kg_relationship_type USING btree (id_name);


--
-- Name: ix_kg_relationship_type_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_name ON kg_relationship_type USING btree (name);


--
-- Name: ix_kg_relationship_type_source_entity_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_source_entity_type_id_name ON kg_relationship_type USING btree (source_entity_type_id_name);


--
-- Name: ix_kg_relationship_type_target_entity_type_id_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_target_entity_type_id_name ON kg_relationship_type USING btree (target_entity_type_id_name);


--
-- Name: ix_kg_relationship_type_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_relationship_type_type ON kg_relationship_type USING btree (type);


--
-- Name: ix_kg_term_id_term; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kg_term_id_term ON kg_term USING btree (id_term);


--
-- Name: ix_llm_provider__persona_composite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_provider__persona_composite ON llm_provider__persona USING btree (persona_id, llm_provider_id);


--
-- Name: ix_llm_provider__persona_llm_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_provider__persona_llm_provider_id ON llm_provider__persona USING btree (llm_provider_id);


--
-- Name: ix_llm_provider__persona_persona_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_provider__persona_persona_id ON llm_provider__persona USING btree (persona_id);


--
-- Name: ix_mcp_connection_config_server_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mcp_connection_config_server_user ON mcp_connection_config USING btree (mcp_server_id, user_email);


--
-- Name: ix_mcp_connection_config_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mcp_connection_config_user_email ON mcp_connection_config USING btree (user_email);


--
-- Name: ix_memory_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_user_id ON memory USING btree (user_id);


--
-- Name: ix_notification_user_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_user_sort ON notification USING btree (user_id, dismissed, first_shown DESC);


--
-- Name: ix_notification_user_type_data; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_notification_user_type_data ON notification USING btree (user_id, notif_type, COALESCE(additional_data, '{}'::jsonb));


--
-- Name: ix_oauth_account_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_oauth_account_account_id ON oauth_account USING btree (account_id);


--
-- Name: ix_oauth_account_oauth_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_oauth_account_oauth_name ON oauth_account USING btree (oauth_name);


--
-- Name: ix_oauth_user_token_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_oauth_user_token_user_id ON oauth_user_token USING btree (user_id);


--
-- Name: ix_one_default_per_llm_model_flow; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_one_default_per_llm_model_flow ON llm_model_flow USING btree (llm_model_flow_type) WHERE (is_default IS TRUE);


--
-- Name: ix_pat_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pat_user_created ON personal_access_token USING btree (user_id, created_at DESC);


--
-- Name: ix_permission_sync_attempt_latest_for_cc_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_permission_sync_attempt_latest_for_cc_pair ON doc_permission_sync_attempt USING btree (connector_credential_pair_id, time_created);


--
-- Name: ix_permission_sync_attempt_status_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_permission_sync_attempt_status_time ON doc_permission_sync_attempt USING btree (status, time_finished DESC);


--
-- Name: ix_persona__document_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona__document_document_id ON persona__document USING btree (document_id);


--
-- Name: ix_persona__hierarchy_node_hierarchy_node_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona__hierarchy_node_hierarchy_node_id ON persona__hierarchy_node USING btree (hierarchy_node_id);


--
-- Name: ix_personal_access_token_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_personal_access_token_expires_at ON personal_access_token USING btree (expires_at);


--
-- Name: ix_project__user_file_project_id_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_project__user_file_project_id_created_at ON project__user_file USING btree (project_id, created_at DESC);


--
-- Name: ix_public_external_user_group_cc_pair_id_stale; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_public_external_user_group_cc_pair_id_stale ON public_external_user_group USING btree (cc_pair_id, stale);


--
-- Name: ix_public_external_user_group_stale; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_public_external_user_group_stale ON public_external_user_group USING btree (stale);


--
-- Name: ix_sandbox_container_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sandbox_container_id ON sandbox USING btree (container_id);


--
-- Name: ix_sandbox_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sandbox_status ON sandbox USING btree (status);


--
-- Name: ix_scim_group_mapping_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_scim_group_mapping_external_id ON scim_group_mapping USING btree (external_id);


--
-- Name: ix_scim_user_mapping_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_scim_user_mapping_external_id ON scim_user_mapping USING btree (external_id);


--
-- Name: ix_search_query_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_query_created_at ON search_query USING btree (created_at);


--
-- Name: ix_search_query_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_query_user_id ON search_query USING btree (user_id);


--
-- Name: ix_search_term_entities; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_term_entities ON kg_term USING btree (entity_types);


--
-- Name: ix_search_term_term; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_term_term ON kg_term USING btree (id_term);


--
-- Name: ix_slack_channel_config_slack_bot_id_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_slack_channel_config_slack_bot_id_default ON slack_channel_config USING btree (slack_bot_id, is_default) WHERE (is_default IS TRUE);


--
-- Name: ix_snapshot_session_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_snapshot_session_created ON snapshot USING btree (session_id, created_at DESC);


--
-- Name: ix_sync_record_entity_id_sync_type_sync_start_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_record_entity_id_sync_type_sync_start_time ON sync_record USING btree (entity_id, sync_type, sync_start_time);


--
-- Name: ix_sync_record_entity_id_sync_type_sync_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_record_entity_id_sync_type_sync_status ON sync_record USING btree (entity_id, sync_type, sync_status);


--
-- Name: ix_tenant_usage_window_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_usage_window_start ON tenant_usage USING btree (window_start);


--
-- Name: ix_tool_mcp_server_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tool_mcp_server_enabled ON tool USING btree (mcp_server_id, enabled);


--
-- Name: ix_user__external_user_group_id_cc_pair_id_stale; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user__external_user_group_id_cc_pair_id_stale ON user__external_user_group_id USING btree (cc_pair_id, stale);


--
-- Name: ix_user__external_user_group_id_stale; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user__external_user_group_id_stale ON user__external_user_group_id USING btree (stale);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_email ON "user" USING btree (email);


--
-- Name: uq_hierarchy_node_one_source_per_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_hierarchy_node_one_source_per_type ON hierarchy_node USING btree (source) WHERE ((node_type)::text = 'SOURCE'::text);


--
-- Name: uq_inputprompt_prompt_public; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_inputprompt_prompt_public ON inputprompt USING btree (prompt) WHERE (user_id IS NULL);


--
-- Name: document update_kg_entity_name_from_doc_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_kg_entity_name_from_doc_trigger AFTER UPDATE OF semantic_id ON document FOR EACH ROW EXECUTE FUNCTION update_kg_entity_name_from_doc();


--
-- Name: kg_entity update_kg_entity_name_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_kg_entity_name_trigger BEFORE INSERT OR UPDATE OF name ON kg_entity FOR EACH ROW EXECUTE FUNCTION update_kg_entity_name();


--
-- Name: accesstoken accesstoken_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY accesstoken
    ADD CONSTRAINT accesstoken_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: agent_workflow_step agent_workflow_step_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow_step
    ADD CONSTRAINT agent_workflow_step_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: agent_workflow_step agent_workflow_step_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow_step
    ADD CONSTRAINT agent_workflow_step_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES agent_workflow(id) ON DELETE CASCADE;


--
-- Name: agent_workflow agent_workflow_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY agent_workflow
    ADD CONSTRAINT agent_workflow_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: artifact artifact_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY artifact
    ADD CONSTRAINT artifact_session_id_fkey FOREIGN KEY (session_id) REFERENCES build_session(id) ON DELETE CASCADE;


--
-- Name: assistant__user_specific_config assistant__user_specific_config_assistant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY assistant__user_specific_config
    ADD CONSTRAINT assistant__user_specific_config_assistant_id_fkey FOREIGN KEY (assistant_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: assistant__user_specific_config assistant__user_specific_config_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY assistant__user_specific_config
    ADD CONSTRAINT assistant__user_specific_config_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: background_error background_error_cc_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY background_error
    ADD CONSTRAINT background_error_cc_pair_id_fkey FOREIGN KEY (cc_pair_id) REFERENCES connector_credential_pair(id) ON DELETE CASCADE;


--
-- Name: build_message build_message_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY build_message
    ADD CONSTRAINT build_message_session_id_fkey FOREIGN KEY (session_id) REFERENCES build_session(id) ON DELETE CASCADE;


--
-- Name: build_session build_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY build_session
    ADD CONSTRAINT build_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: chat_feedback chat_feedback__chat_message_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_feedback
    ADD CONSTRAINT chat_feedback__chat_message_fk FOREIGN KEY (chat_message_id) REFERENCES chat_message(id) ON DELETE SET NULL;


--
-- Name: chat_message__search_doc chat_message__search_doc_chat_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__search_doc
    ADD CONSTRAINT chat_message__search_doc_chat_message_id_fkey FOREIGN KEY (chat_message_id) REFERENCES chat_message(id) ON DELETE CASCADE;


--
-- Name: chat_message__search_doc chat_message__search_doc_search_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__search_doc
    ADD CONSTRAINT chat_message__search_doc_search_doc_id_fkey FOREIGN KEY (search_doc_id) REFERENCES search_doc(id) ON DELETE CASCADE;


--
-- Name: chat_message__standard_answer chat_message__standard_answer_chat_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__standard_answer
    ADD CONSTRAINT chat_message__standard_answer_chat_message_id_fkey FOREIGN KEY (chat_message_id) REFERENCES chat_message(id) ON DELETE CASCADE;


--
-- Name: chat_message__standard_answer chat_message__standard_answer_standard_answer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message__standard_answer
    ADD CONSTRAINT chat_message__standard_answer_standard_answer_id_fkey FOREIGN KEY (standard_answer_id) REFERENCES standard_answer(id);


--
-- Name: chat_message chat_message_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message
    ADD CONSTRAINT chat_message_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES chat_session(id) ON DELETE CASCADE;


--
-- Name: chat_message chat_message_last_summarized_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message
    ADD CONSTRAINT chat_message_last_summarized_message_id_fkey FOREIGN KEY (last_summarized_message_id) REFERENCES chat_message(id) ON DELETE SET NULL;


--
-- Name: chat_session chat_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_session
    ADD CONSTRAINT chat_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: chunk_stats chunk_stats_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chunk_stats
    ADD CONSTRAINT chunk_stats_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id);


--
-- Name: connector_credential_pair connector_credential_pair_connector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector_credential_pair
    ADD CONSTRAINT connector_credential_pair_connector_id_fkey FOREIGN KEY (connector_id) REFERENCES connector(id);


--
-- Name: connector_credential_pair connector_credential_pair_credential_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY connector_credential_pair
    ADD CONSTRAINT connector_credential_pair_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES credential(id);


--
-- Name: credential__user_group credential__user_group_credential_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential__user_group
    ADD CONSTRAINT credential__user_group_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES credential(id);


--
-- Name: credential__user_group credential__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential__user_group
    ADD CONSTRAINT credential__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: credential credential_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credential
    ADD CONSTRAINT credential_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: discord_channel_config discord_channel_config_guild_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_channel_config
    ADD CONSTRAINT discord_channel_config_guild_config_id_fkey FOREIGN KEY (guild_config_id) REFERENCES discord_guild_config(id) ON DELETE CASCADE;


--
-- Name: discord_channel_config discord_channel_config_persona_override_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_channel_config
    ADD CONSTRAINT discord_channel_config_persona_override_id_fkey FOREIGN KEY (persona_override_id) REFERENCES persona(id) ON DELETE SET NULL;


--
-- Name: discord_guild_config discord_guild_config_default_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY discord_guild_config
    ADD CONSTRAINT discord_guild_config_default_persona_id_fkey FOREIGN KEY (default_persona_id) REFERENCES persona(id) ON DELETE SET NULL;


--
-- Name: doc_permission_sync_attempt doc_permission_sync_attempt_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doc_permission_sync_attempt
    ADD CONSTRAINT doc_permission_sync_attempt_connector_credential_pair_id_fkey FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: document__tag document__tag_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document__tag
    ADD CONSTRAINT document__tag_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id);


--
-- Name: document__tag document__tag_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document__tag
    ADD CONSTRAINT document__tag_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES tag(id);


--
-- Name: document_by_connector_credential_pair document_by_connector_credential_pair_connector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_by_connector_credential_pair
    ADD CONSTRAINT document_by_connector_credential_pair_connector_id_fkey FOREIGN KEY (connector_id) REFERENCES connector(id) ON DELETE CASCADE;


--
-- Name: document_by_connector_credential_pair document_by_connector_credential_pair_credential_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_by_connector_credential_pair
    ADD CONSTRAINT document_by_connector_credential_pair_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES credential(id) ON DELETE CASCADE;


--
-- Name: document_by_connector_credential_pair document_by_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_by_connector_credential_pair
    ADD CONSTRAINT document_by_connector_credential_pair_id_fkey FOREIGN KEY (id) REFERENCES document(id);


--
-- Name: document_retrieval_feedback document_retrieval_feedback__chat_message_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback__chat_message_fk FOREIGN KEY (chat_message_id) REFERENCES chat_message(id) ON DELETE SET NULL;


--
-- Name: document_retrieval_feedback document_retrieval_feedback_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id);


--
-- Name: document_set__connector_credential_pair document_set__connector_crede_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__connector_credential_pair
    ADD CONSTRAINT document_set__connector_crede_connector_credential_pair_id_fkey FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: document_set__connector_credential_pair document_set__connector_credential_pair_document_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__connector_credential_pair
    ADD CONSTRAINT document_set__connector_credential_pair_document_set_id_fkey FOREIGN KEY (document_set_id) REFERENCES document_set(id);


--
-- Name: document_set__user document_set__user_document_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user
    ADD CONSTRAINT document_set__user_document_set_id_fkey FOREIGN KEY (document_set_id) REFERENCES document_set(id);


--
-- Name: document_set__user_group document_set__user_group_document_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user_group
    ADD CONSTRAINT document_set__user_group_document_set_id_fkey FOREIGN KEY (document_set_id) REFERENCES document_set(id);


--
-- Name: document_set__user_group document_set__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user_group
    ADD CONSTRAINT document_set__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: document_set__user document_set__user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set__user
    ADD CONSTRAINT document_set__user_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: document_set document_set_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document_set
    ADD CONSTRAINT document_set_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: external_group_permission_sync_attempt external_group_permission_syn_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY external_group_permission_sync_attempt
    ADD CONSTRAINT external_group_permission_syn_connector_credential_pair_id_fkey FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: federated_connector__document_set federated_connector__document_set_document_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector__document_set
    ADD CONSTRAINT federated_connector__document_set_document_set_id_fkey FOREIGN KEY (document_set_id) REFERENCES document_set(id) ON DELETE CASCADE;


--
-- Name: federated_connector__document_set federated_connector__document_set_federated_connector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector__document_set
    ADD CONSTRAINT federated_connector__document_set_federated_connector_id_fkey FOREIGN KEY (federated_connector_id) REFERENCES federated_connector(id) ON DELETE CASCADE;


--
-- Name: federated_connector_oauth_token federated_connector_oauth_token_federated_connector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector_oauth_token
    ADD CONSTRAINT federated_connector_oauth_token_federated_connector_id_fkey FOREIGN KEY (federated_connector_id) REFERENCES federated_connector(id) ON DELETE CASCADE;


--
-- Name: federated_connector_oauth_token federated_connector_oauth_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY federated_connector_oauth_token
    ADD CONSTRAINT federated_connector_oauth_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: file_content file_content_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY file_content
    ADD CONSTRAINT file_content_file_id_fkey FOREIGN KEY (file_id) REFERENCES file_record(file_id) ON DELETE CASCADE;


--
-- Name: chat_message fk_chat_message_latest_child_message_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message
    ADD CONSTRAINT fk_chat_message_latest_child_message_id FOREIGN KEY (latest_child_message_id) REFERENCES chat_message(id);


--
-- Name: chat_message fk_chat_message_parent_message_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_message
    ADD CONSTRAINT fk_chat_message_parent_message_id FOREIGN KEY (parent_message_id) REFERENCES chat_message(id);


--
-- Name: chat_session fk_chat_session_persona_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_session
    ADD CONSTRAINT fk_chat_session_persona_id FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: chat_session fk_chat_session_project_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY chat_session
    ADD CONSTRAINT fk_chat_session_project_id FOREIGN KEY (project_id) REFERENCES user_project(id);


--
-- Name: document fk_document_parent_hierarchy_node; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY document
    ADD CONSTRAINT fk_document_parent_hierarchy_node FOREIGN KEY (parent_hierarchy_node_id) REFERENCES hierarchy_node(id) ON DELETE SET NULL;


--
-- Name: search_settings fk_embedding_model_cloud_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_settings
    ADD CONSTRAINT fk_embedding_model_cloud_provider FOREIGN KEY (provider_type) REFERENCES embedding_provider(provider_type);


--
-- Name: index_attempt fk_index_attempt_connector_credential_pair_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt
    ADD CONSTRAINT fk_index_attempt_connector_credential_pair_id FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: index_attempt fk_index_attempt_search_settings; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt
    ADD CONSTRAINT fk_index_attempt_search_settings FOREIGN KEY (search_settings_id) REFERENCES search_settings(id) ON DELETE SET NULL;


--
-- Name: persona fk_persona_default_model_configuration_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona
    ADD CONSTRAINT fk_persona_default_model_configuration_id FOREIGN KEY (default_model_configuration_id) REFERENCES model_configuration(id) ON DELETE SET NULL;


--
-- Name: project__user_file fk_project__user_file_project_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY project__user_file
    ADD CONSTRAINT fk_project__user_file_project_id FOREIGN KEY (project_id) REFERENCES user_project(id);


--
-- Name: project__user_file fk_project__user_file_user_file_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY project__user_file
    ADD CONSTRAINT fk_project__user_file_user_file_id FOREIGN KEY (user_file_id) REFERENCES user_file(id);


--
-- Name: tool_call fk_tool_call_chat_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call
    ADD CONSTRAINT fk_tool_call_chat_session_id FOREIGN KEY (chat_session_id) REFERENCES chat_session(id) ON DELETE CASCADE;


--
-- Name: tool_call fk_tool_call_parent_chat_message_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call
    ADD CONSTRAINT fk_tool_call_parent_chat_message_id FOREIGN KEY (parent_chat_message_id) REFERENCES chat_message(id) ON DELETE CASCADE;


--
-- Name: tool_call fk_tool_call_parent_tool_call_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call
    ADD CONSTRAINT fk_tool_call_parent_tool_call_id FOREIGN KEY (parent_tool_call_id) REFERENCES tool_call(id) ON DELETE CASCADE;


--
-- Name: user__external_user_group_id fk_user__external_user_group_id_cc_pair_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user__external_user_group_id
    ADD CONSTRAINT fk_user__external_user_group_id_cc_pair_id FOREIGN KEY (cc_pair_id) REFERENCES connector_credential_pair(id) ON DELETE CASCADE;


--
-- Name: hierarchy_fetch_attempt hierarchy_fetch_attempt_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_fetch_attempt
    ADD CONSTRAINT hierarchy_fetch_attempt_connector_credential_pair_id_fkey FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id) ON DELETE CASCADE;


--
-- Name: hierarchy_node hierarchy_node_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_node
    ADD CONSTRAINT hierarchy_node_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;


--
-- Name: hierarchy_node hierarchy_node_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY hierarchy_node
    ADD CONSTRAINT hierarchy_node_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES hierarchy_node(id) ON DELETE SET NULL;


--
-- Name: image_generation_config image_generation_config_model_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY image_generation_config
    ADD CONSTRAINT image_generation_config_model_configuration_id_fkey FOREIGN KEY (model_configuration_id) REFERENCES model_configuration(id) ON DELETE CASCADE;


--
-- Name: index_attempt_errors index_attempt_errors_connector_credential_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt_errors
    ADD CONSTRAINT index_attempt_errors_connector_credential_pair_id_fkey FOREIGN KEY (connector_credential_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: index_attempt_errors index_attempt_errors_index_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY index_attempt_errors
    ADD CONSTRAINT index_attempt_errors_index_attempt_id_fkey FOREIGN KEY (index_attempt_id) REFERENCES index_attempt(id);


--
-- Name: inputprompt__user inputprompt__user_input_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt__user
    ADD CONSTRAINT inputprompt__user_input_prompt_id_fkey FOREIGN KEY (input_prompt_id) REFERENCES inputprompt(id) ON DELETE CASCADE;


--
-- Name: inputprompt__user inputprompt__user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt__user
    ADD CONSTRAINT inputprompt__user_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: inputprompt inputprompt_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY inputprompt
    ADD CONSTRAINT inputprompt_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: kg_entity kg_entity_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity
    ADD CONSTRAINT kg_entity_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id);


--
-- Name: kg_entity kg_entity_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity
    ADD CONSTRAINT kg_entity_entity_type_id_name_fkey FOREIGN KEY (entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_entity_extraction_staging kg_entity_extraction_staging_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity_extraction_staging
    ADD CONSTRAINT kg_entity_extraction_staging_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id);


--
-- Name: kg_entity_extraction_staging kg_entity_extraction_staging_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_entity_extraction_staging
    ADD CONSTRAINT kg_entity_extraction_staging_entity_type_id_name_fkey FOREIGN KEY (entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_stagi_relationship_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_stagi_relationship_type_id_name_fkey FOREIGN KEY (relationship_type_id_name) REFERENCES kg_relationship_type_extraction_staging(id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_source_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_source_document_fkey FOREIGN KEY (source_document) REFERENCES document(id);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_source_node_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_source_node_fkey FOREIGN KEY (source_node) REFERENCES kg_entity_extraction_staging(id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_source_node_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_source_node_type_fkey FOREIGN KEY (source_node_type) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_target_node_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_target_node_fkey FOREIGN KEY (target_node) REFERENCES kg_entity_extraction_staging(id_name);


--
-- Name: kg_relationship_extraction_staging kg_relationship_extraction_staging_target_node_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_extraction_staging
    ADD CONSTRAINT kg_relationship_extraction_staging_target_node_type_fkey FOREIGN KEY (target_node_type) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship kg_relationship_relationship_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_relationship_type_id_name_fkey FOREIGN KEY (relationship_type_id_name) REFERENCES kg_relationship_type(id_name);


--
-- Name: kg_relationship kg_relationship_source_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_source_document_fkey FOREIGN KEY (source_document) REFERENCES document(id);


--
-- Name: kg_relationship kg_relationship_source_node_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_source_node_fkey FOREIGN KEY (source_node) REFERENCES kg_entity(id_name);


--
-- Name: kg_relationship kg_relationship_source_node_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_source_node_type_fkey FOREIGN KEY (source_node_type) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship kg_relationship_target_node_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_target_node_fkey FOREIGN KEY (target_node) REFERENCES kg_entity(id_name);


--
-- Name: kg_relationship kg_relationship_target_node_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship
    ADD CONSTRAINT kg_relationship_target_node_type_fkey FOREIGN KEY (target_node_type) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_type_extraction_staging kg_relationship_type_extraction_source_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type_extraction_staging
    ADD CONSTRAINT kg_relationship_type_extraction_source_entity_type_id_name_fkey FOREIGN KEY (source_entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_type_extraction_staging kg_relationship_type_extraction_target_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type_extraction_staging
    ADD CONSTRAINT kg_relationship_type_extraction_target_entity_type_id_name_fkey FOREIGN KEY (target_entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_type kg_relationship_type_source_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type
    ADD CONSTRAINT kg_relationship_type_source_entity_type_id_name_fkey FOREIGN KEY (source_entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: kg_relationship_type kg_relationship_type_target_entity_type_id_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kg_relationship_type
    ADD CONSTRAINT kg_relationship_type_target_entity_type_id_name_fkey FOREIGN KEY (target_entity_type_id_name) REFERENCES kg_entity_type(id_name);


--
-- Name: llm_model_flow llm_model_flow_model_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_model_flow
    ADD CONSTRAINT llm_model_flow_model_configuration_id_fkey FOREIGN KEY (model_configuration_id) REFERENCES model_configuration(id) ON DELETE CASCADE;


--
-- Name: llm_provider__persona llm_provider__persona_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__persona
    ADD CONSTRAINT llm_provider__persona_llm_provider_id_fkey FOREIGN KEY (llm_provider_id) REFERENCES llm_provider(id) ON DELETE CASCADE;


--
-- Name: llm_provider__persona llm_provider__persona_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__persona
    ADD CONSTRAINT llm_provider__persona_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: llm_provider__user_group llm_provider__user_group_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__user_group
    ADD CONSTRAINT llm_provider__user_group_llm_provider_id_fkey FOREIGN KEY (llm_provider_id) REFERENCES llm_provider(id);


--
-- Name: llm_provider__user_group llm_provider__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY llm_provider__user_group
    ADD CONSTRAINT llm_provider__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: mcp_connection_config mcp_connection_config_mcp_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_connection_config
    ADD CONSTRAINT mcp_connection_config_mcp_server_id_fkey FOREIGN KEY (mcp_server_id) REFERENCES mcp_server(id) ON DELETE CASCADE;


--
-- Name: mcp_server__user_group mcp_server__user_group_mcp_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user_group
    ADD CONSTRAINT mcp_server__user_group_mcp_server_id_fkey FOREIGN KEY (mcp_server_id) REFERENCES mcp_server(id) ON DELETE CASCADE;


--
-- Name: mcp_server__user_group mcp_server__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user_group
    ADD CONSTRAINT mcp_server__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: mcp_server__user mcp_server__user_mcp_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user
    ADD CONSTRAINT mcp_server__user_mcp_server_id_fkey FOREIGN KEY (mcp_server_id) REFERENCES mcp_server(id) ON DELETE CASCADE;


--
-- Name: mcp_server__user mcp_server__user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server__user
    ADD CONSTRAINT mcp_server__user_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: mcp_server mcp_server_admin_config_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mcp_server
    ADD CONSTRAINT mcp_server_admin_config_fk FOREIGN KEY (admin_connection_config_id) REFERENCES mcp_connection_config(id) ON DELETE SET NULL;


--
-- Name: memory memory_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY memory
    ADD CONSTRAINT memory_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: model_configuration model_configuration_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY model_configuration
    ADD CONSTRAINT model_configuration_llm_provider_id_fkey FOREIGN KEY (llm_provider_id) REFERENCES llm_provider(id) ON DELETE CASCADE;


--
-- Name: notification notification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY notification
    ADD CONSTRAINT notification_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: oauth_account oauth_account_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_account
    ADD CONSTRAINT oauth_account_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: oauth_user_token oauth_user_token_oauth_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_user_token
    ADD CONSTRAINT oauth_user_token_oauth_config_id_fkey FOREIGN KEY (oauth_config_id) REFERENCES oauth_config(id) ON DELETE CASCADE;


--
-- Name: oauth_user_token oauth_user_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY oauth_user_token
    ADD CONSTRAINT oauth_user_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: persona__document persona__document_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document
    ADD CONSTRAINT persona__document_document_id_fkey FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE;


--
-- Name: persona__document persona__document_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document
    ADD CONSTRAINT persona__document_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: persona__document_set persona__document_set_document_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document_set
    ADD CONSTRAINT persona__document_set_document_set_id_fkey FOREIGN KEY (document_set_id) REFERENCES document_set(id);


--
-- Name: persona__document_set persona__document_set_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__document_set
    ADD CONSTRAINT persona__document_set_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: persona__hierarchy_node persona__hierarchy_node_hierarchy_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__hierarchy_node
    ADD CONSTRAINT persona__hierarchy_node_hierarchy_node_id_fkey FOREIGN KEY (hierarchy_node_id) REFERENCES hierarchy_node(id) ON DELETE CASCADE;


--
-- Name: persona__hierarchy_node persona__hierarchy_node_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__hierarchy_node
    ADD CONSTRAINT persona__hierarchy_node_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: persona__persona_label persona__persona_label_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__persona_label
    ADD CONSTRAINT persona__persona_label_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: persona__persona_label persona__persona_label_persona_label_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__persona_label
    ADD CONSTRAINT persona__persona_label_persona_label_id_fkey FOREIGN KEY (persona_label_id) REFERENCES persona_label(id) ON DELETE CASCADE;


--
-- Name: persona__tool persona__tool_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__tool
    ADD CONSTRAINT persona__tool_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE CASCADE;


--
-- Name: persona__tool persona__tool_tool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__tool
    ADD CONSTRAINT persona__tool_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES tool(id) ON DELETE CASCADE;


--
-- Name: persona__user_file persona__user_file_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_file
    ADD CONSTRAINT persona__user_file_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: persona__user_file persona__user_file_user_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_file
    ADD CONSTRAINT persona__user_file_user_file_id_fkey FOREIGN KEY (user_file_id) REFERENCES user_file(id);


--
-- Name: persona persona__user_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona
    ADD CONSTRAINT persona__user_fk FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: persona__user_group persona__user_group_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_group
    ADD CONSTRAINT persona__user_group_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: persona__user_group persona__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user_group
    ADD CONSTRAINT persona__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: persona__user persona__user_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user
    ADD CONSTRAINT persona__user_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: persona__user persona__user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona__user
    ADD CONSTRAINT persona__user_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: persona persona_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY persona
    ADD CONSTRAINT persona_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES agent_workflow(id) ON DELETE SET NULL;


--
-- Name: personal_access_token personal_access_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY personal_access_token
    ADD CONSTRAINT personal_access_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: public_external_user_group public_external_user_group_cc_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public_external_user_group
    ADD CONSTRAINT public_external_user_group_cc_pair_id_fkey FOREIGN KEY (cc_pair_id) REFERENCES connector_credential_pair(id) ON DELETE CASCADE;


--
-- Name: saml saml_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY saml
    ADD CONSTRAINT saml_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: sandbox sandbox_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sandbox
    ADD CONSTRAINT sandbox_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: scim_group_mapping scim_group_mapping_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_group_mapping
    ADD CONSTRAINT scim_group_mapping_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id) ON DELETE CASCADE;


--
-- Name: scim_token scim_token_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_token
    ADD CONSTRAINT scim_token_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: scim_user_mapping scim_user_mapping_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scim_user_mapping
    ADD CONSTRAINT scim_user_mapping_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: search_query search_query_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_query
    ADD CONSTRAINT search_query_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: slack_channel_config__standard_answer_category slack_bot_config__standard_ans_standard_answer_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config__standard_answer_category
    ADD CONSTRAINT slack_bot_config__standard_ans_standard_answer_category_id_fkey FOREIGN KEY (standard_answer_category_id) REFERENCES standard_answer_category(id);


--
-- Name: slack_channel_config slack_channel_config_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config
    ADD CONSTRAINT slack_channel_config_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES persona(id);


--
-- Name: slack_channel_config slack_channel_config_slack_bot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY slack_channel_config
    ADD CONSTRAINT slack_channel_config_slack_bot_id_fkey FOREIGN KEY (slack_bot_id) REFERENCES slack_bot(id);


--
-- Name: snapshot snapshot_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY snapshot
    ADD CONSTRAINT snapshot_session_id_fkey FOREIGN KEY (session_id) REFERENCES build_session(id) ON DELETE CASCADE;


--
-- Name: standard_answer__standard_answer_category standard_answer__standard_answ_standard_answer_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer__standard_answer_category
    ADD CONSTRAINT standard_answer__standard_answ_standard_answer_category_id_fkey FOREIGN KEY (standard_answer_category_id) REFERENCES standard_answer_category(id);


--
-- Name: standard_answer__standard_answer_category standard_answer__standard_answer_catego_standard_answer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY standard_answer__standard_answer_category
    ADD CONSTRAINT standard_answer__standard_answer_catego_standard_answer_id_fkey FOREIGN KEY (standard_answer_id) REFERENCES standard_answer(id);


--
-- Name: token_rate_limit__user_group token_rate_limit__user_group_rate_limit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY token_rate_limit__user_group
    ADD CONSTRAINT token_rate_limit__user_group_rate_limit_id_fkey FOREIGN KEY (rate_limit_id) REFERENCES token_rate_limit(id);


--
-- Name: token_rate_limit__user_group token_rate_limit__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY token_rate_limit__user_group
    ADD CONSTRAINT token_rate_limit__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: tool_call__search_doc tool_call__search_doc_search_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call__search_doc
    ADD CONSTRAINT tool_call__search_doc_search_doc_id_fkey FOREIGN KEY (search_doc_id) REFERENCES search_doc(id) ON DELETE CASCADE;


--
-- Name: tool_call__search_doc tool_call__search_doc_tool_call_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool_call__search_doc
    ADD CONSTRAINT tool_call__search_doc_tool_call_id_fkey FOREIGN KEY (tool_call_id) REFERENCES tool_call(id) ON DELETE CASCADE;


--
-- Name: tool tool_mcp_server_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool
    ADD CONSTRAINT tool_mcp_server_fk FOREIGN KEY (mcp_server_id) REFERENCES mcp_server(id) ON DELETE CASCADE;


--
-- Name: tool tool_oauth_config_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool
    ADD CONSTRAINT tool_oauth_config_fk FOREIGN KEY (oauth_config_id) REFERENCES oauth_config(id) ON DELETE SET NULL;


--
-- Name: tool tool_user_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tool
    ADD CONSTRAINT tool_user_fk FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: usage_reports usage_reports_report_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY usage_reports
    ADD CONSTRAINT usage_reports_report_name_fkey FOREIGN KEY (report_name) REFERENCES file_record(file_id);


--
-- Name: usage_reports usage_reports_requestor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY usage_reports
    ADD CONSTRAINT usage_reports_requestor_user_id_fkey FOREIGN KEY (requestor_user_id) REFERENCES "user"(id);


--
-- Name: user__user_group user__user_group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user__user_group
    ADD CONSTRAINT user__user_group_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: user__user_group user__user_group_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user__user_group
    ADD CONSTRAINT user__user_group_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: user_project user_folder_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_project
    ADD CONSTRAINT user_folder_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: user_group__connector_credential_pair user_group__connector_credential_pair_cc_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group__connector_credential_pair
    ADD CONSTRAINT user_group__connector_credential_pair_cc_pair_id_fkey FOREIGN KEY (cc_pair_id) REFERENCES connector_credential_pair(id);


--
-- Name: user_group__connector_credential_pair user_group__connector_credential_pair_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_group__connector_credential_pair
    ADD CONSTRAINT user_group__connector_credential_pair_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);


--
-- Name: workflow_execution workflow_execution_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution
    ADD CONSTRAINT workflow_execution_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES chat_session(id) ON DELETE SET NULL;


--
-- Name: workflow_execution workflow_execution_paused_at_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution
    ADD CONSTRAINT workflow_execution_paused_at_step_id_fkey FOREIGN KEY (paused_at_step_id) REFERENCES agent_workflow_step(id) ON DELETE SET NULL;


--
-- Name: workflow_execution workflow_execution_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution
    ADD CONSTRAINT workflow_execution_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE SET NULL;


--
-- Name: workflow_execution workflow_execution_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY workflow_execution
    ADD CONSTRAINT workflow_execution_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES agent_workflow(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--



-- ===== SEED DATA: built-in tools + default assistant + default search settings =====

INSERT INTO persona (id, name, deleted, description, num_chunks, llm_model_version_override, user_id, llm_relevance_filter, llm_filter_extraction, recency_bias, is_visible, display_priority, starter_messages, is_public, llm_model_provider_override, uploaded_image_id, chunks_above, chunks_below, builtin_persona, is_default_persona, search_start_date, system_prompt, task_prompt, datetime_aware, replace_base_system_prompt, icon_name, default_model_configuration_id, workflow_id, max_output_tokens) VALUES (0, 'Assistant', false, 'Your AI assistant with search, web browsing, and image generation capabilities.', 25, NULL, NULL, false, true, 'AUTO', true, 0, NULL, true, NULL, NULL, 0, 0, true, true, NULL, NULL, NULL, true, false, NULL, NULL, NULL, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (5, 'OktaProfileTool', 'The Okta Profile Action allows the agent to fetch the current user''s information from Okta. This may include the user''s name, email, phone number, address, and other details such as their manager and direct reports.', 'OktaProfileTool', NULL, NULL, 'Okta Profile', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (3, 'web_search', 'The Web Search Action allows the agent to perform internet searches for up-to-date information.', 'WebSearchTool', NULL, NULL, 'Web Search', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (2, 'generate_image', 'The Image Generation Action allows the agent to use DALL-E 3 or GPT-IMAGE-1 to generate images. The action will be used when the user asks the agent to generate an image.', 'ImageGenerationTool', NULL, NULL, 'Image Generation', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (6, 'python', 'The Code Interpreter Action allows the assistant to execute Python code in a secure, isolated environment for data analysis, computation, visualization, and file processing.', 'PythonTool', NULL, NULL, 'Code Interpreter', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (7, 'open_url', 'The Open URL Action allows the agent to fetch and read contents of web pages.', 'OpenURLTool', NULL, NULL, 'Open URL', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (4, 'run_kg_search', 'The Knowledge Graph Search Action allows the agent to search the Knowledge Graph for information. This tool can (for now) only be active in the KG Beta Agent, and it requires the Knowledge Graph to be enabled.', 'KnowledgeGraphTool', NULL, NULL, 'Knowledge Graph Search', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (8, 'research_agent', 'The Research Agent is a sub-agent that conducts research on a specific topic.', 'ResearchAgent', NULL, NULL, 'Research Agent', NULL, false, NULL, NULL, false, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (9, 'read_file', 'Read sections of user-uploaded files by character offset. Useful for inspecting large files that cannot fit entirely in context.', 'FileReaderTool', NULL, NULL, 'File Reader', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (10, 'MemoryTool', 'Save memories about the user for future conversations.', 'MemoryTool', NULL, NULL, 'Add Memory', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (1, 'internal_search', 'The Search Action allows the agent to search through connected knowledge to help build an answer.', 'SearchTool', NULL, NULL, 'Knowledge Search', NULL, false, NULL, NULL, true, NULL);
INSERT INTO tool (id, name, description, in_code_tool_id, openapi_schema, user_id, display_name, custom_headers, passthrough_auth, mcp_server_id, mcp_input_schema, enabled, oauth_config_id) VALUES (139, 'HttpRequestTool', 'Make HTTP requests to any URL. Supports GET, POST, PUT, DELETE, PATCH methods with custom headers and request body.', 'HttpRequestTool', NULL, NULL, 'HTTP Request', NULL, false, NULL, NULL, true, NULL);
INSERT INTO persona__tool (persona_id, tool_id) VALUES (0, 1);
INSERT INTO persona__tool (persona_id, tool_id) VALUES (0, 2);
INSERT INTO persona__tool (persona_id, tool_id) VALUES (0, 6);
INSERT INTO persona__tool (persona_id, tool_id) VALUES (0, 7);
INSERT INTO search_settings (id, model_name, model_dim, "normalize", query_prefix, passage_prefix, index_name, status, provider_type, multipass_indexing, multilingual_expansion, embedding_precision, reduced_dimension, enable_contextual_rag, contextual_rag_llm_name, contextual_rag_llm_provider, switchover_type) VALUES (2, 'nomic-ai/nomic-embed-text-v1', 768, true, 'search_query: ', 'search_document: ', 'danswer_chunk_nomic_ai_nomic_embed_text_v1', 'PRESENT', NULL, false, '{}', 'FLOAT', NULL, false, NULL, NULL, 'REINDEX');

SELECT setval(pg_get_serial_sequence('tool','id'), (SELECT max(id) FROM tool), true);
SELECT setval(pg_get_serial_sequence('search_settings','id'), (SELECT max(id) FROM search_settings), true);
SELECT setval(pg_get_serial_sequence('persona','id'), 1, false);
