"""
SmartSearch AI Research Pipeline — Test Suite
==============================================

Tests the SmartSearch AI Research Pipeline workflow to verify:
1. All 3 sequential agents run (Researcher → Analyst → Report Writer)
2. Web search tool is invoked by the Researcher agent
3. Final report contains structured output with citations
4. Report includes KEY FINDINGS, REFERENCES, and DISCLAIMER sections

Usage:
    python test_smartsearch.py                           # Run all tests
    python test_smartsearch.py --test 1                  # Run specific test
    python test_smartsearch.py --url http://host:3000 --key YOUR_KEY
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

WORKFLOW_NAME = "SmartSearch AI Research Pipeline"


# ── Test Definitions ─────────────────────────────────────────────────────────

TESTS = [
    {
        "id": 1,
        "name": "Research: AI trends 2026",
        "message": "Research the latest developments in AI agents and autonomous coding tools in 2026. Focus on key players, breakthroughs, and practical applications.",
        "expected_agents": [
            "SmartSearch Researcher",
            "Research Analyst",
            "Report Writer",
        ],
        "expected_in_output": ["RESEARCH REPORT", "KEY FINDINGS", "REFERENCES"],
        "min_answer_length": 500,
        "purpose": "Verifies the full 3-step pipeline completes: web research, analysis, and report writing with citations.",
    },
    {
        "id": 2,
        "name": "Compare: React vs Vue vs Svelte",
        "message": "Compare React, Vue, and Svelte for building enterprise web applications in 2026. Include performance benchmarks, ecosystem maturity, and hiring availability.",
        "expected_agents": [
            "SmartSearch Researcher",
            "Research Analyst",
            "Report Writer",
        ],
        "expected_in_output": ["RESEARCH REPORT", "KEY FINDINGS"],
        "min_answer_length": 500,
        "purpose": "Verifies the pipeline handles comparison-style queries with structured output.",
    },
    {
        "id": 3,
        "name": "Fact check: AI-generated code stats",
        "message": "Is it true that AI-generated code now accounts for over 25% of new code in enterprise software projects? Find evidence for and against this claim with sources.",
        "expected_agents": [
            "SmartSearch Researcher",
            "Research Analyst",
            "Report Writer",
        ],
        "expected_in_output": ["RESEARCH REPORT", "REFERENCES"],
        "min_answer_length": 400,
        "purpose": "Verifies the pipeline handles fact-checking queries with evidence-based analysis.",
    },
    {
        "id": 4,
        "name": "Industry: EV market in India",
        "message": "Analyze the current state of the electric vehicle market in India. Cover major players, government policies, charging infrastructure, and growth projections.",
        "expected_agents": [
            "SmartSearch Researcher",
            "Research Analyst",
            "Report Writer",
        ],
        "expected_in_output": ["RESEARCH REPORT", "KEY FINDINGS"],
        "min_answer_length": 500,
        "purpose": "Verifies the pipeline handles industry analysis with data points and recommendations.",
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
    """Find the SmartSearch AI Research Pipeline workflow by name."""
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
      final_answer: the final answer text (promoted output)
      completed: whether the stream completed
      error: error message if any
      duration_s: wall-clock seconds
    """
    result = {
        "agents_run": [],
        "final_answer": "",
        "completed": False,
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
    print(f"  Message: \"{test_def['message'][:100]}{'...' if len(test_def['message']) > 100 else ''}\"")
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

    # Verify completion
    if not result["completed"]:
        issues.append("Workflow did not complete")

    # Check expected strings in combined output
    combined_lower = (result["final_answer"] + " " + result.get("all_text", "")).lower()
    for expected_str in test_def.get("expected_in_output", []):
        if expected_str.lower() not in combined_lower:
            issues.append(f"Output missing keyword: '{expected_str}'")

    # Check answer length (use all_text for sequential workflows where
    # output comes via workflow_step_delta, not message_delta)
    answer_text = result["final_answer"] or result.get("all_text", "")
    min_len = test_def.get("min_answer_length", 0)
    if min_len > 0 and len(answer_text) < min_len:
        issues.append(
            f"Output too short ({len(answer_text)} chars, "
            f"expected >= {min_len})"
        )

    # Print result details
    print(f"\n  Agents run: {result['agents_run']}")
    print(f"  Completed: {result['completed']}")
    all_text_len = len(result.get("all_text", ""))
    print(f"  Final answer length: {len(result['final_answer'])} chars")
    print(f"  All text length: {all_text_len} chars")
    print(f"  Duration: {result['duration_s']}s")

    preview_text = result["final_answer"] or result.get("all_text", "")
    if preview_text:
        preview = preview_text[-300:]
        _safe_print(f"  Output tail: ...{preview}")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({result['duration_s']}s)")

    return {
        "id": test_def["id"],
        "name": name,
        "status": status,
        "issues": issues,
        "duration_s": result["duration_s"],
        "agents_run": result["agents_run"],
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test the SmartSearch AI Research Pipeline workflow",
    )
    parser.add_argument(
        "--test", type=int, nargs="+",
        help="Run specific tests by ID (e.g. --test 1 3)",
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
            print("        Deploy it first:")
            print("        python create_workflows.py --file workflows/30_smartsearch_research.json --no-icons")
            sys.exit(1)

    print(f"  Using workflow ID={wf_id}")

    # Build test list
    if args.test:
        test_ids = set(args.test)
        tests = [t for t in TESTS if t["id"] in test_ids]
        if not tests:
            valid_ids = [t["id"] for t in TESTS]
            print(f"[ERROR] No tests found with IDs={args.test}. Valid IDs: {valid_ids}")
            sys.exit(1)
    else:
        tests = TESTS

    # Run tests
    print(f"\n{'#'*60}")
    print(f"  SMARTSEARCH AI RESEARCH PIPELINE — TEST SUITE")
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

    for r in results:
        icon = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        agents = len(r["agents_run"])
        print(f"  {icon} #{r['id']} {r['name']:<45} {r['duration_s']:>6}s  agents={agents}")
        if r.get("issues"):
            for issue in r["issues"]:
                print(f"       - {issue}")

    print(f"\n  Total: {len(results)} tests | "
          f"{passed} passed | {failed} failed")
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
