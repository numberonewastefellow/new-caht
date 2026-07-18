"""
M&A Due Diligence Panel Workflow — Test Suite
==============================================

Tests the M&A Due Diligence Panel workflow with 3 deal scenarios:
  - D1: SaaS acquisition ($50M ARR, 120% NRR, customer concentration)
        Expected: Financial + Commercial + Technology + HR — NOT ESG, NOT Operations
  - D2: Manufacturing acquisition ($200M revenue, 3 plants, EPA liability)
        Expected: Financial + Operations + ESG + Legal — NOT Technology/IP
  - D3: Healthcare AI startup (pre-revenue, 12 patents, FDA pending)
        Expected: Financial + Legal/Regulatory + Technology/IP + Commercial — NOT Operations, NOT ESG

Each deal test:
  1. Sends deal data with all available CSV files
  2. Workflow routes: Deal Triage → Financial Analyst → Specialists → Investment Memo Writer
  3. HITL may trigger (Deal Triage or Legal/Regulatory requesting materials)
  4. Validates: correct analysts engaged, wrong analysts NOT engaged (guard rail),
     expected keywords in output (DCF, valuation, risk, recommendation), PythonTool usage

Usage:
    python test_mna_due_diligence.py                    # Run all tests
    python test_mna_due_diligence.py --test 1           # Run D1 only
    python test_mna_due_diligence.py --test 2           # Run D2 only
    python test_mna_due_diligence.py --test 3           # Run D3 only
    python test_mna_due_diligence.py --workflow-id 99   # Use specific workflow ID
    python test_mna_due_diligence.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from config import (
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)

# ── Constants ────────────────────────────────────────────────────────────────

WORKFLOW_NAME = "M&A Due Diligence Panel"
DATA_DIR = Path(__file__).parent / "test_data" / "mna_due_diligence"


# ── Deal Data Loader ─────────────────────────────────────────────────────────


def load_deal_data(deal_id: str) -> str:
    """Load all CSV data files for a deal and format as a text block.

    Args:
        deal_id: e.g. "D1", "D2", "D3"
    """
    deal_dir = DATA_DIR / deal_id
    if not deal_dir.exists():
        return f"[ERROR] Deal data directory not found: {deal_dir}"

    parts = []
    for fpath in sorted(deal_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# ── Build Test Messages ──────────────────────────────────────────────────────


def build_d1_message() -> str:
    """D1: SaaS acquisition — CloudMetrics Inc."""
    data = load_deal_data("D1")
    return (
        "Please evaluate this acquisition target:\n\n"
        "Target: CloudMetrics Inc. — B2B SaaS analytics platform\n"
        "Asking Price: $250M (5x ARR)\n"
        "Revenue: $50M ARR, 120% net revenue retention, but top 3 customers "
        "represent 45% of total revenue\n"
        "Employees: 180 (60% engineering)\n"
        "Founded: 2019, HQ: Austin, TX\n"
        "Deal Rationale: Strategic bolt-on to expand our analytics offering. "
        "Target has strong NRR but significant customer concentration in "
        "top 3 enterprise accounts.\n\n"
        f"Available deal data:\n{data}\n\n"
        "Please perform a complete due diligence workup — triage the deal, "
        "run financial models (DCF valuation, revenue analysis), assess all "
        "relevant risk areas for a SaaS acquisition, and produce a final "
        "investment memo with go/no-go recommendation."
    )


def build_d2_message() -> str:
    """D2: Manufacturing acquisition — PrecisionWorks Manufacturing."""
    data = load_deal_data("D2")
    return (
        "Please evaluate this acquisition target:\n\n"
        "Target: PrecisionWorks Manufacturing LLC — Industrial components manufacturer\n"
        "Asking Price: $320M (1.6x revenue, 8x EBITDA)\n"
        "Revenue: $200M, declining margins due to rising input costs\n"
        "Employees: 1,450 across 3 plants (Midwest US)\n"
        "Founded: 1987, HQ: Cleveland, OH\n"
        "Deal Rationale: Vertical integration play — target supplies critical "
        "components to our assembly lines. 3 manufacturing plants with aging "
        "equipment. Known EPA remediation issue at Plant 2 (former chromium "
        "plating operations).\n\n"
        f"Available deal data:\n{data}\n\n"
        "Please perform a complete due diligence workup — triage the deal, "
        "run financial models (DCF valuation, margin analysis), assess all "
        "relevant risk areas for a manufacturing acquisition (especially "
        "operations, environmental, and supply chain), and produce a final "
        "investment memo with go/no-go recommendation."
    )


def build_d3_message() -> str:
    """D3: Healthcare AI startup — NeuralDx Health Inc."""
    data = load_deal_data("D3")
    return (
        "Please evaluate this acquisition target:\n\n"
        "Target: NeuralDx Health Inc. — AI-powered diagnostic imaging startup\n"
        "Asking Price: $80M\n"
        "Revenue: Pre-revenue (R&D stage)\n"
        "Employees: 45 (80% PhD-level researchers)\n"
        "Founded: 2021, HQ: Boston, MA\n"
        "Deal Rationale: Acqui-hire + IP play. Target has 12 patents in "
        "AI-assisted radiology, FDA 510(k) submission pending for their "
        "flagship product. 3 clinical studies completed with strong results. "
        "Key risk: no revenue, regulatory uncertainty, key person dependency "
        "on founding team.\n\n"
        f"Available deal data:\n{data}\n\n"
        "Please perform a complete due diligence workup — triage the deal, "
        "run financial models (IP valuation, burn rate analysis), assess all "
        "relevant risk areas for a healthcare/biotech acquisition (especially "
        "regulatory, IP portfolio, clinical data, and competitive landscape), "
        "and produce a final investment memo with go/no-go recommendation."
    )


# ── Test Definitions ─────────────────────────────────────────────────────────

DEAL_TESTS = [
    {
        "id": 1,
        "name": "D1: SaaS Acquisition — CloudMetrics ($50M ARR, customer concentration)",
        "mode": "full_diligence",
        "build_message": build_d1_message,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Deal Triage may request audited financials
        "expected_agents": [
            "Deal Triage Analyst",
            "Financial Analyst",
            "Commercial/Market Analyst",
            "Technology/IP Analyst",
            "HR/Culture Analyst",
            "Investment Memo Writer",
        ],
        "reject_agents": [
            "ESG/Compliance Analyst",
            "Operations Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "valuation",
            "risk",
            "recommendation",
        ],
        "expected_in_all_text": [
            "dcf",
            "customer concentration",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates SaaS routing: Deal Triage → Financial (DCF + SaaS metrics) "
            "→ Commercial/Market (TAM/SAM, HHI) → Technology/IP (tech stack, debt) "
            "→ HR/Culture (key person, retention) → Tax + Legal → Investment Memo. "
            "ESG and Operations should NOT be called for a SaaS deal."
        ),
    },
    {
        "id": 2,
        "name": "D2: Manufacturing Acquisition — PrecisionWorks ($200M, EPA liability)",
        "mode": "full_diligence",
        "build_message": build_d2_message,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Legal may request environmental reports
        "expected_agents": [
            "Deal Triage Analyst",
            "Financial Analyst",
            "Operations Analyst",
            "ESG/Compliance Analyst",
            "Legal/Regulatory Analyst",
            "Investment Memo Writer",
        ],
        "reject_agents": [
            "Technology/IP Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "valuation",
            "risk",
            "recommendation",
        ],
        "expected_in_all_text": [
            "dcf",
            "epa",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates Manufacturing routing: Deal Triage → Financial (DCF + margins) "
            "→ Operations (capacity, supply chain) → ESG (environmental liabilities) "
            "→ Legal/Regulatory → Tax → Investment Memo. "
            "Technology/IP Analyst should NOT be heavily engaged for a "
            "traditional manufacturing deal."
        ),
    },
    {
        "id": 3,
        "name": "D3: Healthcare AI Startup — NeuralDx (pre-revenue, FDA pending)",
        "mode": "full_diligence",
        "build_message": build_d3_message,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Legal may request IP filings
        "expected_agents": [
            "Deal Triage Analyst",
            "Financial Analyst",
            "Legal/Regulatory Analyst",
            "Technology/IP Analyst",
            "Commercial/Market Analyst",
            "Investment Memo Writer",
        ],
        "reject_agents": [
            "Operations Analyst",
            "ESG/Compliance Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "valuation",
            "risk",
            "recommendation",
        ],
        "expected_in_all_text": [
            "fda",
            "patent",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates Healthcare/Biotech routing: Deal Triage → Financial "
            "(burn rate, IP valuation) → Legal/Regulatory (FDA, IP) "
            "→ Technology/IP (patent portfolio, AI models) → Commercial/Market "
            "(competitive landscape) → Tax → Investment Memo. "
            "Operations and ESG should NOT be called for a pre-revenue "
            "healthcare AI startup."
        ),
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
    """Find the M&A Due Diligence Panel workflow by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def create_chat_session(agent_id: int = 0) -> str | None:
    """Create a chat session and return its UUID."""
    resp = api("POST", "converse/create-chat-session", {"agent_id": agent_id})
    if resp.status_code != 200:
        print(f"[ERROR] Could not create chat session: {resp.status_code} {resp.text[:300]}")
        return None
    data = resp.json()
    session_id = str(data.get("chat_session_id", ""))
    return session_id if session_id else None


