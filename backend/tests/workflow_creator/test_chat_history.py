"""
Test: Workflow Chat History Persistence
========================================

Verifies that workflow messages are persisted to the chat_message table
so they survive page reloads.

Flow:
  1. Create a chat session with the Travel Planner agent
  2. Send a message via the /chat/send-message API (same path as UI)
  3. Verify the assistant response is saved to DB by loading the session
  4. Check that the response contains actual content (not empty/placeholder)

Usage:
    python test_chat_history.py --agent-id <ID>
    python test_chat_history.py --agent-id <ID> --workflow-id 17  # also run HITL round
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


def _safe_print(text: str, **kwargs):
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe, **kwargs)


def create_chat_session(agent_id: int) -> str | None:
    """Create a chat session with the given agent."""
    resp = api("POST", "converse/create-chat-session", {"agent_id": agent_id})
    if resp.status_code != 200:
        print(f"[ERROR] Create session failed: {resp.status_code} {resp.text[:300]}")
        return None
    data = resp.json()
    return str(data.get("chat_session_id", ""))


def send_chat_message(
    chat_session_id: str,
    message: str,
    agent_id: int,
    parent_message_id: int | None = None,
) -> tuple[int | None, int | None, str]:
    """Send a message via the chat API and stream the response.

    Returns (user_message_id, assistant_message_id, collected_answer_text).
    """
    body = {
        "chat_session_id": chat_session_id,
        "message": message,
        "agent_id": agent_id,
        "prompt_id": 0,
        "parent_message_id": parent_message_id or -1,
        "search_doc_ids": None,
        "retrieval_options": None,
        "query_override": None,
        "include_citations": True,
    }

    resp = stream_api("POST", "converse/send-chat-message", body)
    if resp.status_code != 200:
        print(f"[ERROR] Send message failed: {resp.status_code} {resp.text[:500]}")
        return None, None, ""

    user_msg_id = None
    assistant_msg_id = None
    answer_parts = []

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            data = json.loads(line)

            # MessageResponseIDInfo (first packet)
            if "user_message_id" in data:
                user_msg_id = data["user_message_id"]
                assistant_msg_id = data.get("reserved_assistant_message_id")
                continue

            # Streaming error
            if "error" in data and "type" not in data.get("obj", {}):
                print(f"  [ERROR] {data['error'][:200]}")
                continue

            obj = data.get("obj", data)
            ptype = obj.get("type", "")

            if ptype == "workflow_step_start":
                _safe_print(f"  [{obj.get('step_name', '?')}] running...")
            elif ptype == "workflow_step_delta":
                pass  # Skip verbose output
            elif ptype == "workflow_step_end":
                _safe_print(f"  [{obj.get('step_name', '?')}] done")
            elif ptype == "workflow_pause_for_input":
                _safe_print(f"  [PAUSED] {obj.get('agent_name', '?')}")
            elif ptype == "message_delta":
                content = obj.get("content", "")
                answer_parts.append(content)
            elif ptype == "stop":
                _safe_print("  [COMPLETE]")

        except json.JSONDecodeError:
            pass

    return user_msg_id, assistant_msg_id, "".join(answer_parts)


def load_chat_session(chat_session_id: str) -> dict | None:
    """Load a chat session to verify persisted messages."""
    resp = api("GET", f"converse/get-chat-session/{chat_session_id}")
    if resp.status_code != 200:
        print(f"[ERROR] Load session failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Test workflow chat history persistence")
    parser.add_argument("--agent-id", type=int, required=True, help="Agent ID with workflow_id set")
    parser.add_argument("--workflow-id", type=int, default=None, help="Workflow ID (for info only)")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)

    agent_id = args.agent_id

    print("\n" + "=" * 60)
    print("TEST: Workflow Chat History Persistence")
    print("=" * 60)

    # Step 1: Create chat session
    print("\n[1] Creating chat session...")
    session_id = create_chat_session(agent_id)
    if not session_id:
        sys.exit(1)
    print(f"  Session ID: {session_id}")

    # Step 2: Send a message via chat API
    print("\n[2] Sending message via /chat/send-message...")
    message = "I want to travel to Georgia country for skiing with my family"
    print(f"  Message: \"{message}\"")

    user_id, asst_id, answer = send_chat_message(session_id, message, agent_id)
    print(f"  User msg ID: {user_id}")
    print(f"  Assistant msg ID: {asst_id}")
    answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
    _safe_print(f"  Answer preview: {answer_preview}")

    # Step 3: Wait briefly, then load the session
    print("\n[3] Loading chat session to verify persistence...")
    time.sleep(2)

    session_data = load_chat_session(session_id)
    if not session_data:
        sys.exit(1)

    messages = session_data.get("messages", [])
    packets_list = session_data.get("packets", [])

    print(f"  Messages in DB: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_type = msg.get("message_type", "?")
        msg_text = (msg.get("message", "") or "")[:100]
        msg_id = msg.get("message_id", "?")
        _safe_print(f"    [{i}] id={msg_id} type={msg_type} text=\"{msg_text}...\"")

    print(f"  Packet lists (for assistant messages): {len(packets_list)}")
    for i, plist in enumerate(packets_list):
        print(f"    [{i}] {len(plist)} packets")
        # Show packet types
        ptypes = [p.get("obj", {}).get("type", "?") for p in plist[:10]]
        print(f"        Types: {ptypes}")

    # Step 4: Verify
    print("\n[4] Verification...")
    all_ok = True

    # Check we have at least user + assistant messages (plus root)
    non_root_msgs = [m for m in messages if m.get("message_type") != "system"]
    user_msgs = [m for m in messages if m.get("message_type") == "user"]
    asst_msgs = [m for m in messages if m.get("message_type") == "assistant"]

    if len(user_msgs) >= 1:
        print(f"  [OK] User messages found: {len(user_msgs)}")
    else:
        print(f"  [FAIL] No user messages found")
        all_ok = False

    if len(asst_msgs) >= 1:
        print(f"  [OK] Assistant messages found: {len(asst_msgs)}")
        # Check assistant message has content
        for am in asst_msgs:
            text = am.get("message", "") or ""
            if len(text) > 10:
                _safe_print(f"  [OK] Assistant message has content ({len(text)} chars)")
            else:
                print(f"  [FAIL] Assistant message is empty or too short: \"{text}\"")
                all_ok = False
    else:
        print(f"  [FAIL] No assistant messages found")
        all_ok = False

    # Check packets reconstruction
    if packets_list:
        for i, plist in enumerate(packets_list):
            if len(plist) > 0:
                print(f"  [OK] Packet list [{i}] has {len(plist)} packets for reconstruction")
            else:
                print(f"  [WARN] Packet list [{i}] is empty")
    else:
        print(f"  [WARN] No packet lists returned (timeline won't reconstruct)")

    print("\n" + "-" * 60)
    if all_ok:
        print("  RESULT: PASS - Chat history persists correctly")
    else:
        print("  RESULT: FAIL - Chat history NOT persisted")
    print("-" * 60 + "\n")

    return all_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
