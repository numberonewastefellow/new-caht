from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr

from app.services.executor_base import EntryKind


class ExecuteFile(BaseModel):
    path: StrictStr = Field(..., description="Relative file path within the execution workspace.")
    file_id: StrictStr = Field(
        ..., description="UUID of a previously uploaded file to use for execution."
    )


class WorkspaceFile(BaseModel):
    path: StrictStr
    kind: EntryKind
    file_id: StrictStr | None = Field(
        None, description="ID of the file in storage (only for files, not directories)."
    )


class ExecuteRequest(BaseModel):
    code: StrictStr = Field(..., description="Python source to execute.")
    stdin: StrictStr | None = Field(None, description="Optional stdin passed to the program.")
    timeout_ms: StrictInt = Field(2000, ge=1, description="Execution timeout in milliseconds.")
    last_line_interactive: bool = Field(
        True,
        description=(
            "If True, the last line of code will print its value to stdout if it's a bare "
            "expression (like Jupyter notebooks or Python REPL). Only the last line is affected; "
            "earlier expressions are not printed. Default is True."
        ),
    )
    files: list[ExecuteFile] = Field(
        default_factory=list,
        description="Optional collection of files to stage in the execution workspace.",
    )
    session_id: StrictStr | None = Field(
        None,
        description=(
            "Optional session ID for persistent execution. When provided, code runs in "
            "a persistent kernel where variables and imports survive between calls. "
            "When absent, uses ephemeral stateless execution (backward compatible)."
        ),
    )


class CreateSessionResponse(BaseModel):
    session_id: StrictStr = Field(..., description="Unique identifier for the session.")


class ExecuteResponse(BaseModel):
    stdout: StrictStr
    stderr: StrictStr
    exit_code: int | None
    timed_out: bool
    duration_ms: StrictInt
    error_kind: StrictStr | None = Field(
        default=None,
        description="Non-timeout failure mode when set: 'oom', 'kernel_died', or 'timeout'.",
    )
    files: list[WorkspaceFile] = Field(
        default_factory=list,
        description="Snapshot of the execution workspace after completion.",
    )


# Largest program /v1/run_function accepts (the code-node harness embeds the user code
# and its inputs, both base64-encoded).
RUN_FUNCTION_MAX_PROGRAM_CHARS = 8_000_000


class RunFunctionRequest(BaseModel):
    program: StrictStr = Field(
        ...,
        max_length=RUN_FUNCTION_MAX_PROGRAM_CHARS,
        description=(
            "Self-contained Python program, run as-is with `python -` (no last-line "
            "wrapper, no figure prologue, no workspace files)."
        ),
    )
    timeout_ms: StrictInt = Field(..., ge=1, description="Wall-clock timeout in milliseconds.")
    read_result_file: StrictBool = Field(
        False,
        description=(
            "If true, return the file the program wrote to $OM_RESULT_PATH (/tmp/result) "
            "as result_payload: a result channel separate from stdout."
        ),
    )


class RunFunctionResponse(BaseModel):
    stdout: StrictStr = Field(..., description="Program stdout, cut at MAX_OUTPUT_BYTES.")
    stderr: StrictStr = Field(
        ..., description="Program stderr, cut at RUN_FUNCTION_MAX_STDERR_BYTES."
    )
    exit_code: int | None = Field(..., description="Process exit code; null on timeout.")
    timed_out: bool = Field(..., description="The wall-clock timeout fired.")
    duration_ms: StrictInt
    error_kind: Literal["timeout", "oom", "sandbox_error"] | None = Field(
        ...,
        description=(
            "'timeout': wall-clock timeout or CPU-time limit (exit 152); 'oom': killed "
            "for memory (exit 137); 'sandbox_error': the sandbox could not run the "
            "program; null otherwise (inspect exit_code)."
        ),
    )
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    result_payload: StrictStr | None = Field(
        None,
        description=(
            "Contents of the result file (UTF-8), when read_result_file was set and the "
            "program wrote one."
        ),
    )
    result_error: Literal["too_large", "invalid_utf8"] | None = Field(
        None,
        description="Why a written result file was not returned (never truncated).",
    )
    pool_hit: bool = Field(
        False, description="The run used a pre-started (warm) single-use sandbox."
    )


class SSEModel(BaseModel):
    """Base for Server-Sent Event payloads.

    Subclasses declare ``sse_event`` as a ClassVar to set the SSE event type.
    Call ``to_sse()`` to get a fully-formatted SSE frame.
    """

    sse_event: ClassVar[str]

    def to_sse(self) -> str:
        data = self.model_dump_json()
        return f"event: {self.sse_event}\ndata: {data}\n\n"


class StreamOutputEvent(SSEModel):
    """Payload for 'output' SSE events."""

    sse_event: ClassVar[str] = "output"

    stream: Literal["stdout", "stderr"]
    data: StrictStr


class StreamResultEvent(SSEModel):
    """Payload for the final 'result' SSE event."""

    sse_event: ClassVar[str] = "result"

    exit_code: int | None
    timed_out: bool
    duration_ms: StrictInt
    error_kind: StrictStr | None = Field(
        default=None,
        description="Non-timeout failure mode when set: 'oom', 'kernel_died', or 'timeout'.",
    )
    files: list[WorkspaceFile] = Field(
        default_factory=list,
        description="Snapshot of the execution workspace after completion.",
    )


class StreamErrorEvent(SSEModel):
    """Payload for 'error' SSE events."""

    sse_event: ClassVar[str] = "error"

    message: StrictStr


class UploadFileResponse(BaseModel):
    file_id: StrictStr = Field(..., description="Unique identifier for the uploaded file.")
    filename: StrictStr = Field(..., description="Original filename as provided during upload.")
    size_bytes: StrictInt = Field(..., description="Size of the uploaded file in bytes.")


class FileMetadataResponse(BaseModel):
    file_id: StrictStr
    filename: StrictStr
    size_bytes: StrictInt
    upload_time: float = Field(..., description="Unix timestamp of when the file was uploaded.")


class ListFilesResponse(BaseModel):
    files: list[FileMetadataResponse] = Field(
        default_factory=list,
        description="List of all stored files with their metadata.",
    )


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    message: StrictStr | None = None
