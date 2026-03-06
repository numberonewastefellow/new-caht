"""
Discussion & Debate Panel Workflow — Test Suite
================================================

Tests the Discussion & Debate Panel workflow across all three modes:
  - DISCUSSION mode: Topic debate with 4 panelists + synthesizer
  - TECHNICAL mode: Code/data task routed to Code Engineer / Data Analyst
  - MIXED mode: Both discussion panelists AND coding agents
  - HITL mode: Vague topic triggers moderator clarification questions

Also tests the Moderator check-in (pause between rounds) flow.

Usage:
    python test_discussion_workflow.py                    # Run all tests
    python test_discussion_workflow.py --only-hitl        # Test only HITL (vague topics)
    python test_discussion_workflow.py --only-discussion  # Test only DISCUSSION mode
    python test_discussion_workflow.py --only-technical   # Test only TECHNICAL mode
    python test_discussion_workflow.py --only-mixed       # Test only MIXED mode
    python test_discussion_workflow.py --test 1           # Run specific test by ID
    python test_discussion_workflow.py --url http://host:3000 --key YOUR_KEY
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


# ── Constants ────────────────────────────────────────────────────────────────

WORKFLOW_NAME = "Discussion & Debate Panel"


# ── Test Definitions ─────────────────────────────────────────────────────────

DISCUSSION_TESTS = [
    {
        "id": 1,
        "name": "DISCUSSION: AI grading essays",
        "mode": "discussion",
        "message": "Should AI be used to grade student essays in schools?",
        "is_hitl": False,
        "expected_agents": [
            "Topic Moderator",
            "Scholar Agent",
            "Advocate Agent",
            "Critic Agent",
            "Practitioner Agent",
            "Discussion Synthesizer",
        ],
        "expect_python": False,
        "expected_in_output": ["summary", "agree"],
        "min_answer_length": 200,
        "purpose": "Verifies full DISCUSSION flow: Moderator scopes immediately (clear topic), "
                   "all 4 panelists give opening statements, Moderator check-in, Synthesizer wraps up.",
    },
    {
        "id": 2,
        "name": "DISCUSSION: Remote vs hybrid work",
        "mode": "discussion",
        "message": "Is fully remote work better than hybrid or in-office for software engineering teams?",
        "is_hitl": False,
        "expected_agents": [
            "Topic Moderator",
            "Scholar Agent",
            "Advocate Agent",
            "Critic Agent",
            "Practitioner Agent",
            "Discussion Synthesizer",
        ],
        "expect_python": False,
        "expected_in_output": ["remote", "hybrid"],
        "min_answer_length": 200,
        "purpose": "Verifies panelists reference each other's points in a workplace debate.",
    },
]

TECHNICAL_TESTS = [
    {
        "id": 3,
        "name": "TECHNICAL: Debug discount function",
        "mode": "technical",
        "message": (
            "Debug this Python function. It should apply a 10% discount only to items "
            "over $100, but it discounts everything:\n\n"
            "def calculate_discount(items, threshold=100):\n"
            "    discounted = []\n"
            "    for item in items:\n"
            "        item['price'] = item['price'] * 0.9\n"
            "        if item['price'] > threshold:\n"
            "            discounted.append(item)\n"
            "    return discounted\n\n"
            "Test: [{'name': 'A', 'price': 50}, {'name': 'B', 'price': 150}]\n"
            "Expected: Only B gets discount."
        ),
        "is_hitl": False,
        "expected_agents": [
            "Topic Moderator",
            "Code Engineer",
            "Discussion Synthesizer",
        ],
        "expect_python": True,
        "expected_in_output": ["fix", "discount"],
        "min_answer_length": 100,
        "purpose": "Verifies TECHNICAL mode: Moderator classifies as TECHNICAL, "
                   "Code Engineer executes Python to fix the bug, Synthesizer reports.",
    },
    {
        "id": 4,
        "name": "TECHNICAL: Data analysis request",
        "mode": "technical",
        "message": (
            "Analyze sample sales data with columns: month, product (A/B/C), region "
            "(North/South/East/West), revenue, units_sold. 24 rows over 6 months. "
            "I want to know: which product has the highest revenue growth? "
            "Which region is underperforming? Show me a chart."
        ),
        "is_hitl": False,
        "expected_agents": [
            "Topic Moderator",
            "Data Analyst",
            "Discussion Synthesizer",
        ],
        "expect_python": True,
        "expected_in_output": ["revenue", "product"],
        "min_answer_length": 100,
        "purpose": "Verifies TECHNICAL mode: Moderator classifies as TECHNICAL, "
                   "Data Analyst generates sample data and creates visualizations.",
    },
]

MIXED_TESTS = [
    {
        "id": 5,
        "name": "MIXED: Open-source vs proprietary LLMs with cost analysis",
        "mode": "mixed",
        "message": (
            "Should companies build on open-source LLMs or use proprietary APIs "
            "like GPT-4 and Claude? Show me a cost comparison with sample data "
            "for a company doing 1M API calls per month."
        ),
        "is_hitl": False,
        "expected_agents": [
            "Topic Moderator",
            "Discussion Synthesizer",
        ],
        # In MIXED mode, we expect SOME panelists + SOME coding agents
        # but exact routing depends on the orchestrator LLM's decisions
        "expect_python": True,
        "expected_in_output": ["cost", "open"],
        "min_answer_length": 200,
        "purpose": "Verifies MIXED mode: Both discussion panelists and coding agents "
                   "contribute. Data Analyst or Code Engineer should produce cost comparison.",
    },
]

HITL_TESTS = [
    {
        "id": 6,
        "name": "HITL: Vague topic 'discuss cryptocurrency'",
        "mode": "hitl",
        "message": "Let's discuss cryptocurrency",
        "is_hitl": True,
        "expected_agents": ["Topic Moderator"],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["?"],
        "min_answer_length": 0,
        "purpose": "Verifies HITL: Vague topic triggers Moderator's [NEEDS_INPUT] "
                   "with clarifying questions about which aspect of crypto to discuss.",
    },
    {
        "id": 7,
        "name": "HITL: Vague topic 'talk about AI'",
        "mode": "hitl",
        "message": "Let's talk about artificial intelligence",
        "is_hitl": True,
        "expected_agents": ["Topic Moderator"],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["?"],
        "min_answer_length": 0,
        "purpose": "Verifies HITL: Very broad topic triggers Moderator scoping questions.",
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────


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
    """Find the Discussion & Debate Panel workflow by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def run_workflow_test(workflow_id: int, message: str) -> dict:
    """Run a workflow and collect structured results.

    Returns dict with:
      agents_run: list of step names that produced output
      was_paused: whether workflow paused for input
      pause_text: the pause questions text (if paused)
      final_answer: the final answer text (promoted output)
      completed: whether the stream completed
      python_executions: number of PythonTool executions
      error: error message if any
      duration_s: wall-clock seconds
    """
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

    result["final_answer"] = "".join(final_parts)
    result["all_text"] = "".join(all_text_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_test(test_def: dict, workflow_id: int) -> dict:
    """Run a single test and return pass/fail result."""
    name = test_def["name"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_def['id']}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Message: \"{test_def['message'][:100]}{'...' if len(test_def['message']) > 100 else ''}\"")
    print(f"  HITL: {test_def['is_hitl']}")
    print(f"{'='*60}")

    result = run_workflow_test(workflow_id, test_def["message"])

    # Analyze results
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
            issues.append("Expected PAUSE but workflow did not pause")
        else:
            pause_lower = result["pause_text"].lower()
            for kw in test_def.get("expected_pause_keywords", []):
                if kw.lower() not in pause_lower:
                    issues.append(f"Pause text missing keyword: '{kw}'")

    # For non-HITL tests: verify completion and output
    if not test_def["is_hitl"]:
        if not result["completed"]:
            issues.append("Workflow did not complete")

        # Check expected strings in combined output (final answer + agent outputs)
        combined_lower = (result["final_answer"] + " " + result.get("all_text", "")).lower()
        for expected_str in test_def.get("expected_in_output", []):
            if expected_str.lower() not in combined_lower:
                issues.append(f"Output missing keyword: '{expected_str}'")

        # Check Python execution
        if test_def.get("expect_python") and result["python_executions"] == 0:
            issues.append("Expected Python code execution but none occurred")

        # Check answer length
        min_len = test_def.get("min_answer_length", 0)
        if min_len > 0 and len(result["final_answer"]) < min_len:
            issues.append(
                f"Final answer too short ({len(result['final_answer'])} chars, "
                f"expected >= {min_len})"
            )

    # Print result details
    print(f"\n  Agents run: {result['agents_run']}")
    print(f"  Paused: {result['was_paused']}")
    print(f"  Completed: {result['completed']}")
    print(f"  Python executions: {result['python_executions']}")
    print(f"  Files generated: {len(result['files_generated'])}")
    print(f"  Final answer length: {len(result['final_answer'])} chars")
    print(f"  Duration: {result['duration_s']}s")

    if result["was_paused"] and result["pause_text"]:
        preview = result["pause_text"][:200]
        _safe_print(f"  Pause preview: {preview}...")

    if result["final_answer"]:
        preview = result["final_answer"][:200]
        _safe_print(f"  Answer preview: {preview}...")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({result['duration_s']}s)")

    return {
        "id": test_def["id"],
        "name": name,
        "mode": test_def["mode"],
        "status": status,
        "issues": issues,
        "duration_s": result["duration_s"],
        "agents_run": result["agents_run"],
        "python_executions": result["python_executions"],
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test the Discussion & Debate Panel workflow",
    )
    parser.add_argument(
        "--only-discussion", action="store_true",
        help="Only test DISCUSSION mode",
    )
    parser.add_argument(
        "--only-technical", action="store_true",
        help="Only test TECHNICAL mode",
    )
    parser.add_argument(
        "--only-mixed", action="store_true",
        help="Only test MIXED mode",
    )
    parser.add_argument(
        "--only-hitl", action="store_true",
        help="Only test HITL (vague topic) mode",
    )
    parser.add_argument(
        "--test", type=int, nargs="+",
        help="Run specific tests by ID (e.g. --test 1 3 5)",
    )
    parser.add_argument(
        "--workflow-id", type=int, default=None,
        help="Use a specific workflow ID instead of auto-detecting",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    # Find workflow
    if args.workflow_id:
        wf_id = args.workflow_id
    else:
        print(f"\nLooking for workflow: '{WORKFLOW_NAME}'...")
        wf_id = find_workflow_id()
        if wf_id is None:
            print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found on server.")
            print("        Deploy it first: python create_workflows.py --file workflows/21_discussion_debate.json")
            sys.exit(1)

    print(f"  Using workflow ID={wf_id}")

    # Build test list
    all_tests = DISCUSSION_TESTS + TECHNICAL_TESTS + MIXED_TESTS + HITL_TESTS

    if args.test:
        test_ids = set(args.test)
        tests = [t for t in all_tests if t["id"] in test_ids]
        if not tests:
            valid_ids = [t["id"] for t in all_tests]
            print(f"[ERROR] No tests found with IDs={args.test}. Valid IDs: {valid_ids}")
            sys.exit(1)
    elif args.only_discussion:
        tests = DISCUSSION_TESTS
    elif args.only_technical:
        tests = TECHNICAL_TESTS
    elif args.only_mixed:
        tests = MIXED_TESTS
    elif args.only_hitl:
        tests = HITL_TESTS
    else:
        tests = all_tests

    # Run tests
    print(f"\n{'#'*60}")
    print(f"  DISCUSSION WORKFLOW TEST SUITE")
    print(f"  Running {len(tests)} test(s)")
    print(f"{'#'*60}")

    results = []
    total_start = time.time()

    for test_def in tests:
        result = run_test(test_def, wf_id)
        results.append(result)

    total_time = time.time() - total_start

    # Summary
    print(f"\n\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    # Group by mode
    modes = {}
    for r in results:
        mode = r["mode"]
        if mode not in modes:
            modes[mode] = {"pass": 0, "fail": 0}
        if r["status"] == "PASS":
            modes[mode]["pass"] += 1
        else:
            modes[mode]["fail"] += 1

    for r in results:
        icon = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        agents = len(r["agents_run"])
        py = r["python_executions"]
        print(f"  {icon} #{r['id']} {r['name']:<50} {r['duration_s']:>6}s  agents={agents}  py={py}")
        if r.get("issues"):
            for issue in r["issues"]:
                print(f"       - {issue}")

    print(f"\n  By mode:")
    for mode, counts in modes.items():
        print(f"    {mode.upper():12s}: {counts['pass']} passed, {counts['fail']} failed")

    print(f"\n  Total: {len(results)} tests | "
          f"{passed} passed | {failed} failed")
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
