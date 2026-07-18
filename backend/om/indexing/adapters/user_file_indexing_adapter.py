import contextlib
import datetime
import time
from collections.abc import Generator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import TransactionalContext

from om.access.access import get_access_for_knowledge_files
from om.access.models import DocumentAccess
from om.configs.constants import DEFAULT_BOOST
from om.configs.constants import NotificationType
from om.connectors.models import Document
from om.db.enums import KnowledgeFileStatus
from om.db.models import Persona
from om.db.models import KnowledgeFile
from om.db.notification import create_notification
from om.db.knowledge_file import fetch_chunk_counts_for_knowledge_files
from om.db.knowledge_file import fetch_user_workspace_ids_for_knowledge_files
from om.file_store.utils import store_user_file_plaintext
from om.indexing.indexing_pipeline import DocumentBatchPrepareContext
from om.indexing.models import BuildMetadataAwareChunksResult
from om.indexing.models import DocMetadataAwareIndexChunk
from om.indexing.models import IndexChunk
from om.indexing.models import UpdatableChunkData
from om.llm.factory import get_default_llm
from om.natural_language_processing.utils import get_tokenizer
from om.utils.logger import setup_logger

logger = setup_logger()

_NUM_LOCK_ATTEMPTS = 3
retry_delay = 0.5


def _acquire_user_file_locks(db_session: Session, knowledge_file_ids: list[str]) -> bool:
    """Acquire locks for the specified user files."""
    # Convert to UUIDs for the DB comparison
    user_file_uuid_list = [UUID(knowledge_file_id) for knowledge_file_id in knowledge_file_ids]
    stmt = (
        select(KnowledgeFile.id)
        .where(KnowledgeFile.id.in_(user_file_uuid_list))
        .with_for_update(nowait=True)
    )
    # will raise exception if any of the documents are already locked
    documents = db_session.scalars(stmt).all()

    # make sure we found every document
    if len(documents) != len(set(knowledge_file_ids)):
        logger.warning("Didn't find row for all specified user file IDs. Aborting.")
        return False

    return True


