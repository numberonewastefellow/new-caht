"""Unit tests for the code node harness: build, run (subprocess), parse, validate."""

import subprocess
import sys
from typing import Any

import pytest

from om.workflows.nodes.code_harness import build_harness
from om.workflows.nodes.code_harness import HarnessOutputError
from om.workflows.nodes.code_harness import HarnessResult
from om.workflows.nodes.code_harness import MAX_LOG_CHARS
from om.workflows.nodes.code_harness import new_nonce
from om.workflows.nodes.code_harness import OutputValidationError
from om.workflows.nodes.code_harness import parse_harness_output
from om.workflows.nodes.code_harness import validate_outputs


def _run(code: str, inputs: dict[str, Any] | None = None) -> tuple[HarnessResult, str]:
    """Execute the harness the way the code interpreter would: a fresh python."""
    nonce = new_nonce()
    proc = subprocess.run(
        [sys.executable, "-c", build_harness(code, inputs or {}, nonce)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return parse_harness_output(proc.stdout, nonce), proc.stdout


class TestHarnessRun:
    def test_returns_result_and_captures_prints(self) -> None:
        result, stdout = _run(
            "def main(inputs):\n    print('working on', inputs['n'])\n"
            "    return {'double': inputs['n'] * 2}\n",
            {"n": 21},
        )
        assert result.ok is True
        assert result.result == {"double": 42}
        assert result.logs == "working on 21\n"
        assert "working on" not in stdout.split("\x00")[0]  # prints never reach stdout

    def test_exception_is_reported_with_trace(self) -> None:
        result, _ = _run("def main(inputs):\n    raise ValueError('bad input')\n")
        assert result.ok is False
        assert result.error_type == "ValueError"
        assert result.error_message == "bad input"
        assert result.trace is not None and "<user_code>" in result.trace

    def test_missing_main(self) -> None:
        result, _ = _run("x = 1\n")
        assert result.ok is False
        assert result.error_type == "TypeError"
        assert "main(inputs)" in (result.error_message or "")

    def test_system_exit_is_caught(self) -> None:
        result, _ = _run("import sys\ndef main(inputs):\n    sys.exit(3)\n")
        assert result.ok is False
        assert result.error_type == "SystemExit"

    @pytest.mark.parametrize("value", ["{1, 2}", "float('nan')", "object()"])
    def test_non_json_result_is_rejected_inside_the_harness(self, value: str) -> None:
        result, _ = _run(f"def main(inputs):\n    return {{'x': {value}}}\n")
        assert result.ok is False
        assert result.error_type == "InvalidOutput"

    def test_template_breaking_source_is_harmless(self) -> None:
        code = (
            "s = '\\'\\'\\' {} {{ }} \\x00OMRES:'\n"
            "def main(inputs):\n    return {'s': s}\n"
        )
        result, _ = _run(code)
        assert result.ok is True
        assert result.result["s"].startswith("''' {} {{ }}")

    def test_logs_are_capped(self) -> None:
        result, _ = _run(
            f"def main(inputs):\n    print('x' * {MAX_LOG_CHARS * 2})\n    return {{}}\n"
        )
        assert len(result.logs) == MAX_LOG_CHARS

    def test_forged_frame_with_another_nonce_is_ignored(self) -> None:
        code = (
            "import os\n"
            "def main(inputs):\n"
            "    os.write(1, b'\\x00OMRES:deadbeef:9\\x00{\"ok\":1}')\n"
            "    return {'real': True}\n"
        )
        result, _ = _run(code)
        assert result.result == {"real": True}


class TestParse:
    def test_no_frame(self) -> None:
        with pytest.raises(HarnessOutputError, match="no result"):
            parse_harness_output("hello", "n1")

    def test_two_frames_for_the_same_nonce(self) -> None:
        frame = '\x00OMRES:n1:11\x00{"ok":true}'
        with pytest.raises(HarnessOutputError, match="more than one"):
            parse_harness_output(frame + frame, "n1")

    def test_truncated_frame(self) -> None:
        with pytest.raises(HarnessOutputError, match="truncated"):
            parse_harness_output('\x00OMRES:n1:50\x00{"ok":true}', "n1")

    def test_oversized_frame(self) -> None:
        with pytest.raises(HarnessOutputError, match="too large"):
            parse_harness_output("\x00OMRES:n1:99999999\x00{}", "n1")

    def test_malformed_frame(self) -> None:
        with pytest.raises(HarnessOutputError, match="malformed"):
            parse_harness_output('\x00OMRES:n1:7\x00{"a":1}', "n1")


class TestValidateOutputs:
    def test_valid(self) -> None:
        result = {"title": "x", "count": 3, "ratio": 0.5, "ok": True, "tags": ["a"], "meta": {}}
        declared = {
            "title": "string", "count": "integer", "ratio": "number",
            "ok": "boolean", "tags": "array", "meta": "object",
        }
        assert validate_outputs(result, declared) == result  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("result", "declared", "message"),
        [
            ([1], {"a": "string"}, "must return a dict"),
            ({}, {"a": "string"}, "Missing outputs: a"),
            ({"a": "x", "b": 1}, {"a": "string"}, "Undeclared outputs: b"),
            ({"a": 1}, {"a": "string"}, "must be string"),
            ({"a": True}, {"a": "number"}, "must be number"),  # bool is not a number
            ({"a": 1.5}, {"a": "integer"}, "must be integer"),
            ({"a": "x" * 100_001}, {"a": "string"}, "too long"),
            ({"a": list(range(1001))}, {"a": "array"}, "too many items"),
            ({"a": [{}] * 101}, {"a": "array"}, "too many items"),
            ({"a": 2**60}, {"a": "integer"}, "too large an integer"),
            ({"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}, {"a": "object"}, "nested too deeply"),
            ({"a": {1: "x"}}, {"a": "object"}, "non-string key"),
        ],
    )
    def test_invalid(self, result: Any, declared: Any, message: str) -> None:
        with pytest.raises(OutputValidationError, match=message):
            validate_outputs(result, declared)
