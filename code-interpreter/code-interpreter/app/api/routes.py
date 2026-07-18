from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.app_configs import EXECUTOR_BACKEND, get_settings
from app.models.schemas import (
    CreateSessionResponse,
    ExecuteRequest,
    ExecuteResponse,
    FileMetadataResponse,
    ListFilesResponse,
    StreamErrorEvent,
    StreamOutputEvent,
    StreamResultEvent,
    UploadFileResponse,
    WorkspaceFile,
)
from app.services.executor_base import (
    EntryKind,
    StreamChunk,
    StreamEvent,
    StreamResult,
    WorkspaceEntry,
)
from app.services.executor_factory import execute_python, execute_python_streaming
from app.services.file_storage import FileStorageService
from app.services.session_manager import _STREAM_SENTINEL, SessionManager

# Sentinel returned by _safe_next when the wrapped sync generator is exhausted.
_STREAM_DONE = object()

# SSE headers that defeat proxy buffering so chunks reach the browser immediately.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

router = APIRouter()

# Initialize file storage service
_file_storage: FileStorageService | None = None

# Session manager (initialized in main.py lifespan)
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global SessionManager instance."""
    if _session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not initialized",
        )
    return _session_manager


def set_session_manager(manager: SessionManager) -> None:
    """Set the global SessionManager (called from main.py lifespan)."""
    global _session_manager
    _session_manager = manager


def get_file_storage() -> FileStorageService:
    """Get or create the global FileStorageService instance."""
    global _file_storage
    if _file_storage is None:
        settings = get_settings()
        _file_storage = FileStorageService(Path(settings.file_storage_dir))
    return _file_storage


def _validate_timeout(req: ExecuteRequest) -> None:
    settings = get_settings()
    if req.timeout_ms > settings.max_exec_timeout_ms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"timeout_ms exceeds maximum of {settings.max_exec_timeout_ms} ms",
        )


def _stage_request_files(
    req: ExecuteRequest,
    storage: FileStorageService,
) -> tuple[list[tuple[str, bytes]], dict[str, bytes]]:
    """Resolve uploaded file IDs into content for the executor.

    Returns (staged_files, input_files_map).
    """
    staged_files: list[tuple[str, bytes]] = []
    input_files_map: dict[str, bytes] = {}
    for file in req.files:
        try:
            content, _ = storage.get_file(file.file_id)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID '{file.file_id}' not found for path '{file.path}'.",
            ) from exc
        staged_files.append((file.path, content))
        input_files_map[file.path] = content
    return staged_files, input_files_map


def _save_workspace_files(
    entries: tuple[WorkspaceEntry, ...],
    input_files_map: dict[str, bytes],
    storage: FileStorageService,
) -> list[WorkspaceFile]:
    """Filter and save new/modified workspace files to storage."""
    workspace_files: list[WorkspaceFile] = []
    for entry in entries:
        if entry.kind == EntryKind.DIRECTORY:
            continue
        if entry.kind == EntryKind.FILE and entry.content is not None:
            if entry.path in input_files_map and entry.content == input_files_map[entry.path]:
                continue
            file_id = storage.save_file(entry.content, entry.path)
            workspace_files.append(WorkspaceFile(path=entry.path, kind=entry.kind, file_id=file_id))
    return workspace_files


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session() -> CreateSessionResponse:
    """Create a persistent execution session.

    Returns a session_id that can be passed to /execute for stateful execution
    where variables, imports, and DataFrames survive between calls.
    """
    mgr = get_session_manager()
    settings = get_settings()
    try:
        session_id = mgr.create_session(memory_limit_mb=settings.memory_limit_mb)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return CreateSessionResponse(session_id=session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str) -> Response:
    """Destroy a persistent execution session and its container."""
    mgr = get_session_manager()
    if not mgr.has_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    mgr.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/execute", response_model=ExecuteResponse, status_code=status.HTTP_200_OK)
def execute(req: ExecuteRequest) -> ExecuteResponse:
    """Execute provided Python code synchronously.

    If ``session_id`` is provided, executes in a persistent session where
    variables survive between calls.  Otherwise uses ephemeral execution
    (backward compatible).
    """
    _validate_timeout(req)
    settings = get_settings()
    storage = get_file_storage()
    staged_files, input_files_map = _stage_request_files(req, storage)

    # --- Session-based execution ---
    if req.session_id:
        mgr = get_session_manager()
        if not mgr.has_session(req.session_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{req.session_id}' not found",
            )
        try:
            result = mgr.execute_in_session(
                session_id=req.session_id,
                code=req.code,
                timeout_ms=req.timeout_ms,
                max_output_bytes=settings.max_output_bytes,
                files=staged_files or None,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        return ExecuteResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            duration_ms=result.duration_ms,
            files=_save_workspace_files(result.files, input_files_map, storage),
        )

    # --- Ephemeral execution (original behavior) ---
    try:
        result = execute_python(
            code=req.code,
            stdin=req.stdin,
            timeout_ms=req.timeout_ms,
            max_output_bytes=settings.max_output_bytes,
            cpu_time_limit_sec=settings.cpu_time_limit_sec,
            memory_limit_mb=settings.memory_limit_mb,
            files=staged_files,
            last_line_interactive=req.last_line_interactive,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ExecuteResponse(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
        files=_save_workspace_files(result.files, input_files_map, storage),
    )


def _safe_next(gen: Iterator[StreamEvent]) -> object:
    """Advance a sync stream generator by one item without raising.

    Returns the next StreamEvent, ``_STREAM_DONE`` on exhaustion, or the raised
    exception object (so the async wrapper can surface it as an error event).
    """
    try:
        return next(gen)
    except StopIteration:
        return _STREAM_DONE
    except Exception as exc:  # noqa: BLE001 - forwarded to the client as an error event
        return exc


@router.post("/execute/stream")
async def execute_stream(req: ExecuteRequest, request: Request) -> StreamingResponse:
    """Execute Python code with streaming output via Server-Sent Events.

    Ephemeral (no ``session_id``) and session-based streaming are both supported.
    Session streaming requires the Docker executor backend (persistent kernels are
    Docker-only), mirroring the constraint on the blocking session path.
    """
    _validate_timeout(req)
    settings = get_settings()
    storage = get_file_storage()
    staged_files, input_files_map = _stage_request_files(req, storage)

    def _result_to_sse(result: StreamResult) -> str:
        return StreamResultEvent(
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            duration_ms=result.duration_ms,
            error_kind=result.error_kind,
            files=_save_workspace_files(result.files, input_files_map, storage),
        ).to_sse()

    # --- Session streaming (persistent kernel; Docker-only) ---
    if req.session_id:
        # Case-insensitive to match how the executor factory selects the backend.
        if EXECUTOR_BACKEND.lower() != "docker":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session streaming requires the docker executor backend.",
            )
        mgr = get_session_manager()
        if not mgr.has_session(req.session_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{req.session_id}' not found",
            )
        if mgr.is_session_busy(req.session_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session is busy with another execution.",
            )

        sid = req.session_id

        async def session_gen() -> AsyncIterator[str]:
            stream = None
            try:
                stream = mgr.stream_session(
                    sid,
                    req.code,
                    req.timeout_ms,
                    settings.max_output_bytes,
                    staged_files or None,
                )
                while True:
                    if await request.is_disconnected():
                        break
                    # Poll off the anyio pool so a worker is held for <=1s, never
                    # for the whole cell (the reader thread owns the blocking read).
                    ev = await run_in_threadpool(stream.poll, 1.0)
                    if ev is None:
                        yield ": keepalive\n\n"
                        continue
                    if ev is _STREAM_SENTINEL:
                        break
                    if isinstance(ev, StreamChunk):
                        yield StreamOutputEvent(stream=ev.stream, data=ev.data).to_sse()
                    elif isinstance(ev, StreamResult):
                        yield _result_to_sse(ev)
                    elif isinstance(ev, BaseException):
                        yield StreamErrorEvent(message=str(ev)).to_sse()
                        break
            except Exception as exc:
                # A result-serialization / file-save failure must surface as an error
                # event, not a silently truncated stream.
                yield StreamErrorEvent(message=str(exc)).to_sse()
            finally:
                if stream is not None:
                    stream.cancel()

        return StreamingResponse(
            session_gen(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    # --- Ephemeral streaming (stateless; original behavior + disconnect handling) ---
    async def ephemeral_gen() -> AsyncIterator[str]:
        gen = execute_python_streaming(
            code=req.code,
            stdin=req.stdin,
            timeout_ms=req.timeout_ms,
            max_output_bytes=settings.max_output_bytes,
            cpu_time_limit_sec=settings.cpu_time_limit_sec,
            memory_limit_mb=settings.memory_limit_mb,
            files=staged_files,
            last_line_interactive=req.last_line_interactive,
        )
        try:
            while True:
                if await request.is_disconnected():
                    break
                ev = await run_in_threadpool(_safe_next, gen)
                if ev is _STREAM_DONE:
                    break
                if isinstance(ev, StreamChunk):
                    yield StreamOutputEvent(stream=ev.stream, data=ev.data).to_sse()
                elif isinstance(ev, StreamResult):
                    yield _result_to_sse(ev)
                elif isinstance(ev, BaseException):
                    yield StreamErrorEvent(message=str(ev)).to_sse()
                    break
        except Exception as exc:
            yield StreamErrorEvent(message=str(exc)).to_sse()
        finally:
            gen.close()

    return StreamingResponse(
        ephemeral_gen(), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@router.post("/files", response_model=UploadFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)) -> UploadFileResponse:  # noqa: B008
    """Upload a file for later use in code execution."""
    settings = get_settings()
    storage = get_file_storage()

    # Read file content
    content = await file.read()

    # Validate file size
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {settings.max_file_size_mb} MB",
        )

    # Save file and get ID
    filename = file.filename or "unnamed"
    file_id = storage.save_file(content, filename)

    return UploadFileResponse(
        file_id=file_id,
        filename=filename,
        size_bytes=len(content),
    )


@router.get("/files/{file_id}")
async def download_file(file_id: str) -> Response:
    """Download a previously uploaded file by its ID."""
    storage = get_file_storage()

    try:
        content, metadata = storage.get_file(file_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found",
        ) from exc

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{metadata.filename}"',
        },
    )


@router.get("/files", response_model=ListFilesResponse, status_code=status.HTTP_200_OK)
def list_files() -> ListFilesResponse:
    """List all uploaded files with their metadata."""
    storage = get_file_storage()
    files = storage.list_files()

    return ListFilesResponse(
        files=[
            FileMetadataResponse(
                file_id=f.file_id,
                filename=f.filename,
                size_bytes=f.size_bytes,
                upload_time=f.upload_time,
            )
            for f in files
        ]
    )


@router.delete("/files/{file_id}")
def delete_file(file_id: str) -> Response:
    """Delete a previously uploaded file by its ID."""
    storage = get_file_storage()

    if not storage.delete_file(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