class KnowledgeFileIndexingAdapter:
    def __init__(self, tenant_id: str, db_session: Session):
        self.tenant_id = tenant_id
        self.db_session = db_session

    def prepare(
        self, documents: list[Document], ignore_time_skip: bool  # noqa: ARG002
    ) -> DocumentBatchPrepareContext:
        return DocumentBatchPrepareContext(
            updatable_docs=documents, id_to_boost_map={}  # TODO(subash): add boost map
        )

    @contextlib.contextmanager
    def lock_context(
        self, documents: list[Document]
    ) -> Generator[TransactionalContext, None, None]:
        self.db_session.commit()  # ensure that we're not in a transaction
        lock_acquired = False
        for i in range(_NUM_LOCK_ATTEMPTS):
            try:
                with self.db_session.begin() as transaction:
                    lock_acquired = _acquire_user_file_locks(
                        db_session=self.db_session,
                        knowledge_file_ids=[doc.id for doc in documents],
                    )
                    if lock_acquired:
                        yield transaction
                        break
            except OperationalError as e:
                logger.warning(
                    f"Failed to acquire locks for user files on attempt {i}, retrying. Error: {e}"
                )

            time.sleep(retry_delay)

        if not lock_acquired:
            raise RuntimeError(
                f"Failed to acquire locks after {_NUM_LOCK_ATTEMPTS} attempts "
                f"for user files: {[doc.id for doc in documents]}"
            )

    def build_metadata_aware_chunks(
        self,
        chunks_with_embeddings: list[IndexChunk],
        chunk_content_scores: list[float],
        tenant_id: str,
        context: DocumentBatchPrepareContext,
    ) -> BuildMetadataAwareChunksResult:

        no_access = DocumentAccess.build(
            user_emails=[],
            user_groups=[],
            external_user_emails=[],
            external_user_group_ids=[],
            is_public=False,
        )

        updatable_ids = [doc.id for doc in context.updatable_docs]
        knowledge_file_id_to_workspace_ids = fetch_user_workspace_ids_for_knowledge_files(
            knowledge_file_ids=updatable_ids,
            db_session=self.db_session,
        )
        knowledge_file_id_to_access: dict[str, DocumentAccess] = get_access_for_knowledge_files(
            knowledge_file_ids=updatable_ids,
            db_session=self.db_session,
        )
        knowledge_file_id_to_previous_chunk_cnt: dict[str, int] = {
            knowledge_file_id: chunk_count
            for knowledge_file_id, chunk_count in fetch_chunk_counts_for_knowledge_files(
                knowledge_file_ids=updatable_ids,
                db_session=self.db_session,
            )
        }

        knowledge_file_id_to_new_chunk_cnt: dict[str, int] = {
            knowledge_file_id: len(
                [
                    chunk
                    for chunk in chunks_with_embeddings
                    if chunk.source_document.id == knowledge_file_id
                ]
            )
            for knowledge_file_id in updatable_ids
        }

        # Initialize tokenizer used for token count calculation
        try:
            llm = get_default_llm()
            llm_tokenizer = get_tokenizer(
                model_name=llm.config.model_name,
                provider_type=llm.config.model_provider,
            )
        except Exception as e:
            logger.error(f"Error getting tokenizer: {e}")
            llm_tokenizer = None

        knowledge_file_id_to_raw_text: dict[str, str] = {}
        knowledge_file_id_to_token_count: dict[str, int | None] = {}
        for knowledge_file_id in updatable_ids:
            user_file_chunks = [
                chunk
                for chunk in chunks_with_embeddings
                if chunk.source_document.id == knowledge_file_id
            ]
            if user_file_chunks:
                combined_content = " ".join(
                    [chunk.content for chunk in user_file_chunks]
                )
                knowledge_file_id_to_raw_text[str(knowledge_file_id)] = combined_content
                token_count = (
                    len(llm_tokenizer.encode(combined_content)) if llm_tokenizer else 0
                )
                knowledge_file_id_to_token_count[str(knowledge_file_id)] = token_count
            else:
                knowledge_file_id_to_raw_text[str(knowledge_file_id)] = ""
                knowledge_file_id_to_token_count[str(knowledge_file_id)] = None

        access_aware_chunks = [
            DocMetadataAwareIndexChunk.from_index_chunk(
                index_chunk=chunk,
                access=knowledge_file_id_to_access.get(chunk.source_document.id, no_access),
                document_sets=set(),
                user_workspace=knowledge_file_id_to_workspace_ids.get(
                    chunk.source_document.id, []
                ),
                # we are going to index userfiles only once, so we just set the boost to the default
                boost=DEFAULT_BOOST,
                tenant_id=tenant_id,
                aggregated_chunk_boost_factor=chunk_content_scores[chunk_num],
            )
            for chunk_num, chunk in enumerate(chunks_with_embeddings)
        ]

        return BuildMetadataAwareChunksResult(
            chunks=access_aware_chunks,
            doc_id_to_previous_chunk_cnt=knowledge_file_id_to_previous_chunk_cnt,
            doc_id_to_new_chunk_cnt=knowledge_file_id_to_new_chunk_cnt,
            knowledge_file_id_to_raw_text=knowledge_file_id_to_raw_text,
            knowledge_file_id_to_token_count=knowledge_file_id_to_token_count,
        )

    def _notify_assistant_owners_if_files_ready(
        self, knowledge_files: list[KnowledgeFile]
    ) -> None:
        """
        Check if all files for associated assistants are processed and notify owners.
        Only sends notification when all files for an assistant are COMPLETED.
        """
        for knowledge_file in knowledge_files:
            if knowledge_file.status == KnowledgeFileStatus.COMPLETED:
                for assistant in knowledge_file.assistants:
                    # Skip assistants without owners
                    if assistant.user_id is None:
                        continue

                    # Check if all OTHER files for this assistant are completed
                    # (we already know current file is completed from the outer check)
                    all_files_completed = all(
                        f.status == KnowledgeFileStatus.COMPLETED
                        for f in assistant.knowledge_files
                        if f.id != knowledge_file.id
                    )

                    if all_files_completed:
                        create_notification(
                            user_id=assistant.user_id,
                            notif_type=NotificationType.ASSISTANT_FILES_READY,
                            db_session=self.db_session,
                            title="Your files are ready!",
                            description=f"All files for agent {assistant.name} have been processed and are now available.",
                            additional_data={
                                "persona_id": assistant.id,
                                "link": f"/assistants/{assistant.id}",
                            },
                            autocommit=False,
                        )

    def post_index(
        self,
        context: DocumentBatchPrepareContext,
        updatable_chunk_data: list[UpdatableChunkData],  # noqa: ARG002
        filtered_documents: list[Document],  # noqa: ARG002
        result: BuildMetadataAwareChunksResult,
    ) -> None:
        knowledge_file_ids = [doc.id for doc in context.updatable_docs]

        knowledge_files = (
            self.db_session.query(KnowledgeFile)
            .options(selectinload(KnowledgeFile.assistants).selectinload(Persona.knowledge_files))
            .filter(KnowledgeFile.id.in_(knowledge_file_ids))
            .all()
        )
        for knowledge_file in knowledge_files:
            # don't update the status if the user file is being deleted
            if knowledge_file.status != KnowledgeFileStatus.DELETING:
                knowledge_file.status = KnowledgeFileStatus.COMPLETED
            knowledge_file.last_workspace_sync_at = datetime.datetime.now(
                datetime.timezone.utc
            )
            knowledge_file.chunk_count = result.doc_id_to_new_chunk_cnt[str(knowledge_file.id)]
            knowledge_file.token_count = result.knowledge_file_id_to_token_count[
                str(knowledge_file.id)
            ]

        # Notify assistant owners if all their files are now processed
        self._notify_assistant_owners_if_files_ready(knowledge_files)

        self.db_session.commit()

        # Store the plaintext in the file store for faster retrieval
        # NOTE: this creates its own session to avoid committing the overall
        # transaction.
        for knowledge_file_id, raw_text in result.knowledge_file_id_to_raw_text.items():
            store_user_file_plaintext(
                knowledge_file_id=UUID(knowledge_file_id),
                plaintext_content=raw_text,
            )
