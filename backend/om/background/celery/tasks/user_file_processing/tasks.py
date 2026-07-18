import datetime
import time
from uuid import UUID

import sqlalchemy as sa
from celery import shared_task
from celery import Task
from redis.lock import Lock as RedisLock
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.background.celery.apps.app_base import task_logger
from om.background.celery.tasks.shared.RetryDocumentIndex import RetryDocumentIndex
from om.configs.app_configs import DISABLE_VECTOR_DB
from om.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from om.configs.constants import CELERY_USER_FILE_PROCESSING_LOCK_TIMEOUT
from om.configs.constants import CELERY_USER_FILE_PROJECT_SYNC_LOCK_TIMEOUT
from om.configs.constants import DocumentSource
from om.configs.constants import OmCeleryPriority
from om.configs.constants import OmCeleryQueues
from om.configs.constants import OmCeleryTask
from om.configs.constants import OmRedisLocks
from om.connectors.file.connector import LocalFileConnector
from om.connectors.models import Document
from om.connectors.models import HierarchyNode
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.enums import UserFileStatus
from om.db.models import UserFile
from om.db.search_settings import get_active_search_settings
from om.db.search_settings import get_active_search_settings_list
from om.document_index.factory import get_all_document_indices
from om.document_index.interfaces_new import MetadataUpdateRequest
from om.file_store.file_store import get_default_file_store
from om.file_store.utils import store_user_file_plaintext
from om.file_store.utils import user_file_id_to_plaintext_file_name
from om.indexing.adapters.user_file_indexing_adapter import UserFileIndexingAdapter
from om.indexing.embedder import DefaultIndexingEmbedder
from om.indexing.indexing_pipeline import run_indexing_pipeline
from om.redis.redis_pool import get_redis_client


def _as_uuid(value: str | UUID) -> UUID:
    """Return a UUID, accepting either a UUID or a string-like value."""
    return value if isinstance(value, UUID) else UUID(str(value))


def _user_file_lock_key(user_file_id: str | UUID) -> str:
    return f"{OmRedisLocks.USER_FILE_PROCESSING_LOCK_PREFIX}:{user_file_id}"


def _user_file_project_sync_lock_key(user_file_id: str | UUID) -> str:
    return f"{OmRedisLocks.USER_FILE_PROJECT_SYNC_LOCK_PREFIX}:{user_file_id}"


def _user_file_delete_lock_key(user_file_id: str | UUID) -> str:
    return f"{OmRedisLocks.USER_FILE_DELETE_LOCK_PREFIX}:{user_file_id}"


