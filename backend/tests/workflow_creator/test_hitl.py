"""
Human-in-the-Loop (HITL) Test for Workflow Pause/Resume
========================================================

Tests the Travel Planner workflow with `can_request_input=True` on the
Details Collector step. Sends a vague initial message, then provides
incremental details across 3 rounds to verify the pause/resume cycle.

Uses the /workflow/{id}/run endpoint with a shared chat_session_id so
the engine can find and resume paused executions.

Flow:
  1. Create a chat session (to get a UUID for tracking)
  2. Send vague message → expect PAUSE
  3. Resume with partial details → expect PAUSE again
  4. Resume with more details → expect PAUSE again
  5. Resume with final details → expect workflow to COMPLETE

Usage:
    python test_hitl.py                    # Use existing "Travel Planner (Interactive)"
    python test_hitl.py --create           # Create from 05_travel_planner_hitl_test.json first
    python test_hitl.py --workflow-id 17   # Use a specific workflow ID
    python test_hitl.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time

from config import (
    WORKFLOWS_DIR,
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)
from create_workflows import create_workflow


# ── Test Messages ────────────────────────────────────────────────────────────

# Round 0: Very vague — missing dates, travelers, origin, budget, interests
INITIAL_MESSAGE = "I want to go to Bali"

# Round 1: Add dates only — still missing travelers, origin, budget
FOLLOWUP_1 = "Sometime in March, about 5 days"

# Round 2: Add travelers and origin — still missing budget
FOLLOWUP_2 = "2 adults, we'll be flying from Dubai"

# Round 3: Add budget and interests — should complete the details collection
FOLLOWUP_3 = "Budget is around $3000 total. We love surfing and temples."


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


def create_chat_session(persona_id: int = 0) -> str | None:
    """Create a chat session and return its UUID."""
    resp = api("POST", "converse/create-chat-session", {"persona_id": persona_id})
    if resp.status_code != 200:
        print(f"[ERROR] Could not create chat session: {resp.status_code} {resp.text[:300]}")
        return None
    data = resp.json()
    session_id = str(data.get("chat_session_id", ""))
    if session_id:
        return session_id
    print(f"[ERROR] No chat_session_id in response: {data}")
    return None


def run_workflow_round(
    workflow_id: int,
    message: str,
    chat_session_id: str | None = None,
) -> tuple[bool, bool, str]:
    """Run one round of workflow execution via /workflow/{id}/run.

    Args:
        workflow_id: The workflow to run
        message: The user's message
        chat_session_id: UUID for pause/resume tracking

    Returns:
        (was_paused, completed, pause_questions)
    """
    body: dict = {"message": message}
    if chat_session_id:
        body["chat_session_id"] = chat_session_id

    resp = stream_api("POST", f"workflow/{workflow_id}/run", body)

    if resp.status_code != 200:
        print(f"[ERROR] Workflow API returned {resp.status_code}: {resp.text[:500]}")
        return False, False, ""

    was_paused = False
    completed = False
    pause_questions = ""
    has_error = False

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)

            # Check for error responses
            if "error" in packet and not "type" in packet.get("obj", {}):
                print(f"  [ERROR] {packet['error'][:200]}")
                has_error = True
                continue

            obj = packet.get("obj", packet)
            ptype = obj.get("type", "unknown")

            if ptype == "workflow_step_start":
                step_name = obj.get("step_name", "?")
                persona = obj.get("persona_name", "?")
                _safe_print(f"\n  [{step_name}] (Agent: {persona})")
                print("  " + "-" * 48)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                _safe_print(f"  {content}", end="")

            elif ptype == "workflow_step_end":
                _safe_print(f"\n  [End: {obj.get('step_name', '?')}]")

            elif ptype == "workflow_orchestrator_thinking":
                content = obj.get("content", "")
                _safe_print(f"\n  [Orchestrator] {content[:150]}...")

            elif ptype == "workflow_pause_for_input":
                was_paused = True
                pause_questions = obj.get("questions", "")
                step_name = obj.get("step_name", "?")
                persona = obj.get("persona_name", "?")
                _safe_print(f"\n  {'='*50}")
                _safe_print(f"  [PAUSED] {persona} needs more info:")
                _safe_print(f"  {'='*50}")
                _safe_print(f"  {pause_questions}")
                _safe_print(f"  {'='*50}")

            elif ptype == "message_start":
                _safe_print("\n  [Final Answer]")
                print("  " + "-" * 48)

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                _safe_print(f"  {content}", end="")

            elif ptype == "stop":
                completed = True
                _safe_print("\n\n  --- Stream Complete ---")

            elif ptype in (
                "message_end", "section_end",
                "reasoning_start", "reasoning_delta",
                "reasoning_end", "reasoning_done",
            ):
                pass

            else:
                # Debug: show unknown packet types
                _safe_print(f"  [{ptype}] {json.dumps(obj)[:150]}")

        except json.JSONDecodeError:
            _safe_print(f"  [RAW] {line[:150]}")

    print()
    return was_paused, completed, pause_questions


# ── Main Test ────────────────────────────────────────────────────────────────


def run_hitl_test(
    workflow_id: int | None = None,
    do_create: bool = False,
):
    """Run the full HITL test cycle."""

    # ── Step 1: Find or create workflow ──────────────────────────────────
    if do_create:
        print("\n" + "=" * 60)
        print("STEP 1: Creating HITL Test Workflow")
        print("=" * 60)

        json_file = WORKFLOWS_DIR / "05_travel_planner_hitl_test.json"
        if not json_file.exists():
            print(f"[ERROR] File not found: {json_file}")
            sys.exit(1)

        payload = json.loads(json_file.read_text(encoding="utf-8"))
        workflow_name = payload["name"]

        # Check if already exists
        resp = api("GET", "workflow")
        if resp.status_code == 200:
            for w in resp.json():
                if w["name"] == workflow_name:
                    workflow_id = w["id"]
                    print(f"  [SKIP] Already exists: ID={workflow_id}")
                    break

        if workflow_id is None:
            result = create_workflow(payload)
            if result:
                workflow_id = result["id"]
                print(f"  [OK] Created workflow ID={workflow_id}")
            else:
                print("[FAIL] Could not create workflow")
                sys.exit(1)

    elif workflow_id is None:
        # Auto-find "Travel Planner (Interactive)" which has HITL enabled
        print("\n" + "=" * 60)
        print("STEP 1: Finding HITL-enabled Workflow")
        print("=" * 60)

        resp = api("GET", "workflow")
        if resp.status_code != 200:
            print(f"[ERROR] Could not list workflows: {resp.status_code}")
            sys.exit(1)

        for w in resp.json():
            # Look for any workflow with can_request_input on a step
            for step in w.get("steps", []):
                if step.get("can_request_input"):
                    workflow_id = w["id"]
                    print(f"  [OK] Found: '{w['name']}' (ID={workflow_id})")
                    print(f"       HITL step: {step['step_name']}")
                    break
            if workflow_id:
                break

        if workflow_id is None:
            print("[ERROR] No workflow with can_request_input=True found.")
            print("        Run with --create or create one manually.")
            sys.exit(1)

    print(f"\n  Using workflow ID={workflow_id}")

    # ── Step 2: Create chat session for tracking ─────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Creating Chat Session (for pause/resume tracking)")
    print("=" * 60)

    chat_session_id = create_chat_session()
    if not chat_session_id:
        print("[ERROR] Could not create chat session")
        sys.exit(1)
    print(f"  [OK] chat_session_id = {chat_session_id}")

    # ── Step 3: Run test rounds ──────────────────────────────────────────
    messages = [
        ("ROUND 0 - Vague request (expect PAUSE)", INITIAL_MESSAGE),
        ("ROUND 1 - Add dates (expect PAUSE)", FOLLOWUP_1),
        ("ROUND 2 - Add travelers + origin (expect PAUSE)", FOLLOWUP_2),
        ("ROUND 3 - Add budget + interests (expect COMPLETE)", FOLLOWUP_3),
    ]

    results = []
    start_time = time.time()

    for i, (label, message) in enumerate(messages):
        print("\n" + "=" * 60)
        print(f"ROUND {i}: {label}")
        print(f"  User: \"{message}\"")
        print("=" * 60)

        round_start = time.time()
        was_paused, completed, questions = run_workflow_round(
            workflow_id=workflow_id,
            message=message,
            chat_session_id=chat_session_id,
        )
        round_duration = time.time() - round_start

        results.append({
            "round": i,
            "label": label,
            "message": message,
            "was_paused": was_paused,
            "completed": completed,
            "had_questions": bool(questions),
            "duration_s": round(round_duration, 1),
        })

        print(f"  Duration: {round_duration:.1f}s | Paused: {was_paused} | Completed: {completed}")

        # Brief pause between rounds for DB to settle
        if was_paused and i < len(messages) - 1:
            print(f"\n  Waiting 2s before next round...")
            time.sleep(2)

        # If workflow completed (no pause), remaining rounds are skipped
        if completed and not was_paused:
            print(f"\n  [INFO] Workflow completed at round {i} - skipping remaining rounds")
            break

    total_time = time.time() - start_time

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for r in results:
        if r["round"] < 3:
            # Rounds 0-2 should pause
            if r["was_paused"]:
                status = "PASS (paused as expected)"
            elif r["completed"]:
                status = "WARN (completed early - agent had enough info)"
            else:
                status = "FAIL (expected pause but got neither pause nor complete)"
                all_passed = False
        else:
            # Round 3 should complete (or at least not pause indefinitely)
            if r["completed"] and not r["was_paused"]:
                status = "PASS (completed as expected)"
            elif r["was_paused"]:
                status = "WARN (paused again - agent wants even more info)"
            elif r["completed"]:
                status = "PASS (completed)"
            else:
                status = "FAIL (neither paused nor completed)"
                all_passed = False

        print(f"  Round {r['round']}: {status}  ({r['duration_s']}s)")
        print(f"    Message: \"{r['message']}\"")

    print(f"\n  Total time: {total_time:.1f}s")
    print("-" * 60)
    if all_passed:
        print("  OVERALL: ALL TESTS PASSED")
    else:
        print("  OVERALL: SOME TESTS FAILED - see above")
    print("-" * 60 + "\n")

    return all_passed


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test Human-in-the-Loop workflow pause/resume",
    )
    parser.add_argument(
        "--create", action="store_true",
        help="Create HITL test workflow from JSON before running",
    )
    parser.add_argument(
        "--workflow-id", type=int, default=None,
        help="Use a specific workflow ID",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    success = run_hitl_test(
        workflow_id=args.workflow_id,
        do_create=args.create,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
