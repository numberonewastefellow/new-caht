"""
Test Runner for Universal Problem Solver Workflow
===================================================

Tests the Universal Problem Solver workflow with 2 test cases designed to
verify correct agent routing:

  Test 1: Coding Bug — expects Problem Analyzer → Code Engineer → Report Synthesizer
  Test 2: Data Analysis — expects Problem Analyzer → Data Analyst → Report Synthesizer

The test resolves the workflow ID by name (no hardcoded IDs).

Usage:
    python test_universal_solver.py
    python test_universal_solver.py --url http://192.168.1.10:3000
    python test_universal_solver.py --test 1         # Run only test #1
    python test_universal_solver.py --sequential     # Run sequentially
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

WORKFLOW_NAME = "Universal Problem Solver"

# ── Test Definitions ──────────────────────────────────────────────────────

TEST_CASES = [
    # Test 1: Coding Bug → should route to: Analyzer → Code Engineer → Synthesizer
    {
        "id": 1,
        "name": "UPS: Coding Bug (Discount Logic)",
        "message": (
            "Bug in our pricing module. The function `apply_tiered_pricing(amount, tiers)` "
            "should apply the HIGHEST matching tier discount, but it applies the FIRST match.\n\n"
            "Code:\n"
            "```python\n"
            "def apply_tiered_pricing(amount, tiers):\n"
            "    \"\"\"Apply tiered pricing. tiers = [(min_amount, discount_pct), ...]\"\"\"\n"
            "    for min_amt, discount in tiers:\n"
            "        if amount >= min_amt:\n"
            "            return round(amount * (1 - discount / 100), 2)\n"
            "    return amount\n"
            "\n"
            "tiers = [(100, 5), (500, 10), (1000, 15)]  # $100+=5%, $500+=10%, $1000+=15%\n"
            "```\n\n"
            "Test that fails:\n"
            "```python\n"
            "print(apply_tiered_pricing(1500, tiers))\n"
            "# Expected: 1275.0 (15% off — matches $1000+ tier)\n"
            "# Actual:   1425.0 (5% off — matches $100+ tier first)\n"
            "```\n\n"
            "The tiers list is ordered ascending, so the function hits the lowest tier first "
            "and returns immediately instead of checking for a better match."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_keywords": ["fix", "tier", "discount"],
        "expect_agents": ["Problem Analyzer & Planner", "Code Engineer"],
        "reject_agents": ["Knowledge Researcher", "Data Analyst & Visualizer", "ML Engineer"],
    },
    # Test 2: Data Analysis → should route to: Analyzer → Data Analyst → Synthesizer
    {
        "id": 2,
        "name": "UPS: Data Analysis (Sales by Region)",
        "message": (
            "Sales data: CSV with columns month (Jan-Dec 2024), region "
            "(North/South/East/West), product_category (Electronics/Clothing/Food/Home), "
            "revenue, units_sold, returns, avg_rating (1-5). "
            "48 rows (12 months x 4 regions). "
            "Analysis objectives: "
            "Calculate total revenue by region and identify the top performer. "
            "Find which product category has the highest return rate. "
            "Create a monthly revenue trend chart broken down by region. "
            "Identify seasonal patterns — which months have highest sales."
        ),
        "timeout": 600,
        "expect_python": True,
        "expect_keywords": ["revenue", "region"],
        "expect_agents": ["Problem Analyzer & Planner", "Data Analyst & Visualizer"],
        "reject_agents": ["Code Engineer", "ML Engineer"],
    },
]


# ── Workflow ID Resolution ────────────────────────────────────────────────


def resolve_workflow_id(name: str) -> int | None:
    """Find a workflow ID by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"  [ERROR] GET /workflow failed: {resp.status_code}")
        return None

    for wf in resp.json():
        if wf["name"].lower() == name.lower():
            return wf["id"]
    return None


# ── Test Runner ───────────────────────────────────────────────────────────


def run_single_test(test: dict, workflow_id: int) -> dict:
    """Run a single workflow test and validate agent routing."""
    test_id = test["id"]
    name = test["name"]

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
        "routing_correct": False,
    }

    start_time = time.time()

    try:
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
        full_text = []
        in_final_answer = False

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)

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
                    print(f"    [AGENT] >> {step_name}")

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
                        print(f"    [PY#{result['python_executions']}] savefig={has_savefig} show={has_show}")

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
                        if "Error" in stderr or "error" in stderr:
                            print(f"    [PY-ERR] {stderr[:300]}")

                elif ptype == "message_start":
                    in_final_answer = True

                elif ptype == "message_delta":
                    content = obj.get("content", obj.get("delta", ""))
                    if content:
                        if in_final_answer:
                            final_parts.append(content)
                        full_text.append(content)

                elif ptype == "workflow_pause_for_input":
                    result["error"] = f"Workflow paused: {obj.get('questions', '')[:200]}"

            except json.JSONDecodeError:
                pass

        result["duration_s"] = round(time.time() - start_time, 1)
        result["packet_types"] = packet_types
        result["files_generated"] = file_ids
        result["files_with_metadata"] = files_info
        result["final_answer_length"] = sum(len(p) for p in final_parts)

        # Keyword hits
        combined_text = " ".join(full_text).lower()
        for kw in test.get("expect_keywords", []):
            if kw.lower() in combined_text:
                result["keyword_hits"].append(kw)

        # ── Validate ──────────────────────────────────────────────────
        failures = []

        # 1. Python execution
        if test.get("expect_python") and result["python_executions"] == 0:
            failures.append("No Python code executed")

        # 2. Keywords
        missing_kw = set(test.get("expect_keywords", [])) - set(result["keyword_hits"])
        if missing_kw:
            failures.append(f"Missing keywords: {missing_kw}")

        # 3. Unexpected pause
        if result["error"] and "paused" in result["error"].lower():
            failures.append(result["error"])

        # 4. Agent routing validation (KEY CHECK)
        agents_run_set = set(result["agents_run"])

        # Check expected agents were called
        for expected in test.get("expect_agents", []):
            if expected not in agents_run_set:
                failures.append(f"Expected agent NOT called: '{expected}'")

        # Check rejected agents were NOT called
        for rejected in test.get("reject_agents", []):
            if rejected in agents_run_set:
                failures.append(f"Wrong agent called: '{rejected}' (should not be used for this problem)")

        # Synthesizer should always be called
        if "Report Synthesizer" not in agents_run_set:
            failures.append("Report Synthesizer not called (should always be the final agent)")

        # Check agent routing correctness (all expected present, no rejected)
        expected_ok = all(e in agents_run_set for e in test.get("expect_agents", []))
        rejected_ok = all(r not in agents_run_set for r in test.get("reject_agents", []))
        result["routing_correct"] = expected_ok and rejected_ok

        if failures:
            result["error"] = "; ".join(failures)
        else:
            result["passed"] = True

    except Exception as e:
        result["error"] = f"Exception: {str(e)[:200]}"
        result["duration_s"] = round(time.time() - start_time, 1)

    return result


