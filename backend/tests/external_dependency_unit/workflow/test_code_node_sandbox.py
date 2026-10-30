"""Code node against a real (hardened) code-interpreter sandbox.

Runs only when CODE_INTERPRETER_BASE_URL (and CODE_INTERPRETER_API_TOKEN) point
at a running code-interpreter. Exercises the full path: harness -> sandbox ->
frame -> validation, plus the sandbox's isolation guarantees as seen by a code
step (no network, read-only filesystem, time limit).
"""

import pytest

from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
from om.workflows.nodes.code import CodeNodeConfigV1
from om.workflows.nodes.code import CodeNodeError
from om.workflows.nodes.code import execute_code

pytestmark = pytest.mark.skipif(
    not CODE_INTERPRETER_BASE_URL, reason="needs a running code-interpreter"
)


def _run(code: str, outputs: list[dict[str, str]], inputs: dict | None = None, **kw: object) -> dict:
    config = CodeNodeConfigV1(code=code, outputs=outputs, **kw)  # type: ignore[arg-type]
    return execute_code(config, inputs or {})


def test_round_trip_with_typed_outputs() -> None:
    result = _run(
        "import statistics\n"
        "def main(inputs):\n"
        "    print('logs never mix with the result')\n"
        "    xs = inputs['xs']\n"
        "    return {'mean': statistics.mean(xs), 'n': len(xs), 'label': 'ok'}\n",
        [{"name": "mean", "type": "number"}, {"name": "n", "type": "integer"},
         {"name": "label", "type": "string"}],
        {"xs": [1, 2, 3, 4]},
    )
    assert result == {"mean": 2.5, "n": 4, "label": "ok"}


def test_scientific_packages_available() -> None:
    result = _run(
        "import numpy as np\ndef main(inputs):\n    return {'s': int(np.arange(5).sum())}\n",
        [{"name": "s", "type": "integer"}],
    )
    assert result == {"s": 10}


def test_network_is_blocked() -> None:
    code = (
        "import socket\n"
        "def main(inputs):\n"
        "    socket.create_connection(('1.1.1.1', 80), timeout=3)\n"
        "    return {'x': 'connected'}\n"
    )
    with pytest.raises(CodeNodeError, match="OSError|gaierror|timeout|unreachable"):
        _run(code, [{"name": "x", "type": "string"}])


def test_root_filesystem_is_read_only() -> None:
    code = "def main(inputs):\n    open('/etc/x', 'w').write('x')\n    return {}\n"
    with pytest.raises(CodeNodeError, match="OSError|PermissionError|Read-only"):
        _run(code, [{"name": "x", "type": "string"}])


def test_time_limit() -> None:
    code = "import time\ndef main(inputs):\n    time.sleep(10)\n    return {'x': 'late'}\n"
    with pytest.raises(CodeNodeError, match="timed out"):
        _run(code, [{"name": "x", "type": "string"}], timeout_seconds=2)


def test_forged_frame_cannot_replace_the_result() -> None:
    code = (
        "import os\n"
        "def main(inputs):\n"
        "    os.write(1, b'\\x00OMRES:0000:9\\x00{\"ok\":1}')\n"
        "    return {'x': 'real'}\n"
    )
    assert _run(code, [{"name": "x", "type": "string"}]) == {"x": "real"}


def test_undeclared_output_rejected() -> None:
    with pytest.raises(CodeNodeError, match="Undeclared outputs: extra"):
        _run(
            "def main(inputs):\n    return {'x': 1, 'extra': 2}\n",
            [{"name": "x", "type": "integer"}],
        )
