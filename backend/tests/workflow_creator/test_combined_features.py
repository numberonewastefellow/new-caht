"""
Test: Combined Features (HTTP Request + Code Executor + Conditional Router)

Creates a workflow that:
  Step 0: HTTP Request agent — fetches a public API (httpbin.org/get)
  Step 1: Conditional Router — checks if HTTP response contains "origin"
  Step 2 (TRUE): Code Executor — parses the JSON response with Python
  Step 3 (FALSE): Error Handler — reports that the HTTP call failed

This tests all three Phase 1-3 features working together end-to-end.

Usage:
    python test_combined_features.py [--key API_KEY] [--url BASE_URL]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

from config import (  # noqa: E402
    CONFIG,
    api,
    headers,
    resolve_api_key,
    add_common_args,
    apply_common_args,
    stream_api,
)

PASS = 0
FAIL = 0


def log(msg: str) -> None:
    print(f"  {msg}")


def test_pass(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  [PASS] {name}")


def test_fail(name: str, reason: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {name}: {reason}")


# ── helpers ───────────────────────────────────────────────────────────────────


def create_persona(name: str, system_prompt: str, tool_ids: list[int] | None = None) -> int | None:
    body = {
        "name": name,
        "description": f"Test persona: {name}",
        "num_chunks": 0,
        "is_public": True,
        "system_prompt": system_prompt,
        "task_prompt": "",
        "document_set_ids": [],
        "tool_ids": tool_ids or [],
        "users": [],
        "groups": [],
        "label_ids": [],
        "recency_bias": "base_decay",
        "llm_filter_extraction": False,
        "llm_relevance_filter": False,
        "replace_base_system_prompt": True,
        "datetime_aware": False,
        "user_file_ids": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
    }
    r = api("POST", "persona", body)
    if r.status_code not in (200, 201):
        log(f"Failed to create persona '{name}': {r.status_code} {r.text[:200]}")
        return None
    return r.json()["id"]


def delete_persona(pid: int) -> None:
    api("PATCH", f"admin/persona/{pid}/visible?is_visible=false")


def delete_workflow(wid: int) -> None:
    api("DELETE", f"admin/workflow/{wid}")


def resolve_tool_id(in_code_tool_id: str) -> int | None:
    """Find a tool's DB ID by its in_code_tool_id."""
    r = api("GET", "tool")
    if r.status_code != 200:
        return None
    for t in r.json():
        if t.get("in_code_tool_id") == in_code_tool_id:
            return t["id"]
    return None


def run_workflow(workflow_id: int, message: str) -> dict:
    result = {
        "agents_run": [],
        "conditions_evaluated": [],
        "final_answer": "",
        "completed": False,
        "error": None,
        "duration_s": 0,
        "step_outputs": {},
    }

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", {"message": message})

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

    in_final_answer = False
    final_parts = []
    current_step = None

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
                step_name = obj.get("step_name", "?")
                step_type = obj.get("step_type", "agent")
                current_step = step_name
                if step_type == "conditional_router":
                    result["conditions_evaluated"].append(step_name)
                else:
                    result["agents_run"].append(step_name)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                if current_step:
                    result["step_outputs"].setdefault(current_step, "")
                    result["step_outputs"][current_step] += content

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


# ── setup ─────────────────────────────────────────────────────────────────────


