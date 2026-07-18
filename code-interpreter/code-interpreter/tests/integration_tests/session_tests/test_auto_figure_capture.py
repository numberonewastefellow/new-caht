"""Tests for automatic matplotlib figure capture (A1).

Charts should reach the client even when user code never calls ``plt.savefig``
(e.g. it uses ``plt.show()`` or just builds a figure), matching ChatGPT/Gemini
behavior. Any figure still open when a cell finishes is auto-saved to the
workspace as ``figure_N.png`` with a process-monotonic counter.

These run against a live code-interpreter service (auto-skipped otherwise via
the module-level ``pytestmark`` in conftest).
"""

from __future__ import annotations

import re

import requests

from .conftest import (
    BASE_URL,
    execute_ephemeral,
    execute_in_session,
)

_FIGURE_RE = re.compile(r"^figure_\d+\.png$")


def _figure_files(files: list[dict]) -> list[str]:
    return sorted(f["path"] for f in files if _FIGURE_RE.match(f["path"]))


def _find_file(files: list[dict], path: str) -> dict | None:
    return next((f for f in files if f["path"] == path), None)


def _assert_valid_png(api: requests.Session, file_id: str) -> None:
    dl = api.get(f"{BASE_URL}/v1/files/{file_id}")
    assert dl.status_code == 200
    assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(dl.content) > 500


# ------------------------------------------------------------------
# Capture without an explicit savefig
# ------------------------------------------------------------------


def test_capture_without_savefig(api: requests.Session, session_id: str) -> None:
    """A plot with no savefig is still captured as figure_1.png."""
    r = execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "plt.plot([1, 2, 3], [4, 5, 6])\n"
            "plt.title('No Savefig')\n"
            "print('done')"
        ),
    )
    assert r["exit_code"] == 0
    assert r["stdout"] == "done\n"

    figs = _figure_files(r["files"])
    assert figs == ["figure_1.png"], f"expected auto-captured figure, got {r['files']}"
    fig = _find_file(r["files"], "figure_1.png")
    assert fig is not None and fig["file_id"] is not None
    _assert_valid_png(api, fig["file_id"])


def test_capture_with_plt_show(api: requests.Session, session_id: str) -> None:
    """plt.show() (a no-op under Agg) still leaves the figure open -> captured."""
    r = execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "plt.bar(['a', 'b'], [1, 2])\n"
            "plt.show()\n"
            "print('shown')"
        ),
    )
    assert r["exit_code"] == 0
    assert _figure_files(r["files"]) == ["figure_1.png"]


# ------------------------------------------------------------------
# Monotonic counter across cells in the same session
# ------------------------------------------------------------------


def test_capture_monotonic_across_calls(
    api: requests.Session, session_id: str
) -> None:
    """Successive cells produce figure_1, figure_2 (counter never resets/collides)."""
    execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
        ),
    )

    r1 = execute_in_session(
        api, session_id, "plt.plot([1, 2, 3])\nprint('c1')"
    )
    assert _figure_files(r1["files"]) == ["figure_1.png"]

    r2 = execute_in_session(
        api, session_id, "plt.plot([3, 2, 1])\nprint('c2')"
    )
    # Second cell's figure must NOT overwrite the first: it is figure_2.
    assert _figure_files(r2["files"]) == ["figure_2.png"]


# ------------------------------------------------------------------
# No-op paths (must not invent files)
# ------------------------------------------------------------------


def test_no_capture_without_matplotlib(
    api: requests.Session, session_id: str
) -> None:
    """A non-plotting cell produces no figure_*.png artifacts."""
    r = execute_in_session(api, session_id, "print(sum(range(10)))")
    assert r["exit_code"] == 0
    assert r["stdout"] == "45\n"
    assert _figure_files(r["files"]) == []


def test_no_phantom_capture_after_close(
    api: requests.Session, session_id: str
) -> None:
    """If the user saves and closes explicitly, we do not add a phantom figure."""
    r = execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "plt.plot([1, 2, 3])\n"
            "plt.savefig('mine.png', dpi=80)\n"
            "plt.close()\n"
            "print('saved')"
        ),
    )
    assert r["exit_code"] == 0
    assert _find_file(r["files"], "mine.png") is not None
    # Nothing left open at end of cell -> no auto-captured figure_*.png.
    assert _figure_files(r["files"]) == []


def test_capture_on_error(api: requests.Session, session_id: str) -> None:
    """A figure built before an exception is still captured (atexit/finally path)."""
    r = execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "plt.plot([1, 2, 3])\n"
            "raise ValueError('boom')"
        ),
    )
    assert r["exit_code"] == 1
    assert "ValueError" in r["stderr"]
    assert _figure_files(r["files"]) == ["figure_1.png"]


# ------------------------------------------------------------------
# Ephemeral (no session) path
# ------------------------------------------------------------------


def test_capture_ephemeral(api: requests.Session) -> None:
    """The ephemeral prologue captures an open figure with no savefig."""
    r = execute_ephemeral(
        api,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "plt.plot([1, 2, 3])\n"
            "print('ephemeral')"
        ),
    )
    assert r["exit_code"] == 0
    assert _figure_files(r["files"]) == ["figure_1.png"]
