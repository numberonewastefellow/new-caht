import mimetypes
import time
from io import BytesIO
from typing import Any
from typing import cast
from typing import TYPE_CHECKING
from uuid import UUID

import requests

from pydantic import TypeAdapter
from sqlalchemy.orm import Session
from typing_extensions import override

from om.chat.emitter import Emitter
from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
from om.configs.app_configs import CODE_INTERPRETER_DEFAULT_TIMEOUT_MS
from om.configs.app_configs import CODE_INTERPRETER_MAX_OUTPUT_LENGTH
from om.configs.app_configs import CODE_INTERPRETER_MAX_SELF_HEAL_ATTEMPTS
from om.configs.constants import FileOrigin
from om.file_store.utils import build_full_frontend_file_url
from om.file_store.utils import get_default_file_store
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import PythonToolDelta
from om.server.query_and_chat.streaming_models import PythonToolFile
from om.server.query_and_chat.streaming_models import PythonToolStart
from om.tools.interface import Tool
from om.tools.models import LlmPythonExecutionResult
from om.tools.models import PythonExecutionFile
from om.tools.models import PythonToolOverrideKwargs
from om.tools.models import ToolCallException
from om.tools.models import ToolResponse
from om.tools.tool_implementations.python.code_interpreter_client import (
    CodeInterpreterClient,
)
from om.tools.tool_implementations.python.code_interpreter_client import FileInput
from om.utils.logger import setup_logger

if TYPE_CHECKING:
    from om.llm.interfaces import LLM
    from om.tools.tool_implementations.python.code_interpreter_client import (
        ExecuteResponse,
    )


logger = setup_logger()

CODE_FIELD = "code"

# Hard wall-clock budget for the entire run() (including self-heal retries, LLM
# fix calls, and file downloads). Kept comfortably under tool_runner's
# TOOL_EXECUTION_TIMEOUT_SECONDS (600s) so the tool always returns a real result
# (success or error) before the threadpool abandons our thread without emitting a
# terminal SectionEnd packet.
SELF_HEAL_TOTAL_DEADLINE_SECONDS = 480

# Bound for each LLM "fix my code" call so a hung secondary call can't eat the
# whole budget.
SELF_HEAL_LLM_TIMEOUT_SECONDS = 60

# Max chars of traceback fed into the self-heal fix prompt. Kept small and
# tail-biased: a Python traceback's actual exception lives at the END, and the
# full output cap (CODE_INTERPRETER_MAX_OUTPUT_LENGTH, 50k) is far more than the
# fixer needs.
SELF_HEAL_MAX_ERROR_CHARS = 4000

# Stop starting new self-heal work (LLM fix call or re-execute) once fewer than
# this many seconds of the wall-clock budget remain.
DEADLINE_GUARD_SECONDS = 5


def _truncate_output(output: str, max_length: int, label: str = "output") -> str:
    """
    Truncate output string to max_length and append truncation message if needed.

    Args:
        output: The original output string to truncate
        max_length: Maximum length before truncation
        label: Label for logging (e.g., "stdout", "stderr")

    Returns:
        Truncated string with truncation message appended if truncated
    """
    truncated = output[:max_length]
    if len(output) > max_length:
        truncated += (
            "\n... [output truncated, "
            f"{len(output) - max_length} "
            "characters omitted]"
        )
        logger.debug(f"Truncated {label}: {truncated}")
    return truncated


def _truncate_tail(output: str, max_length: int) -> str:
    """Truncate keeping the TAIL of the string (with a leading marker).

    Used for tracebacks fed to the self-heal fixer: the exception type/message
    lives at the end, so we keep the last `max_length` chars rather than the head.
    """
    if len(output) <= max_length:
        return output
    omitted = len(output) - max_length
    return f"[... {omitted} characters omitted ...]\n{output[-max_length:]}"