def run_workflow_stream(
    workflow_id: int,
    message: str,
    chat_session_id: str | None = None,
) -> dict:
    """Run a workflow round and collect structured results.

    Returns dict with:
      agents_run, was_paused, pause_text, final_answer, completed,
      python_executions, files_generated, error, duration_s, all_text
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
        "all_text": "",
    }

    body = {"message": message}
    if chat_session_id:
        body["chat_session_id"] = chat_session_id

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", body)

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

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
                agent = obj.get("step_name", "?")
                if agent not in result["agents_run"]:
                    result["agents_run"].append(agent)
                agent = obj.get("agent_name", "?")
                _safe_print(f"\n  [{agent}] (Agent: {agent})")
                print("  " + "-" * 48)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                if content:
                    all_text_parts.append(content)

            elif ptype == "workflow_pause_for_input":
                result["was_paused"] = True
                result["pause_text"] = obj.get("questions", "")
                step = obj.get("step_name", "?")
                _safe_print(f"\n  {'='*50}")
                _safe_print(f"  [PAUSED] {step} needs more info:")
                _safe_print(f"  {'='*50}")
                _safe_print(f"  {result['pause_text'][:300]}")

            elif ptype == "python_tool_start":
                result["python_executions"] += 1

            elif ptype == "python_tool_delta":
                fids = obj.get("file_ids", [])
                if fids:
                    result["files_generated"].extend(fids)

            elif ptype == "message_start":
                in_final_answer = True
                _safe_print("\n  [Final Answer]")
                print("  " + "-" * 48)

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                if content:
                    if in_final_answer:
                        final_parts.append(content)
                    all_text_parts.append(content)

            elif ptype == "stop":
                result["completed"] = True
                _safe_print("\n  --- Stream Complete ---")

        except json.JSONDecodeError:
            pass

    result["final_answer"] = "".join(final_parts)
    result["all_text"] = "".join(all_text_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_deal_test(test_def: dict, workflow_id: int) -> dict:
    """Run a deal due diligence test with optional HITL multi-round flow.

    For deal tests (D1/D2/D3), the flow is:
      Round 0: Send deal data → may pause (analyst requests materials)
      Round 1: If paused, send acknowledgement → expect completion
    """
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Expect HITL pause: {test_def.get('expect_hitl_pause', False)}")
    print(f"{'='*60}")

    issues = []
    all_agents = []
    total_python = 0
    total_files = []
    total_duration = 0

    # Build initial message
    build_fn = test_def.get("build_message")
    if build_fn:
        message = build_fn()
    else:
        message = test_def.get("message", "")

    msg_preview = message[:120].replace("\n", " ")
    print(f"  Message: \"{msg_preview}...\"")

    # Create chat session for HITL tracking
    chat_session_id = create_chat_session()
    if not chat_session_id:
        return {
            "id": test_id, "name": name, "mode": test_def["mode"],
            "status": "FAIL", "issues": ["Could not create chat session"],
            "duration_s": 0, "agents_run": [], "python_executions": 0,
        }

    # ── Round 0: Initial submission ──
    print(f"\n  --- ROUND 0: Initial deal submission ---")
    r0 = run_workflow_stream(workflow_id, message, chat_session_id)
    all_agents.extend(r0["agents_run"])
    total_python += r0["python_executions"]
    total_files.extend(r0["files_generated"])
    total_duration += r0["duration_s"]

    if r0["error"]:
        issues.append(f"Round 0 error: {r0['error']}")

    # ── Round 1: If paused, provide acknowledgement ──
    final_result = r0
    if r0["was_paused"] and test_def.get("expect_hitl_pause"):
        followup_msg = (
            "I understand the request for additional materials. For the purposes "
            "of this evaluation, please proceed with the analysis based on all "
            "the data already provided. Assume the available data is sufficient "
            "to complete the due diligence assessment."
        )
        print(f"\n  --- ROUND 1: Providing follow-up (proceed with available data) ---")
        print(f"  Follow-up: \"{followup_msg[:100]}...\"")

        time.sleep(2)  # Brief pause for DB
        r1 = run_workflow_stream(workflow_id, followup_msg, chat_session_id)
        # Merge agents from round 1
        for a in r1["agents_run"]:
            if a not in all_agents:
                all_agents.append(a)
        total_python += r1["python_executions"]
        total_files.extend(r1["files_generated"])
        total_duration += r1["duration_s"]
        final_result = r1

        if r1["error"]:
            issues.append(f"Round 1 error: {r1['error']}")

    elif not r0["was_paused"] and test_def.get("expect_hitl_pause"):
        # Analyst didn't pause — that's OK if the workflow still completed correctly
        print("  [INFO] Expected HITL pause but analyst proceeded without "
              "requesting additional materials — this is acceptable")

    # ── Validate results ──

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(
                f"WRONG ANALYST: '{agent}' was called but should NOT have been "
                f"for this deal type"
            )

    # Check completion
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output content
    if final_result["completed"]:
        combined_lower = (
            final_result["final_answer"] + " " + final_result.get("all_text", "")
        ).lower()

        # Check keywords in final answer / investment memo
        for kw in test_def.get("expected_in_output", []):
            if kw.lower() not in combined_lower:
                issues.append(f"Output missing keyword: '{kw}'")

        # Check keywords in all text (across all agent outputs)
        for kw in test_def.get("expected_in_all_text", []):
            if kw.lower() not in combined_lower:
                issues.append(f"All-text missing keyword: '{kw}'")

        # Check PythonTool usage
        if test_def.get("expect_python") and total_python == 0:
            issues.append("Expected PythonTool execution but none occurred")

        # Check minimum answer length
        min_len = test_def.get("min_answer_length", 0)
        if min_len > 0 and len(final_result["final_answer"]) < min_len:
            issues.append(
                f"Final answer too short ({len(final_result['final_answer'])} chars, "
                f"expected >= {min_len})"
            )

    # ── Print summary ──
    print(f"\n  Agents run: {all_agents}")
    print(f"  Total PythonTool executions: {total_python}")
    print(f"  Total files generated: {len(total_files)}")
    print(f"  Final answer length: {len(final_result['final_answer'])} chars")
    print(f"  Total duration: {total_duration}s")

    if final_result["final_answer"]:
        preview = final_result["final_answer"][:200]
        _safe_print(f"  Answer preview: {preview}...")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({total_duration}s)")

    return {
        "id": test_id,
        "name": name,
        "mode": test_def["mode"],
        "status": status,
        "issues": issues,
        "duration_s": total_duration,
        "agents_run": all_agents,
        "python_executions": total_python,
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test the M&A Due Diligence Panel workflow",
    )
    parser.add_argument(
        "--test", type=int, nargs="+",
        help="Run specific tests by ID (e.g. --test 1 2)",
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
        workflow_id = args.workflow_id
    else:
        print(f"\nLooking for workflow: '{WORKFLOW_NAME}'...")
        workflow_id = find_workflow_id()
        if workflow_id is None:
            print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy it first:")
            print(f"  python create_workflows.py --file workflows/27_mna_due_diligence.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.test:
        all_tests = {t["id"]: t for t in DEAL_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = DEAL_TESTS[:]

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  M&A DUE DILIGENCE WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Verify test data exists
    for deal_id in ["D1", "D2", "D3"]:
        deal_dir = DATA_DIR / deal_id
        if not deal_dir.exists():
            print(f"[WARN] Deal data directory missing: {deal_dir}")
        else:
            csv_count = len(list(deal_dir.glob("*.csv")))
            print(f"  {deal_id}: {csv_count} CSV files available")

    # Run tests
    results = []
    for test_def in tests_to_run:
        r = run_deal_test(test_def, workflow_id)
        results.append(r)

    # ── Summary ──
    print(f"\n\n{'='*60}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    passed = 0
    failed = 0
    for r in results:
        tag = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        agents_str = f"agents={len(r['agents_run'])}"
        py_str = f"py={r['python_executions']}" if r["python_executions"] else ""
        extras = "  ".join(filter(None, [agents_str, py_str]))
        print(f"  {tag} #{r['id']} {r['name']:<60} {r['duration_s']}s  {extras}")
        if r["issues"]:
            for issue in r["issues"]:
                print(f"       {issue}")
        if r["status"] == "PASS":
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {len(results)} tests | {passed} passed | {failed} failed")
    total_time = sum(r["duration_s"] for r in results)
    print(f"  Total time: {total_time}s")

    # Print agent routing summary
    print(f"\n  AGENT ROUTING SUMMARY:")
    for r in results:
        print(f"  D{r['id']}: {' -> '.join(r['agents_run'])}")

    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
