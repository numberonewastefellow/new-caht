"""
Data Science Tutor Workflow -- Test Suite
==========================================

Tests the Data Science Tutor workflow which combines LLM explanation with
live code execution (Code Interpreter / PythonTool).

Test cases:
  1. Linear regression (math + from-scratch implementation)
  2. Pandas groupby (practical data wrangling)
  3. HITL: Vague topic triggers clarification

Usage:
    python test_data_science_tutor.py                    # Run all tests
    python test_data_science_tutor.py --test 1           # Run specific test
    python test_data_science_tutor.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time

from config import (
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)


# -- Constants ----------------------------------------------------------------

WORKFLOW_NAME = "Data Science Tutor"


# -- Test Definitions ---------------------------------------------------------

TESTS = [
    {
        "id": 1,
        "name": "Linear regression from scratch",
        "message": (
            "Teach me linear regression from scratch. "
            "Show me the math, then implement it in Python without sklearn."
        ),
        "is_hitl": False,
        "expected_agents": [
            "Concept Explainer",
            "Code Demonstrator",
            "Practice Generator",
            "Summary Reporter",
        ],
        "expect_python": True,
        "expected_in_output": ["regression", "slope"],
        "min_answer_length": 200,
        "purpose": (
            "Verifies full 4-phase flow: concept explanation, "
            "code demo with PythonTool, practice exercise, summary."
        ),
    },
    {
        "id": 2,
        "name": "Pandas groupby and pivot tables",
        "message": (
            "I want to learn pandas groupby and pivot tables. "
            "Show me with real examples using sample sales data."
        ),
        "is_hitl": False,
        "expected_agents": [
            "Concept Explainer",
            "Code Demonstrator",
            "Practice Generator",
            "Summary Reporter",
        ],
        "expect_python": True,
        "expected_in_output": ["groupby", "pivot"],
        "min_answer_length": 200,
        "purpose": (
            "Verifies practical data wrangling topic triggers "
            "code execution with pandas."
        ),
    },
    {
        "id": 3,
        "name": "HITL: Vague topic 'teach me data science'",
        "message": "Teach me data science",
        "is_hitl": True,
        "expected_agents": ["Concept Explainer"],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["?"],
        "min_answer_length": 0,
        "purpose": (
            "Verifies HITL: Vague topic triggers Concept Explainer's "
            "[NEEDS_INPUT] with clarifying questions."
        ),
    },
]


# -- Helpers ------------------------------------------------------------------


def _safe_print(text: str, **kwargs):
    """Print with Unicode fallback for Windows terminals."""
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe, **kwargs)


def find_workflow_id() -> int | None:
    """Find the Data Science Tutor workflow by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def run_workflow_test(workflow_id: int, message: str) -> dict:
    """Run a workflow and collect structured results."""
    result = {
        "agents_run": [],
        "was_paused": False,
        "pause_text": "",
        "final_answer": "",
        "completed": False,
        "python_executions": 0,
        "files_generated": [],
        "error": None,
        "duration_s": 0,
    }

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", {"message": message})

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

    current_agent = None
    in_final_answer = False
    final_parts = []
    all_text_parts = []

    try:
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                packet = json.loads(line)

                if "error" in packet and "type" not in packet.get("obj", {}):
                    result["error"] = packet["error"][:200]
                    continue

                obj = packet.get("obj", packet)
                ptype = obj.get("type", "")

                if ptype == "workflow_step_start":
                    current_agent = obj.get("step_name", "?")
                    if current_agent not in result["agents_run"]:
                        result["agents_run"].append(current_agent)

                elif ptype == "workflow_step_delta":
                    content = obj.get("content", "")
                    if content:
                        all_text_parts.append(content)

                elif ptype == "workflow_pause_for_input":
                    result["was_paused"] = True
                    result["pause_text"] = obj.get("questions", "")

                elif ptype == "python_tool_start":
                    result["python_executions"] += 1

                elif ptype == "python_tool_delta":
                    fids = obj.get("file_ids", [])
                    if fids:
                        result["files_generated"].extend(fids)
                    stdout = obj.get("stdout", "")
                    if stdout:
                        all_text_parts.append(stdout)

                elif ptype == "message_start":
                    in_final_answer = True

                elif ptype == "message_delta":
                    content = obj.get("content", obj.get("delta", ""))
                    if content:
                        if in_final_answer:
                            final_parts.append(content)
                        all_text_parts.append(content)

                elif ptype == "stop":
                    result["completed"] = True

            except json.JSONDecodeError:
                pass
    except Exception as e:
        if not result["error"]:
            result["error"] = f"Stream error: {type(e).__name__}: {str(e)[:150]}"
        if result["agents_run"] and not result["completed"]:
            result["completed"] = True  # treat as complete if we got some data

    result["final_answer"] = "".join(final_parts)
    result["all_text"] = "".join(all_text_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# -- Test Runner --------------------------------------------------------------


def run_test(test_def: dict, workflow_id: int) -> dict:
    """Run a single test and return pass/fail result."""
    name = test_def["name"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_def['id']}: {name}")
    print(f"  Message: \"{test_def['message'][:80]}{'...' if len(test_def['message']) > 80 else ''}\"")
    print(f"  HITL: {test_def['is_hitl']}")
    print(f"{'='*60}")

    result = run_workflow_test(workflow_id, test_def["message"])

    issues = []

    # Check for errors
    if result["error"]:
        issues.append(f"Error: {result['error']}")

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in result["agents_run"]:
            issues.append(f"Agent '{agent}' did not run")

    # For HITL tests: verify pause
    if test_def["is_hitl"]:
        if not result["was_paused"]:
            issues.append("Expected workflow to pause for input but it didn't")
        pause_keywords = test_def.get("expected_pause_keywords", [])
        for kw in pause_keywords:
            if kw.lower() not in result.get("pause_text", "").lower():
                issues.append(f"Pause text missing keyword: '{kw}'")
    else:
        # Non-HITL: check completion
        if not result["completed"]:
            issues.append("Workflow did not complete (no 'stop' packet)")

        # Check Python execution
        if test_def.get("expect_python"):
            if result["python_executions"] == 0:
                issues.append("Expected Python code execution but none detected")

        # Check output keywords
        all_text = result.get("all_text", "").lower()
        for kw in test_def.get("expected_in_output", []):
            if kw.lower() not in all_text:
                issues.append(f"Output missing keyword: '{kw}'")

        # Check minimum answer length
        min_len = test_def.get("min_answer_length", 0)
        final_len = len(result.get("final_answer", ""))
        if min_len > 0 and final_len < min_len:
            issues.append(f"Final answer too short: {final_len} chars (min {min_len})")

    # Report
    passed = len(issues) == 0
    status = "PASS" if passed else "FAIL"

    print(f"\n--- Results ---")
    print(f"  Status: {status}")
    print(f"  Duration: {result['duration_s']}s")
    print(f"  Agents run: {result['agents_run']}")
    print(f"  Python executions: {result['python_executions']}")
    if result["was_paused"]:
        _safe_print(f"  Paused: Yes")
        _safe_print(f"  Pause text: {result['pause_text'][:200]}")
    if result["final_answer"]:
        _safe_print(f"  Final answer: {result['final_answer'][:200]}...")

    if issues:
        print(f"\n  Issues:")
        for issue in issues:
            print(f"    - {issue}")

    return {
        "test_id": test_def["id"],
        "name": name,
        "passed": passed,
        "issues": issues,
        "duration_s": result["duration_s"],
        "agents_run": result["agents_run"],
        "python_execs": result["python_executions"],
    }


def main():
    parser = argparse.ArgumentParser(description="Test Data Science Tutor workflow")
    parser.add_argument("--test", "-t", type=int, help="Run specific test by ID")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)

    # Find workflow
    wf_id = find_workflow_id()
    if wf_id is None:
        print(f"\n[ERROR] Workflow '{WORKFLOW_NAME}' not found.")
        print("Deploy it first: python create_workflows.py --file workflows/31_data_science_tutor.json")
        sys.exit(1)

    print(f"\nFound '{WORKFLOW_NAME}' (ID={wf_id})")

    # Select tests
    if args.test:
        selected = [t for t in TESTS if t["id"] == args.test]
        if not selected:
            print(f"[ERROR] No test with ID={args.test}")
            sys.exit(1)
    else:
        selected = TESTS

    print(f"Running {len(selected)} test(s)...\n")

    # Run
    results = []
    for test_def in selected:
        r = run_test(test_def, wf_id)
        results.append(r)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{len(results)} passed, {failed} failed")
    print(f"{'='*60}")

    for r in results:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{icon}] #{r['test_id']} {r['name']} ({r['duration_s']}s, {r['python_execs']} py execs)")
        if not r["passed"]:
            for issue in r["issues"]:
                print(f"         - {issue}")

    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
