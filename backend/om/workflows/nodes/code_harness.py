"""Run a code node's ``main(inputs) -> dict`` in the code interpreter, safely.

Three pure steps (no I/O here, so they are fully unit-testable):

1. ``build_harness`` wraps the user's source in a small Python program. The
   source travels base64-encoded and is compiled under ``<user_code>``, so it
   can never break out of the template. Before the user's code runs, the
   harness saves the real stdout and redirects ``print`` into a capped log
   buffer; the result is written as exactly one frame tagged with a per-run
   random nonce.
2. ``parse_harness_output`` accepts exactly one well-formed frame for that
   nonce. The nonce prevents accidental collisions (inputs or logs containing
   a marker) and cross-run confusion. It is not a security boundary: user code
   shares the process and could forge its own result.
3. ``validate_outputs`` is the trust boundary: the result must be a dict whose
   keys equal the declared outputs, with the declared types and within size
   and depth limits. Anything else fails the node.
"""

from __future__ import annotations

import base64
import json
import math
import re
import secrets
from dataclasses import dataclass
from typing import Any
from typing import Literal

OutputType = Literal["string", "number", "integer", "boolean", "object", "array"]

# Limits on what a code node may return.
MAX_RESULT_BYTES = 1_000_000
MAX_DEPTH = 5
MAX_STRING_CHARS = 100_000
MAX_ARRAY_ITEMS = 1_000
MAX_OBJECT_ARRAY_ITEMS = 100
MAX_SAFE_INTEGER = 2**53

# Limits on what the harness reports back besides the result.
MAX_LOG_CHARS = 64_000
MAX_TRACE_CHARS = 8_000


class HarnessOutputError(ValueError):
    """The harness output is missing, malformed, or ambiguous."""


class OutputValidationError(ValueError):
    """The returned value does not match the node's declared outputs."""


@dataclass(frozen=True)
class HarnessResult:
    """What the user's code produced, as reported by the harness frame."""

    ok: bool
    result: Any = None
    logs: str = ""
    # Set when ok is False
    error_type: str | None = None
    error_message: str | None = None
    trace: str | None = None


def new_nonce() -> str:
    return secrets.token_hex(16)


_FRAME_PREFIX = "\x00OMRES:"


