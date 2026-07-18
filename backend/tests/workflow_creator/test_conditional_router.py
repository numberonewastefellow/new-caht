"""
Test: Conditional Router (If-Else Branch in Sequential Workflows)

Verifies:
1. Workflow with conditional_router step can be created via API
2. TRUE branch executes when condition matches, FALSE branch is skipped
3. FALSE branch executes when condition doesn't match, TRUE branch is skipped
4. Conditional router step itself appears in the stream as a step

Usage:
    python test_conditional_router.py [--key API_KEY] [--url BASE_URL]
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


def create_persona(name: str, system_prompt: str) -> int | None:
    """Create a minimal persona. Returns persona ID."""
    body = {
        "name": name,
        "description": f"Test persona: {name}",
        "num_chunks": 0,
        "is_public": True,
        "system_prompt": system_prompt,
        "task_prompt": "",
        "document_set_ids": [],
        "tool_ids": [],
        "users": [],
        "groups": [],
        "label_ids": [],
        "recency_bias": "base_decay",
        "llm_filter_extraction": False,
        "llm_relevance_filter": False,
        "replace_base_system_prompt": True,
        "datetime_aware": False,
        "knowledge_file_ids": [],
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


def run_workflow(workflow_id: int, message: str) -> dict:
    """Run a workflow via streaming API and collect results."""
    result = {
        "agents_run": [],
        "conditions_evaluated": [],
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
                step_name = obj.get("step_name", "?")
                step_type = obj.get("step_type", "agent")
                if step_type == "conditional_router":
                    result["conditions_evaluated"].append(step_name)
                else:
                    result["agents_run"].append(step_name)

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


# ── test setup ───────────────────────────────────────────────────────────────


def setup_test_workflow() -> dict | None:
    """Create a workflow with:
    Step 0: Classifier agent (outputs text containing "POSITIVE" or "NEGATIVE")
    Step 1: Conditional router (checks if step_0 output contains "POSITIVE")
    Step 2: Positive Handler (true branch)
    Step 3: Negative Handler (false branch)

    Returns dict with workflow_id, persona_ids for cleanup.
    """
    ts = int(time.time())

    # Create personas
    classifier_id = create_persona(
        f"Classifier {ts}",
        "You are a sentiment classifier. Analyze the user's message. "
        "If the message expresses positive sentiment, happiness, or good news, "
        "output exactly: SENTIMENT: POSITIVE\n"
        "If the message expresses negative sentiment, sadness, or bad news, "
        "output exactly: SENTIMENT: NEGATIVE\n"
        "Output ONLY the sentiment line, nothing else.",
    )
    if not classifier_id:
        return None

    positive_id = create_persona(
        f"Positive Handler {ts}",
        "You are a celebration agent. The previous step detected POSITIVE sentiment. "
        "Write a brief, enthusiastic congratulations message (2-3 sentences). "
        "Always include the word CELEBRATION in your response.",
    )
    if not positive_id:
        delete_persona(classifier_id)
        return None

    negative_id = create_persona(
        f"Negative Handler {ts}",
        "You are a support agent. The previous step detected NEGATIVE sentiment. "
        "Write a brief, empathetic support message (2-3 sentences). "
        "Always include the word SUPPORT in your response.",
    )
    if not negative_id:
        delete_persona(classifier_id)
        delete_persona(positive_id)
        return None

    # Create the workflow
    workflow_body = {
        "name": f"Conditional Test {ts}",
        "description": "Tests conditional routing",
        "orchestration_mode": "sequential",
        "max_steps": 10,
        "max_calls_per_agent": 2,
        "timeout_seconds": 300,
        "is_public": True,
        "steps": [
            {
                "step_type": "agent",
                "persona_id": classifier_id,
                "step_order": 0,
                "step_name": "Classifier",
                "step_description": "Classify sentiment",
                "output_key": "sentiment",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": False,
            },
            {
                "step_type": "conditional_router",
                "persona_id": None,
                "step_order": 1,
                "step_name": "Sentiment Check",
                "step_description": "Route based on sentiment",
                "output_key": "condition_result",
                "condition": {
                    "condition_field": "$sentiment.output",
                    "operator": "contains",
                    "match_value": "POSITIVE",
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
                "persona_id": positive_id,
                "step_order": 2,
                "step_name": "Positive Handler",
                "step_description": "Handle positive sentiment",
                "output_key": "positive_response",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": True,
            },
            {
                "step_type": "agent",
                "persona_id": negative_id,
                "step_order": 3,
                "step_name": "Negative Handler",
                "step_description": "Handle negative sentiment",
                "output_key": "negative_response",
                "is_terminal": False,
                "can_request_input": False,
                "promote_output": True,
            },
        ],
    }

    r = api("POST", "admin/workflow", workflow_body)
    if r.status_code not in (200, 201):
        log(f"Failed to create workflow: {r.status_code} {r.text[:300]}")
        delete_persona(classifier_id)
        delete_persona(positive_id)
        delete_persona(negative_id)
        return None

    wf = r.json()
    return {
        "workflow_id": wf["id"],
        "persona_ids": [classifier_id, positive_id, negative_id],
    }


# ── tests ─────────────────────────────────────────────────────────────────────


def test_1_workflow_creation(setup: dict):
    """Test that workflow with conditional_router step was created correctly."""
    print("\n=== Test 1: Conditional Workflow Creation ===")

    wf_id = setup["workflow_id"]
    r = api("GET", f"workflow/{wf_id}")
    if r.status_code != 200:
        test_fail("Fetch workflow", f"Status {r.status_code}")
        return

    wf = r.json()
    steps = wf["steps"]

    if len(steps) == 4:
        test_pass(f"Workflow has 4 steps")
    else:
        test_fail("Step count", f"Expected 4, got {len(steps)}")
        return

    # Check step types
    cond_steps = [s for s in steps if s.get("step_type") == "conditional_router"]
    agent_steps = [s for s in steps if s.get("step_type", "agent") == "agent"]

    if len(cond_steps) == 1:
        test_pass("Found 1 conditional_router step")
    else:
        test_fail("Conditional step", f"Expected 1, got {len(cond_steps)}")

    if len(agent_steps) == 3:
        test_pass("Found 3 agent steps")
    else:
        test_fail("Agent steps", f"Expected 3, got {len(agent_steps)}")

    # Check condition config is stored
    cond = cond_steps[0] if cond_steps else {}
    condition = cond.get("condition", {})
    if condition and condition.get("operator") == "contains":
        test_pass("Condition config stored correctly")
    else:
        test_fail("Condition config", f"Got: {condition}")

    # Check persona_id is null for conditional step
    if cond.get("persona_id") is None:
        test_pass("Conditional step has null persona_id")
    else:
        test_fail("Conditional persona_id", f"Expected None, got {cond.get('persona_id')}")


def test_2_true_branch(setup: dict):
    """Test that positive input triggers TRUE branch."""
    print("\n=== Test 2: TRUE Branch (Positive Input) ===")

    wf_id = setup["workflow_id"]
    result = run_workflow(
        wf_id,
        "I just got promoted at work and I'm so happy! Best day ever!",
    )

    if result["error"]:
        test_fail("Execution", f"Error: {result['error']}")
        return

    log(f"Agents run: {result['agents_run']}")
    log(f"Conditions evaluated: {result['conditions_evaluated']}")
    log(f"Duration: {result['duration_s']}s")
    log(f"Answer preview: {result['final_answer'][:200]}")

    # Classifier should have run
    if "Classifier" in result["agents_run"]:
        test_pass("Classifier ran")
    else:
        test_fail("Classifier", f"Not in agents: {result['agents_run']}")

    # Condition should have been evaluated
    if "Sentiment Check" in result["conditions_evaluated"]:
        test_pass("Condition was evaluated")
    else:
        test_fail("Condition eval", f"Not in conditions: {result['conditions_evaluated']}")

    # Positive Handler should have run (TRUE branch)
    if "Positive Handler" in result["agents_run"]:
        test_pass("Positive Handler ran (TRUE branch)")
    else:
        test_fail("TRUE branch", f"Positive Handler not in: {result['agents_run']}")

    # Negative Handler should NOT have run (FALSE branch skipped)
    if "Negative Handler" not in result["agents_run"]:
        test_pass("Negative Handler skipped (FALSE branch)")
    else:
        test_fail("FALSE branch skip", "Negative Handler ran but should have been skipped")

    if result["completed"]:
        test_pass("Workflow completed")
    else:
        test_fail("Completion", "Workflow did not complete")


def test_3_false_branch(setup: dict):
    """Test that negative input triggers FALSE branch."""
    print("\n=== Test 3: FALSE Branch (Negative Input) ===")

    wf_id = setup["workflow_id"]
    result = run_workflow(
        wf_id,
        "I lost my job today and I'm feeling terrible. Everything is going wrong.",
    )

    if result["error"]:
        test_fail("Execution", f"Error: {result['error']}")
        return

    log(f"Agents run: {result['agents_run']}")
    log(f"Conditions evaluated: {result['conditions_evaluated']}")
    log(f"Duration: {result['duration_s']}s")
    log(f"Answer preview: {result['final_answer'][:200]}")

    # Classifier should have run
    if "Classifier" in result["agents_run"]:
        test_pass("Classifier ran")
    else:
        test_fail("Classifier", f"Not in agents: {result['agents_run']}")

    # Condition should have been evaluated
    if "Sentiment Check" in result["conditions_evaluated"]:
        test_pass("Condition was evaluated")
    else:
        test_fail("Condition eval", f"Not in conditions: {result['conditions_evaluated']}")

    # Negative Handler should have run (FALSE branch)
    if "Negative Handler" in result["agents_run"]:
        test_pass("Negative Handler ran (FALSE branch)")
    else:
        test_fail("FALSE branch", f"Negative Handler not in: {result['agents_run']}")

    # Positive Handler should NOT have run (TRUE branch skipped)
    if "Positive Handler" not in result["agents_run"]:
        test_pass("Positive Handler skipped (TRUE branch)")
    else:
        test_fail("TRUE branch skip", "Positive Handler ran but should have been skipped")

    if result["completed"]:
        test_pass("Workflow completed")
    else:
        test_fail("Completion", "Workflow did not complete")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test conditional router workflows")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print(f"Base URL: {CONFIG['base_url']}")
    print(f"API Key: {CONFIG['api_key'][:8]}...")

    print("\n" + "=" * 60)
    print("CONDITIONAL ROUTER TEST SUITE")
    print("=" * 60)

    # Setup
    print("\n--- Setup: Creating test workflow ---")
    setup = setup_test_workflow()
    if not setup:
        print("\n[FATAL] Could not create test workflow. Aborting.")
        sys.exit(1)

    log(f"Workflow ID: {setup['workflow_id']}")
    log(f"Persona IDs: {setup['persona_ids']}")

    try:
        test_1_workflow_creation(setup)
        test_2_true_branch(setup)
        test_3_false_branch(setup)
    finally:
        # Cleanup
        print("\n--- Cleanup ---")
        delete_workflow(setup["workflow_id"])
        for pid in setup["persona_ids"]:
            delete_persona(pid)
        log("Cleaned up workflow and personas")

    print(f"\n{'='*60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
