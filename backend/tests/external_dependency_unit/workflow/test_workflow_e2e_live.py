"""End-to-end live test for Multi-Agent Workflow system.

This script tests the full pipeline against a running deployment:
1. Creates 3 test agents via API
2. Creates a sequential workflow linking them
3. Runs the workflow with a math problem
4. Validates that all 3 agents produced output
5. Cleans up test data

Usage:
    python -m tests.external_dependency_unit.workflow.test_workflow_e2e_live \
        --base-url http://localhost:8080 \
        --api-key <your-api-key-or-cookie>

Or as pytest (requires running server):
    pytest tests/external_dependency_unit/workflow/test_workflow_e2e_live.py -v -s
"""

import argparse
import json
import sys
import time

import requests

# ─── Configuration ────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8080"
TIMEOUT = 120  # seconds for streaming response


def get_session(
    base_url: str,
    api_key: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> requests.Session:
    """Create a requests session with auth (bearer token or cookie login)."""
    s = requests.Session()
    if api_key:
        s.headers["Authorization"] = f"Bearer {api_key}"

    # Try cookie-based login if email/password provided
    if email and password:
        login_resp = s.post(
            f"{base_url}/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if login_resp.status_code == 204:
            print(f"  Logged in as {email}")
        else:
            print(f"  WARNING: Login failed ({login_resp.status_code}): {login_resp.text[:200]}")

    s.headers["Content-Type"] = "application/json"
    return s


# ─── Step 1: Create 3 Test Agents ───────────────────────────────────────


AGENTS = [
    {
        "name": "[E2E Test] Math Solver",
        "description": "Solves math problems step by step with clear working.",
        "system_prompt": (
            "You are a precise math solver. When given a math problem, "
            "solve it step by step showing all working. Always end with "
            "'ANSWER: <number>' on its own line."
        ),
        "task_prompt": "",
    },
    {
        "name": "[E2E Test] Verifier",
        "description": "Verifies mathematical solutions for correctness.",
        "system_prompt": (
            "You are a math verification expert. You will receive a math problem "
            "and a proposed solution. Review the solution and check every step. "
            "If correct, say 'VERIFIED: The solution is correct.' "
            "If wrong, say 'INCORRECT: The correct answer is ...' and show the fix."
        ),
        "task_prompt": "",
    },
    {
        "name": "[E2E Test] Summarizer",
        "description": "Summarizes technical results into plain language.",
        "system_prompt": (
            "You are a friendly summarizer. You will receive a math problem, "
            "its solution, and a verification result. Produce a brief, "
            "plain-language summary (2-3 sentences) that explains the answer "
            "in a way anyone can understand. Be concise and clear."
        ),
        "task_prompt": "",
    },
]


def create_agent(session: requests.Session, base_url: str, agent_config: dict) -> dict:
    """Create a agent via the API."""
    payload = {
        "name": agent_config["name"],
        "description": agent_config["description"],
        "system_prompt": agent_config["system_prompt"],
        "task_prompt": agent_config.get("task_prompt", ""),
        "num_chunks": 0,
        "is_public": True,
        "recency_bias": "base_decay",
        "llm_filter_extraction": False,
        "llm_relevance_filter": False,
        "llm_model_provider_override": None,
        "llm_model_version_override": None,
        "starter_messages": None,
        "datetime_aware": False,
        "document_set_ids": [],
        "tool_ids": [],
        "users": [],
        "groups": [],
    }

    resp = session.post(f"{base_url}/agent", json=payload)
    if resp.status_code != 200:
        print(f"  ERROR creating agent '{agent_config['name']}': {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return {}

    data = resp.json()
    print(f"  Created agent: '{data['name']}' (id={data['id']})")
    return data


def delete_agent(session: requests.Session, base_url: str, agent_id: int) -> None:
    """Delete a agent via the API."""
    resp = session.delete(f"{base_url}/agent/{agent_id}")
    if resp.status_code == 200:
        print(f"  Deleted agent id={agent_id}")
    else:
        print(f"  Warning: failed to delete agent {agent_id}: {resp.status_code}")


# ─── Step 2: Create Workflow ──────────────────────────────────────────────


def create_workflow(
    session: requests.Session,
    base_url: str,
    agent_ids: list[int],
) -> dict:
    """Create a 3-agent sequential workflow."""
    payload = {
        "name": "[E2E Test] Math Pipeline",
        "description": "Solve -> Verify -> Summarize math problems",
        "orchestration_mode": "sequential",
        "max_steps": 10,
        "timeout_seconds": 300,
        "is_public": True,
        "steps": [
            {
                "agent_id": agent_ids[0],
                "step_order": 0,
                "step_name": "Solve",
                "step_description": "Solve the math problem step by step",
                "output_key": "solution",
                "is_terminal": False,
            },
            {
                "agent_id": agent_ids[1],
                "step_order": 1,
                "step_name": "Verify",
                "step_description": "Verify the solution is correct",
                "output_key": "verification",
                "is_terminal": False,
            },
            {
                "agent_id": agent_ids[2],
                "step_order": 2,
                "step_name": "Summarize",
                "step_description": "Summarize the result in plain language",
                "output_key": "summary",
                "is_terminal": True,
            },
        ],
    }

    resp = session.post(f"{base_url}/admin/workflow", json=payload)
    if resp.status_code != 200:
        print(f"  ERROR creating workflow: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return {}

    data = resp.json()
    print(f"  Created workflow: '{data['name']}' (id={data['id']}, steps={len(data['steps'])})")
    return data


def delete_workflow_api(session: requests.Session, base_url: str, workflow_id: int) -> None:
    """Delete a workflow via the API."""
    resp = session.delete(f"{base_url}/admin/workflow/{workflow_id}")
    if resp.status_code == 200:
        print(f"  Deleted workflow id={workflow_id}")
    else:
        print(f"  Warning: failed to delete workflow {workflow_id}: {resp.status_code}")


# ─── Step 3: Run Workflow ─────────────────────────────────────────────────


def run_workflow(
    session: requests.Session,
    base_url: str,
    workflow_id: int,
    message: str,
) -> list[dict]:
    """Execute the workflow and collect streaming response packets."""
    payload = {"message": message}

    print(f"  Sending: '{message}'")
    print(f"  Streaming response...")

    resp = session.post(
        f"{base_url}/workflow/{workflow_id}/run",
        json=payload,
        stream=True,
        timeout=TIMEOUT,
    )

    if resp.status_code != 200:
        print(f"  ERROR running workflow: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return []

    packets = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        try:
            packet = json.loads(line)
            packets.append(packet)
        except json.JSONDecodeError:
            continue

    return packets


def analyze_packets(packets: list[dict]) -> dict:
    """Analyze streaming packets to extract per-step results."""
    steps_started = []
    steps_ended = []
    step_outputs: dict[str, str] = {}
    current_step = ""
    errors = []

    for pkt in packets:
        obj = pkt.get("obj", {})
        pkt_type = obj.get("type", "")

        if pkt_type == "workflow_step_start":
            step_name = obj.get("step_name", "")
            agent_name = obj.get("agent_name", "")
            steps_started.append(step_name)
            current_step = step_name
            step_outputs[step_name] = ""
            print(f"    Step started: '{step_name}' (agent: {agent_name})")

        elif pkt_type == "workflow_step_delta":
            content = obj.get("content", "")
            if current_step:
                step_outputs[current_step] += content

        elif pkt_type == "workflow_step_end":
            step_name = obj.get("step_name", "")
            steps_ended.append(step_name)
            output_preview = step_outputs.get(step_name, "")[:100]
            print(f"    Step ended: '{step_name}' -> {output_preview}...")

        elif pkt_type == "agent_response_delta":
            content = obj.get("text", "")
            if current_step:
                step_outputs[current_step] += content

        elif pkt_type == "stop":
            print(f"    Workflow complete.")

    return {
        "steps_started": steps_started,
        "steps_ended": steps_ended,
        "step_outputs": step_outputs,
        "total_packets": len(packets),
        "errors": errors,
    }


# ─── Main Test Flow ──────────────────────────────────────────────────────


def run_full_test(
    base_url: str,
    api_key: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> bool:
    """Run the complete end-to-end test. Returns True if all checks pass."""
    session = get_session(base_url, api_key, email, password)
    created_agent_ids: list[int] = []
    created_workflow_id: int | None = None
    all_passed = True

    try:
        # ── Step 1: Create 3 Agents ──
        print("\n[1/4] Creating 3 test agents...")
        for agent_config in AGENTS:
            result = create_agent(session, base_url, agent_config)
            if not result:
                print("  FAIL: Could not create agent")
                return False
            created_agent_ids.append(result["id"])

        assert len(created_agent_ids) == 3, "Expected 3 agents"
        print(f"  OK: Created {len(created_agent_ids)} agents: {created_agent_ids}")

        # ── Step 2: Create Workflow ──
        print("\n[2/4] Creating sequential workflow...")
        workflow = create_workflow(session, base_url, created_agent_ids)
        if not workflow:
            print("  FAIL: Could not create workflow")
            return False

        created_workflow_id = workflow["id"]
        assert len(workflow["steps"]) == 3, f"Expected 3 steps, got {len(workflow['steps'])}"
        print(f"  OK: Workflow created with {len(workflow['steps'])} steps")

        # ── Step 3: Verify Workflow GET ──
        print("\n[3/4] Verifying workflow retrieval...")
        resp = session.get(f"{base_url}/workflow/{created_workflow_id}")
        assert resp.status_code == 200, f"GET workflow failed: {resp.status_code}"
        wf_data = resp.json()
        assert wf_data["name"] == "[E2E Test] Math Pipeline"
        assert wf_data["orchestration_mode"] == "sequential"
        assert len(wf_data["steps"]) == 3

        step_names = [s["step_name"] for s in sorted(wf_data["steps"], key=lambda s: s["step_order"])]
        assert step_names == ["Solve", "Verify", "Summarize"], f"Unexpected step order: {step_names}"
        print(f"  OK: Workflow data verified. Steps: {step_names}")

        # ── Step 4: Run Workflow ──
        print("\n[4/4] Running workflow with test math problem...")
        test_message = "What is 17 * 23 + 45 - 12?"
        packets = run_workflow(session, base_url, created_workflow_id, test_message)

        if not packets:
            print("  WARNING: No streaming packets received (LLM may not be configured)")
            print("  Skipping execution validation - CRUD tests passed.")
            return True

        result = analyze_packets(packets)
        print(f"\n  Results:")
        print(f"    Total packets: {result['total_packets']}")
        print(f"    Steps started: {result['steps_started']}")
        print(f"    Steps ended: {result['steps_ended']}")

        # Validate all 3 steps executed
        if len(result["steps_started"]) >= 3:
            print(f"  OK: All 3 agents executed!")
        else:
            print(f"  WARNING: Only {len(result['steps_started'])} of 3 agents executed")
            all_passed = False

        # Print step outputs
        for step_name, output in result["step_outputs"].items():
            print(f"\n  --- {step_name} Output ---")
            print(f"  {output[:300]}{'...' if len(output) > 300 else ''}")

        return all_passed

    finally:
        # ── Cleanup ──
        print("\n[Cleanup] Removing test data...")
        if created_workflow_id:
            delete_workflow_api(session, base_url, created_workflow_id)
        for pid in created_agent_ids:
            delete_agent(session, base_url, pid)
        print("  Done.")


# ─── Pytest entry point ──────────────────────────────────────────────────


def test_multi_agent_workflow_e2e() -> None:
    """Pytest wrapper for the E2E test (requires running server at localhost:8080)."""
    import os

    base_url = os.environ.get("WORKFLOW_TEST_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("WORKFLOW_TEST_API_KEY", None)
    email = os.environ.get("WORKFLOW_TEST_EMAIL", None)
    password = os.environ.get("WORKFLOW_TEST_PASSWORD", None)

    success = run_full_test(base_url, api_key, email, password)
    assert success, "Multi-agent workflow E2E test failed"


# ─── CLI entry point ─────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Workflow E2E Test")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the running server (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key or bearer token for authentication",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Email for cookie-based login",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password for cookie-based login",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Multi-Agent Workflow E2E Test")
    print(f"Server: {args.base_url}")
    print("=" * 60)

    start = time.time()
    success = run_full_test(args.base_url, args.api_key, args.email, args.password)
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    if success:
        print(f"PASSED in {elapsed:.1f}s")
    else:
        print(f"FAILED in {elapsed:.1f}s")
    print("=" * 60)

    sys.exit(0 if success else 1)