def build_harness(code: str, inputs: dict[str, Any], nonce: str) -> str:
    """The Python program to execute for one code node run."""
    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    inputs_b64 = base64.b64encode(
        json.dumps(inputs, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    return _HARNESS_TEMPLATE.format(
        nonce=nonce,
        code_b64=code_b64,
        inputs_b64=inputs_b64,
        max_log_chars=MAX_LOG_CHARS,
        max_trace_chars=MAX_TRACE_CHARS,
    )


# The harness itself. Kept dependency-free (stdlib only) and with "_om_" names
# so it does not collide with user globals.
_HARNESS_TEMPLATE = '''\
import base64 as _om_b64
import io as _om_io
import json as _om_json
import os as _om_os
import sys as _om_sys

_om_out = _om_os.fdopen(_om_os.dup(1), "w", encoding="utf-8")


class _OmCappedLog(_om_io.StringIO):
    def write(self, s):
        room = {max_log_chars} - self.tell()
        return super().write(s[:room]) if room > 0 else len(s)


def _om_emit(payload):
    data = _om_json.dumps(payload, allow_nan=False, ensure_ascii=False)
    _om_out.write("\\x00OMRES:{nonce}:" + str(len(data)) + "\\x00" + data)
    _om_out.flush()


_om_log = _OmCappedLog()
_om_sys.stdout = _om_log
_om_sys.stderr = _om_log


def _om_run():
    namespace = {{"__name__": "__om_user__"}}
    source = _om_b64.b64decode("{code_b64}").decode("utf-8")
    exec(compile(source, "<user_code>", "exec"), namespace)
    main = namespace.get("main")
    if not callable(main):
        raise TypeError("define a function main(inputs) that returns a dict")
    inputs = _om_json.loads(_om_b64.b64decode("{inputs_b64}").decode("utf-8"))
    return main(inputs)


try:
    _om_result = _om_run()
    try:
        _om_emit({{"ok": True, "result": _om_result, "logs": _om_log.getvalue()}})
    except (TypeError, ValueError) as _om_exc:
        _om_emit({{"ok": False, "type": "InvalidOutput",
                   "message": "main() must return JSON data: " + str(_om_exc)[:500],
                   "logs": _om_log.getvalue()}})
except BaseException as _om_exc:
    import traceback as _om_tb
    _om_emit({{"ok": False, "type": type(_om_exc).__name__,
               "message": str(_om_exc)[:2000],
               "trace": _om_tb.format_exc()[-{max_trace_chars}:],
               "logs": _om_log.getvalue()}})
'''


def parse_harness_output(stdout: str, nonce: str) -> HarnessResult:
    """Extract the single result frame for ``nonce`` from the run's stdout.

    Raises:
        HarnessOutputError: no frame, more than one frame, a length mismatch,
            an oversized frame, or invalid JSON.
    """
    marker = re.compile(re.escape(f"{_FRAME_PREFIX}{nonce}:") + r"(\d+)\x00")
    matches = list(marker.finditer(stdout))
    if not matches:
        raise HarnessOutputError("The code produced no result")
    if len(matches) > 1:
        raise HarnessOutputError("The code produced more than one result")

    match = matches[0]
    length = int(match.group(1))
    if length > MAX_RESULT_BYTES:
        raise HarnessOutputError(
            f"The result is too large (limit {MAX_RESULT_BYTES // 1000} KB)"
        )
    data = stdout[match.end() : match.end() + length]
    if len(data) != length:
        raise HarnessOutputError("The result was truncated")
    try:
        frame = json.loads(data)
    except json.JSONDecodeError as e:
        raise HarnessOutputError("The result frame is not valid JSON") from e
    if not isinstance(frame, dict) or not isinstance(frame.get("ok"), bool):
        raise HarnessOutputError("The result frame is malformed")

    if frame["ok"]:
        return HarnessResult(ok=True, result=frame.get("result"), logs=frame.get("logs", ""))
    return HarnessResult(
        ok=False,
        logs=frame.get("logs", ""),
        error_type=str(frame.get("type", "Error")),
        error_message=str(frame.get("message", "")),
        trace=frame.get("trace"),
    )


def validate_outputs(result: Any, declared: dict[str, OutputType]) -> dict[str, Any]:
    """Check ``result`` against the declared outputs; return it unchanged.

    Raises:
        OutputValidationError: wrong shape, missing/extra keys, wrong types, or
            limits exceeded.
    """
    if not isinstance(result, dict):
        raise OutputValidationError(
            f"main() must return a dict, got {type(result).__name__}"
        )
    keys = set(result)
    missing = sorted(set(declared) - keys)
    extra = sorted(keys - set(declared))
    if missing:
        raise OutputValidationError(f"Missing outputs: {', '.join(missing)}")
    if extra:
        raise OutputValidationError(f"Undeclared outputs: {', '.join(extra)}")

    for name, expected in declared.items():
        _check_type(name, result[name], expected)
        _check_limits(name, result[name], depth=1)

    size = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    if size > MAX_RESULT_BYTES:
        raise OutputValidationError(
            f"Outputs are too large ({size} bytes, limit {MAX_RESULT_BYTES})"
        )
    return result


def _check_type(name: str, value: Any, expected: OutputType) -> None:
    ok = {
        "string": isinstance(value, str),
        # bool is a subclass of int in Python; it is not a number here.
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }[expected]
    if not ok:
        raise OutputValidationError(
            f"Output '{name}' must be {expected}, got {type(value).__name__}"
        )


def _check_limits(path: str, value: Any, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise OutputValidationError(f"Output '{path}' is nested too deeply")
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise OutputValidationError(f"Output '{path}' is too long")
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise OutputValidationError(f"Output '{path}' is not a finite number")
    elif isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise OutputValidationError(f"Output '{path}' is too large an integer")
    elif isinstance(value, list):
        limit = (
            MAX_OBJECT_ARRAY_ITEMS
            if any(isinstance(v, dict) for v in value)
            else MAX_ARRAY_ITEMS
        )
        if len(value) > limit:
            raise OutputValidationError(f"Output '{path}' has too many items")
        for i, item in enumerate(value):
            _check_limits(f"{path}[{i}]", item, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise OutputValidationError(f"Output '{path}' has a non-string key")
            _check_limits(f"{path}.{key}", item, depth + 1)
