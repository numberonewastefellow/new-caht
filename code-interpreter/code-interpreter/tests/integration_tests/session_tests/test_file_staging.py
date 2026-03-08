"""Tests for file staging and file output within persistent sessions."""

from __future__ import annotations

import json

import requests

from .conftest import (
    BASE_URL,
    execute_in_session,
    read_sample,
    upload_file,
)


# ------------------------------------------------------------------
# File staging into session
# ------------------------------------------------------------------


def test_staged_file_readable_in_session(
    api: requests.Session, session_id: str
) -> None:
    """Upload a file, stage it, and read it inside the session."""
    content = b"hello from test\n"
    file_id = upload_file(api, "greeting.txt", content)

    r = execute_in_session(
        api,
        session_id,
        "print(open('greeting.txt').read())",
        files=[{"path": "greeting.txt", "file_id": file_id}],
    )
    assert r["stdout"] == "hello from test\n\n"


def test_staged_file_persists_in_session(
    api: requests.Session, session_id: str
) -> None:
    """File staged in call 1 should still be on disk in call 2."""
    content = b"persistent file content"
    file_id = upload_file(api, "data.txt", content)

    # Call 1: stage file
    execute_in_session(
        api,
        session_id,
        "import os\nprint(os.path.exists('data.txt'))",
        files=[{"path": "data.txt", "file_id": file_id}],
    )

    # Call 2: file should still be there (no re-staging needed)
    r = execute_in_session(
        api, session_id, "print(open('data.txt').read())"
    )
    assert r["stdout"] == "persistent file content\n"


def test_stage_csv_and_json_together(
    api: requests.Session, session_id: str
) -> None:
    """Stage multiple files in one call."""
    csv_content = read_sample("sales.csv")
    json_content = read_sample("config.json")

    csv_id = upload_file(api, "sales.csv", csv_content)
    json_id = upload_file(api, "config.json", json_content)

    r = execute_in_session(
        api,
        session_id,
        (
            "import json\n"
            "config = json.load(open('config.json'))\n"
            "print(f\"Project: {config['project']}\")\n"
            "# Count CSV lines (minus header)\n"
            "lines = open('sales.csv').readlines()\n"
            "print(f'CSV rows: {len(lines) - 1}')"
        ),
        files=[
            {"path": "sales.csv", "file_id": csv_id},
            {"path": "config.json", "file_id": json_id},
        ],
    )
    assert "Project: test-analytics" in r["stdout"]
    assert "CSV rows: 10" in r["stdout"]


# ------------------------------------------------------------------
# File output from session
# ------------------------------------------------------------------


def test_session_produces_output_file(
    api: requests.Session, session_id: str
) -> None:
    """Write a file inside the session and verify it's returned."""
    r = execute_in_session(
        api,
        session_id,
        (
            "with open('result.txt', 'w') as f:\n"
            "    f.write('computation result: 42')\n"
            "print('done')"
        ),
    )
    assert r["stdout"] == "done\n"

    # The file should appear in the response files list
    files = r.get("files", [])
    result_file = next((f for f in files if f["path"] == "result.txt"), None)
    assert result_file is not None, f"result.txt not found in {files}"
    assert result_file["kind"] == "file"

    # Download and verify content
    file_id = result_file["file_id"]
    dl = api.get(f"{BASE_URL}/v1/files/{file_id}")
    assert dl.status_code == 200
    assert dl.content == b"computation result: 42"


def test_output_file_persists_across_calls(
    api: requests.Session, session_id: str
) -> None:
    """File written in call 1 should be readable in call 2."""
    # Call 1: write file
    execute_in_session(
        api,
        session_id,
        "open('intermediate.txt', 'w').write('step1')",
    )

    # Call 2: read it back
    r = execute_in_session(
        api, session_id, "print(open('intermediate.txt').read())"
    )
    assert r["stdout"] == "step1\n"

    # Call 3: append to it
    execute_in_session(
        api,
        session_id,
        (
            "with open('intermediate.txt', 'a') as f:\n"
            "    f.write(' + step2')"
        ),
    )

    # Call 4: verify appended content
    r2 = execute_in_session(
        api, session_id, "print(open('intermediate.txt').read())"
    )
    assert r2["stdout"] == "step1 + step2\n"


def test_session_csv_round_trip(
    api: requests.Session, session_id: str
) -> None:
    """Load CSV, transform, save as new CSV, download and verify."""
    csv_content = read_sample("employees.csv")
    file_id = upload_file(api, "employees.csv", csv_content)

    # Call 1: load and transform
    execute_in_session(
        api,
        session_id,
        (
            "import pandas as pd\n"
            "df = pd.read_csv('employees.csv')\n"
            "summary = df.groupby('department').agg(\n"
            "    count=('id', 'count'),\n"
            "    avg_salary=('salary', 'mean')\n"
            ").reset_index()\n"
            "summary.to_csv('dept_summary.csv', index=False)\n"
            "print(f'Saved {len(summary)} departments')"
        ),
        files=[{"path": "employees.csv", "file_id": file_id}],
    )

    # Call 2: read back the generated CSV
    r2 = execute_in_session(
        api,
        session_id,
        (
            "result = pd.read_csv('dept_summary.csv')\n"
            "print(result.to_string(index=False))"
        ),
    )
    assert "Engineering" in r2["stdout"]
    assert r2["exit_code"] == 0
