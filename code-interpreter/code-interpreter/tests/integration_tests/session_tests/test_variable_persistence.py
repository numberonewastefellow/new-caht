"""Tests that variables, imports, and functions persist across calls in a session."""

from __future__ import annotations

import json

import requests

from .conftest import execute_in_session


# ------------------------------------------------------------------
# Scalar variable persistence
# ------------------------------------------------------------------


def test_int_variable_persists(
    api: requests.Session, session_id: str
) -> None:
    """A variable defined in call 1 should be readable in call 2."""
    r1 = execute_in_session(api, session_id, "x = 42")
    assert r1["exit_code"] == 0

    r2 = execute_in_session(api, session_id, "print(x)")
    assert r2["stdout"] == "42\n"


def test_string_variable_persists(
    api: requests.Session, session_id: str
) -> None:
    r1 = execute_in_session(api, session_id, "name = 'persistent_kernel'")
    assert r1["exit_code"] == 0

    r2 = execute_in_session(api, session_id, "print(name.upper())")
    assert r2["stdout"] == "PERSISTENT_KERNEL\n"


def test_list_variable_grows_across_calls(
    api: requests.Session, session_id: str
) -> None:
    """Append to a list across multiple calls."""
    execute_in_session(api, session_id, "items = []")
    execute_in_session(api, session_id, "items.append('a')")
    execute_in_session(api, session_id, "items.append('b')")
    execute_in_session(api, session_id, "items.append('c')")

    r = execute_in_session(api, session_id, "print(items)")
    assert r["stdout"] == "['a', 'b', 'c']\n"


def test_dict_variable_persists(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(api, session_id, "config = {'key': 'value', 'count': 0}")
    execute_in_session(api, session_id, "config['count'] += 1")
    execute_in_session(api, session_id, "config['count'] += 1")

    r = execute_in_session(api, session_id, "import json\nprint(json.dumps(config))")
    result = json.loads(r["stdout"].strip())
    assert result == {"key": "value", "count": 2}


# ------------------------------------------------------------------
# Function & class persistence
# ------------------------------------------------------------------


def test_function_defined_in_call1_usable_in_call2(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(
        api,
        session_id,
        "def greet(name):\n    return f'Hello, {name}!'",
    )

    r = execute_in_session(api, session_id, "print(greet('World'))")
    assert r["stdout"] == "Hello, World!\n"


def test_class_defined_persists(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(
        api,
        session_id,
        (
            "class Counter:\n"
            "    def __init__(self):\n"
            "        self.n = 0\n"
            "    def inc(self):\n"
            "        self.n += 1\n"
            "        return self.n"
        ),
    )
    execute_in_session(api, session_id, "c = Counter()")
    execute_in_session(api, session_id, "c.inc()\nc.inc()\nc.inc()")

    r = execute_in_session(api, session_id, "print(c.n)")
    assert r["stdout"] == "3\n"


# ------------------------------------------------------------------
# Import persistence
# ------------------------------------------------------------------


def test_import_persists(
    api: requests.Session, session_id: str
) -> None:
    """Import in call 1 should be available in call 2."""
    execute_in_session(api, session_id, "import math")

    r = execute_in_session(api, session_id, "print(round(math.pi, 4))")
    assert r["stdout"] == "3.1416\n"


def test_from_import_persists(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(api, session_id, "from collections import Counter")

    r = execute_in_session(
        api, session_id, "c = Counter('abracadabra')\nprint(c.most_common(3))"
    )
    assert r["exit_code"] == 0
    assert "('a', 5)" in r["stdout"]


# ------------------------------------------------------------------
# Jupyter-like last-expression printing
# ------------------------------------------------------------------


def test_last_expression_printed(
    api: requests.Session, session_id: str
) -> None:
    """Bare expression on last line should print its repr."""
    r = execute_in_session(api, session_id, "2 + 2")
    assert "4" in r["stdout"]


def test_last_expression_with_variable(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(api, session_id, "x = [1, 2, 3]")
    r = execute_in_session(api, session_id, "len(x)")
    assert "3" in r["stdout"]
