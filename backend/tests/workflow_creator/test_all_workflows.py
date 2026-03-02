"""
Automated Test Suite: All Showcase Workflows
==============================================

Tests all 8 showcase workflows to verify:
1. Non-HITL workflows complete end-to-end with all agents running
2. HITL workflows pause correctly on vague input
3. All agents produce structured, meaningful output
4. promote_output works (final answer contains the promoted agent's output)

Workflow IDs are auto-detected by name, so the test adapts to any deployment.

Usage:
    python test_all_workflows.py                    # Test all workflows
    python test_all_workflows.py --only-hitl        # Test only HITL workflows
    python test_all_workflows.py --only-non-hitl    # Test only non-HITL workflows
    python test_all_workflows.py --workflow "Investment Analysis Pipeline"  # Test specific workflow
    python test_all_workflows.py --url http://host:3000 --key YOUR_KEY
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


# ── Test Definitions ─────────────────────────────────────────────────────────
#
# Each test defines:
#   - name: Workflow name (must match the deployed workflow name exactly)
#   - message: The test input message
#   - is_hitl: Whether the workflow has a HITL step (expects pause on vague input)
#   - expected_agents: List of agent step names that should run
#   - expected_in_output: Strings that should appear in the final output
#   - purpose: Human-readable description of what the test verifies


NON_HITL_TESTS = [
    {
        "name": "Investment Analysis Pipeline",
        "message": "Analyze Tesla (TSLA) for a long-term investment",
        "is_hitl": False,
        "expected_agents": [
            "Fundamental Analyst",
            "Technical Analyst",
            "Macro Economist",
            "Risk Assessor",
            "Portfolio Strategist",
        ],
        # Purpose: Verifies all 5 specialist agents run and the Portfolio Strategist
        # produces a buy/hold/sell verdict with entry/exit strategy.
        # Expected output: Structured investment recommendation with:
        #   - VERDICT (STRONG BUY/BUY/HOLD/SELL/STRONG SELL)
        #   - Entry/exit price targets
        #   - Analyst consensus summary table
        #   - Risk-adjusted position sizing
        #   - DISCLAIMER about not being financial advice
        "expected_in_output": ["VERDICT", "DISCLAIMER"],
    },
    {
        "name": "Movie Production Planner",
        "message": "A sci-fi thriller about AI gaining consciousness in a Mars colony",
        "is_hitl": False,
        "expected_agents": [
            "Story Concept Developer",
            "Casting Director",
            "Location Scout",
            "Budget Estimator",
            "Pitch Deck Builder",
        ],
        # Purpose: Verifies the sequential 5-step pipeline from concept to pitch deck.
        # Expected output: Professional pitch deck with:
        #   - Logline and story synopsis
        #   - Cast suggestions with real actor names
        #   - Real filming locations with cost estimates
        #   - Production budget breakdown
        #   - Studio-ready pitch format
        "expected_in_output": ["PITCH DECK", "THE HOOK", "THE NUMBERS"],
    },
    {
        "name": "Policy Draft Review Pipeline",
        "message": "Review a proposed free laptop scheme for college students in the state",
        "is_hitl": False,
        "expected_agents": [
            "Policy Analyst",
            "Legal Compliance Reviewer",
            "Budget Impact Assessor",
            "Stakeholder Impact Analyst",
            "Executive Summary Writer",
        ],
        # Purpose: Verifies the sequential 5-step policy review pipeline.
        # Expected output: Executive brief for senior officials with:
        #   - RECOMMENDATION (APPROVE/APPROVE WITH MODIFICATIONS/DEFER/NOT RECOMMENDED)
        #   - Traffic-light ratings (Green/Amber/Red) for each dimension
        #   - Fiscal summary with costs in crores (Indian context)
        #   - Implementation timeline with phases
        #   - Decision checklist
        "expected_in_output": ["EXECUTIVE BRIEF", "RECOMMENDATION"],
    },
    {
        "name": "Clinical Trial Protocol Designer",
        "message": "Design a Phase 2 trial for a new diabetes drug that improves insulin sensitivity",
        "is_hitl": False,
        "expected_agents": [
            "Study Designer",
            "Regulatory Advisor",
            "Statistical Analyst",
            "Protocol Compiler",
        ],
        # Purpose: Verifies the 4-agent clinical trial design pipeline.
        # Expected output: ICH-GCP formatted protocol synopsis with:
        #   - Study title, phase, design type
        #   - Primary and secondary endpoints
        #   - Inclusion/exclusion criteria
        #   - Statistical analysis plan
        #   - Safety monitoring requirements
        #   - DISCLAIMER about educational purpose
        "expected_in_output": ["PROTOCOL SYNOPSIS", "DISCLAIMER"],
    },
    {
        "name": "Legal Contract Review & Risk Advisor",
        "message": "Review a mutual NDA between our company (Acme Corp, a fintech startup in the US) and DataVault Inc (a cloud storage provider). 2-year term, covers proprietary algorithms and customer data. We're concerned about the non-solicitation clause and data return provisions. Contract value is tied to a $5M partnership deal. Governed by Delaware law.",
        "is_hitl": False,
        "expected_agents": [
            "Contract Intake Specialist",
            "Clause Analyzer",
            "Regulatory Compliance Checker",
            "Risk Assessor",
            "Negotiation Strategist",
            "Executive Review Summary",
        ],
        # Purpose: Verifies the full 6-agent contract review pipeline completes
        # end-to-end when given enough detail (no HITL pause needed).
        # Expected output: Executive summary with:
        #   - CONTRACT REVIEW heading
        #   - RECOMMENDATION (SIGN/NEGOTIATE/REJECT)
        #   - Risk dashboard with traffic-light ratings
        #   - Negotiation summary and action items
        #   - DISCLAIMER about not being legal advice
        "expected_in_output": ["CONTRACT REVIEW", "RECOMMENDATION", "DISCLAIMER"],
    },
    {
        "name": "IT Incident Triage & Resolution",
        "message": "Multiple users are reporting they can't login to our Salesforce CRM since 9 AM today. About 200 sales team members are affected across 3 offices. They get 'SSO Authentication Failed' errors. Our Okta SSO dashboard shows the Salesforce integration is showing warnings. No recent changes to SSO config. Other Okta-integrated apps like Slack and Jira work fine.",
        "is_hitl": False,
        "expected_agents": [
            "Incident Intake & Classifier",
            "Diagnostic Engine",
            "Resolution Advisor",
            "Impact & SLA Analyzer",
            "Incident Report & Comms Drafter",
        ],
        # Purpose: Verifies the full 5-agent IT incident pipeline completes
        # end-to-end when given comprehensive incident details.
        # Expected output: Incident report with:
        #   - INCIDENT REPORT heading
        #   - EXECUTIVE SUMMARY section
        #   - Root cause analysis
        #   - Resolution steps
        #   - Management notification and end-user notice
        "expected_in_output": ["INCIDENT REPORT", "EXECUTIVE SUMMARY"],
    },
    {
        "name": "Automated Data Analysis Pipeline",
        "message": "Analyze our company revenue data: CSV with columns date, product_line (Enterprise/SMB/Consumer), region (US/EU/APAC), revenue, units_sold, discount_pct. 24 months of data, ~5000 rows. I want to know: 1) Which product lines are growing fastest? 2) Regional performance comparison 3) Impact of discounts on revenue 4) Seasonal patterns.",
        "is_hitl": False,
        "expected_agents": [
            "Data Intake Specialist",
            "Data Profiler",
            "Analysis Engine",
            "Visualization Generator",
            "Insight Report Writer",
        ],
        # Purpose: Verifies the full 5-agent data analysis pipeline with code execution.
        # Agents write and run Python code (pandas, matplotlib) to profile, analyze,
        # and visualize data. Expected output: Business-ready insight report with:
        #   - DATA ANALYSIS REPORT heading
        #   - KEY FINDINGS table
        #   - Recommended actions
        #   - DISCLAIMER about sample data
        "expected_in_output": ["DATA ANALYSIS REPORT", "KEY FINDINGS", "DISCLAIMER"],
    },
    {
        "name": "Code Debug & Fix Assistant",
        "message": "Bug in our Python inventory system. The function `calculate_discount(items, threshold=100)` should apply a 10% discount to items over the threshold, but it's applying the discount to ALL items regardless of price. Here's the code:\n\ndef calculate_discount(items, threshold=100):\n    discounted = []\n    for item in items:\n        item['price'] = item['price'] * 0.9\n        if item['price'] > threshold:\n            discounted.append(item)\n    return discounted\n\nExpected: Only items with price > 100 get 10% off. Actual: All items get 10% off. Test input: [{'name': 'A', 'price': 50}, {'name': 'B', 'price': 150}]",
        "is_hitl": False,
        "expected_agents": [
            "Bug Report Intake",
            "Reproducer & Diagnoser",
            "Fix Generator",
            "Test Writer & Verifier",
            "PR Summary Drafter",
        ],
        # Purpose: Verifies the full 5-agent debug pipeline with code execution.
        # Agents write and run Python code to reproduce, fix, and test the bug.
        # Expected output: PR-ready summary with:
        #   - BUG FIX heading
        #   - Code diff
        #   - Test results table
        #   - Review notes
        "expected_in_output": ["BUG FIX", "PASS"],
    },
    {
        "name": "ML Model Rapid Prototyper",
        "message": "Build a fraud detection model for our payment system. Data has: transaction_amount, merchant_category (retail/food/travel/online), time_of_day, day_of_week, customer_age, account_age_days, num_transactions_24h, avg_transaction_amount, distance_from_home_km, is_international, and is_fraud (target). About 50,000 transactions with 2% fraud rate. Key requirement: minimize false negatives (catch real fraud) while keeping false positive rate under 5%.",
        "is_hitl": False,
        "expected_agents": [
            "ML Requirements Collector",
            "Data Preprocessor",
            "Feature Engineer",
            "Model Trainer & Evaluator",
            "Model Selection Reporter",
        ],
        # Purpose: Verifies the full 5-agent ML pipeline with code execution.
        # Agents write and run Python code (scikit-learn) to preprocess, engineer
        # features, train models, and evaluate. Expected output: Model report with:
        #   - ML MODEL PROTOTYPE REPORT heading
        #   - RECOMMENDED MODEL section
        #   - Performance dashboard table
        #   - DISCLAIMER about synthetic data
        "expected_in_output": ["ML MODEL PROTOTYPE REPORT", "RECOMMENDED MODEL", "DISCLAIMER"],
    },
]


HITL_TESTS = [
    {
        "name": "Patient Intake & Triage Assistant",
        "message": "I've been having chest pain for 2 days",
        "is_hitl": True,
        "expected_agents": ["Intake Coordinator"],
        # Purpose: Verifies the HITL intake agent pauses to collect more
        # patient details (severity, associated symptoms, medical history,
        # medications, allergies). Chest pain is mentioned but many required
        # fields are missing.
        # Expected behavior: Agent pauses and asks follow-up questions about:
        #   - Pain description (location, type, severity 1-10)
        #   - Associated symptoms
        #   - Medical history, medications, allergies
        #   - Age/context
        "expected_in_output": [],
        "expected_pause_keywords": ["symptom", "medical", "medication"],
    },
    {
        "name": "Citizen Complaint Resolution System",
        "message": "There's a large pothole on MG Road near the central junction",
        "is_hitl": True,
        "expected_agents": ["Complaint Intake Officer"],
        # Purpose: Verifies the HITL complaint intake pauses to collect
        # missing details. Location is given but urgency, duration, impact,
        # and contact info are missing.
        # Expected behavior: Agent acknowledges the pothole, asks about:
        #   - Exact location details
        #   - Size and hazard assessment
        #   - Duration and impact (vehicles/people affected)
        "expected_in_output": [],
        "expected_pause_keywords": ["pothole", "size"],
    },
    {
        "name": "Portfolio Risk Monitor",
        "message": "Analyze my portfolio: 40% AAPL, 30% GOOGL, 20% TSLA, 10% BTC",
        "is_hitl": True,
        "expected_agents": ["Portfolio Input Collector"],
        # Purpose: Verifies the HITL portfolio collector pauses despite
        # having holdings/allocations. Missing: total value, horizon, risk
        # tolerance, and investment goals.
        # Expected behavior: Agent acknowledges holdings, asks about:
        #   - Total portfolio value
        #   - Investment horizon
        #   - Risk tolerance and goals
        "expected_in_output": [],
        "expected_pause_keywords": ["portfolio", "horizon", "risk"],
    },
    {
        "name": "Event Planning Coordinator",
        "message": "Plan a corporate annual gala for 200 people",
        "is_hitl": True,
        "expected_agents": ["Requirements Collector"],
        # Purpose: Verifies the HITL event requirements collector pauses.
        # Event type and guest count are given but date, budget, location,
        # theme, dietary needs, and special requirements are missing.
        # Expected behavior: Agent acknowledges the gala, asks about:
        #   - Date/time preference
        #   - Budget range
        #   - Location, theme, dietary needs
        "expected_in_output": [],
        "expected_pause_keywords": ["date", "budget"],
    },
    {
        "name": "Legal Contract Review & Risk Advisor",
        "message": "Review a SaaS vendor agreement we're about to sign",
        "is_hitl": True,
        "expected_agents": ["Contract Intake Specialist"],
        # Purpose: Verifies the HITL contract intake pauses to collect
        # missing details. Only contract type is vaguely indicated; all
        # other required fields (parties, value, duration, jurisdiction,
        # concerns) are missing.
        # Expected behavior: Agent acknowledges the review request, asks about:
        #   - Vendor name and service
        #   - Contract value and duration
        #   - Specific concerns or clauses to focus on
        "expected_in_output": [],
        "expected_pause_keywords": ["parties", "contract"],
    },
    {
        "name": "IT Incident Triage & Resolution",
        "message": "Our email system is down",
        "is_hitl": True,
        "expected_agents": ["Incident Intake & Classifier"],
        # Purpose: Verifies the HITL incident intake pauses to collect
        # missing triage details. Only the affected system is vaguely
        # described; timeline, scope, error messages, and other critical
        # triage fields are missing.
        # Expected behavior: Agent acknowledges the outage, asks about:
        #   - Which email system (O365, Gmail, Exchange)
        #   - When it started and how many users affected
        #   - Specific error messages
        "expected_in_output": [],
        "expected_pause_keywords": ["users", "affected"],
    },
    {
        "name": "Automated Data Analysis Pipeline",
        "message": "Analyze our quarterly sales data",
        "is_hitl": True,
        "expected_agents": ["Data Intake Specialist"],
        # Purpose: Verifies the HITL data intake pauses when given a vague
        # request. No column details, data size, or specific questions provided.
        # Expected behavior: Agent asks about:
        #   - Column/field names
        #   - Data size and time period
        #   - Specific analysis questions
        "expected_in_output": [],
        "expected_pause_keywords": ["column", "data", "analysis"],
    },
    {
        "name": "Code Debug & Fix Assistant",
        "message": "My sorting function doesn't handle duplicate values correctly",
        "is_hitl": True,
        "expected_agents": ["Bug Report Intake"],
        # Purpose: Verifies the HITL bug intake pauses when only a vague
        # description is given. No code, language, or test case provided.
        # Expected behavior: Agent asks for:
        #   - The actual code
        #   - Language
        #   - Example input/output showing the bug
        "expected_in_output": [],
        "expected_pause_keywords": ["code", "language"],
    },
    {
        "name": "ML Model Rapid Prototyper",
        "message": "Build a model to predict customer churn",
        "is_hitl": True,
        "expected_agents": ["ML Requirements Collector"],
        # Purpose: Verifies the HITL ML intake pauses when only the task
        # type is given. No features, data size, or performance priorities.
        # Expected behavior: Agent asks about:
        #   - Features/columns available
        #   - Dataset size and churn rate
        #   - Performance priorities (precision vs recall)
        "expected_in_output": [],
        "expected_pause_keywords": ["feature", "data", "churn"],
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


def resolve_workflow_ids() -> dict[str, int]:
    """Fetch all workflows and return a name -> id mapping."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        sys.exit(1)
    return {w["name"]: w["id"] for w in resp.json()}


