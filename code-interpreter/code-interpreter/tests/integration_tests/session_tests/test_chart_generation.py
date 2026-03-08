"""Tests for chart/plot generation within persistent sessions."""

from __future__ import annotations

import requests

from .conftest import (
    BASE_URL,
    execute_in_session,
    read_sample,
    upload_file,
)


def _find_file(files: list[dict], path: str) -> dict | None:
    return next((f for f in files if f["path"] == path), None)


# ------------------------------------------------------------------
# Basic chart generation
# ------------------------------------------------------------------


def test_simple_bar_chart(
    api: requests.Session, session_id: str
) -> None:
    """Generate a bar chart and verify PNG output."""
    r = execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "categories = ['A', 'B', 'C', 'D']\n"
            "values = [25, 40, 30, 55]\n"
            "plt.figure(figsize=(6, 4))\n"
            "plt.bar(categories, values)\n"
            "plt.title('Test Bar Chart')\n"
            "plt.tight_layout()\n"
            "plt.savefig('bar_chart.png', dpi=80)\n"
            "plt.close()\n"
            "print('chart saved')"
        ),
    )
    assert r["stdout"] == "chart saved\n"
    assert r["exit_code"] == 0

    # Verify PNG file returned
    bar_file = _find_file(r["files"], "bar_chart.png")
    assert bar_file is not None, f"bar_chart.png not in {r['files']}"
    assert bar_file["file_id"] is not None

    # Download and verify PNG magic bytes
    dl = api.get(f"{BASE_URL}/v1/files/{bar_file['file_id']}")
    assert dl.status_code == 200
    assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(dl.content) > 1000


# ------------------------------------------------------------------
# Multi-step: load data, then chart in separate call
# ------------------------------------------------------------------


def test_chart_from_persisted_dataframe(
    api: requests.Session, session_id: str
) -> None:
    """Load data in call 1, generate chart in call 2 using persisted DataFrame."""
    csv_content = read_sample("sales.csv")
    file_id = upload_file(api, "sales.csv", csv_content)

    # Call 1: load data
    execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "df = pd.read_csv('sales.csv')\n"
            "print(f'Loaded {len(df)} rows')"
        ),
        files=[{"path": "sales.csv", "file_id": file_id}],
    )

    # Call 2: generate chart from persisted DataFrame (no re-staging)
    r2 = execute_in_session(
        api,
        session_id,
        (
            "revenue_by_product = df.groupby('product')['revenue'].sum()\n"
            "fig, ax = plt.subplots(figsize=(8, 5))\n"
            "revenue_by_product.plot(kind='bar', ax=ax)\n"
            "ax.set_title('Revenue by Product')\n"
            "ax.set_ylabel('Revenue ($)')\n"
            "plt.tight_layout()\n"
            "fig.savefig('revenue_chart.png', dpi=100)\n"
            "plt.close(fig)\n"
            "print('revenue chart done')"
        ),
    )
    assert r2["stdout"] == "revenue chart done\n"

    chart_file = _find_file(r2["files"], "revenue_chart.png")
    assert chart_file is not None
    assert chart_file["file_id"] is not None

    # Verify PNG
    dl = api.get(f"{BASE_URL}/v1/files/{chart_file['file_id']}")
    assert dl.content[:4] == b"\x89PNG"
    assert len(dl.content) > 2000


# ------------------------------------------------------------------
# Multiple charts in sequence
# ------------------------------------------------------------------


def test_multiple_charts_across_calls(
    api: requests.Session, session_id: str
) -> None:
    """Generate different charts in successive calls, all using the same data."""
    # Setup
    execute_in_session(
        api,
        session_id,
        (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import numpy as np\n"
            "np.random.seed(42)\n"
            "data = np.random.randn(200)"
        ),
    )

    # Chart 1: histogram
    r1 = execute_in_session(
        api,
        session_id,
        (
            "plt.figure()\n"
            "plt.hist(data, bins=20)\n"
            "plt.title('Histogram')\n"
            "plt.savefig('hist.png')\n"
            "plt.close()\n"
            "print('hist done')"
        ),
    )
    assert r1["exit_code"] == 0
    assert _find_file(r1["files"], "hist.png") is not None

    # Chart 2: line plot (cumulative sum)
    r2 = execute_in_session(
        api,
        session_id,
        (
            "plt.figure()\n"
            "plt.plot(np.cumsum(data))\n"
            "plt.title('Cumulative Sum')\n"
            "plt.savefig('cumsum.png')\n"
            "plt.close()\n"
            "print('cumsum done')"
        ),
    )
    assert r2["exit_code"] == 0
    assert _find_file(r2["files"], "cumsum.png") is not None


# ------------------------------------------------------------------
# Seaborn chart
# ------------------------------------------------------------------


def test_seaborn_chart(
    api: requests.Session, session_id: str
) -> None:
    """Generate a seaborn chart to ensure the full data stack works."""
    csv_content = read_sample("employees.csv")
    file_id = upload_file(api, "employees.csv", csv_content)

    execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import seaborn as sns\n"
            "import matplotlib.pyplot as plt\n"
            "df = pd.read_csv('employees.csv')"
        ),
        files=[{"path": "employees.csv", "file_id": file_id}],
    )

    r = execute_in_session(
        api,
        session_id,
        (
            "fig, ax = plt.subplots(figsize=(8, 5))\n"
            "sns.boxplot(data=df, x='department', y='salary', ax=ax)\n"
            "ax.set_title('Salary by Department')\n"
            "plt.tight_layout()\n"
            "fig.savefig('salary_box.png', dpi=100)\n"
            "plt.close(fig)\n"
            "print('seaborn chart done')"
        ),
    )
    assert r["stdout"] == "seaborn chart done\n"

    chart_file = _find_file(r["files"], "salary_box.png")
    assert chart_file is not None

    dl = api.get(f"{BASE_URL}/v1/files/{chart_file['file_id']}")
    assert dl.content[:4] == b"\x89PNG"
    assert len(dl.content) > 2000
