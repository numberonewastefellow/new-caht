"""
Parallel Test Runner for Coding Workflows (PythonTool / Chart Generation)
=========================================================================

Tests all 3 coding workflows with 2 test cases each (6 total), run in parallel.

Workflows tested:
  - ID=45: Automated Data Analysis Pipeline  (sales data + attrition data)
  - ID=47: Code Debug & Fix Assistant        (sort bug + data pipeline bug)
  - ID=48: ML Model Rapid Prototyper         (house price regression + churn classification)

Validates:
  - PythonTool code execution (python_tool_start + python_tool_delta packets)
  - Chart/file generation (file_ids and files metadata in delta packets)
  - Enriched PythonToolFile metadata (file_id + filename)
  - Agent response content

Usage:
    python test_coding_workflows.py
    python test_coding_workflows.py --url http://192.168.1.10:3000
    python test_coding_workflows.py --test 1    # Run only test #1
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add parent dirs to path for imports
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from workflow_creator.config import stream_api  # noqa: E402
from agents_creator.config import (  # noqa: E402
    CONFIG,
    add_common_args,
    api,
    apply_common_args,
)

# ── Test Definitions ──────────────────────────────────────────────────────

TEST_CASES = [
    # ── Data Analysis Pipeline (ID=45) ─────────────────────────────────
    {
        "id": 1,
        "name": "DataAnalysis: Quarterly Sales Revenue",
        "workflow_id": 45,
        "message": (
            "Revenue data: CSV with columns date, product_line (Enterprise/SMB/Consumer), "
            "region (North America/Europe/APAC), revenue, units_sold, discount_pct, "
            "customer_segment. 12 months of data (Jan-Dec 2023), 108 rows. "
            "Analysis objectives: "
            "Identify which product line has the strongest revenue growth trend. "
            "Compare regional performance and identify the top-performing region. "
            "Analyze correlation between discount percentage and units sold. "
            "Determine seasonal patterns in revenue across quarters."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": True,
        "expect_keywords": ["revenue", "growth", "region"],
    },
    {
        "id": 2,
        "name": "DataAnalysis: Employee Attrition",
        "workflow_id": 45,
        "message": (
            "Employee HR data: CSV with columns employee_id, department "
            "(Sales/Engineering/HR/Marketing), job_role, age, gender, education, "
            "monthly_income, years_at_company, years_since_promotion, overtime (Yes/No), "
            "job_satisfaction (1-4), work_life_balance (1-4), performance_rating (2-4), "
            "distance_from_home_km, num_companies_worked, attrition (Yes/No). "
            "40 employees total. "
            "Analysis objectives: "
            "Identify the top factors correlated with employee attrition. "
            "Compare attrition rates across departments. "
            "Analyze the relationship between overtime and attrition. "
            "Determine if job satisfaction and work-life balance predict attrition."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": True,
        "expect_keywords": ["attrition", "department"],
    },
    # ── Code Debug & Fix (ID=47) ───────────────────────────────────────
    {
        "id": 3,
        "name": "CodeDebug: Sorting with Duplicates",
        "workflow_id": 47,
        "message": (
            "Bug Report:\n\n"
            "Function: custom_sort_and_deduplicate\n\n"
            "Code:\n"
            "```python\n"
            "def custom_sort_and_deduplicate(items, key=None):\n"
            "    \"\"\"Sort items and remove duplicates, keeping first occurrence.\"\"\"\n"
            "    seen = set()\n"
            "    result = []\n"
            "    for item in sorted(items, key=key):\n"
            "        val = key(item) if key else item\n"
            "        if val not in seen:\n"
            "            seen.add(val)\n"
            "            result.append(item)\n"
            "    return result\n"
            "```\n\n"
            "Error: When key=None and items contain unhashable types like dicts or lists, "
            "the function crashes with TypeError: unhashable type: 'dict'.\n\n"
            "Test case that fails:\n"
            "```python\n"
            "data = [{'name': 'Alice', 'score': 90}, {'name': 'Bob', 'score': 85}, "
            "{'name': 'Alice', 'score': 90}]\n"
            "result = custom_sort_and_deduplicate(data, key=lambda x: x['name'])\n"
            "# Expected: [{'name': 'Alice', 'score': 90}, {'name': 'Bob', 'score': 85}]\n"
            "# Actual: TypeError because sorted() can't compare dicts without key\n"
            "```\n\n"
            "Additional issue: Even when key is provided, the function adds the key value "
            "to `seen` set, but if the key value itself is unhashable (e.g., a list), "
            "it still crashes.\n\n"
            "Expected behavior: Function should handle both hashable and unhashable types "
            "gracefully, deduplicating by the key function when provided."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,
        "expect_keywords": ["fix", "test"],
    },
    {
        "id": 4,
        "name": "CodeDebug: CSV Parser Off-By-One",
        "workflow_id": 47,
        "message": (
            "Bug Report:\n\n"
            "Function: parse_csv_with_headers\n\n"
            "Code:\n"
            "```python\n"
            "def parse_csv_with_headers(csv_text):\n"
            "    \"\"\"Parse CSV text into list of dicts using first row as headers.\"\"\"\n"
            "    lines = csv_text.strip().split('\\n')\n"
            "    headers = lines[0].split(',')\n"
            "    records = []\n"
            "    for i in range(len(lines)):\n"
            "        values = lines[i].split(',')\n"
            "        record = {}\n"
            "        for j in range(len(headers)):\n"
            "            record[headers[j]] = values[j] if j < len(values) else ''\n"
            "        records.append(record)\n"
            "    return records\n"
            "\n"
            "def calculate_column_stats(records, column):\n"
            "    \"\"\"Calculate mean and std of a numeric column.\"\"\"\n"
            "    values = [float(r[column]) for r in records]\n"
            "    mean = sum(values) / len(values)\n"
            "    variance = sum((v - mean) ** 2 for v in values) / len(values)\n"
            "    return {'mean': mean, 'std': variance ** 0.5, 'count': len(values)}\n"
            "```\n\n"
            "Error: Two bugs here.\n"
            "1) parse_csv_with_headers includes the header row as a data record (off-by-one: "
            "loop starts at i=0 instead of i=1)\n"
            "2) calculate_column_stats crashes with ValueError: could not convert string to float "
            "because the header row is included as a record, so it tries to convert the column "
            "name string to float.\n\n"
            "Test input:\n"
            "```python\n"
            "csv_data = 'name,age,salary\\nAlice,30,75000\\nBob,25,65000\\nCharlie,35,85000'\n"
            "records = parse_csv_with_headers(csv_data)\n"
            "stats = calculate_column_stats(records, 'salary')\n"
            "# Expected: {'mean': 75000.0, 'std': 8164.97, 'count': 3}\n"
            "# Actual: ValueError: could not convert string to float: 'salary'\n"
            "```\n\n"
            "Expected: parse_csv_with_headers should skip the header row in the output, "
            "and calculate_column_stats should correctly compute stats for numeric columns."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,
        "expect_keywords": ["fix", "test"],
    },
    # ── ML Model Rapid Prototyper (ID=48) ──────────────────────────────
    {
        "id": 5,
        "name": "MLModel: House Price Regression",
        "workflow_id": 48,
        "message": (
            "Build a regression model to predict house sale prices. "
            "Features: bedrooms, bathrooms, sqft_living, sqft_lot, floors, waterfront (0/1), "
            "view_score (0-4), condition (1-5), grade (1-13), year_built, zipcode. "
            "Target: sale_price. "
            "Dataset: 30 houses from Seattle area. "
            "Approximate price range $245K to $3.2M. "
            "Key characteristics: waterfront homes are significantly more expensive, "
            "grade and sqft_living are the strongest predictors. "
            "Train at least 3 models: Linear Regression, Random Forest, Gradient Boosting. "
            "Report RMSE, MAE, and R-squared for each. "
            "Generate a scatter plot of predicted vs actual prices and a feature importance chart."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": True,
        "expect_keywords": ["model", "rmse", "r-squared"],
    },
    {
        "id": 6,
        "name": "MLModel: Customer Churn Classification",
        "workflow_id": 48,
        "message": (
            "Build a classification model to predict customer churn for a telecom company. "
            "Features: tenure_months, monthly_charges, total_charges, contract_type "
            "(Month-to-month/One year/Two year), payment_method, internet_service "
            "(DSL/Fiber optic), online_security (Yes/No), tech_support (Yes/No), "
            "streaming_tv, streaming_movies, paperless_billing, gender, senior_citizen (0/1), "
            "partner (Yes/No), dependents (Yes/No), num_support_tickets, avg_monthly_usage_gb. "
            "Target: churned (Yes/No). "
            "Dataset: 30 customers. Churn rate approximately 40%. "
            "Key patterns: month-to-month contracts + fiber optic + electronic check = high churn risk. "
            "Train at least 3 models: Logistic Regression, Random Forest, Gradient Boosting. "
            "Report accuracy, precision, recall, F1, and AUC-ROC. "
            "Minimize false negatives (missed churners). "
            "Generate an ROC curve comparison chart and feature importance plot."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": True,
        "expect_keywords": ["model", "accuracy", "churn"],
    },
]


# ── Test Runner ───────────────────────────────────────────────────────────


def run_single_test(test: dict) -> dict:
    """Run a single workflow test and return results."""
    test_id = test["id"]
    name = test["name"]
    workflow_id = test["workflow_id"]
    timeout = test.get("timeout", 600)

    result = {
        "id": test_id,
        "name": name,
        "workflow_id": workflow_id,
        "passed": False,
        "error": None,
        "duration_s": 0,
        "packet_types": {},
        "python_executions": 0,
        "files_generated": [],
        "files_with_metadata": [],
        "answer_length": 0,
        "keyword_hits": [],
    }

    start_time = time.time()

    try:
        # 1. Create chat session
        resp = api("POST", "chat/create-chat-session", {
            "persona_id": workflow_id,
            "description": f"Test: {name}",
        })
        if resp.status_code != 200:
            result["error"] = f"Failed to create session: {resp.status_code}"
            return result

        session = resp.json()
        session_id = session["chat_session_id"]

        # 2. Send message
        body = {
            "chat_session_id": session_id,
            "message": test["message"],
            "persona_id": workflow_id,
            "prompt_id": 0,
            "parent_message_id": -1,
            "search_doc_ids": None,
            "retrieval_options": None,
            "query_override": None,
            "include_citations": True,
        }

        resp = stream_api("POST", "chat/send-chat-message", body)
        if resp.status_code != 200:
            result["error"] = f"Send message failed: {resp.status_code}"
            return result

        # 3. Parse streaming response
        packet_types = {}
        file_ids = []
        files_info = []
        answer_parts = []
        full_text = []  # All text content for keyword matching

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)

                # Skip message ID packet
                if "user_message_id" in data:
                    continue

                obj = data.get("obj", data)
                ptype = obj.get("type", "unknown")
                packet_types[ptype] = packet_types.get(ptype, 0) + 1

                if ptype == "python_tool_start":
                    result["python_executions"] += 1

                elif ptype == "python_tool_delta":
                    fids = obj.get("file_ids", [])
                    if fids:
                        file_ids.extend(fids)
                    pfiles = obj.get("files", [])
                    if pfiles:
                        files_info.extend(pfiles)
                    stdout = obj.get("stdout", "")
                    if stdout:
                        full_text.append(stdout)
                    stderr = obj.get("stderr", "")
                    if stderr:
                        full_text.append(stderr)

                elif ptype in ("message_delta", "agent_response_delta"):
                    text = obj.get("answer", "")
                    if text:
                        answer_parts.append(text)
                        full_text.append(text)

                elif ptype == "workflow_step_delta":
                    content = obj.get("content", "")
                    if content:
                        full_text.append(content)

                elif ptype == "error":
                    err_msg = obj.get("error", str(data))
                    result["error"] = f"Stream error: {err_msg[:200]}"

            except json.JSONDecodeError:
                pass

        result["duration_s"] = round(time.time() - start_time, 1)
        result["packet_types"] = packet_types
        result["files_generated"] = file_ids
        result["files_with_metadata"] = files_info
        result["answer_length"] = sum(len(p) for p in answer_parts)

        # 4. Check keyword hits
        combined_text = " ".join(full_text).lower()
        for kw in test.get("expect_keywords", []):
            if kw.lower() in combined_text:
                result["keyword_hits"].append(kw)

        # 5. Validate expectations
        failures = []

        if test.get("expect_python") and result["python_executions"] == 0:
            failures.append("No Python code executed")

        if test.get("expect_files") and len(file_ids) == 0 and len(files_info) == 0:
            failures.append("No files generated")

        # Check enriched metadata (our new feature)
        if test.get("expect_files") and file_ids and not files_info:
            failures.append("Files generated but no enriched metadata (PythonToolFile missing)")

        missing_kw = set(test.get("expect_keywords", [])) - set(result["keyword_hits"])
        if missing_kw:
            failures.append(f"Missing keywords: {missing_kw}")

        if failures:
            result["error"] = "; ".join(failures)
        else:
            result["passed"] = True

    except Exception as e:
        result["error"] = f"Exception: {str(e)[:200]}"
        result["duration_s"] = round(time.time() - start_time, 1)

    return result


def print_result(r: dict) -> None:
    """Pretty-print a single test result."""
    status = "PASS" if r["passed"] else "FAIL"
    icon = "+" if r["passed"] else "-"
    print(f"\n  [{icon}] Test #{r['id']}: {r['name']}")
    print(f"      Workflow: {r['workflow_id']}  |  Duration: {r['duration_s']}s")
    print(f"      Python executions: {r['python_executions']}")

    if r["files_with_metadata"]:
        fnames = [f.get("filename", "?") for f in r["files_with_metadata"]]
        print(f"      Files (enriched): {fnames}")
    elif r["files_generated"]:
        print(f"      File IDs (bare): {r['files_generated']}")
    else:
        print(f"      Files: none")

    print(f"      Keywords found: {r['keyword_hits']}")
    key_packets = {k: v for k, v in r["packet_types"].items()
                   if k in ("python_tool_start", "python_tool_delta", "section_end",
                            "workflow_step_start", "workflow_step_delta", "message_delta")}
    print(f"      Key packets: {key_packets}")

    if r["error"]:
        print(f"      Error: {r['error']}")


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Test coding workflows with PythonTool")
    add_common_args(parser)
    parser.add_argument("--test", type=int, help="Run only a specific test by ID (1-6)")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially")
    args = parser.parse_args()
    apply_common_args(args)

    tests = TEST_CASES
    if args.test:
        tests = [t for t in TEST_CASES if t["id"] == args.test]
        if not tests:
            print(f"Error: No test with ID={args.test}. Valid IDs: 1-6")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  CODING WORKFLOW TEST SUITE")
    print(f"  Tests: {len(tests)} | Mode: {'sequential' if args.sequential else 'parallel'}")
    print(f"  Server: {CONFIG['base_url']}")
    print(f"{'='*70}")

    for t in tests:
        print(f"  #{t['id']} {t['name']} (workflow={t['workflow_id']})")

    print(f"\nStarting tests...\n")
    start_all = time.time()
    results = []

    if args.sequential:
        for t in tests:
            print(f"  Running #{t['id']}: {t['name']}...")
            r = run_single_test(t)
            results.append(r)
            print_result(r)
    else:
        # Run all tests in parallel
        with ThreadPoolExecutor(max_workers=len(tests)) as executor:
            futures = {executor.submit(run_single_test, t): t for t in tests}
            print(f"  Launched {len(futures)} tests in parallel...")

            for future in as_completed(futures):
                r = future.result()
                results.append(r)
                print_result(r)

    total_time = round(time.time() - start_all, 1)

    # Sort results by test ID for final summary
    results.sort(key=lambda r: r["id"])

    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    total_files = sum(len(r["files_generated"]) + len(r["files_with_metadata"]) for r in results)
    total_python = sum(r["python_executions"] for r in results)

    print(f"\n{'='*70}")
    print(f"  RESULTS: {passed} passed, {failed} failed  |  Total: {total_time}s")
    print(f"  Python executions: {total_python}  |  Files generated: {total_files}")
    print(f"{'='*70}")

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        fcount = len(r["files_with_metadata"]) or len(r["files_generated"])
        print(f"  {'[+]' if r['passed'] else '[-]'} #{r['id']} {r['name']:<45} "
              f"{r['duration_s']:>6}s  py={r['python_executions']}  files={fcount}")

    if failed:
        print(f"\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  #{r['id']} {r['name']}: {r['error']}")

    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