def run_workflow_test(
    workflow_id: int,
    message: str,
) -> dict:
    """Run a workflow and collect structured results.

    Returns dict with:
      agents_run: list of step names that produced output
      was_paused: whether workflow paused for input
      pause_text: the pause questions text (if paused)
      final_answer: the final answer text (promoted output)
      completed: whether the stream completed
      error: error message if any
      duration_s: wall-clock seconds
    """
    result = {
        "agents_run": [],
        "was_paused": False,
        "pause_text": "",
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

            elif ptype == "workflow_pause_for_input":
                result["was_paused"] = True
                result["pause_text"] = obj.get("questions", "")

            elif ptype == "message_start":
                in_final_answer = True

            elif ptype == "message_delta":
                if in_final_answer:
                    content = obj.get("content", obj.get("delta", ""))
                    final_parts.append(content)

            elif ptype == "stop":
                result["completed"] = True

        except json.JSONDecodeError:
            pass

    result["final_answer"] = "".join(final_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_test(test_def: dict, workflow_ids: dict) -> dict:
    """Run a single test and return pass/fail result."""
    name = test_def["name"]
    wf_id = workflow_ids.get(name)

    if wf_id is None:
        return {
            "name": name,
            "status": "SKIP",
            "reason": f"Workflow '{name}' not found on server",
            "duration_s": 0,
        }

    print(f"\n{'='*60}")
    print(f"TEST: {name} (ID={wf_id})")
    print(f"  Message: \"{test_def['message']}\"")
    print(f"  HITL: {test_def['is_hitl']}")
    print(f"{'='*60}")

    result = run_workflow_test(wf_id, test_def["message"])

    # Analyze results
    issues = []

    # Check for errors
    if result["error"]:
        issues.append(f"Error: {result['error']}")

    # Check agents ran
    expected = test_def.get("expected_agents", [])
    for agent in expected:
        if agent not in result["agents_run"]:
            issues.append(f"Agent '{agent}' did not run")

    # For HITL tests: verify pause
    if test_def["is_hitl"]:
        if not result["was_paused"]:
            issues.append("Expected PAUSE but workflow did not pause")
        else:
            # Check pause keywords
            pause_lower = result["pause_text"].lower()
            for kw in test_def.get("expected_pause_keywords", []):
                if kw.lower() not in pause_lower:
                    issues.append(f"Pause text missing keyword: '{kw}'")

    # For non-HITL tests: verify completion and output
    if not test_def["is_hitl"]:
        if not result["completed"]:
            issues.append("Workflow did not complete")

        # Check expected strings in final answer
        answer_lower = result["final_answer"].lower()
        for expected_str in test_def.get("expected_in_output", []):
            if expected_str.lower() not in answer_lower:
                issues.append(f"Final answer missing: '{expected_str}'")

        # Check final answer isn't too short
        if len(result["final_answer"]) < 100:
            issues.append(f"Final answer too short ({len(result['final_answer'])} chars)")

    # Print result details
    print(f"\n  Agents run: {result['agents_run']}")
    print(f"  Paused: {result['was_paused']}")
    print(f"  Completed: {result['completed']}")
    print(f"  Final answer length: {len(result['final_answer'])} chars")
    print(f"  Duration: {result['duration_s']}s")

    if result["was_paused"] and result["pause_text"]:
        preview = result["pause_text"][:150]
        _safe_print(f"  Pause preview: {preview}...")

    if result["final_answer"]:
        preview = result["final_answer"][:150]
        _safe_print(f"  Answer preview: {preview}...")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({result['duration_s']}s)")

    return {
        "name": name,
        "status": status,
        "issues": issues,
        "duration_s": result["duration_s"],
        "agents_run": result["agents_run"],
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test all showcase workflows",
    )
    parser.add_argument(
        "--only-hitl", action="store_true",
        help="Only test HITL workflows",
    )
    parser.add_argument(
        "--only-non-hitl", action="store_true",
        help="Only test non-HITL workflows",
    )
    parser.add_argument(
        "--workflow", type=str, default=None,
        help="Test a specific workflow by name",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    # Build test list
    tests = []
    if args.workflow:
        # Find specific workflow in all tests
        all_tests = NON_HITL_TESTS + HITL_TESTS
        for t in all_tests:
            if args.workflow.lower() in t["name"].lower():
                tests.append(t)
        if not tests:
            print(f"[ERROR] No test found matching '{args.workflow}'")
            sys.exit(1)
    elif args.only_hitl:
        tests = HITL_TESTS
    elif args.only_non_hitl:
        tests = NON_HITL_TESTS
    else:
        tests = NON_HITL_TESTS + HITL_TESTS

    # Resolve workflow IDs
    print("\nResolving workflow IDs...")
    workflow_ids = resolve_workflow_ids()
    print(f"  Found {len(workflow_ids)} workflows on server")

    # Run tests
    print(f"\n{'#'*60}")
    print(f"  RUNNING {len(tests)} TESTS")
    print(f"{'#'*60}")

    results = []
    total_start = time.time()

    for test_def in tests:
        result = run_test(test_def, workflow_ids)
        results.append(result)

    total_time = time.time() - total_start

    # Summary
    print(f"\n\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    for r in results:
        icon = {"PASS": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[r["status"]]
        print(f"  {icon} {r['name']} ({r['duration_s']}s)")
        if r.get("issues"):
            for issue in r["issues"]:
                print(f"       - {issue}")

    print(f"\n  Total: {len(results)} tests | "
          f"{passed} passed | {failed} failed | {skipped} skipped")
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
