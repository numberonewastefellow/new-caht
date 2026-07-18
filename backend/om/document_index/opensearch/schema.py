import hashlib
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Self

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator
from pydantic import SerializerFunctionWrapHandler

from om.configs.app_configs import OPENSEARCH_INDEX_NUM_REPLICAS
from om.configs.app_configs import OPENSEARCH_INDEX_NUM_SHARDS
from om.configs.app_configs import OPENSEARCH_TEXT_ANALYZER
from om.configs.app_configs import USING_AWS_MANAGED_OPENSEARCH
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.constants import DEFAULT_MAX_CHUNK_SIZE
from om.document_index.opensearch.constants import EF_CONSTRUCTION
from om.document_index.opensearch.constants import EF_SEARCH
from om.document_index.opensearch.constants import M
from om.document_index.opensearch.string_filtering import DocumentIDTooLongError
from om.document_index.opensearch.string_filtering import (
    filter_and_validate_document_id,
)
from om.document_index.opensearch.string_filtering import (
    MAX_DOCUMENT_ID_ENCODED_LENGTH,
)
from om.utils.tenant import get_tenant_id_short_string
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id

TITLE_FIELD_NAME = "title"
TITLE_EMBEDDING_FIELD_NAME = "title_embedding"
CHUNK_TEXT_FIELD_NAME = "chunk_text"
CONTENT_EMBEDDING_FIELD_NAME = "content_embedding"
SOURCE_TYPE_FIELD_NAME = "source_type"
METADATA_TAGS_FIELD_NAME = "metadata_tags"
UPDATED_AT_FIELD_NAME = "updated_at"
IS_PUBLIC_FIELD_NAME = "is_public"
ACCESS_CONTROL_LIST_FIELD_NAME = "access_control_list"
IS_HIDDEN_FIELD_NAME = "is_hidden"
BOOST_FIELD_NAME = "boost"
DISPLAY_NAME_FIELD_NAME = "display_name"
IMAGE_ID_FIELD_NAME = "image_id"
SOURCE_LINKS_FIELD_NAME = "source_links"
DOCUMENT_SETS_FIELD_NAME = "document_sets"
USER_WORKSPACES_FIELD_NAME = "user_workspaces"
AGENTS_FIELD_NAME = "agents"
DOCUMENT_ID_FIELD_NAME = "document_id"
CHUNK_INDEX_FIELD_NAME = "chunk_index"
MAX_CHUNK_SIZE_FIELD_NAME = "max_chunk_size"
TENANT_ID_FIELD_NAME = "tenant_id"
SNIPPET_FIELD_NAME = "snippet"
DOCUMENT_SUMMARY_FIELD_NAME = "document_summary"
CONTEXTUAL_SUMMARY_FIELD_NAME = "contextual_summary"
METADATA_TEXT_FIELD_NAME = "metadata_text"
PRIMARY_OWNERS_FIELD_NAME = "primary_owners"
SECONDARY_OWNERS_FIELD_NAME = "secondary_owners"
# Hierarchy filtering - list of ancestor hierarchy node IDs
ANCESTOR_HIERARCHY_NODE_IDS_FIELD_NAME = "ancestor_hierarchy_node_ids"
# Knowledge graph chunk fields.
# - kg_entities / kg_terms are flat lists of id strings -> `keyword` arrays
#   (keyword accepts arrays natively; the right type for "chunks containing
#   entity X" term matching).
# - kg_relationships is an array of {source, rel_type, target} triples -> a
#   `nested` field so the three endpoints/type can be queried together (e.g.
#   source=X AND rel_type=Y), mirroring the Vespa `kg_relationship` struct.
#   A flat keyword array would lose this (OpenSearch cannot reliably match
#   multiple values within the same object of a flattened array).
# All are additive to the mapping so adding them requires no reindex; note that
# changing kg_relationships' type LATER would require a reindex, which is why it
# is modeled structurally up front.
KG_ENTITIES_FIELD_NAME = "kg_entities"
KG_RELATIONSHIPS_FIELD_NAME = "kg_relationships"
KG_TERMS_FIELD_NAME = "kg_terms"
# Subfields of the kg_relationships nested objects.
KG_RELATIONSHIP_SOURCE_FIELD_NAME = "source"
KG_RELATIONSHIP_TYPE_FIELD_NAME = "rel_type"
KG_RELATIONSHIP_TARGET_FIELD_NAME = "target"


