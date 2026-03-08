"""Tests that pandas DataFrames and numpy arrays persist across session calls."""

from __future__ import annotations

import json

import pytest
import requests

from .conftest import execute_in_session, read_sample, upload_file, BASE_URL


# ------------------------------------------------------------------
# In-memory DataFrame persistence
# ------------------------------------------------------------------


def test_dataframe_persists_across_calls(
    api: requests.Session, session_id: str
) -> None:
    """Create a DataFrame in call 1, analyze it in call 2."""
    r1 = execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "df = pd.DataFrame({\n"
            "    'name': ['Alice', 'Bob', 'Charlie'],\n"
            "    'age': [30, 25, 35],\n"
            "    'salary': [90000, 70000, 85000],\n"
            "})\n"
            "print(f'Created DataFrame with {len(df)} rows')"
        ),
    )
    assert r1["stdout"] == "Created DataFrame with 3 rows\n"

    # Call 2: query the same DataFrame
    r2 = execute_in_session(
        api, session_id, "print(df[df.age > 28][['name', 'salary']].to_string(index=False))"
    )
    assert "Alice" in r2["stdout"]
    assert "Charlie" in r2["stdout"]
    assert "Bob" not in r2["stdout"]


def test_dataframe_describe(
    api: requests.Session, session_id: str
) -> None:
    """Create DataFrame, then call describe() in a separate execution."""
    execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "df = pd.DataFrame({'x': [10, 20, 30, 40, 50]})"
        ),
    )

    r = execute_in_session(api, session_id, "print(df.x.mean())")
    assert r["stdout"].strip() == "30.0"


def test_dataframe_mutations_persist(
    api: requests.Session, session_id: str
) -> None:
    """Add a column in call 2, verify in call 3."""
    execute_in_session(
        api,
        session_id,
        "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})",
    )

    # Add derived column
    execute_in_session(api, session_id, "df['c'] = df['a'] + df['b']")

    # Verify
    r = execute_in_session(api, session_id, "print(df['c'].tolist())")
    assert r["stdout"].strip() == "[5, 7, 9]"


# ------------------------------------------------------------------
# Load CSV from staged file into DataFrame
# ------------------------------------------------------------------


def test_load_csv_into_dataframe(
    api: requests.Session, session_id: str
) -> None:
    """Upload sales.csv, stage it, load into pandas, query across calls."""
    csv_content = read_sample("sales.csv")
    file_id = upload_file(api, "sales.csv", csv_content)

    # Call 1: load CSV
    r1 = execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "df = pd.read_csv('sales.csv')\n"
            "print(f'Loaded {len(df)} rows, {len(df.columns)} columns')"
        ),
        files=[{"path": "sales.csv", "file_id": file_id}],
    )
    assert "Loaded 10 rows, 6 columns" in r1["stdout"]

    # Call 2: query — no file staging needed, DataFrame is in memory
    r2 = execute_in_session(
        api,
        session_id,
        "print(f'Total revenue: {df.revenue.sum()}')",
    )
    assert "Total revenue:" in r2["stdout"]
    assert r2["exit_code"] == 0

    # Call 3: groupby
    r3 = execute_in_session(
        api,
        session_id,
        (
            "grouped = df.groupby('product')['units'].sum().sort_values(ascending=False)\n"
            "print(grouped.to_string())"
        ),
    )
    assert "Widget" in r3["stdout"]
    assert r3["exit_code"] == 0


def test_load_employees_csv_and_analyze(
    api: requests.Session, session_id: str
) -> None:
    """Multi-step analysis: load, filter, aggregate across 3 calls."""
    csv_content = read_sample("employees.csv")
    file_id = upload_file(api, "employees.csv", csv_content)

    # Call 1: load
    execute_in_session(
        api,
        session_id,
        "import pandas as pd\ndf = pd.read_csv('employees.csv')",
        files=[{"path": "employees.csv", "file_id": file_id}],
    )

    # Call 2: filter engineering dept
    r2 = execute_in_session(
        api,
        session_id,
        (
            "eng = df[df.department == 'Engineering']\n"
            "print(f'Engineers: {len(eng)}')\n"
            "print(f'Avg salary: {eng.salary.mean()}')"
        ),
    )
    assert "Engineers: 4" in r2["stdout"]
    assert "Avg salary: 94000" in r2["stdout"]

    # Call 3: department summary (uses original df, not eng)
    r3 = execute_in_session(
        api,
        session_id,
        (
            "summary = df.groupby('department')['salary'].agg(['mean', 'count'])\n"
            "print(summary.to_string())"
        ),
    )
    assert "Engineering" in r3["stdout"]
    assert "Marketing" in r3["stdout"]
    assert "Sales" in r3["stdout"]


# ------------------------------------------------------------------
# Numpy persistence
# ------------------------------------------------------------------


def test_numpy_array_persists(
    api: requests.Session, session_id: str
) -> None:
    execute_in_session(
        api,
        session_id,
        "import numpy as np\narr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])",
    )

    r = execute_in_session(
        api,
        session_id,
        "print(f'mean={arr.mean()}, std={arr.std():.4f}')",
    )
    assert "mean=3.0" in r["stdout"]
    assert "std=1.4142" in r["stdout"]
