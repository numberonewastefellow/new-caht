"""Persistent Python kernel for session-based code execution.

This script runs inside a python-executor-sci container and stays alive
for the duration of a session. It accepts code via stdin as JSON lines
and executes each snippet in the same globals dictionary, so variables,
imports, and DataFrames survive between calls.

Protocol (JSON lines over stdin/stdout):
  Input:  {"code": "import pandas as pd\\ndf = pd.read_csv('data.csv')"}
  Output: {"stdout": "...", "stderr": "...", "exit_code": 0, "duration_ms": 123}

The kernel catches all exceptions and keeps running.  Only EOF on stdin
(pipe closed) causes the process to exit.
"""

import ast
import contextlib
import io
import json
import sys
import time
import traceback


def _exec_single_mode(code: str, user_globals: dict) -> None:
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


def main() -> None:
    # Shared globals dict — variables persist across calls
    user_globals: dict = {"__name__": "__main__"}

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "stdout": "",
                "stderr": f"Invalid JSON: {line[:200]}",
                "exit_code": 1,
                "duration_ms": 0,
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        code = request.get("code", "")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        exit_code = 0
        start = time.perf_counter()

        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                _exec_single_mode(code, user_globals)
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
        except Exception:
            traceback.print_exc(file=stderr_buf)
            exit_code = 1

        duration_ms = int((time.perf_counter() - start) * 1000)

        response = {
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
