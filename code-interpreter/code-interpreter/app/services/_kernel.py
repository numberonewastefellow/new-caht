"""Persistent Python kernel for session-based code execution.

This script runs inside a python-executor-sci container and stays alive
for the duration of a session. It accepts code via stdin as JSON lines
and executes each snippet in the same globals dictionary, so variables,
imports, and DataFrames survive between calls.

Protocol (JSON lines):
  Input  (stdin):  {"code": "import pandas as pd\\ndf = pd.read_csv('data.csv')"}\\n
  Output (a dedicated protocol fd — a dup of the original stdout pipe):
    {"type":"output","stream":"stdout","data":"...","cell":N}\\n   # streamed per read
    {"type":"output","stream":"stderr","data":"...","cell":N}\\n
    {"type":"result","exit_code":0,"timed_out":false,"duration_ms":123,"cell":N}\\n

Capture is done at the OS file-descriptor level: fd 1/2 are ``dup2``'d onto
private pipes drained by pump threads, so output from subprocesses, C
extensions, and raw ``os.write`` is captured too (a Python-level
``redirect_stdout`` would miss all of those). The protocol fd is a plain
``os.dup`` of the original stdout and is O_CLOEXEC by default (PEP 446), so
user subprocesses can neither inherit it nor forge protocol frames.

The kernel catches all exceptions and keeps running. Only EOF on stdin
(pipe closed) causes the process to exit.
"""

import ast
import codecs
import contextlib
import json
import os
import sys
import threading
import time
import traceback
from typing import Any


def _exec_single_mode(code: str, user_globals: dict[str, Any]) -> None:
    """Execute code with Jupyter-like last-expression printing.

    If the last statement is a bare expression, its value is printed
    to stdout (like ``compile(..., 'single')`` mode).
    """
    tree = ast.parse(code)
    if not tree.body:
        return

    # Execute all statements except the last normally
    for node in tree.body[:-1]:
        module = ast.Module(body=[node], type_ignores=[])
        ast.fix_missing_locations(module)
        exec(compile(module, "<cell>", "exec"), user_globals)  # noqa: S102

    # For the last statement, use 'single' mode if it's a bare expression
    last_node = tree.body[-1]
    if isinstance(last_node, ast.Expr):
        interactive = ast.Interactive(body=[last_node])
        ast.fix_missing_locations(interactive)
        exec(compile(interactive, "<cell>", "single"), user_globals)  # noqa: S102
    else:
        module = ast.Module(body=[last_node], type_ignores=[])
        ast.fix_missing_locations(module)
        exec(compile(module, "<cell>", "exec"), user_globals)  # noqa: S102


# Process-monotonic counter so a figure produced in an earlier cell is never
# overwritten by a later cell (pyplot restarts its figure numbers after close()).
_figure_counter = 0


def _capture_open_figures(workspace_dir: str) -> None:
    """Persist matplotlib figures the user code left open without saving.

    Mirrors notebook behavior: any figure still open after a cell runs is written
    to the workspace so it flows through the normal file-capture path (charts show
    up even when the user forgot ``plt.savefig`` or used ``plt.show()``).

    This is a no-op unless ``matplotlib.pyplot`` has actually been imported by the
    user's code, so non-plotting cells and non-matplotlib sessions are unaffected.
    We never import pyplot ourselves.
    """
    global _figure_counter

    plt: Any = sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return

    try:
        fignums = list(plt.get_fignums())
    except Exception:
        return

    for num in fignums:
        # A single malformed figure must never break the cell's result.
        with contextlib.suppress(Exception):
            fig = plt.figure(num)
            _figure_counter += 1
            fig.savefig(
                f"{workspace_dir}/figure_{_figure_counter}.png",
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)


