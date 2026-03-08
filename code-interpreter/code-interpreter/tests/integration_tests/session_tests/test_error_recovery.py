"""Tests that sessions survive errors and remain usable."""

from __future__ import annotations

import requests

from .conftest import execute_in_session


# ------------------------------------------------------------------
# Exception does NOT kill the session
# ------------------------------------------------------------------


def test_exception_does_not_kill_session(
    api: requests.Session, session_id: str
) -> None:
    """A Python exception should be caught; the session stays alive."""
    # Call 1: set state
    execute_in_session(api, session_id, "x = 'before_error'")

    # Call 2: cause an exception
    r_err = execute_in_session(api, session_id, "1 / 0")
    assert r_err["exit_code"] != 0
    assert "ZeroDivisionError" in r_err["stderr"]

    # Call 3: session still works, x still defined
    r_ok = execute_in_session(api, session_id, "print(x)")
    assert r_ok["stdout"] == "before_error\n"
    assert r_ok["exit_code"] == 0


def test_syntax_error_does_not_kill_session(
    api: requests.Session, session_id: str
) -> None:
    """A SyntaxError should not crash the kernel."""
    execute_in_session(api, session_id, "y = 99")

    r_err = execute_in_session(api, session_id, "def broken(\nreturn 1")
    assert r_err["exit_code"] != 0
    assert "SyntaxError" in r_err["stderr"]

    # Still alive
    r_ok = execute_in_session(api, session_id, "print(y)")
    assert r_ok["stdout"] == "99\n"


def test_name_error_does_not_kill_session(
    api: requests.Session, session_id: str
) -> None:
    """Referencing undefined variable should not crash kernel."""
    r_err = execute_in_session(api, session_id, "print(undefined_var)")
    assert r_err["exit_code"] != 0
    assert "NameError" in r_err["stderr"]

    # Session still works
    r_ok = execute_in_session(api, session_id, "print('still alive')")
    assert r_ok["stdout"] == "still alive\n"


def test_import_error_does_not_kill_session(
    api: requests.Session, session_id: str
) -> None:
    """Failed import should not crash the kernel."""
    r_err = execute_in_session(
        api, session_id, "import nonexistent_package_xyz_123"
    )
    assert r_err["exit_code"] != 0
    assert "ModuleNotFoundError" in r_err["stderr"]

    # Session still works
    r_ok = execute_in_session(api, session_id, "print(2 + 2)")
    assert r_ok["stdout"] == "4\n"


# ------------------------------------------------------------------
# State survives errors
# ------------------------------------------------------------------


def test_partial_execution_preserves_state(
    api: requests.Session, session_id: str
) -> None:
    """If line 1 succeeds and line 2 fails, line 1's state is kept."""
    r = execute_in_session(
        api,
        session_id,
        "a = 'set_before_crash'\n1/0",
    )
    assert r["exit_code"] != 0

    # 'a' was set before the crash
    r2 = execute_in_session(api, session_id, "print(a)")
    assert r2["stdout"] == "set_before_crash\n"


def test_multiple_errors_then_recovery(
    api: requests.Session, session_id: str
) -> None:
    """Multiple consecutive errors followed by normal execution."""
    execute_in_session(api, session_id, "counter = 0")

    for _ in range(3):
        r = execute_in_session(api, session_id, "raise ValueError('boom')")
        assert r["exit_code"] != 0

    # Session still works
    execute_in_session(api, session_id, "counter += 1")
    r = execute_in_session(api, session_id, "print(counter)")
    assert r["stdout"] == "1\n"


# ------------------------------------------------------------------
# Large output
# ------------------------------------------------------------------


def test_large_stdout_does_not_crash(
    api: requests.Session, session_id: str
) -> None:
    """Printing a lot of output should not crash the session."""
    r = execute_in_session(
        api,
        session_id,
        "for i in range(1000):\n    print(f'line {i}')",
        timeout_ms=30_000,
    )
    assert r["exit_code"] == 0
    assert "line 0" in r["stdout"]
    assert "line 999" in r["stdout"]

    # Session still alive
    r2 = execute_in_session(api, session_id, "print('ok')")
    assert r2["stdout"] == "ok\n"
