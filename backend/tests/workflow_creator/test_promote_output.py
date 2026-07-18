"""
Test: promote_output packet ordering -- sequential vs llm_decision
==================================================================

Bug:  When a workflow step has promote_output=true, the backend emits
      the promoted output (message_start + message_delta) BEFORE the
      step's WorkflowStepEnd packet. The frontend's handleToolAfterMessage-
      Packet() sees the trailing WorkflowStepEnd as a tool packet arriving
      after message_start and resets finalAnswerComing=false, which hides
      the promoted output from the display area.

Why llm_decision is not affected:
      After all tool calls, the orchestrator emits a SECOND message_start
      as its own final answer (workflow_engine.py line 1834). This comes
      AFTER the last WorkflowStepEnd and re-sets finalAnswerComing=true,
      so the frontend displays it. This is accidental recovery, not by
      design -- the same ordering bug exists but is masked.

Fix:  In workflow_engine.py sequential mode, move WorkflowStepEnd +
      SectionEnd to emit BEFORE the promote_output block so no tool
      packet follows the promoted message_start.

      Optionally, update packetUtils.ts isActualToolCallPacket() to
      exclude WORKFLOW_STEP_* packets from the finalAnswerComing reset.

Test results (BEFORE fix):
      Sequential:    BUG  -- message_start[6] followed by step_end[9]
      LLM-Decision:  OK   -- message_start[22] is last (orchestrator recovery)

Test results (AFTER fix):
      Sequential:    OK   -- message_start comes after all step_end packets
      LLM-Decision:  OK   -- unchanged

Tested packet sequence (sequential, BEFORE fix):
      [0] turn=0  wf_step_start   Echo Agent (promote=False)
      [1] turn=0  wf_step_delta   ECHO: ...
      [2] turn=0  wf_step_end     Echo Agent
      [3] turn=0  section_end
      [4] turn=1  wf_step_start   Summary Agent (promote=True)
      [5] turn=1  wf_step_delta   SUMMARY: ...
      [6] turn=2  message_start                    <-- finalAnswerComing=true
      [7] turn=2  message_delta   SUMMARY: ...
      [8] turn=2  section_end
      [9] turn=1  wf_step_end     Summary Agent    <-- RESETS finalAnswerComing=false
     [10] turn=1  section_end
     [11] turn=3  stop

Related files:
      Backend:   backend/onyx/workflows/workflow_engine.py (sequential engine)
      Frontend:  web/src/app/app/services/packetUtils.ts (isActualToolCallPacket)
      Frontend:  web/src/app/app/message/.../hooks/packetProcessor.ts (handleToolAfterMessagePacket)

Usage:
    python test_promote_output.py                    # test both modes
    python test_promote_output.py --sequential-only  # test sequential only
    python test_promote_output.py --llm-only         # test llm_decision only
    python test_promote_output.py --skip-create      # reuse existing workflows
    python test_promote_output.py --cleanup          # delete test workflows after
    python test_promote_output.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

from config import (  # noqa: E402
    api,
    stream_api,
    add_common_args,
    apply_common_args,
)

# ── Test Agents & Workflows ────────────────────────────────────────────────

ECHO_PROMPT = (
    "You are Echo Agent. Repeat the user's message with the prefix 'ECHO: '. "
    "Keep it very short — one sentence max. Do not add anything else."
)
SUMMARY_PROMPT = (
    "You are Summary Agent. Write a one-sentence summary of all prior outputs. "
    "Start with 'SUMMARY: '. Keep it very short. "
    "STATUS: COMPLETE"
)

ORCHESTRATOR_PROMPT = (
    "You coordinate two agents. For any user message:\n"
    "1. First call echo_agent with the user's message\n"
    "2. Then call summary_agent to summarize\n"
    "Always call both agents in order. After summary_agent responds, "
    "provide the summary as your final answer."
)

TEST_MESSAGE = "The quick brown fox jumps over the lazy dog."


def create_agent(name: str, prompt: str) -> int | None:
    body = {
        "name": name,
        "description": f"Test agent: {name}",
        "num_chunks": 0,
        "is_public": True,
        "system_prompt": prompt,
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
    r = api("POST", "agent", body)
    if r.status_code not in (200, 201):
        print(f"  [ERR] Create agent '{name}': {r.status_code} {r.text[:200]}")
        return None
    pid = r.json()["id"]
    print(f"  [OK] Agent '{name}' -> ID={pid}")
    return pid


def find_or_create_agent(name: str, prompt: str) -> int | None:
    """Find existing agent by name, or create new one."""
    resp = api("GET", "agent")
    if resp.status_code == 200:
        for p in resp.json():
            if p["name"] == name:
                print(f"  [OK] Reusing agent '{name}' -> ID={p['id']}")
                return p["id"]
    return create_agent(name, prompt)


def create_workflow(name: str, mode: str, echo_pid: int, summary_pid: int,
                    orchestrator_prompt: str = "") -> int | None:
    steps = [
        {
            "agent_id": echo_pid,
            "step_order": 0,
            "step_name": "Echo Agent",
            "step_description": "Echoes the input",
            "output_key": "echo_output",
            "is_terminal": False,
            "can_request_input": False,
            "promote_output": False,
        },
        {
            "agent_id": summary_pid,
            "step_order": 1,
            "step_name": "Summary Agent",
            "step_description": "Summarizes all outputs",
            "output_key": "summary_output",
            "is_terminal": True if mode == "sequential" else False,
            "can_request_input": False,
            "promote_output": True,
        },
    ]
    body = {
        "name": name,
        "description": f"Test promote_output in {mode} mode",
        "orchestration_mode": mode,
        "orchestrator_prompt": orchestrator_prompt,
        "max_steps": 10,
        "max_calls_per_agent": 2,
        "timeout_seconds": 120,
        "is_public": True,
        "steps": steps,
    }
    r = api("POST", "admin/workflow", body)
    if r.status_code not in (200, 201):
        print(f"  [ERR] Create workflow '{name}': {r.status_code} {r.text[:200]}")
        return None
    wid = r.json()["id"]
    print(f"  [OK] Workflow '{name}' -> ID={wid} (mode={mode})")
    return wid


def find_workflow(name: str) -> int | None:
    resp = api("GET", "workflow")
    if resp.status_code == 200:
        for w in resp.json():
            if w["name"] == name:
                return w["id"]
    return None


def delete_workflow(wid: int) -> None:
    api("DELETE", f"admin/workflow/{wid}")


# ── Stream & Observe ─────────────────────────────────────────────────────────

def stream_and_observe(workflow_id: int, message: str, label: str) -> dict:
    """Stream a workflow run and log every packet with type + placement.

    Returns a result dict with:
      - packets: list of (turn_index, type, content_preview)
      - message_start_indices: positions where message_start appeared
      - step_end_indices: positions where workflow_step_end appeared
      - final_answer: the promoted/final text
      - bug_detected: True if message_start comes before a later workflow_step_end
    """
    print(f"\n{'='*70}")
    print(f"  STREAMING: {label}")
    print(f"  Workflow ID={workflow_id} | Message: \"{message[:60]}...\"")
    print(f"{'='*70}")

    result = {
        "packets": [],
        "message_start_positions": [],
        "step_end_positions": [],
        "final_answer": "",
        "agents_run": [],
        "completed": False,
        "error": None,
    }

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", {"message": message})

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        print(f"  [ERR] {result['error']}")
        return result

    packet_index = 0
    final_parts = []
    in_final = False

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)
        except json.JSONDecodeError:
            continue

        if "error" in packet and "type" not in packet.get("obj", {}):
            result["error"] = packet["error"][:200]
            continue

        obj = packet.get("obj", packet)
        ptype = obj.get("type", "unknown")
        placement = packet.get("placement", {})
        turn_idx = placement.get("turn_index", "?")

        # Content preview
        content = ""
        if ptype == "workflow_step_start":
            content = obj.get("step_name", "")
            promote = obj.get("promote_output", False)
            content += f" (promote={promote})"
            if obj.get("step_name") not in result["agents_run"]:
                result["agents_run"].append(obj.get("step_name"))
        elif ptype == "workflow_step_delta":
            content = (obj.get("content", "") or "")[:80]
        elif ptype == "workflow_step_end":
            content = obj.get("step_name", "")
        elif ptype == "message_start":
            content = "(final_documents present)" if obj.get("final_documents") else ""
        elif ptype == "message_delta":
            delta = obj.get("content", obj.get("delta", ""))
            content = (delta or "")[:80]
            if delta:
                final_parts.append(delta)
                in_final = True
        elif ptype == "workflow_orchestrator_thinking":
            content = (obj.get("content", "") or "")[:60]
        elif ptype == "workflow_pause_for_input":
            content = (obj.get("questions", "") or "")[:60]
        elif ptype == "section_end":
            content = ""
        elif ptype == "stop":
            result["completed"] = True
            content = obj.get("stop_reason", "")

        # Track positions with turn_index for per-step bug detection
        if ptype == "message_start":
            result["message_start_positions"].append((packet_index, turn_idx))
        if ptype == "workflow_step_end":
            result["step_end_positions"].append((packet_index, turn_idx))

        # Log the packet
        content = content or ""
        entry = (turn_idx, ptype, content[:80])
        result["packets"].append(entry)

        # Pretty print
        type_display = ptype.replace("workflow_", "wf_")
        content_display = f" -> {content[:70]}" if content else ""
        print(f"  [{packet_index:3d}] turn={turn_idx} | {type_display:30s}{content_display}")

        packet_index += 1

    result["final_answer"] = "".join(final_parts)
    duration = round(time.time() - start, 1)

    print(f"\n  --- Stream complete ({duration}s) ---")
    print(f"  Agents: {result['agents_run']}")
    print(f"  Final answer length: {len(result['final_answer'])} chars")
    if result["final_answer"]:
        print(f"  Final answer preview: {result['final_answer'][:120]}...")
    print(f"  message_start at packet positions: {result['message_start_positions']}")
    print(f"  workflow_step_end at packet positions: {result['step_end_positions']}")

    # Bug detection: For each promote_output step, the promoted message_start
    # (turn N+1) must come AFTER that step's workflow_step_end (turn N).
    # A step_end from a DIFFERENT step at a later turn is fine — it's a
    # separate group and won't reset finalAnswerComing for the earlier promote.
    bug = False
    for ms_pos, ms_turn in result["message_start_positions"]:
        # The promoting step has turn = ms_turn - 1
        promoting_step_turn = ms_turn - 1
        for se_pos, se_turn in result["step_end_positions"]:
            if se_turn == promoting_step_turn and se_pos > ms_pos:
                bug = True
                print(f"\n  !! BUG: message_start at [{ms_pos}] (turn={ms_turn}) "
                      f"is followed by its step's workflow_step_end at [{se_pos}] "
                      f"(turn={se_turn})")
                print(f"    -> This will reset finalAnswerComing=false in the frontend")

    if not bug and result["message_start_positions"]:
        print(f"\n  OK: All promoted message_start packets come AFTER their step's workflow_step_end")

    if not result["message_start_positions"]:
        print(f"\n  !! WARNING: No message_start packet found -- no final answer emitted")

    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test promote_output packet ordering")
    add_common_args(parser)
    parser.add_argument("--skip-create", action="store_true",
                        help="Skip workflow creation, reuse existing")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete test workflows after running")
    parser.add_argument("--sequential-only", action="store_true",
                        help="Only test sequential mode")
    parser.add_argument("--llm-only", action="store_true",
                        help="Only test llm_decision mode")
    args = parser.parse_args()
    apply_common_args(args)

    SEQ_NAME = "ZZ_Test_Promote_Sequential"
    LLM_NAME = "ZZ_Test_Promote_LLM_Decision"

    seq_wid = None
    llm_wid = None

    # ── Setup ──
    if not args.skip_create:
        print("\n" + "=" * 70)
        print("  SETUP: Creating test agents and workflows")
        print("=" * 70)

        echo_pid = find_or_create_agent("ZZ_Test_Echo_Agent", ECHO_PROMPT)
        summary_pid = find_or_create_agent("ZZ_Test_Summary_Agent", SUMMARY_PROMPT)

        if not echo_pid or not summary_pid:
            print("[FATAL] Could not create test agents")
            sys.exit(1)

        # Check if workflows already exist
        seq_wid = find_workflow(SEQ_NAME)
        llm_wid = find_workflow(LLM_NAME)

        if not seq_wid and not args.llm_only:
            seq_wid = create_workflow(SEQ_NAME, "sequential", echo_pid, summary_pid)
        elif seq_wid:
            print(f"  [OK] Reusing workflow '{SEQ_NAME}' -> ID={seq_wid}")

        if not llm_wid and not args.sequential_only:
            llm_wid = create_workflow(LLM_NAME, "llm_decision", echo_pid, summary_pid,
                                      orchestrator_prompt=ORCHESTRATOR_PROMPT)
        elif llm_wid:
            print(f"  [OK] Reusing workflow '{LLM_NAME}' -> ID={llm_wid}")
    else:
        seq_wid = find_workflow(SEQ_NAME)
        llm_wid = find_workflow(LLM_NAME)
        print(f"  Reusing: sequential={seq_wid}, llm_decision={llm_wid}")

    # ── Run Tests ──
    results = {}

    if seq_wid and not args.llm_only:
        results["sequential"] = stream_and_observe(
            seq_wid, TEST_MESSAGE, "SEQUENTIAL mode (promote_output=true)"
        )

    if llm_wid and not args.sequential_only:
        results["llm_decision"] = stream_and_observe(
            llm_wid, TEST_MESSAGE, "LLM_DECISION mode (promote_output=true)"
        )

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}")

    for mode, r in results.items():
        has_final = len(r["final_answer"]) > 0
        msg_positions = r["message_start_positions"]
        end_positions = r["step_end_positions"]

        # Check if any promoted message_start is followed by its own step's step_end
        bug = False
        for ms_pos, ms_turn in msg_positions:
            promoting_step_turn = ms_turn - 1
            for se_pos, se_turn in end_positions:
                if se_turn == promoting_step_turn and se_pos > ms_pos:
                    bug = True

        status = "BUG" if bug else ("OK" if has_final else "NO_OUTPUT")
        print(f"\n  {mode.upper()}:")
        print(f"    Status:          {status}")
        print(f"    Agents run:      {r['agents_run']}")
        print(f"    Completed:       {r['completed']}")
        print(f"    Final answer:    {len(r['final_answer'])} chars")
        print(f"    message_start:   positions {[p for p, _ in msg_positions]}")
        print(f"    step_end:        positions {[p for p, _ in end_positions]}")
        if bug:
            print(f"    !! BUG: promoted message_start before its step's step_end")
        if r.get("error"):
            print(f"    Error:           {r['error']}")

    # ── Cleanup ──
    if args.cleanup:
        print(f"\n  Cleaning up...")
        if seq_wid:
            delete_workflow(seq_wid)
            print(f"  Deleted workflow {seq_wid}")
        if llm_wid:
            delete_workflow(llm_wid)
            print(f"  Deleted workflow {llm_wid}")

    print()


if __name__ == "__main__":
    main()
