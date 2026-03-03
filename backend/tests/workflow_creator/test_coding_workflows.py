"""
Parallel Test Runner for Coding Workflows (PythonTool / Chart Generation)
=========================================================================

Tests all 3 coding workflows with 12 test cases, run in parallel.

Workflows tested:
  - ID=45: Automated Data Analysis Pipeline  (sales, attrition, e-commerce, manufacturing)
  - ID=47: Code Debug & Fix Assistant        (sort bug, CSV parser, cart discount, flatten)
  - ID=48: ML Model Rapid Prototyper         (house price, churn, fraud, student scores)

Validates:
  - PythonTool code execution (python_tool_start + python_tool_delta packets)
  - Chart/file generation (file_ids and files metadata in delta packets)
  - Enriched PythonToolFile metadata (file_id + filename)
  - Agent response content

Usage:
    python test_coding_workflows.py
    python test_coding_workflows.py --url http://192.168.1.10:3000
    python test_coding_workflows.py --test 1    # Run only test #1

See test_data/README.md for sample questions and dataset documentation.
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
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
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
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
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
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
        "expect_keywords": ["model", "accuracy", "churn"],
    },
    # ── NEW: Data Analysis — E-commerce Funnel ─────────────────────────
    {
        "id": 7,
        "name": "DataAnalysis: E-commerce Conversion Funnel",
        "workflow_id": 45,
        "message": (
            "E-commerce funnel data: columns date, traffic_source "
            "(Organic/Paid/Social/Email/Direct), device_type (Desktop/Mobile/Tablet), "
            "sessions, product_views, add_to_cart, checkouts, purchases, revenue, "
            "avg_order_value. 4 months of bi-weekly data, ~45 rows. "
            "Analysis objectives: "
            "Calculate conversion rate by traffic source (sessions to purchases). "
            "Compare Desktop vs Mobile performance gap in conversion and revenue. "
            "Identify which traffic source delivers the highest ROI (revenue per session). "
            "Find the best-performing month and traffic source combination."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
        "expect_keywords": ["conversion", "traffic", "revenue"],
    },
    # ── NEW: Data Analysis — Manufacturing QC ──────────────────────────
    {
        "id": 8,
        "name": "DataAnalysis: Manufacturing Quality Control",
        "workflow_id": 45,
        "message": (
            "Manufacturing quality data: columns batch_id, production_line (A/B/C), "
            "shift (Day/Night), operator_id, temperature_celsius, pressure_bar, "
            "humidity_pct, cycle_time_seconds, defect_count, defect_type "
            "(None/Cosmetic/Structural/Functional), pass_fail (Pass/Fail). "
            "40 batches over 3 months. "
            "Analysis objectives: "
            "Identify which production line has the highest defect rate. "
            "Compare night shift vs day shift defect rates. "
            "Find the temperature and pressure ranges that correlate with defects. "
            "Rank the top 3 operators by quality score (lowest defect count)."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
        "expect_keywords": ["defect", "production", "shift"],
    },
    # ── NEW: Code Debug — Shopping Cart ────────────────────────────────
    {
        "id": 9,
        "name": "CodeDebug: Shopping Cart Bulk Discount",
        "workflow_id": 47,
        "message": (
            "Bug in our e-commerce cart. The function `apply_bulk_discount(cart_items, min_qty=3)` "
            "should give 15% off when a customer buys 3+ of the SAME item, but it's checking "
            "total cart quantity instead.\n\n"
            "Code:\n"
            "```python\n"
            "def apply_bulk_discount(cart_items, min_qty=3, discount=0.15):\n"
            "    total_qty = sum(item['quantity'] for item in cart_items)\n"
            "    if total_qty >= min_qty:\n"
            "        for item in cart_items:\n"
            "            item['price'] = round(item['price'] * (1 - discount), 2)\n"
            "    return cart_items\n"
            "```\n\n"
            "Test that fails:\n"
            "```python\n"
            "cart = [\n"
            "    {'name': 'Widget', 'price': 25.00, 'quantity': 1},\n"
            "    {'name': 'Gadget', 'price': 50.00, 'quantity': 1},\n"
            "    {'name': 'Doohickey', 'price': 10.00, 'quantity': 1}\n"
            "]\n"
            "result = apply_bulk_discount(cart)\n"
            "# Expected: No discount (no single item has qty >= 3)\n"
            "# Actual: All items get 15% off because total_qty=3\n"
            "```\n\n"
            "Expected behavior: Only items where quantity >= min_qty should receive "
            "the discount. Items with lower quantity should keep their original price."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,
        "expect_keywords": ["fix", "test", "discount"],
    },
    # ── NEW: Code Debug — Recursive Flatten ────────────────────────────
    {
        "id": 10,
        "name": "CodeDebug: Recursive Flatten Max Depth",
        "workflow_id": 47,
        "message": (
            "Our nested data flattener doesn't respect the max_depth parameter. "
            "It always flattens everything regardless of depth limit.\n\n"
            "Code:\n"
            "```python\n"
            "def flatten(data, max_depth=None, _current_depth=0):\n"
            "    result = []\n"
            "    for item in data:\n"
            "        if isinstance(item, (list, tuple)):\n"
            "            result.extend(flatten(item, max_depth, _current_depth))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result\n"
            "```\n\n"
            "Tests that fail:\n"
            "```python\n"
            "nested = [1, [2, [3, [4, [5]]]]]\n"
            "# flatten(nested, max_depth=1) should give [1, 2, [3, [4, [5]]]]\n"
            "# flatten(nested, max_depth=2) should give [1, 2, 3, [4, [5]]]\n"
            "# flatten(nested, max_depth=None) should give [1, 2, 3, 4, 5]\n"
            "# Actual: always returns [1, 2, 3, 4, 5] regardless of max_depth\n"
            "```\n\n"
            "Two bugs: 1) _current_depth is never incremented in recursive calls. "
            "2) max_depth is never checked before recursing."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,
        "expect_keywords": ["fix", "test", "depth"],
    },
    # ── NEW: ML Model — Fraud Detection ────────────────────────────────
    {
        "id": 11,
        "name": "MLModel: Credit Card Fraud Detection",
        "workflow_id": 48,
        "message": (
            "Build a fraud detection model for credit card transactions. "
            "Features: transaction_amount, merchant_category (retail/food/travel/online/entertainment), "
            "time_of_day (hour 0-23), day_of_week (0=Mon to 6=Sun), card_age_days, "
            "num_transactions_24h, avg_transaction_amount, distance_from_home_km, "
            "is_international (0/1), is_weekend (0/1), amount_vs_avg_ratio. "
            "Target: is_fraud (0/1). "
            "Dataset: 5000 transactions with 1.5% fraud rate (highly imbalanced). "
            "Priority: Maximize recall (catch frauds) while keeping false positive rate under 3%. "
            "Train: Logistic Regression, Random Forest, Gradient Boosting. "
            "Use class_weight='balanced' or SMOTE for handling imbalance. "
            "Generate ROC curves and a precision-recall curve."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
        "expect_keywords": ["fraud", "recall", "model"],
    },
    # ── NEW: ML Model — Student Scores ─────────────────────────────────
    {
        "id": 12,
        "name": "MLModel: Student Exam Score Prediction",
        "workflow_id": 48,
        "message": (
            "Predict student final exam scores. "
            "Features: study_hours_per_week, attendance_pct, previous_gpa (0-4.0), "
            "parent_education (High School/Bachelor/Master/PhD), "
            "extracurricular_activities (0-5), sleep_hours_avg, commute_minutes, "
            "part_time_job (Yes/No), tutoring (Yes/No), practice_tests_completed. "
            "Target: final_score (0-100). "
            "Dataset: 200 students. "
            "Score distribution: mean ~68, std ~15, range 25-98. "
            "Key correlations: study_hours and previous_gpa are strongest predictors. "
            "Train at least 3 models: Linear Regression, Random Forest, Gradient Boosting. "
            "Report RMSE, MAE, and R-squared. "
            "Generate predicted vs actual scatter plot and feature importance chart."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_files": False,  # File gen is best-effort (depends on LLM saving as PNG)
        "expect_keywords": ["model", "rmse", "score"],
    },
]


# ── Test Runner ───────────────────────────────────────────────────────────


def run_single_test(test: dict) -> dict:
    """Run a single workflow test via POST /workflow/{id}/run and return results."""
    test_id = test["id"]
    name = test["name"]
    workflow_id = test["workflow_id"]

    result = {
        "id": test_id,
        "name": name,
        "workflow_id": workflow_id,
        "passed": False,
        "error": None,
        "duration_s": 0,
        "packet_types": {},
        "agents_run": [],
        "python_executions": 0,
        "files_generated": [],
        "files_with_metadata": [],
        "final_answer_length": 0,
        "keyword_hits": [],
    }

    start_time = time.time()

    try:
        # Run workflow via dedicated workflow API
        resp = stream_api("POST", f"workflow/{workflow_id}/run", {
            "message": test["message"],
        })
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
            result["duration_s"] = round(time.time() - start_time, 1)
            return result

        # Parse streaming response
        packet_types = {}
        file_ids = []
        files_info = []
        final_parts = []
        full_text = []  # All text content for keyword matching
        in_final_answer = False

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)

                # Skip session info packets
                if "user_message_id" in data:
                    continue
                if "error" in data and "type" not in data.get("obj", {}):
                    result["error"] = f"Stream error: {data['error'][:200]}"
                    continue

                obj = data.get("obj", data)
                ptype = obj.get("type", "unknown")
                packet_types[ptype] = packet_types.get(ptype, 0) + 1

                # Workflow step tracking
                if ptype == "workflow_step_start":
                    step_name = obj.get("step_name", "?")
                    if step_name not in result["agents_run"]:
                        result["agents_run"].append(step_name)

                elif ptype == "workflow_step_delta":
                    content = obj.get("content", "")
                    if content:
                        full_text.append(content)

                # Python tool tracking
                elif ptype == "python_tool_start":
                    result["python_executions"] += 1
                    code_snippet = obj.get("code", "")
                    if code_snippet:
                        has_savefig = "savefig" in code_snippet
                        has_show = "plt.show" in code_snippet
                        print(f"    [PY#{result['python_executions']}] savefig={has_savefig} show={has_show} len={len(code_snippet)}")

                elif ptype == "python_tool_delta":
                    fids = obj.get("file_ids", [])
                    if fids:
                        file_ids.extend(fids)
                        print(f"    [PY-FILES] {len(fids)} files: {fids[:3]}")
                    pfiles = obj.get("files", [])
                    if pfiles:
                        files_info.extend(pfiles)
                    stdout = obj.get("stdout", "")
                    if stdout:
                        full_text.append(stdout)
                    stderr = obj.get("stderr", "")
                    if stderr:
                        full_text.append(stderr)
                        # Print stderr for debugging chart failures
                        if "Error" in stderr or "error" in stderr:
                            print(f"    [PY-ERR] {stderr[:300]}")
                    # Log exit_code if present
                    exit_code = obj.get("exit_code")
                    if exit_code and exit_code != 0:
                        print(f"    [PY-EXIT] code={exit_code} stdout={stdout[:200] if stdout else ''}")

                # Final answer (promoted output)
                elif ptype == "message_start":
                    in_final_answer = True

                elif ptype == "message_delta":
                    content = obj.get("content", obj.get("delta", ""))
                    if content:
                        if in_final_answer:
                            final_parts.append(content)
                        full_text.append(content)

                elif ptype == "workflow_pause_for_input":
                    result["error"] = f"Workflow paused unexpectedly: {obj.get('questions', '')[:200]}"

                elif ptype == "stop":
                    pass  # Normal completion

            except json.JSONDecodeError:
                pass

        result["duration_s"] = round(time.time() - start_time, 1)
        result["packet_types"] = packet_types
        result["files_generated"] = file_ids
        result["files_with_metadata"] = files_info
        result["final_answer_length"] = sum(len(p) for p in final_parts)

        # Check keyword hits against ALL text (agent output + stdout + final answer)
        combined_text = " ".join(full_text).lower()
        for kw in test.get("expect_keywords", []):
            if kw.lower() in combined_text:
                result["keyword_hits"].append(kw)

        # Validate expectations
        failures = []

        if test.get("expect_python") and result["python_executions"] == 0:
            failures.append("No Python code executed")

        if test.get("expect_files") and len(file_ids) == 0 and len(files_info) == 0:
            failures.append("No files generated")

        # Check enriched metadata (our new PythonToolFile feature)
        if test.get("expect_files") and file_ids and not files_info:
            failures.append("Files generated but no enriched metadata (PythonToolFile missing)")

        missing_kw = set(test.get("expect_keywords", [])) - set(result["keyword_hits"])
        if missing_kw:
            failures.append(f"Missing keywords: {missing_kw}")

        if result["error"] and "paused" in result["error"].lower():
            failures.append(result["error"])

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
    icon = "+" if r["passed"] else "-"
    print(f"\n  [{icon}] Test #{r['id']}: {r['name']}")
    print(f"      Workflow: {r['workflow_id']}  |  Duration: {r['duration_s']}s")
    print(f"      Agents run: {r.get('agents_run', [])}")
    print(f"      Python executions: {r['python_executions']}")

    if r["files_with_metadata"]:
        fnames = [f.get("filename", "?") for f in r["files_with_metadata"]]
        print(f"      Files (enriched): {fnames}")
    elif r["files_generated"]:
        print(f"      File IDs (bare): {r['files_generated']}")
    else:
        print(f"      Files: none")

    print(f"      Keywords found: {r['keyword_hits']}")
    print(f"      Final answer: {r.get('final_answer_length', 0)} chars")
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
    parser.add_argument("--test", type=int, nargs="+", help="Run specific tests by ID (e.g. --test 7 8 9)")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially")
    args = parser.parse_args()
    apply_common_args(args)

    tests = TEST_CASES
    if args.test:
        test_ids = set(args.test)
        tests = [t for t in TEST_CASES if t["id"] in test_ids]
        if not tests:
            print(f"Error: No tests found with IDs={args.test}. Valid IDs: 1-12")
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
        fcount = len(r["files_with_metadata"]) or len(r["files_generated"])
        agents = len(r.get("agents_run", []))
        print(f"  {'[+]' if r['passed'] else '[-]'} #{r['id']} {r['name']:<45} "
              f"{r['duration_s']:>6}s  agents={agents}  py={r['python_executions']}  files={fcount}")

    if failed:
        print(f"\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  #{r['id']} {r['name']}: {r['error']}")

    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