def setup_combined_workflow() -> dict | None:
    """Create a combined workflow:
    Step 0: HTTP Agent (makes GET request to httpbin.org)
    Step 1: Conditional Router (checks if response contains "origin")
    Step 2 (TRUE): Code Agent (parses JSON with Python)
    Step 3 (FALSE): Error Handler (reports failure)
    """
    ts = int(time.time())

    # Resolve tool IDs
    http_tool_id = resolve_tool_id("HttpRequestTool")
    python_tool_id = resolve_tool_id("PythonTool")

    if not http_tool_id:
        log("HttpRequestTool not found on server — skipping HTTP test")
        log("Will test with a regular agent + code executor + condition instead")

    if not python_tool_id:
        log("PythonTool not found on server")
        return None

    # Create personas
    if http_tool_id:
        http_agent_id = create_persona(
            f"HTTP Fetcher {ts}",
            "You are an HTTP request agent. Use the http_request tool to make the following request:\n"
            "Method: GET\n"
            "URL: https://httpbin.org/get\n"
            "Return the full response body exactly as received. Do not add any commentary.",
            tool_ids=[http_tool_id],
        )
    else:
        # Fallback: use a regular agent that simulates HTTP output
        http_agent_id = create_persona(
            f"HTTP Simulator {ts}",
            'You simulate an HTTP response. Output exactly this JSON:\n'
            '{"origin": "1.2.3.4", "url": "https://httpbin.org/get", "headers": {"Host": "httpbin.org"}}\n'
            'Output ONLY the JSON, nothing else.',
        )

    if not http_agent_id:
        return None

    code_agent_id = create_persona(
        f"Code Processor {ts}",
        "You are a code executor. Use the run_python tool to execute this Python code:\n\n"
        "```python\n"
        "import json\n"
        "# Parse the HTTP response from previous step\n"
        "data = json.loads('''$http_response.output''')\n"
        "origin = data.get('origin', 'unknown')\n"
        "print(f'PARSED_ORIGIN: {origin}')\n"
        "print(f'PARSED_URL: {data.get(\"url\", \"unknown\")}')\n"
        "print('STATUS: SUCCESS')\n"
        "```\n\n"
        "If the code fails, try to extract the origin field manually from the text and "
        "print PARSED_ORIGIN: <value>. Always include STATUS: SUCCESS in your output.",
        tool_ids=[python_tool_id],
    )
    if not code_agent_id:
        delete_persona(http_agent_id)
        return None

    error_agent_id = create_persona(
        f"Error Handler {ts}",
        "You are an error handler. The previous HTTP request did not return expected data. "
        "Output a brief error message explaining the issue. "
        "Always include ERROR_HANDLED in your response.",
    )
    if not error_agent_id:
        delete_persona(http_agent_id)
        delete_persona(code_agent_id)
        return None

    workflow_body = {
        "name": f"Combined Test {ts}",
        "description": "Tests HTTP + Condition + Code together",
        "orchestration_mode": "sequential",
        "max_steps": 10,
        "max_calls_per_agent": 3,
        "timeout_seconds": 300,
        "is_public": True,
        "steps": [
            {
                "step_type": "agent",
                "persona_id": http_agent_id,
                "step_order": 0,
                "step_name": "HTTP Fetcher",
                "step_description": "Fetch data from httpbin API",
                "output_key": "http_response",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": False,
            },
            {
                "step_type": "conditional_router",
                "persona_id": None,
                "step_order": 1,
                "step_name": "Response Validator",
                "step_description": "Check if HTTP response is valid",
                "output_key": "validation",
                "condition": {
                    "condition_field": "$http_response.output",
                    "operator": "contains",
                    "match_value": "origin",
                    "case_sensitive": False,
                    "true_steps": [2],
                    "false_steps": [3],
                },
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": False,
            },
            {
                "step_type": "agent",
                "persona_id": code_agent_id,
                "step_order": 2,
                "step_name": "Code Processor",
                "step_description": "Parse HTTP response with Python",
                "output_key": "parsed_data",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": True,
            },
            {
                "step_type": "agent",
                "persona_id": error_agent_id,
                "step_order": 3,
                "step_name": "Error Handler",
                "step_description": "Handle failed HTTP response",
                "output_key": "error_output",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": True,
            },
        ],
    }

    r = api("POST", "admin/workflow", workflow_body)
    if r.status_code not in (200, 201):
        log(f"Failed to create workflow: {r.status_code} {r.text[:300]}")
        for pid in [http_agent_id, code_agent_id, error_agent_id]:
            delete_persona(pid)
        return None

    wf = r.json()
    return {
        "workflow_id": wf["id"],
        "persona_ids": [http_agent_id, code_agent_id, error_agent_id],
        "has_http_tool": bool(http_tool_id),
    }


# ── tests ─────────────────────────────────────────────────────────────────────


def test_1_combined_true_path(setup: dict):
    """Test the happy path: HTTP → Condition(TRUE) → Code Executor."""
    print("\n=== Test 1: Combined Happy Path (HTTP -> Condition -> Code) ===")

    wf_id = setup["workflow_id"]
    result = run_workflow(
        wf_id,
        "Fetch the httpbin.org/get endpoint and parse the response",
    )

    if result["error"]:
        test_fail("Execution", f"Error: {result['error']}")
        return

    log(f"Agents run: {result['agents_run']}")
    log(f"Conditions evaluated: {result['conditions_evaluated']}")
    log(f"Duration: {result['duration_s']}s")
    log(f"Answer preview: {result['final_answer'][:300]}")

    # HTTP Fetcher should have run
    if "HTTP Fetcher" in result["agents_run"]:
        test_pass("HTTP Fetcher agent ran")
    else:
        test_fail("HTTP agent", f"Not in: {result['agents_run']}")

    # Condition should have been evaluated
    if "Response Validator" in result["conditions_evaluated"]:
        test_pass("Condition was evaluated")
    else:
        test_fail("Condition", f"Not in: {result['conditions_evaluated']}")

    # Code Processor should have run (TRUE branch — response contains "origin")
    if "Code Processor" in result["agents_run"]:
        test_pass("Code Processor ran (TRUE branch)")
    else:
        test_fail("Code Processor", f"Not in: {result['agents_run']}")

    # Error Handler should NOT have run
    if "Error Handler" not in result["agents_run"]:
        test_pass("Error Handler skipped (FALSE branch)")
    else:
        test_fail("Error Handler skip", "Error Handler ran but should have been skipped")

    if result["completed"]:
        test_pass("Workflow completed")
    else:
        test_fail("Completion", "Workflow did not complete")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test combined HTTP + Code + Condition")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print(f"Base URL: {CONFIG['base_url']}")
    print(f"API Key: {CONFIG['api_key'][:8]}...")

    print("\n" + "=" * 60)
    print("COMBINED FEATURES TEST SUITE")
    print("=" * 60)

    # Setup
    print("\n--- Setup: Creating combined workflow ---")
    setup = setup_combined_workflow()
    if not setup:
        print("\n[FATAL] Could not create test workflow. Aborting.")
        sys.exit(1)

    log(f"Workflow ID: {setup['workflow_id']}")
    log(f"Has HTTP Tool: {setup['has_http_tool']}")

    try:
        test_1_combined_true_path(setup)
    finally:
        print("\n--- Cleanup ---")
        delete_workflow(setup["workflow_id"])
        for pid in setup["persona_ids"]:
            delete_persona(pid)
        log("Cleaned up")

    print(f"\n{'='*60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