def print_result(r: dict) -> None:
    """Pretty-print a test result with agent routing details."""
    icon = "+" if r["passed"] else "-"
    routing_icon = "OK" if r.get("routing_correct") else "WRONG"

    print(f"\n  [{icon}] Test #{r['id']}: {r['name']}")
    print(f"      Workflow: {r['workflow_id']}  |  Duration: {r['duration_s']}s")
    print(f"      Agents run: {r.get('agents_run', [])}")
    print(f"      Routing: [{routing_icon}]")
    print(f"      Python executions: {r['python_executions']}")

    if r["files_with_metadata"]:
        fnames = [f.get("filename", "?") for f in r["files_with_metadata"]]
        print(f"      Files (enriched): {fnames}")
    elif r["files_generated"]:
        print(f"      File IDs: {r['files_generated']}")
    else:
        print(f"      Files: none")

    print(f"      Keywords found: {r['keyword_hits']}")
    print(f"      Final answer: {r.get('final_answer_length', 0)} chars")

    if r["error"]:
        print(f"      Error: {r['error']}")


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test Universal Problem Solver workflow — agent routing validation"
    )
    add_common_args(parser)
    parser.add_argument("--test", type=int, nargs="+", help="Run specific tests by ID (1 or 2)")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially")
    args = parser.parse_args()
    apply_common_args(args)

    # Resolve workflow ID by name
    print(f"\n  Resolving workflow '{WORKFLOW_NAME}'...")
    workflow_id = resolve_workflow_id(WORKFLOW_NAME)
    if workflow_id is None:
        print(f"\n  [ERROR] Workflow '{WORKFLOW_NAME}' not found on server.")
        print(f"  Deploy it first:")
        print(f"    python create_workflows.py --file workflows/20_universal_problem_solver.json")
        sys.exit(1)
    print(f"  Found: workflow_id={workflow_id}")

    tests = TEST_CASES
    if args.test:
        test_ids = set(args.test)
        tests = [t for t in TEST_CASES if t["id"] in test_ids]
        if not tests:
            print(f"Error: No tests found with IDs={args.test}. Valid IDs: 1-2")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  UNIVERSAL PROBLEM SOLVER — AGENT ROUTING TEST")
    print(f"  Workflow: {WORKFLOW_NAME} (ID={workflow_id})")
    print(f"  Tests: {len(tests)} | Mode: {'sequential' if args.sequential else 'parallel'}")
    print(f"  Server: {CONFIG['base_url']}")
    print(f"{'='*70}")

    for t in tests:
        expect = ", ".join(t.get("expect_agents", []))
        reject = ", ".join(t.get("reject_agents", []))
        print(f"  #{t['id']} {t['name']}")
        print(f"      Expect: {expect} + Report Synthesizer")
        print(f"      Reject: {reject}")

    print(f"\nStarting tests...\n")
    start_all = time.time()
    results = []

    if args.sequential or len(tests) == 1:
        for t in tests:
            print(f"  Running #{t['id']}: {t['name']}...")
            r = run_single_test(t, workflow_id)
            results.append(r)
            print_result(r)
    else:
        with ThreadPoolExecutor(max_workers=len(tests)) as executor:
            futures = {executor.submit(run_single_test, t, workflow_id): t for t in tests}
            print(f"  Launched {len(futures)} tests in parallel...")
            for future in as_completed(futures):
                r = future.result()
                results.append(r)
                print_result(r)

    total_time = round(time.time() - start_all, 1)
    results.sort(key=lambda r: r["id"])

    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    routing_correct = sum(1 for r in results if r.get("routing_correct"))

    print(f"\n{'='*70}")
    print(f"  RESULTS: {passed}/{len(results)} passed  |  Routing: {routing_correct}/{len(results)} correct  |  Total: {total_time}s")
    print(f"{'='*70}")

    for r in results:
        routing = "OK" if r.get("routing_correct") else "WRONG"
        agents = " >> ".join(r.get("agents_run", []))
        print(f"  {'[+]' if r['passed'] else '[-]'} #{r['id']} {r['name']:<40} "
              f"{r['duration_s']:>6}s  routing=[{routing}]  py={r['python_executions']}")
        print(f"       Agents: {agents}")

    if failed:
        print(f"\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  #{r['id']} {r['name']}: {r['error']}")

    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