@shared_task(
    name=OmCeleryTask.CHECK_FOR_USER_FILE_PROCESSING,
    soft_time_limit=300,
    bind=True,
    ignore_result=True,
)
def check_user_file_processing(self: Task, *, tenant_id: str) -> None:
    """Scan for user files with PROCESSING status and enqueue per-file tasks.

    Uses direct Redis locks to avoid overlapping runs.
    """
    task_logger.info("check_user_file_processing - Starting")

    redis_client = get_redis_client(tenant_id=tenant_id)
    lock: RedisLock = redis_client.lock(
        OmRedisLocks.USER_FILE_PROCESSING_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    # Do not overlap generator runs
    if not lock.acquire(blocking=False):
        return None

    enqueued = 0
    try:
        with get_session_with_current_tenant() as db_session:
            user_file_ids = (
                db_session.execute(
                    select(UserFile.id).where(
                        UserFile.status == UserFileStatus.PROCESSING
                    )
                )
                .scalars()
                .all()
            )

            for user_file_id in user_file_ids:
                self.app.send_task(
                    OmCeleryTask.PROCESS_SINGLE_USER_FILE,
                    kwargs={"user_file_id": str(user_file_id), "tenant_id": tenant_id},
                    queue=OmCeleryQueues.USER_FILE_PROCESSING,
                    priority=OmCeleryPriority.HIGH,
                )
                enqueued += 1

    finally:
        if lock.owned():
            lock.release()

    task_logger.info(
        f"check_user_file_processing - Enqueued {enqueued} tasks for tenant={tenant_id}"
    )
    return None


def _process_user_file_without_vector_db(
    uf: UserFile,
    documents: list[Document],
    db_session: Session,
) -> None:
    """Process a user file when the vector DB is disabled.

    Extracts raw text and computes a token count, stores the plaintext in
    the file store, and marks the file as COMPLETED.  Skips embedding and
    the indexing pipeline entirely.
    """
    from om.llm.factory import get_default_llm
    from om.llm.factory import get_llm_tokenizer_encode_func

    # Combine section text from all document sections
    combined_text = " ".join(
        section.text for doc in documents for section in doc.sections if section.text
    )

    # Compute token count using the user's default LLM tokenizer
    try:
        llm = get_default_llm()
        encode = get_llm_tokenizer_encode_func(llm)
        token_count: int | None = len(encode(combined_text))
    except Exception:
        task_logger.warning(
            f"_process_user_file_without_vector_db - "
            f"Failed to compute token count for {uf.id}, falling back to None"
        )
        token_count = None

    # Persist plaintext for fast FileReaderTool loads
    store_user_file_plaintext(
        user_file_id=uf.id,
        plaintext_content=combined_text,
    )

    # Update the DB record
    if uf.status != UserFileStatus.DELETING:
        uf.status = UserFileStatus.COMPLETED
    uf.token_count = token_count
    uf.chunk_count = 0  # no chunks without vector DB
    uf.last_project_sync_at = datetime.datetime.now(datetime.timezone.utc)
    db_session.add(uf)
    db_session.commit()

    task_logger.info(
        f"_process_user_file_without_vector_db - "
        f"Completed id={uf.id} tokens={token_count}"
    )


def _process_user_file_with_indexing(
    uf: UserFile,
    user_file_id: str,
    documents: list[Document],
    tenant_id: str,
    db_session: Session,
) -> None:
    """Process a user file through the full indexing pipeline (vector DB path)."""
    search_settings_list = get_active_search_settings_list(db_session)
    current_search_settings = next(
        (ss for ss in search_settings_list if ss.status.is_current()),
        None,
    )
    if current_search_settings is None:
        raise RuntimeError(
            f"_process_user_file_with_indexing - "
            f"No current search settings found for tenant={tenant_id}"
        )

    adapter = UserFileIndexingAdapter(
        tenant_id=tenant_id,
        db_session=db_session,
    )

    embedding_model = DefaultIndexingEmbedder.from_db_search_settings(
        search_settings=current_search_settings,
    )

    document_indices = get_all_document_indices(
        current_search_settings,
        None,
    )

    index_pipeline_result = run_indexing_pipeline(
        embedder=embedding_model,
        document_indices=document_indices,
        ignore_time_skip=True,
        db_session=db_session,
        tenant_id=tenant_id,
        document_batch=documents,
        request_id=None,
        adapter=adapter,
    )

    task_logger.info(
        f"_process_user_file_with_indexing - "
        f"Indexing pipeline completed ={index_pipeline_result}"
    )

    if (
        index_pipeline_result.failures
        or index_pipeline_result.total_docs != len(documents)
        or index_pipeline_result.total_chunks == 0
    ):
        task_logger.error(
            f"_process_user_file_with_indexing - "
            f"Indexing pipeline failed id={user_file_id}"
        )
        if uf.status != UserFileStatus.DELETING:
            uf.status = UserFileStatus.FAILED
            db_session.add(uf)
            db_session.commit()
        raise RuntimeError(f"Indexing pipeline failed for user file {user_file_id}")


@shared_task(
    name=OmCeleryTask.PROCESS_SINGLE_USER_FILE,
    bind=True,
    ignore_result=True,
)
def process_single_user_file(
    self: Task, *, user_file_id: str, tenant_id: str  # noqa: ARG001
) -> None:
    task_logger.info(f"process_single_user_file - Starting id={user_file_id}")
    start = time.monotonic()

    redis_client = get_redis_client(tenant_id=tenant_id)
    file_lock: RedisLock = redis_client.lock(
        _user_file_lock_key(user_file_id),
        timeout=CELERY_USER_FILE_PROCESSING_LOCK_TIMEOUT,
    )

    if not file_lock.acquire(blocking=False):
        task_logger.info(
            f"process_single_user_file - Lock held, skipping user_file_id={user_file_id}"
        )
        return None

    documents: list[Document] = []
    try:
        with get_session_with_current_tenant() as db_session:
            uf = db_session.get(UserFile, _as_uuid(user_file_id))
            if not uf:
                task_logger.warning(
                    f"process_single_user_file - UserFile not found id={user_file_id}"
                )
                return None

            if uf.status != UserFileStatus.PROCESSING:
                task_logger.info(
                    f"process_single_user_file - Skipping id={user_file_id} status={uf.status}"
                )
                return None

            connector = LocalFileConnector(
                file_locations=[uf.file_id],
                file_names=[uf.name] if uf.name else None,
            )
            connector.load_credentials({})

            try:
                for batch in connector.load_from_state():
                    documents.extend(
                        [doc for doc in batch if not isinstance(doc, HierarchyNode)]
                    )

                # update the document id to userfile id in the documents
                for document in documents:
                    document.id = str(user_file_id)
                    document.source = DocumentSource.USER_FILE

                if DISABLE_VECTOR_DB:
                    _process_user_file_without_vector_db(
                        uf=uf,
                        documents=documents,
                        db_session=db_session,
                    )
                else:
                    _process_user_file_with_indexing(
                        uf=uf,
                        user_file_id=user_file_id,
                        documents=documents,
                        tenant_id=tenant_id,
                        db_session=db_session,
                    )

            except Exception as e:
                task_logger.exception(
                    f"process_single_user_file - Error processing file id={user_file_id} - {e.__class__.__name__}"
                )
                # don't update the status if the user file is being deleted
                current_user_file = db_session.get(UserFile, _as_uuid(user_file_id))
                if (
                    current_user_file
                    and current_user_file.status != UserFileStatus.DELETING
                ):
                    uf.status = UserFileStatus.FAILED
                    db_session.add(uf)
                    db_session.commit()
                return None

        elapsed = time.monotonic() - start
        task_logger.info(
            f"process_single_user_file - Finished id={user_file_id} docs={len(documents)} elapsed={elapsed:.2f}s"
        )
        return None
    except Exception as e:
        # Attempt to mark the file as failed
        with get_session_with_current_tenant() as db_session:
            uf = db_session.get(UserFile, _as_uuid(user_file_id))
            if uf:
                # don't update the status if the user file is being deleted
                if uf.status != UserFileStatus.DELETING:
                    uf.status = UserFileStatus.FAILED
                db_session.add(uf)
                db_session.commit()

        task_logger.exception(
            f"process_single_user_file - Error processing file id={user_file_id} - {e.__class__.__name__}"
        )
        return None
    finally:
        if file_lock.owned():
            file_lock.release()


@shared_task(
    name=OmCeleryTask.CHECK_FOR_USER_FILE_DELETE,
    soft_time_limit=300,
    bind=True,
    ignore_result=True,
)
def check_for_user_file_delete(self: Task, *, tenant_id: str) -> None:
    """Scan for user files with DELETING status and enqueue per-file tasks."""
    task_logger.info("check_for_user_file_delete - Starting")
    redis_client = get_redis_client(tenant_id=tenant_id)
    lock: RedisLock = redis_client.lock(
        OmRedisLocks.USER_FILE_DELETE_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )
    if not lock.acquire(blocking=False):
        return None
    enqueued = 0
    try:
        with get_session_with_current_tenant() as db_session:
            user_file_ids = (
                db_session.execute(
                    select(UserFile.id).where(
                        UserFile.status == UserFileStatus.DELETING
                    )
                )
                .scalars()
                .all()
            )
            for user_file_id in user_file_ids:
                self.app.send_task(
                    OmCeleryTask.DELETE_SINGLE_USER_FILE,
                    kwargs={"user_file_id": str(user_file_id), "tenant_id": tenant_id},
                    queue=OmCeleryQueues.USER_FILE_DELETE,
                    priority=OmCeleryPriority.HIGH,
                )
                enqueued += 1
    except Exception as e:
        task_logger.exception(
            f"check_for_user_file_delete - Error enqueuing deletes - {e.__class__.__name__}"
        )
        return None
    finally:
        if lock.owned():
            lock.release()
    task_logger.info(
        f"check_for_user_file_delete - Enqueued {enqueued} tasks for tenant={tenant_id}"
    )
    return None


@shared_task(
    name=OmCeleryTask.DELETE_SINGLE_USER_FILE,
    bind=True,
    ignore_result=True,
)
def process_single_user_file_delete(
    self: Task, *, user_file_id: str, tenant_id: str  # noqa: ARG001
) -> None:
    """Process a single user file delete."""
    task_logger.info(f"process_single_user_file_delete - Starting id={user_file_id}")
    redis_client = get_redis_client(tenant_id=tenant_id)
    file_lock: RedisLock = redis_client.lock(
        _user_file_delete_lock_key(user_file_id),
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )
    if not file_lock.acquire(blocking=False):
        task_logger.info(
            f"process_single_user_file_delete - Lock held, skipping user_file_id={user_file_id}"
        )
        return None
    try:
        with get_session_with_current_tenant() as db_session:
            user_file = db_session.get(UserFile, _as_uuid(user_file_id))
            if not user_file:
                task_logger.info(
                    f"process_single_user_file_delete - User file not found id={user_file_id}"
                )
                return None

            # 1) Delete vector DB chunks (skip when disabled)
            if not DISABLE_VECTOR_DB:
                active_search_settings = get_active_search_settings(db_session)
                document_indices = get_all_document_indices(
                    search_settings=active_search_settings.primary,
                    secondary_search_settings=active_search_settings.secondary,
                )
                retry_document_indices: list[RetryDocumentIndex] = [
                    RetryDocumentIndex(document_index)
                    for document_index in document_indices
                ]
                # OpenSearch deletes by document_id; chunk_count (from the DB) is a
                # hint and may be None (the index handles an unknown count).
                for retry_document_index in retry_document_indices:
                    retry_document_index.delete(
                        user_file_id,
                        chunk_count=user_file.chunk_count,
                    )

            # 2) Delete the user-uploaded file content from filestore (blob + metadata)
            file_store = get_default_file_store()
            try:
                file_store.delete_file(user_file.file_id)
                file_store.delete_file(
                    user_file_id_to_plaintext_file_name(user_file.id)
                )
            except Exception as e:
                # This block executed only if the file is not found in the filestore
                task_logger.exception(
                    f"process_single_user_file_delete - Error deleting file id={user_file.id} - {e.__class__.__name__}"
                )

            # 3) Finally, delete the UserFile row
            db_session.delete(user_file)
            db_session.commit()
            task_logger.info(
                f"process_single_user_file_delete - Completed id={user_file_id}"
            )
    except Exception as e:
        task_logger.exception(
            f"process_single_user_file_delete - Error processing file id={user_file_id} - {e.__class__.__name__}"
        )
        return None
    finally:
        if file_lock.owned():
            file_lock.release()
    return None


@shared_task(
    name=OmCeleryTask.CHECK_FOR_USER_FILE_PROJECT_SYNC,
    soft_time_limit=300,
    bind=True,
    ignore_result=True,
)
def check_for_user_file_project_sync(self: Task, *, tenant_id: str) -> None:
    """Scan for user files with PROJECT_SYNC status and enqueue per-file tasks."""
    task_logger.info("check_for_user_file_project_sync - Starting")

    redis_client = get_redis_client(tenant_id=tenant_id)
    lock: RedisLock = redis_client.lock(
        OmRedisLocks.USER_FILE_PROJECT_SYNC_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    if not lock.acquire(blocking=False):
        return None

    enqueued = 0
    try:
        with get_session_with_current_tenant() as db_session:
            user_file_ids = (
                db_session.execute(
                    select(UserFile.id).where(
                        sa.and_(
                            UserFile.needs_project_sync.is_(True),
                            UserFile.status == UserFileStatus.COMPLETED,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for user_file_id in user_file_ids:
                self.app.send_task(
                    OmCeleryTask.PROCESS_SINGLE_USER_FILE_PROJECT_SYNC,
                    kwargs={"user_file_id": str(user_file_id), "tenant_id": tenant_id},
                    queue=OmCeleryQueues.USER_FILE_PROJECT_SYNC,
                    priority=OmCeleryPriority.HIGH,
                )
                enqueued += 1
    finally:
        if lock.owned():
            lock.release()

    task_logger.info(
        f"check_for_user_file_project_sync - Enqueued {enqueued} tasks for tenant={tenant_id}"
    )
    return None


@shared_task(
    name=OmCeleryTask.PROCESS_SINGLE_USER_FILE_PROJECT_SYNC,
    bind=True,
    ignore_result=True,
)
def process_single_user_file_project_sync(
    self: Task, *, user_file_id: str, tenant_id: str  # noqa: ARG001
) -> None:
    """Process a single user file project sync."""
    task_logger.info(
        f"process_single_user_file_project_sync - Starting id={user_file_id}"
    )

    redis_client = get_redis_client(tenant_id=tenant_id)
    file_lock: RedisLock = redis_client.lock(
        _user_file_project_sync_lock_key(user_file_id),
        timeout=CELERY_USER_FILE_PROJECT_SYNC_LOCK_TIMEOUT,
    )

    if not file_lock.acquire(blocking=False):
        task_logger.info(
            f"process_single_user_file_project_sync - Lock held, skipping user_file_id={user_file_id}"
        )
        return None

    try:
        with get_session_with_current_tenant() as db_session:
            user_file = db_session.get(UserFile, _as_uuid(user_file_id))
            if not user_file:
                task_logger.info(
                    f"process_single_user_file_project_sync - User file not found id={user_file_id}"
                )
                return None

            # Sync project metadata to vector DB (skip when disabled)
            if not DISABLE_VECTOR_DB:
                active_search_settings = get_active_search_settings(db_session)
                document_indices = get_all_document_indices(
                    search_settings=active_search_settings.primary,
                    secondary_search_settings=active_search_settings.secondary,
                )
                retry_document_indices: list[RetryDocumentIndex] = [
                    RetryDocumentIndex(document_index)
                    for document_index in document_indices
                ]

                project_ids = [project.id for project in user_file.projects]
                update_request = MetadataUpdateRequest(
                    document_ids=[str(user_file.id)],
                    doc_id_to_chunk_cnt={
                        str(user_file.id): (
                            user_file.chunk_count
                            if user_file.chunk_count is not None
                            else -1
                        )
                    },
                    project_ids=set(project_ids),
                )
                for retry_document_index in retry_document_indices:
                    retry_document_index.update([update_request])

            task_logger.info(
                f"process_single_user_file_project_sync - User file id={user_file_id}"
            )

            user_file.needs_project_sync = False
            user_file.last_project_sync_at = datetime.datetime.now(
                datetime.timezone.utc
            )
            db_session.add(user_file)
            db_session.commit()

    except Exception as e:
        task_logger.exception(
            f"process_single_user_file_project_sync - Error syncing project for file id={user_file_id} - {e.__class__.__name__}"
        )
        return None
    finally:
        if file_lock.owned():
            file_lock.release()

    return None