# Faiss was also tried but it didn't have any benefits
# NMSLIB is deprecated, not recommended
OPENSEARCH_KNN_ENGINE = "lucene"


def get_opensearch_doc_chunk_id(
    tenant_state: TenantState,
    document_id: str,
    chunk_index: int,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
) -> str:
    """
    Returns a unique identifier for the chunk.

    This will be the string used to identify the chunk in OpenSearch. Any direct
    chunk queries should use this function.

    If the document ID is too long, a hash of the ID is used instead.
    """
    opensearch_doc_chunk_id_suffix: str = f"__{max_chunk_size}__{chunk_index}"
    encoded_suffix_length: int = len(opensearch_doc_chunk_id_suffix.encode("utf-8"))
    max_encoded_permissible_doc_id_length: int = (
        MAX_DOCUMENT_ID_ENCODED_LENGTH - encoded_suffix_length
    )
    opensearch_doc_chunk_id_tenant_prefix: str = ""
    if tenant_state.multitenant:
        short_tenant_id: str = get_tenant_id_short_string(tenant_state.tenant_id)
        # Use tenant ID because in multitenant mode each tenant has its own
        # Documents table, so there is a very small chance that doc IDs are not
        # actually unique across all tenants.
        opensearch_doc_chunk_id_tenant_prefix = f"{short_tenant_id}__"
        encoded_prefix_length: int = len(
            opensearch_doc_chunk_id_tenant_prefix.encode("utf-8")
        )
        max_encoded_permissible_doc_id_length -= encoded_prefix_length

    try:
        sanitized_document_id: str = filter_and_validate_document_id(
            document_id, max_encoded_length=max_encoded_permissible_doc_id_length
        )
    except DocumentIDTooLongError:
        # If the document ID is too long, use a hash instead.
        # We use blake2b because it is faster and equally secure as SHA-256, and
        # accepts digest_size which controls the number of bytes returned in the
        # hash. Edit: Actually modern CPUs have good hardware acceleration
        # specifically for SHA-256 so really blake2b is not expected to be
        # faster in some production settings.
        # digest_size is the size of the returned hash in bytes. Since we're
        # decoding the hash bytes as a hex string, the digest_size should be
        # half the max target size of the hash string.
        # Subtract 1 because filter_and_validate_document_id compares on >= on
        # max_encoded_length.
        # 64 is the max digest_size blake2b returns.
        digest_size: int = min((max_encoded_permissible_doc_id_length - 1) // 2, 64)
        sanitized_document_id = hashlib.blake2b(
            document_id.encode("utf-8"), digest_size=digest_size
        ).hexdigest()

    opensearch_doc_chunk_id: str = f"{opensearch_doc_chunk_id_tenant_prefix}{sanitized_document_id}{opensearch_doc_chunk_id_suffix}"

    # Do one more validation to ensure we haven't exceeded the max length.
    opensearch_doc_chunk_id = filter_and_validate_document_id(opensearch_doc_chunk_id)
    return opensearch_doc_chunk_id


def set_or_convert_timezone_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        # astimezone will raise if value does not have a timezone set.
        value = value.replace(tzinfo=timezone.utc)
    else:
        # Does appropriate time conversion if value was set in a different
        # timezone.
        value = value.astimezone(timezone.utc)
    return value


class KGRelationship(BaseModel):
    """A single knowledge-graph relationship stored on a chunk.

    Modeled as an OpenSearch ``nested`` object (see get_document_schema) so the
    endpoints and type can be queried together (e.g. source=X AND rel_type=Y).
    Mirrors the Vespa ``kg_relationship`` struct. The three fields correspond to
    the parts of a relationship id_name split on ``__``.
    """

    model_config = {"frozen": True}

    source: str
    rel_type: str
    target: str


class DocumentChunkWithoutVectors(BaseModel):
    """
    Represents a chunk of a document in the OpenSearch index without vectors.

    The names of these fields are based on the OpenSearch schema. Changes to the
    schema require changes here. See get_document_schema.

    WARNING: Relies on MULTI_TENANT which is global state. Also uses
    get_current_tenant_id. Generally relying on global state is bad, in this
    case we accept it because of the importance of validating tenant logic.
    """

    model_config = {"frozen": True}

    document_id: str
    chunk_index: int
    # The maximum number of tokens this chunk's content can hold. Previously
    # there was a concept of large chunks, this is a generic concept of that. We
    # can choose to have any size of chunks in the index and they should be
    # distinct from one another.
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE

    # Either both should be None or both should be non-None.
    title: str | None = None
    chunk_text: str

    source_type: str
    # A list of key-value pairs separated by INDEX_SEPARATOR. See
    # convert_metadata_dict_to_list_of_strings.
    metadata_tags: list[str] | None = None
    # If it exists, time zone should always be UTC.
    updated_at: datetime | None = None

    is_public: bool
    access_control_list: list[str]
    # Defaults to False, currently gets written during update not index.
    is_hidden: bool = False

    boost: int

    display_name: str
    image_id: str | None = None
    # Contains a string representation of a dict which maps offset into the raw
    # chunk text to the link corresponding to that point.
    source_links: str | None = None
    snippet: str
    # doc_summary, chunk_context, and metadata_suffix are all stored simply to
    # reverse the augmentations to content. Ideally these would just be start
    # and stop indices into the content string. For legacy reasons they are not
    # right now.
    document_summary: str
    contextual_summary: str
    metadata_text: str | None = None

    document_sets: list[str] | None = None
    user_workspaces: list[int] | None = None
    agents: list[int] | None = None
    primary_owners: list[str] | None = None
    secondary_owners: list[str] | None = None

    # List of ancestor hierarchy node IDs for hierarchy-based filtering.
    # None means no hierarchy info (document will be excluded from
    # hierarchy-filtered searches).
    ancestor_hierarchy_node_ids: list[int] | None = None

    # Knowledge graph fields. kg_entities/kg_terms are keyword-string lists;
    # kg_relationships is a list of nested {source, rel_type, target} objects.
    # None means the field was never populated for this chunk (excluded from the
    # serialized doc, like the other optional list fields above).
    kg_entities: list[str] | None = None
    kg_relationships: list[KGRelationship] | None = None
    kg_terms: list[str] | None = None

    tenant_id: TenantState = Field(
        default_factory=lambda: TenantState(
            tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT
        )
    )

    def __str__(self) -> str:
        return (
            f"DocumentChunk(document_id={self.document_id}, chunk_index={self.chunk_index}, "
            f"content length={len(self.chunk_text)}, tenant_id={self.tenant_id.tenant_id})."
        )

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        """Invokes pydantic's serialization logic, then excludes Nones.

        We do this because .model_dump(exclude_none=True) does not work after
        @field_serializer logic, so for some field serializers which return None
        and which we would like to exclude from the final dump, they would be
        included without this.

        Args:
            handler: Callable from pydantic which takes the instance of the
                model as an argument and performs standard serialization.

        Returns:
            The return of handler but with None items excluded.
        """
        serialized: dict[str, object] = handler(self)
        serialized_exclude_none = {k: v for k, v in serialized.items() if v is not None}
        return serialized_exclude_none

    @field_serializer("updated_at", mode="wrap")
    def serialize_datetime_fields_to_epoch_seconds(
        self,
        value: datetime | None,
        handler: SerializerFunctionWrapHandler,  # noqa: ARG002
    ) -> int | None:
        """
        Serializes datetime fields to seconds since the Unix epoch.

        If there is no datetime, returns None.
        """
        if value is None:
            return None
        value = set_or_convert_timezone_to_utc(value)
        return int(value.timestamp())

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_epoch_seconds_to_datetime(cls, value: Any) -> datetime | None:
        """Parses seconds since the Unix epoch to a datetime object.

        If the input is None, returns None.

        The datetime returned will be in UTC.
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            value = set_or_convert_timezone_to_utc(value)
            return value
        if not isinstance(value, int):
            raise ValueError(
                f"Bug: Expected an int for the last_updated property from OpenSearch, got {type(value)} instead."
            )
        return datetime.fromtimestamp(value, tz=timezone.utc)

    @field_serializer("tenant_id", mode="wrap")
    def serialize_tenant_state(
        self,
        value: TenantState,
        handler: SerializerFunctionWrapHandler,  # noqa: ARG002
    ) -> str | None:
        """
        Serializes tenant_state to the tenant str if multitenant, or None if
        not.

        The idea is that in single tenant mode, the schema does not have a
        tenant_id field, so we don't want to supply it in our serialized
        DocumentChunk. This assumes the final serialized model excludes None
        fields, which serialize_model should enforce.
        """
        if not value.multitenant:
            return None
        else:
            return value.tenant_id

    @field_validator("tenant_id", mode="before")
    @classmethod
    def parse_tenant_id(cls, value: Any) -> TenantState:
        """
        Generates a TenantState from OpenSearch's tenant_id if it exists, or
        generates a default state if it does not (implies we are in single
        tenant mode).
        """
        if value is None:
            if MULTI_TENANT:
                raise ValueError(
                    "Bug: No tenant_id was supplied but multi-tenant mode is enabled."
                )
            return TenantState(
                tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT
            )
        elif isinstance(value, TenantState):
            if MULTI_TENANT != value.multitenant:
                raise ValueError(
                    f"Bug: An existing TenantState object was supplied to the DocumentChunk model "
                    f"but its multi-tenant mode ({value.multitenant}) does not match the program's "
                    "current global tenancy state."
                )
            return value
        elif not isinstance(value, str):
            raise ValueError(
                f"Bug: Expected a str for the tenant_id property from OpenSearch, got {type(value)} instead."
            )
        else:
            if not MULTI_TENANT:
                raise ValueError(
                    "Bug: Got a non-null str for the tenant_id property from OpenSearch but "
                    "multi-tenant mode is not enabled. This is unexpected because in single-tenant "
                    "mode we don't expect to see a tenant_id."
                )
            return TenantState(tenant_id=value, multitenant=MULTI_TENANT)


class DocumentChunk(DocumentChunkWithoutVectors):
    """Represents a chunk of a document in the OpenSearch index.

    The names of these fields are based on the OpenSearch schema. Changes to the
    schema require changes here. See get_document_schema.
    """

    model_config = {"frozen": True}

    title_embedding: list[float] | None = None
    content_embedding: list[float]

    def __str__(self) -> str:
        return (
            f"DocumentChunk(document_id={self.document_id}, chunk_index={self.chunk_index}, "
            f"content length={len(self.chunk_text)}, content vector length={len(self.content_embedding)}, "
            f"tenant_id={self.tenant_id.tenant_id})"
        )

    @model_validator(mode="after")
    def check_title_and_title_vector_are_consistent(self) -> Self:
        # title and title_vector should both either be None or not.
        if self.title is not None and self.title_embedding is None:
            raise ValueError("Bug: Title vector must not be None if title is not None.")
        if self.title_embedding is not None and self.title is None:
            raise ValueError("Bug: Title must not be None if title vector is not None.")
        return self


class DocumentSchema:
    """
    Represents the schema and indexing strategies of the OpenSearch index.

    TODO(andrei): Implement multi-phase indexing strategies.
    """

    @staticmethod
    def get_document_schema(vector_dimension: int, multitenant: bool) -> dict[str, Any]:
        """Returns the document schema for the OpenSearch index.

        WARNING: Changes / additions to field names here require changes to the
        DocumentChunk class above.

        Notes:
          - By default all fields have indexing enabled.
          - By default almost all fields except text fields have doc_values
            enabled, enabling operations like sorting and aggregations.
          - By default all fields are nullable.
          - "type": "keyword" fields are stored as-is, used for exact matches,
            filtering, etc.
          - "type": "text" fields are OpenSearch-processed strings, used for
            full-text searches.
          - "store": True fields are stored and can be returned on their own,
            independent of the parent document.
          - "index": True fields can be queried on.
          - "doc_values": True fields can be sorted and aggregated efficiently.
            Not supported for "text" type fields.
          - "store": True fields are stored separately from the source document
            and can thus be returned from a query separately from _source.
            Generally this is not necessary.

        Args:
            vector_dimension: The dimension of vector embeddings. Must be a
                positive integer.
            multitenant: Whether the index is multitenant.

        Returns:
            A dictionary representing the document schema, to be supplied to the
                OpenSearch client. The structure of this dictionary is
                determined by OpenSearch documentation.
        """
        schema: dict[str, Any] = {
            # By default OpenSearch allows dynamically adding new properties
            # based on indexed documents. This is awful and we disable it here.
            # An exception will be raised if you try to index a new doc which
            # contains unexpected fields.
            "dynamic": "strict",
            "properties": {
                TITLE_FIELD_NAME: {
                    "type": "text",
                    # Language analyzer (e.g. english) stems at index and search
                    # time for variant matching. Configure via
                    # OPENSEARCH_TEXT_ANALYZER. Existing indices need reindexing
                    # after a change.
                    "analyzer": OPENSEARCH_TEXT_ANALYZER,
                    "fields": {
                        # Subfield accessed as title.keyword. Not indexed for
                        # values longer than 256 chars.
                        # TODO(andrei): Ask Yuhong do we want this?
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    },
                    # This makes highlighting text during queries more efficient
                    # at the cost of disk space. See
                    # https://docs.opensearch.org/latest/search-plugins/searching-data/highlight/#methods-of-obtaining-offsets
                    "index_options": "offsets",
                },
                CHUNK_TEXT_FIELD_NAME: {
                    "type": "text",
                    "store": True,
                    "analyzer": OPENSEARCH_TEXT_ANALYZER,
                    "index_options": "offsets",
                },
                TITLE_EMBEDDING_FIELD_NAME: {
                    "type": "knn_vector",
                    "dimension": vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": OPENSEARCH_KNN_ENGINE,
                        "parameters": {"ef_construction": EF_CONSTRUCTION, "m": M},
                    },
                },
                # TODO(andrei): This is a tensor in Vespa. Also look at feature
                # parity for these other method fields.
                CONTENT_EMBEDDING_FIELD_NAME: {
                    "type": "knn_vector",
                    "dimension": vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": OPENSEARCH_KNN_ENGINE,
                        "parameters": {"ef_construction": EF_CONSTRUCTION, "m": M},
                    },
                },
                SOURCE_TYPE_FIELD_NAME: {"type": "keyword"},
                METADATA_TAGS_FIELD_NAME: {"type": "keyword"},
                UPDATED_AT_FIELD_NAME: {
                    "type": "date",
                    "format": "epoch_second",
                    # For some reason date defaults to False, even though it
                    # would make sense to sort by date.
                    "doc_values": True,
                },
                # Access control fields.
                # Whether the doc is public. Could have fallen under access
                # control list but is such a broad and critical filter that it
                # is its own field. If true, ACCESS_CONTROL_LIST_FIELD_NAME
                # should have no effect on queries.
                IS_PUBLIC_FIELD_NAME: {"type": "boolean"},
                # Access control list for the doc, excluding public access,
                # which is covered above.
                # If a user's access set contains at least one entry from this
                # set, the user should be able to retrieve this document. This
                # only applies if public is set to false; public non-hidden
                # documents are always visible to anyone in a given tenancy
                # regardless of this field.
                ACCESS_CONTROL_LIST_FIELD_NAME: {"type": "keyword"},
                # Whether the doc is hidden from search results.
                # Should clobber all other access search filters, namely
                # IS_PUBLIC_FIELD_NAME and ACCESS_CONTROL_LIST_FIELD_NAME; up to
                # search implementations to guarantee this.
                IS_HIDDEN_FIELD_NAME: {"type": "boolean"},
                BOOST_FIELD_NAME: {"type": "integer"},
                # This field is only used for displaying a useful name for the
                # doc in the UI and is not used for searching. Disabling these
                # features to increase perf. This field is therefore essentially
                # just metadata.
                DISPLAY_NAME_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above; used to display an image along with the doc.
                IMAGE_ID_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above; used to link to the source doc.
                SOURCE_LINKS_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above; used to quickly summarize the doc in the UI.
                SNIPPET_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above.
                # TODO(andrei): If we want to search on this this needs to be
                # changed.
                DOCUMENT_SUMMARY_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above.
                # TODO(andrei): If we want to search on this this needs to be
                # changed.
                CONTEXTUAL_SUMMARY_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    # Generally False by default; just making sure.
                    "store": False,
                },
                # Same as above.
                METADATA_TEXT_FIELD_NAME: {
                    "type": "keyword",
                    "index": False,
                    "doc_values": False,
                    "store": False,
                },
                # Product-specific fields.
                DOCUMENT_SETS_FIELD_NAME: {"type": "keyword"},
                USER_WORKSPACES_FIELD_NAME: {"type": "integer"},
                AGENTS_FIELD_NAME: {"type": "integer"},
                PRIMARY_OWNERS_FIELD_NAME: {"type": "keyword"},
                SECONDARY_OWNERS_FIELD_NAME: {"type": "keyword"},
                # OpenSearch metadata fields.
                DOCUMENT_ID_FIELD_NAME: {"type": "keyword"},
                CHUNK_INDEX_FIELD_NAME: {"type": "integer"},
                # The maximum number of tokens this chunk's content can hold.
                MAX_CHUNK_SIZE_FIELD_NAME: {"type": "integer"},
                # Hierarchy filtering - list of ancestor hierarchy node IDs.
                # Used for scoped search within folder/space hierarchies.
                # OpenSearch's terms query with value_type: "bitmap" can
                # efficiently check if any value in this array matches a
                # query bitmap.
                ANCESTOR_HIERARCHY_NODE_IDS_FIELD_NAME: {"type": "integer"},
                # Knowledge graph fields. kg_entities/kg_terms are keyword
                # arrays (keyword accepts arrays natively). kg_relationships is a
                # nested field of {source, rel_type, target} objects so the
                # endpoints/type can be queried together (mirrors the Vespa
                # struct); a flat keyword array would lose per-object matching.
                # Additive to the mapping, so no reindex is required now.
                KG_ENTITIES_FIELD_NAME: {"type": "keyword"},
                KG_RELATIONSHIPS_FIELD_NAME: {
                    "type": "nested",
                    "properties": {
                        KG_RELATIONSHIP_SOURCE_FIELD_NAME: {"type": "keyword"},
                        KG_RELATIONSHIP_TYPE_FIELD_NAME: {"type": "keyword"},
                        KG_RELATIONSHIP_TARGET_FIELD_NAME: {"type": "keyword"},
                    },
                },
                KG_TERMS_FIELD_NAME: {"type": "keyword"},
            },
        }

        if multitenant:
            schema["properties"][TENANT_ID_FIELD_NAME] = {"type": "keyword"}

        return schema

    @staticmethod
    def get_index_settings_based_on_environment() -> dict[str, Any]:
        """
        Returns the index settings based on the environment.
        """
        if USING_AWS_MANAGED_OPENSEARCH:
            # NOTE: The number of data copies, including the primary (not a
            # replica) copy, must be divisible by the number of AZs.
            if MULTI_TENANT:
                number_of_shards = 324
                number_of_replicas = 2
            else:
                number_of_shards = 3
                number_of_replicas = 2
        else:
            number_of_shards = 1
            number_of_replicas = 1

        if OPENSEARCH_INDEX_NUM_SHARDS is not None:
            number_of_shards = OPENSEARCH_INDEX_NUM_SHARDS
        if OPENSEARCH_INDEX_NUM_REPLICAS is not None:
            number_of_replicas = OPENSEARCH_INDEX_NUM_REPLICAS

        return {
            "index": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
                # Required for vector search.
                "knn": True,
                "knn.algo_param.ef_search": EF_SEARCH,
            }
        }
