"""Live streaming tests for persistent sessions (A2).

Verifies the session branch of ``POST /v1/execute/stream``: output arrives as
multiple ``output`` SSE frames *before* the terminal ``result`` frame, state
persists across streamed cells, and errors/timeouts are reported on the result
frame (not by stderr presence).

Runs against a live code-interpreter service (auto-skipped otherwise via the
module-level ``pytestmark`` in conftest).
"""

from __future__ import annotations

import json
from typing import Any

import requests

from .conftest import BASE_URL


def _stream_cell(
    api: requests.Session,
    session_id: str,
    code: str,
    timeout_ms: int = 15_000,
) -> list[dict[str, Any]]:
    """POST a streamed cell and return the parsed list of {event, data} frames."""
    events: list[dict[str, Any]] = []
    event: str | None = None
    data: str | None = None
    with api.post(
        f"{BASE_URL}/v1/execute/stream",
        json={"code": code, "timeout_ms": timeout_ms, "session_id": session_id},
        stream=True,
        timeout=timeout_ms / 1000 + 30,
    ) as resp:
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
        assert "text/event-stream" in resp.headers.get("content-type", "")
        for line in resp.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
            elif line == "":
                if event is not None and data is not None:
                    events.append({"event": event, "data": json.loads(data)})
                event = None
                data = None
    return events


def _outputs(events: list[dict[str, Any]], stream: str) -> str:
    return "".join(
        e["data"]["data"]
        for e in events
        if e["event"] == "output" and e["data"]["stream"] == stream
    )


def _result(events: list[dict[str, Any]]) -> dict[str, Any]:
    results = [e["data"] for e in events if e["event"] == "result"]
    assert len(results) == 1, f"expected exactly one result frame, got {len(results)}"
    return results[0]


def test_session_stream_multiple_output_frames(
    api: requests.Session, session_id: str
) -> None:
    """A loop of prints yields several output frames, then one result frame."""
    events = _stream_cell(
        api,
        session_id,
        "import sys, time\n"
        "for i in range(5):\n"
        "    print(i); sys.stdout.flush(); time.sleep(0.02)",
    )
    output_frames = [e for e in events if e["event"] == "output"]
    # Liveness: more than one output frame arrived (not one blob at the end).
    assert len(output_frames) >= 2, f"expected streamed frames, got {len(output_frames)}"
    # Ordering: the result frame is last.
    assert events[-1]["event"] == "result"
    result = _result(events)
    assert result["exit_code"] == 0 and result["timed_out"] is False
    # Each line appears exactly once across the frames.
    assert _outputs(events, "stdout") == "0\n1\n2\n3\n4\n"


def test_session_stream_state_persists(
    api: requests.Session, session_id: str
) -> None:
    """Variables set in one streamed cell survive into the next."""
    _stream_cell(api, session_id, "acc = 0")
    _stream_cell(api, session_id, "acc += 42")
    events = _stream_cell(api, session_id, "print(acc)")
    assert _outputs(events, "stdout") == "42\n"
    assert _result(events)["exit_code"] == 0


def test_session_stream_error_reports_nonzero_exit(
    api: requests.Session, session_id: str
) -> None:
    """A raising cell streams the traceback on stderr and reports exit_code != 0."""
    events = _stream_cell(api, session_id, "raise ValueError('boom')")
    assert "ValueError" in _outputs(events, "stderr")
    result = _result(events)
    assert result["exit_code"] not in (0, None)
    # Session survives the error: a following cell still runs.
    ok = _stream_cell(api, session_id, "print('alive')")
    assert _outputs(ok, "stdout") == "alive\n"


def test_session_stream_timeout(api: requests.Session, session_id: str) -> None:
    """A cell exceeding its timeout reports timed_out and the kernel recovers."""
    events = _stream_cell(
        api, session_id, "while True:\n    pass", timeout_ms=1500
    )
    result = _result(events)
    assert result["timed_out"] is True
    assert result["error_kind"] in (None, "timeout")
    # Kernel restarted → session usable again.
    ok = _stream_cell(api, session_id, "print('recovered')")
    assert _outputs(ok, "stdout") == "recovered\n"


def test_session_stream_captures_figure(
    api: requests.Session, session_id: str
) -> None:
    """A1 auto-capture flows through streaming: a chart with no savefig is returned."""
    events = _stream_cell(
        api,
        session_id,
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1, 2, 3])\n"
        "print('plotted')",
    )
    result = _result(events)
    assert result["exit_code"] == 0
    paths = [f["path"] for f in result["files"]]
    assert any(p.startswith("figure_") and p.endswith(".png") for p in paths), paths


def test_session_stream_unknown_session_404(api: requests.Session) -> None:
    """Streaming against a missing session is a pre-stream 404."""
    resp = api.post(
        f"{BASE_URL}/v1/execute/stream",
        json={"code": "print(1)", "timeout_ms": 5000, "session_id": "does-not-exist"},
    )
    assert resp.status_code == 404