def _strip_code_fences(text: str) -> str:
    """Remove a surrounding markdown code fence (```python ... ```), if present.

    The self-heal prompt asks for raw code, but models sometimes wrap it anyway.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    # Drop the opening fence line (``` or ```python)
    lines = lines[1:]
    # Drop the closing fence line if present
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


class PythonTool(Tool[PythonToolOverrideKwargs]):
    """
    Python code execution tool using an external Code Interpreter service.

    This tool allows executing Python code in a secure, isolated sandbox environment.
    It supports uploading files from the chat session and downloading generated files.
    """

    NAME = "python"
    DISPLAY_NAME = "Code Interpreter"
    DESCRIPTION = "Execute Python code in a persistent sandbox environment. Variables and files persist across calls within the same conversation."

    def __init__(
        self,
        tool_id: int,
        emitter: Emitter,
        db_session: Session | None = None,
        chat_session_id: str | None = None,
        llm: "LLM | None" = None,
    ) -> None:
        super().__init__(emitter=emitter)
        self._id = tool_id
        self._db_session = db_session
        self._chat_session_id = chat_session_id
        # Optional LLM used by the in-tool self-heal loop to repair failing code.
        # When None, self-heal is skipped and the agent loop remains the only retry
        # mechanism (see PYTHON_TOOL_GUIDANCE).
        self._llm = llm
        # Cached session_id for reuse across multiple tool calls in the same message
        self._session_id: str | None = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    @classmethod
    def is_available(cls, db_session: Session) -> bool:
        is_available = bool(CODE_INTERPRETER_BASE_URL)
        return is_available

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        CODE_FIELD: {
                            "type": "string",
                            "description": "Python source code to execute",
                        },
                    },
                    "required": [CODE_FIELD],
                },
            },
        }

    def _create_and_persist_session(
        self, client: CodeInterpreterClient
    ) -> str | None:
        """Lazily create a persistent sandbox session and save to ChatSession in DB.

        Returns the new session_id or None if creation fails.
        """
        try:
            new_session_id = client.create_session()
            self._session_id = new_session_id
            logger.info(
                f"Created persistent sandbox session {new_session_id} "
                f"for chat {self._chat_session_id}"
            )

            # Persist to DB so subsequent messages reuse this sandbox.
            # Workflow agent steps use a synthetic scope id (e.g.
            # "agent_step_624_...") that is NOT a real ChatSession UUID — there
            # is no row to update, so skip persistence quietly rather than
            # raising on UUID() and logging a spurious error.
            if self._db_session and self._chat_session_id:
                try:
                    chat_session_uuid = UUID(self._chat_session_id)
                except ValueError:
                    logger.debug(
                        f"chat_session_id={self._chat_session_id} is not a UUID "
                        f"(workflow agent-step scope); skipping sandbox persistence"
                    )
                else:
                    try:
                        from om.db.models import ChatSession

                        self._db_session.query(ChatSession).filter(
                            ChatSession.id == chat_session_uuid
                        ).update({"sandbox_session_id": new_session_id})
                        self._db_session.commit()
                        logger.info(
                            f"Persisted sandbox_session_id={new_session_id} "
                            f"to chat_session={self._chat_session_id}"
                        )
                    except Exception:
                        logger.exception(
                            "Failed to persist sandbox_session_id to DB"
                        )
                        # Non-fatal: the session still works for this message

            return new_session_id
        except Exception:
            logger.exception("Failed to create persistent sandbox session")
            return None

    def _is_retriable_error(self, exc: Exception) -> bool:
        """Check if an execution error is caused by a dead/stale session or
        unreachable code-interpreter service (worth retrying with a fresh session)."""
        if isinstance(exc, requests.exceptions.ConnectionError):
            return True
        if isinstance(exc, requests.exceptions.HTTPError):
            status = getattr(exc.response, "status_code", None)
            # 404 = session not found / service not found
            # 502/503/504 = service restarting
            return status in (404, 502, 503, 504)
        # Catch generic connection-related errors
        error_str = str(exc).lower()
        return any(
            keyword in error_str
            for keyword in ("connection", "404", "not found", "502", "503", "504")
        )

    @staticmethod
    def _is_code_error(response: "ExecuteResponse") -> bool:  # noqa: F821
        """True only for a genuine *code* error worth self-healing.

        Excludes clean success (exit 0) and the non-error terminal states the LLM
        cannot repair: timeout, oom/kernel_died, and a missing result frame
        (``exit_code is None``). Self-healing those would just burn the LLM budget.
        """
        return (
            response.exit_code not in (0, None)
            and not response.timed_out
            and response.error_kind is None
        )

    def _execute_streaming(
        self,
        client: CodeInterpreterClient,
        placement: Placement,
        code: str,
        timeout_ms: int,
        files: list[FileInput] | None,
        session_id: str | None,
    ) -> "tuple[ExecuteResponse, bool]":  # noqa: F821
        """Execute code with live streaming, emitting one PythonToolDelta per chunk.

        Each output chunk is emitted immediately as its own delta carrying exactly
        one populated stream field, so the wire order equals the true stdout/stderr
        interleave order and the UI updates in real time. Returns
        ``(aggregated_response, emitted_any)`` — the aggregated response carries the
        full stdout/stderr for the LLM-facing result (the terminal frame itself
        carries none, since it was already streamed), and ``emitted_any`` records
        whether any byte reached the UI (a fresh-session replay is unsafe once it has).
        """
        from om.tools.tool_implementations.python.code_interpreter_client import (
            ExecuteResponse,
        )

        out_parts: list[str] = []
        err_parts: list[str] = []
        emitted_any = False
        final: ExecuteResponse | None = None

        try:
            for ev in client.execute_stream(
                code=code,
                timeout_ms=timeout_ms,
                files=files,
                session_id=session_id,
            ):
                if ev.kind == "output":
                    data = ev.data or ""
                    if not data:
                        continue
                    if ev.stream == "stderr":
                        err_parts.append(data)
                    else:
                        out_parts.append(data)
                    emitted_any = True
                    # One populated stream field per delta → wire order == interleave.
                    self.emitter.emit(
                        Packet(
                            placement=placement,
                            obj=PythonToolDelta(
                                stdout=data if ev.stream == "stdout" else "",
                                stderr=data if ev.stream == "stderr" else "",
                                file_ids=[],
                            ),
                        )
                    )
                elif ev.result is not None:
                    final = ev.result
        except Exception as stream_err:
            if emitted_any:
                # Partial output is already on screen; a state-less replay on a fresh
                # session would duplicate it and desync. Surface the failure instead
                # of letting _execute_with_retry replay (raise a NON-retriable error).
                self.emitter.emit(
                    Packet(
                        placement=placement,
                        obj=PythonToolDelta(
                            stdout="",
                            stderr="\n[connection lost — partial output above]",
                            file_ids=[],
                        ),
                    )
                )
                raise RuntimeError(
                    "code interpreter stream interrupted after partial output"
                ) from stream_err
            # Nothing emitted yet → let the caller decide whether to retry.
            raise

        aggregated = ExecuteResponse(
            stdout="".join(out_parts),
            stderr="".join(err_parts),
            exit_code=final.exit_code if final else None,
            timed_out=final.timed_out if final else False,
            duration_ms=final.duration_ms if final else 0,
            error_kind=final.error_kind if final else None,
            files=final.files if final else [],
        )
        return aggregated, emitted_any

    def _execute_with_retry(
        self,
        client: CodeInterpreterClient,
        placement: Placement,
        code: str,
        timeout_ms: int,
        files: list[FileInput] | None,
        session_id: str | None,
    ) -> "ExecuteResponse":  # noqa: F821
        """Stream-execute code, retrying once with a fresh session on a retriable
        failure — but only when nothing has streamed yet.

        A retriable error at stream setup (``raise_for_status`` fires before any byte
        is read) means the UI is still empty, so a fresh-session replay is safe. Once
        output has streamed, ``_execute_streaming`` converts the failure into a
        non-retriable error so we never replay over visible output.
        """
        try:
            response, _emitted = self._execute_streaming(
                client=client,
                placement=placement,
                code=code,
                timeout_ms=timeout_ms,
                files=files,
                session_id=session_id,
            )
            return response
        except Exception as first_err:
            if not self._is_retriable_error(first_err):
                raise

            logger.warning(
                f"Code execution failed (retriable): {first_err}. "
                f"Creating fresh session and retrying..."
            )

            # Create a fresh session
            new_session_id = self._create_and_persist_session(client)
            if not new_session_id:
                # Could not create session — re-raise the original error
                raise

            # Retry with the new session
            response, _emitted = self._execute_streaming(
                client=client,
                placement=placement,
                code=code,
                timeout_ms=timeout_ms,
                files=files,
                session_id=new_session_id,
            )
            return response

    def _request_code_fix(
        self,
        code: str,
        error: str,
        timeout_s: int = SELF_HEAL_LLM_TIMEOUT_SECONDS,
    ) -> str | None:
        """Ask the LLM to repair failing code given the traceback.

        Returns corrected Python source, or None if no LLM is available or the
        call fails. Defensively strips markdown code fences in case the model
        wraps its answer despite instructions. `timeout_s` bounds the LLM call
        (clamped by the caller to the remaining wall-clock budget).
        """
        if self._llm is None:
            return None

        from om.llm.models import UserMessage
        from om.prompts.tool_prompts import PYTHON_TOOL_SELF_HEAL_PROMPT

        prompt = PYTHON_TOOL_SELF_HEAL_PROMPT.format(
            code=code,
            # Keep the TAIL of the traceback (the actual exception) and cap it
            # small — feeding the full 50k output cap here is needless token cost.
            error=_truncate_tail(error, SELF_HEAL_MAX_ERROR_CHARS),
        )
        try:
            response = self._llm.invoke(
                prompt=[UserMessage(content=prompt)],
                timeout_override=timeout_s,
            )
            fixed = response.choice.message.content
        except Exception:
            logger.exception("Self-heal: LLM call to fix Python code failed")
            return None

        if not fixed or not fixed.strip():
            return None

        return _strip_code_fences(fixed)

    def _execute_with_self_heal(
        self,
        client: CodeInterpreterClient,
        placement: Placement,
        code: str,
        files: list[FileInput] | None,
        session_id: str | None,
        deadline: float,
    ) -> "tuple[ExecuteResponse, str]":
        """Execute code, repairing and re-running it via the LLM on failure.

        On a non-zero exit code, the failing code + traceback are sent back to the
        LLM (up to CODE_INTERPRETER_MAX_SELF_HEAL_ATTEMPTS times) to produce
        corrected code, which is re-executed in the SAME persistent session so
        prior state is preserved.

        Every LLM fix call and execute is clamped to the remaining wall-clock
        budget (`deadline`) so the whole loop returns before tool_runner's
        threadpool cap can abandon the thread. Returns (final_response,
        self_heal_note) where self_heal_note is a short human/LLM-readable summary
        of the retries (empty if none happened). Progress is streamed to the UI via
        stdout deltas so the section never appears to hang; intermediate failures
        are NOT emitted as stderr so the section status stays accurate (an eventual
        success is shown as success).
        """
        current_code = code

        # Clamp the per-call execute timeout to the remaining budget so a single
        # call can't push the whole run past the threadpool cap.
        first_timeout_ms = min(
            CODE_INTERPRETER_DEFAULT_TIMEOUT_MS,
            max(1, int((deadline - time.monotonic()) * 1000)),
        )
        response = self._execute_with_retry(
            client=client,
            placement=placement,
            code=current_code,
            timeout_ms=first_timeout_ms,
            files=files,
            session_id=session_id,
        )

        # Each entry: the error from an attempt that we then tried to repair.
        attempt_errors: list[str] = []

        attempt = 0
        while (
            self._is_code_error(response)
            and attempt < CODE_INTERPRETER_MAX_SELF_HEAL_ATTEMPTS
            and self._llm is not None
            and (deadline - time.monotonic()) > DEADLINE_GUARD_SECONDS
        ):
            attempt += 1
            attempt_errors.append(response.stderr)

            # Real-time UI feedback into the CURRENT (failing) attempt's pane — a normal
            # delta (NO reset) so the notice stays grouped with the traceback of the
            # attempt it describes. The reset boundary is emitted below, only once a
            # usable fix is confirmed and there is budget to re-execute; that way a run
            # which produces no fix keeps the failed attempt's traceback on screen.
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=PythonToolDelta(
                        stdout=(
                            f"⚠️ Attempt {attempt} failed with an error. "
                            f"Asking the model to fix the code and retrying "
                            f"({attempt}/{CODE_INTERPRETER_MAX_SELF_HEAL_ATTEMPTS})...\n"
                        ),
                        stderr="",
                        file_ids=[],
                    ),
                )
            )

            # Bound the fix call to what's left of the budget.
            fix_timeout_s = min(
                SELF_HEAL_LLM_TIMEOUT_SECONDS,
                max(1, int(deadline - time.monotonic())),
            )
            fixed_code = self._request_code_fix(
                current_code, response.stderr, fix_timeout_s
            )
            if not fixed_code or fixed_code.strip() == current_code.strip():
                # Could not get a (different) fix — stop retrying.
                logger.info(
                    "Self-heal: no usable fix produced on attempt "
                    f"{attempt}; giving up."
                )
                break

            # The fix call may have consumed most of the budget — don't start a
            # re-execute we can't finish before the threadpool cap.
            if (deadline - time.monotonic()) <= DEADLINE_GUARD_SECONDS:
                logger.info(
                    "Self-heal: out of time budget before re-execute; stopping."
                )
                break

            # A usable fix is confirmed and the budget allows a re-execute: emit the
            # attempt boundary NOW (renderer archives the failed attempt as a collapsed
            # block and clears the live pane) so the retry streams into a clean surface.
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=PythonToolDelta(stdout="", stderr="", file_ids=[], reset=True),
                )
            )

            current_code = fixed_code
            logger.info(f"Self-heal: re-executing corrected code (attempt {attempt})")
            retry_timeout_ms = min(
                CODE_INTERPRETER_DEFAULT_TIMEOUT_MS,
                max(1, int((deadline - time.monotonic()) * 1000)),
            )
            # Files were staged into the persistent session on the first run, so
            # don't re-upload them on retries (same session_id keeps the workspace).
            response = self._execute_with_retry(
                client=client,
                placement=placement,
                code=current_code,
                timeout_ms=retry_timeout_ms,
                files=None,
                session_id=session_id,
            )

        self_heal_note = ""
        if attempt_errors:
            if response.exit_code == 0:
                self_heal_note = (
                    f"[self-heal: succeeded after {attempt} automatic fix attempt(s)]"
                )
            else:
                self_heal_note = (
                    f"[self-heal: {attempt} automatic fix attempt(s) made, "
                    f"all failed]"
                )

        return response, self_heal_note

    def emit_start(self, placement: Placement) -> None:
        """Emit start packet for this tool. Code will be emitted in run() method."""
        # Note: PythonToolStart requires code, but we don't have it in emit_start
        # The code is available in run() method via llm_kwargs
        # We'll emit the start packet in run() instead

    def run(
        self,
        placement: Placement,
        override_kwargs: PythonToolOverrideKwargs,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """
        Execute Python code in the Code Interpreter service.

        Args:
            placement: The placement info (turn_index and tab_index) for this tool call.
            override_kwargs: Contains chat_files to stage for execution
            **llm_kwargs: Contains 'code' parameter from LLM

        Returns:
            ToolResponse with execution results
        """
        if CODE_FIELD not in llm_kwargs:
            raise ToolCallException(
                message=f"Missing required '{CODE_FIELD}' parameter in python tool call",
                llm_facing_message=(
                    f"The python tool requires a '{CODE_FIELD}' parameter containing "
                    f"the Python code to execute. Please provide like: "
                    f'{{"code": "print(\'Hello, world!\')"}}'
                ),
            )
        code = cast(str, llm_kwargs[CODE_FIELD])
        chat_files = override_kwargs.chat_files if override_kwargs else []
        session_id = override_kwargs.session_id if override_kwargs else None

        # Use cached session_id from a previous call in this message,
        # falling back to what was passed via override_kwargs
        if self._session_id:
            session_id = self._session_id

        # Emit start event with the code
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=PythonToolStart(code=code),
            )
        )

        # Create Code Interpreter client
        client = CodeInterpreterClient()

        # Lazy session creation: if no session yet and we have a chat context,
        # create a persistent sandbox and save it to the DB
        if session_id is None and self._chat_session_id:
            session_id = self._create_and_persist_session(client)

        # Stage chat files for execution
        files_to_stage: list[FileInput] = []
        for ind, chat_file in enumerate(chat_files):
            file_name = chat_file.filename or f"file_{ind}"
            try:
                # Upload to Code Interpreter
                ci_file_id = client.upload_file(chat_file.content, file_name)

                # Stage for execution
                files_to_stage.append({"path": file_name, "file_id": ci_file_id})

                logger.info(f"Staged file for Python execution: {file_name}")

            except Exception as e:
                logger.warning(f"Failed to stage file {file_name}: {e}")

        # Wall-clock budget for the whole run so we never get abandoned by the
        # threadpool timeout in tool_runner without emitting a terminal packet.
        deadline = time.monotonic() + SELF_HEAL_TOTAL_DEADLINE_SECONDS

        try:
            logger.debug(f"Executing code: {code}")

            # Execute code, repairing and re-running it via the LLM on failure
            # (self-heal). Connection/session failures are still retried inside
            # _execute_with_retry; this adds code-error repair on top.
            response, self_heal_note = self._execute_with_self_heal(
                client=client,
                placement=placement,
                code=code,
                files=files_to_stage or None,
                session_id=session_id,
                deadline=deadline,
            )

            # Truncate output for LLM consumption
            truncated_stdout = _truncate_output(
                response.stdout, CODE_INTERPRETER_MAX_OUTPUT_LENGTH, "stdout"
            )
            truncated_stderr = _truncate_output(
                response.stderr, CODE_INTERPRETER_MAX_OUTPUT_LENGTH, "stderr"
            )

            # Handle generated files
            generated_files: list[PythonExecutionFile] = []
            generated_file_ids: list[str] = []
            file_ids_to_cleanup: list[str] = []
            file_store = get_default_file_store()

            for workspace_file in response.files:
                if workspace_file.kind != "file" or not workspace_file.file_id:
                    continue

                try:
                    # Download file from Code Interpreter
                    file_content = client.download_file(workspace_file.file_id)

                    # Determine MIME type from file extension
                    filename = workspace_file.path.split("/")[-1]
                    mime_type, _ = mimetypes.guess_type(filename)
                    # Default to binary if we can't determine the type
                    mime_type = mime_type or "application/octet-stream"

                    # Save to Onyx file store
                    onyx_file_id = file_store.save_file(
                        content=BytesIO(file_content),
                        display_name=filename,
                        file_origin=FileOrigin.CHAT_UPLOAD,
                        file_type=mime_type,
                    )

                    generated_files.append(
                        PythonExecutionFile(
                            filename=filename,
                            file_link=build_full_frontend_file_url(onyx_file_id),
                        )
                    )
                    generated_file_ids.append(onyx_file_id)

                    # Mark for cleanup
                    file_ids_to_cleanup.append(workspace_file.file_id)

                except Exception as e:
                    logger.error(
                        f"Failed to handle generated file {workspace_file.path}: {e}"
                    )

            # Cleanup Code Interpreter files (skip when in session mode — files persist)
            if not session_id:
                for ci_file_id in file_ids_to_cleanup:
                    try:
                        client.delete_file(ci_file_id)
                    except Exception as e:
                        logger.error(
                            f"Failed to delete Code Interpreter generated file {ci_file_id}: {e}"
                        )

                # Cleanup staged input files
                for file_mapping in files_to_stage:
                    try:
                        client.delete_file(file_mapping["file_id"])
                    except Exception as e:
                        logger.error(
                            f"Failed to delete Code Interpreter staged file {file_mapping['file_id']}: {e}"
                        )

            # Build enriched file metadata for frontend rendering
            python_tool_files = [
                PythonToolFile(
                    file_id=file_id,
                    filename=gen_file.filename,
                )
                for file_id, gen_file in zip(generated_file_ids, generated_files)
            ]

            succeeded = response.exit_code == 0

            # Terminal delta for the UI: program stdout/stderr already streamed live
            # (one delta per chunk), so re-sending it here would double-render. Carry
            # ONLY the self-heal note (never streamed) + files + status/elapsed metadata.
            note_stdout = self_heal_note if (self_heal_note and succeeded) else ""
            note_stderr = self_heal_note if (self_heal_note and not succeeded) else ""
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=PythonToolDelta(
                        stdout=note_stdout,
                        stderr=note_stderr,
                        file_ids=generated_file_ids,
                        files=python_tool_files,
                        exit_code=response.exit_code,
                        timed_out=response.timed_out,
                        duration_ms=response.duration_ms,
                        error_kind=response.error_kind,
                    ),
                )
            )

            # For the LLM-facing result, fold the note into the FULL aggregated output
            # (the model should see everything, including that automatic repair ran).
            if self_heal_note:
                if succeeded:
                    truncated_stdout = (
                        f"{self_heal_note}\n{truncated_stdout}"
                        if truncated_stdout
                        else self_heal_note
                    )
                else:
                    truncated_stderr = (
                        f"{truncated_stderr}\n{self_heal_note}"
                        if truncated_stderr
                        else self_heal_note
                    )

            # Build result
            result = LlmPythonExecutionResult(
                stdout=truncated_stdout,
                stderr=truncated_stderr,
                exit_code=response.exit_code,
                timed_out=response.timed_out,
                generated_files=generated_files,
                error=None if succeeded else truncated_stderr,
            )

            # Serialize result for LLM
            adapter = TypeAdapter(LlmPythonExecutionResult)
            llm_response = adapter.dump_json(result).decode()

            return ToolResponse(
                rich_response=None,  # No rich response needed for Python tool
                llm_facing_response=llm_response,
            )

        except Exception as e:
            logger.error(f"Python execution failed: {e}")

            # Sanitize error messages — don't expose internal URLs to user/LLM
            raw_msg = str(e)
            if self._is_retriable_error(e):
                error_msg = (
                    "Code execution failed: the code interpreter service is "
                    "temporarily unavailable. Please try again in a moment."
                )
            else:
                error_msg = raw_msg

            # Emit error delta (terminal): exit_code drives the failed status in the UI.
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=PythonToolDelta(
                        stdout="",
                        stderr=error_msg,
                        file_ids=[],
                        exit_code=-1,
                    ),
                )
            )

            # Return error result
            result = LlmPythonExecutionResult(
                stdout="",
                stderr=error_msg,
                exit_code=-1,
                timed_out=False,
                generated_files=[],
                error=error_msg,
            )

            adapter = TypeAdapter(LlmPythonExecutionResult)
            llm_response = adapter.dump_json(result).decode()

            return ToolResponse(
                rich_response=None,
                llm_facing_response=llm_response,
            )
