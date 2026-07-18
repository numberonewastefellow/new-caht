from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol


def wrap_last_line_interactive(code: str) -> str:
    """
    Wrap user code to execute in last-line-interactive mode.

    This uses Python's 'single' compilation mode for the last expression only,
    which automatically prints the value to stdout, mimicking Jupyter notebook behavior.
    Only the last line is affected; earlier expressions are not printed.

    Args:
        code: The Python code to wrap

    Returns:
        Wrapped Python code that will print the last expression's value if it's a bare expression
    """
    # Escape the code string for embedding in Python source
    code_escaped = code.replace("\\", "\\\\").replace("'", "\\'")

    wrapper = f"""import ast
import sys

# User code
code = '''{code_escaped}'''

# Parse the code
tree = ast.parse(code)

# Execute all statements except the last one normally
if len(tree.body) > 0:
    for node in tree.body[:-1]:
        code_obj = compile(ast.Module(body=[node], type_ignores=[]), '<stdin>', 'exec')
        exec(code_obj)

    # For the last statement, check if it's an expression
    last_node = tree.body[-1]
    if isinstance(last_node, ast.Expr):
        # Execute in 'single' mode to print the result
        interactive = ast.Interactive(body=[last_node])
        ast.fix_missing_locations(interactive)
        code_obj = compile(interactive, '<stdin>', 'single')
        exec(code_obj)
    else:
        # Not an expression, execute normally
        code_obj = compile(ast.Module(body=[last_node], type_ignores=[]), '<stdin>', 'exec')
        exec(code_obj)
"""
    return wrapper


# Prologue prepended to every ephemeral __main__.py. It registers an atexit hook
# that writes any matplotlib figures the user code left open to the workspace, so
# charts are captured even when the user forgot ``plt.savefig`` / used ``plt.show()``.
# It is registered BEFORE user code (not appended) so it still fires if the cell
# raises — atexit runs on interpreter shutdown, including after an unhandled
# exception. It is a no-op unless matplotlib.pyplot was actually imported, and it
# never imports pyplot itself. Names are ``_onyx_``-prefixed to avoid clobbering
# user globals (safe here: the ephemeral process is single-use and thrown away).
FIGURE_CAPTURE_PROLOGUE = """\
import atexit as _onyx_atexit
import sys as _onyx_sys


def _onyx_capture_open_figures():
    plt = _onyx_sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return
    try:
        fignums = list(plt.get_fignums())
    except Exception:
        return
    _n = 0
    for _num in fignums:
        try:
            _fig = plt.figure(_num)
            _n += 1
            _fig.savefig("/workspace/figure_%d.png" % _n, dpi=150, bbox_inches="tight")
            plt.close(_fig)
        except Exception:
            continue


_onyx_atexit.register(_onyx_capture_open_figures)
"""


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    files: tuple[WorkspaceEntry, ...]


class EntryKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    path: str
    kind: EntryKind
    content: bytes | None = None


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """A chunk of output from the execution."""

    stream: Literal["stdout", "stderr"]
    data: str


@dataclass(frozen=True, slots=True)
class StreamResult:
    """Final execution result emitted at end of stream."""

    exit_code: int | None
    timed_out: bool
    duration_ms: int
    files: tuple[WorkspaceEntry, ...]
    # Distinguishes non-timeout failure modes so the UI can label them precisely
    # (kernel OOM-killed, kernel crashed, session reaped). None on a clean result.
    error_kind: str | None = None


StreamEvent = StreamChunk | StreamResult


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """Result of an executor health check."""

    status: Literal["ok", "error"]
    message: str | None = None


class ExecutorProtocol(Protocol):
    def execute_python(
        self,
        *,
        code: str,
        stdin: str | None,
        timeout_ms: int,
        max_output_bytes: int,
        cpu_time_limit_sec: int | None = None,
        memory_limit_mb: int | None = None,
        files: Sequence[tuple[str, bytes]] | None = None,
        last_line_interactive: bool = True,
    ) -> ExecutionResult: ...


class BaseExecutor(ABC):
    def check_health(self) -> HealthCheck:
        """Check if the executor backend is operational.

        Default implementation returns ok. Override for backend-specific checks.
        """
        return HealthCheck(status="ok")

    @abstractmethod
    def execute_python(
        self,
        *,
        code: str,
        stdin: str | None,
        timeout_ms: int,
        max_output_bytes: int,
        cpu_time_limit_sec: int | None = None,
        memory_limit_mb: int | None = None,
        files: Sequence[tuple[str, bytes]] | None = None,
        last_line_interactive: bool = True,
    ) -> ExecutionResult:
        """Execute Python code in an isolated environment.

        Args:
            last_line_interactive: If True, the last line will print its value to stdout
                                   if it's a bare expression (only the last line is affected).
        """

    def execute_python_streaming(
        self,
        *,
        code: str,
        stdin: str | None,
        timeout_ms: int,
        max_output_bytes: int,
        cpu_time_limit_sec: int | None = None,
        memory_limit_mb: int | None = None,
        files: Sequence[tuple[str, bytes]] | None = None,
        last_line_interactive: bool = True,
    ) -> Generator[StreamEvent, None, None]:
        """Execute Python code and yield output chunks as they arrive.

        Yields StreamChunk events during execution, then a single StreamResult
        at the end. Default implementation raises NotImplementedError.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support streaming execution")

    @staticmethod
    def truncate_output(stream: bytes, max_bytes: int) -> str:
        if len(stream) <= max_bytes:
            return stream.decode("utf-8", errors="replace")
        head = stream[: max(0, max_bytes - 32)]
        suffix = b"\n...[truncated]"
        return (head + suffix).decode("utf-8", errors="replace")