def main() -> None:
    # Shared globals dict — variables persist across calls
    user_globals: dict[str, Any] = {"__name__": "__main__"}

    # Per-process random nonce baked into the cell barrier marker. The marker is
    # matched IN-BAND on the user output pipe, so without a secret nonce untrusted
    # code could print the exact marker bytes and trip the barrier early. os.urandom
    # is unpredictable and never exposed to user code.
    nonce = os.urandom(8).hex().encode("ascii")

    def _marker(cell_id: int) -> bytes:
        return b"\x00\x00__CELL_%b_%d__\x00\x00" % (nonce, cell_id)

    # Dedicated protocol channel: a dup of the ORIGINAL stdout pipe. Every frame
    # (output + result) is written here under a lock. os.dup fds are O_CLOEXEC by
    # default (PEP 446), so user subprocesses cannot inherit it or forge frames.
    proto_fd = os.dup(1)
    proto_lock = threading.Lock()

    def write_frame(obj: dict[str, Any]) -> None:
        # json.dumps escapes embedded newlines, so every frame is exactly one line.
        # Loop until all bytes are written: os.write on a pipe can do a PARTIAL write
        # for buffers larger than PIPE_BUF, which would silently truncate the frame.
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with proto_lock:
            view = memoryview(data)
            while view:
                try:
                    written = os.write(proto_fd, view)
                except BlockingIOError:
                    continue
                view = view[written:]

    # Redirect OS-level fd 1/2 onto private pipes so ALL output — including from
    # subprocesses, C extensions, and raw os.write — is captured. sys.__stdout__/
    # __stderr__ keep the originals alive; we reopen line-buffered on the same fds.
    pout_r, pout_w = os.pipe()
    perr_r, perr_w = os.pipe()
    os.dup2(pout_w, 1)
    os.dup2(perr_w, 2)
    os.close(pout_w)
    os.close(perr_w)
    # newline="" → faithful byte passthrough (never translate the user's newlines).
    sys.stdout = os.fdopen(1, "w", buffering=1, encoding="utf-8", errors="replace", newline="")
    sys.stderr = os.fdopen(2, "w", buffering=1, encoding="utf-8", errors="replace", newline="")

    cell = {"id": 0}
    drained = {"stdout": threading.Event(), "stderr": threading.Event()}

    def pump(rfd: int, stream: str) -> None:
        """Frame everything written to a private pipe, up to the cell barrier."""
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        carry = b""
        while True:
            try:
                data = os.read(rfd, 65536)  # bounds one frame's size (<=64 KB)
            except OSError:
                break
            if not data:
                break
            buf = carry + data
            mk = _marker(cell["id"])
            if mk in buf:
                pre, buf = buf.split(mk, 1)
                if pre:
                    write_frame({"type": "output", "stream": stream,
                                 "data": dec.decode(pre, final=True), "cell": cell["id"]})
                # Fresh decoder per cell so a partial multibyte sequence at the barrier
                # cannot bleed into the next cell's output.
                dec = codecs.getincrementaldecoder("utf-8")("replace")
                carry = buf
                drained[stream].set()
                continue
            # Hold back the last len(mk)-1 bytes so a marker split across two reads
            # is never emitted as user data.
            keep = len(mk) - 1
            if keep and len(buf) > keep:
                emit, carry = buf[:-keep], buf[-keep:]
            elif keep:
                emit, carry = b"", buf
            else:
                emit, carry = buf, b""
            if emit:
                write_frame({"type": "output", "stream": stream,
                             "data": dec.decode(emit), "cell": cell["id"]})

    threading.Thread(target=pump, args=(pout_r, "stdout"), daemon=True).start()
    threading.Thread(target=pump, args=(perr_r, "stderr"), daemon=True).start()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        cell["id"] += 1
        drained["stdout"].clear()
        drained["stderr"].clear()

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            write_frame({"type": "result", "exit_code": 1, "timed_out": False,
                         "duration_ms": 0, "cell": cell["id"]})
            continue
        if not isinstance(request, dict):
            # Valid JSON but not an object (e.g. a bare number/string) — reject it
            # cleanly instead of letting `.get` raise and kill the kernel.
            write_frame({"type": "result", "exit_code": 1, "timed_out": False,
                         "duration_ms": 0, "cell": cell["id"]})
            continue

        code = request.get("code", "")
        exit_code = 0
        start = time.perf_counter()

        try:
            try:
                _exec_single_mode(code, user_globals)
            finally:
                # Capture any figures the user left open, even if the cell raised
                # partway through, so charts still reach the client. Runs BEFORE the
                # barrier/result so the PNGs exist on disk for the workspace snapshot.
                _capture_open_figures("/workspace")
        except SystemExit as e:
            # Match CPython's exit-status mapping: bare sys.exit()/exit() has
            # code None → success (0); an int is the status; anything else is
            # printed to stderr and treated as failure.
            if e.code is None:
                exit_code = 0
            elif isinstance(e.code, int):
                exit_code = e.code
            else:
                print(e.code, file=sys.stderr)
                exit_code = 1
        except Exception:
            traceback.print_exc(file=sys.stderr)
            exit_code = 1

        # Barrier: flush this cell's buffered output, then write the marker to both
        # pipes and wait for the pumps to confirm they've framed everything up to it.
        # This guarantees the result frame is ordered AFTER all of the cell's output,
        # and that stray output from user daemon threads is tagged with THIS cell id
        # (the next cell's reader expects a higher id and drops it).
        with contextlib.suppress(Exception):
            sys.stdout.flush()
            sys.stderr.flush()
        mk = _marker(cell["id"])
        with contextlib.suppress(OSError):
            os.write(1, mk)
        with contextlib.suppress(OSError):
            os.write(2, mk)
        # Wait for BOTH pumps to confirm they have framed all output up to the marker
        # so the result frame is always ordered after the cell's output. The marker is
        # nonce-protected, so `drained` can only be set by the genuine barrier — loop up
        # to a generous bound rather than trusting a single 0.5s wait (a truly wedged
        # pump is the only way this times out, and the reader's own deadline reaps it).
        barrier_deadline = time.monotonic() + 10.0
        for _stream_name in ("stdout", "stderr"):
            while (
                not drained[_stream_name].is_set()
                and time.monotonic() < barrier_deadline
            ):
                drained[_stream_name].wait(timeout=0.1)

        write_frame({"type": "result", "exit_code": exit_code, "timed_out": False,
                     "duration_ms": int((time.perf_counter() - start) * 1000),
                     "cell": cell["id"]})


if __name__ == "__main__":
    main()
