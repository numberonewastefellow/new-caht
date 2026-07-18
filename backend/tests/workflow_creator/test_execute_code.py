"""
Test: Execute Code from Chat (Run button)

Verifies:
1. POST /chat/execute-code executes Python code in the sandbox
2. Result is saved as a sibling ChatMessage (parent-child)
3. Message appears when loading chat history (1/2, 2/2)

Usage:
    python test_execute_code.py [--key API_KEY] [--url BASE_URL]
"""

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import UUID

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


def create_chat_session(agent_id: int = 0) -> str | None:
    """Create a new chat session. Returns chat_session_id."""
    body = {
        "agent_id": agent_id,
        "description": "test-execute-code",
    }
    resp = api("POST", "converse/create-chat-session", body)
    if resp.status_code != 200:
        log(f"Failed to create chat session: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("chat_session_id")


def send_message(chat_session_id: str, message: str, parent_message_id: int = -1) -> dict | None:
    """Send a chat message and collect the streamed response.
    Returns dict with user_message_id, assistant_message_id, response_text.
    """
    body = {
        "message": message,
        "chat_session_id": chat_session_id,
        "parent_message_id": parent_message_id,
        "file_descriptors": [],
        "stream": True,
        "origin": "webapp",
    }

    resp = stream_api("POST", "converse/send-chat-message", body)
    if resp.status_code != 200:
        log(f"Failed to send message: {resp.status_code} {resp.text}")
        return None

    # Parse SSE stream
    user_message_id = None
    assistant_message_id = None
    response_text = ""

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)
        except json.JSONDecodeError:
            continue

        # First packet has the message IDs
        if "user_message_id" in packet:
            user_message_id = packet["user_message_id"]
        if "reserved_assistant_message_id" in packet:
            assistant_message_id = packet["reserved_assistant_message_id"]

        # Collect text from message_delta packets
        obj = packet.get("obj", {})
        if isinstance(obj, dict) and obj.get("type") == "message_delta":
            content = obj.get("content", "")
            if content:
                response_text += content

    return {
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
        "response_text": response_text,
    }


def get_chat_session_detail(chat_session_id: str) -> dict | None:
    """Get full chat session detail including all messages."""
    resp = api("GET", f"converse/get-chat-session/{chat_session_id}")
    if resp.status_code != 200:
        log(f"Failed to get chat session: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def execute_code(
    chat_session_id: str, parent_message_id: int, code: str
) -> dict | None:
    """Call POST /chat/execute-code and return the response."""
    body = {
        "chat_session_id": chat_session_id,
        "parent_message_id": parent_message_id,
        "code": code,
    }
    resp = api("POST", "converse/execute-code", body)
    if resp.status_code != 200:
        log(f"Execute code failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()


# ── tests ─────────────────────────────────────────────────────────────────────


def test_1_basic_execution():
    """Test basic code execution and DB persistence."""
    print("\n=== Test 1: Basic Code Execution ===")

    # Create a chat session
    session_id = create_chat_session()
    if not session_id:
        test_fail("Create chat session", "Could not create session")
        return

    log(f"Chat session: {session_id}")

    # Send a user message to get a parent message
    result = send_message(session_id, "Write a hello world in Python")
    if not result or not result.get("user_message_id"):
        test_fail("Send message", f"No user_message_id returned: {result}")
        return

    user_msg_id = result["user_message_id"]
    assistant_msg_id = result["assistant_message_id"]
    log(f"User message ID: {user_msg_id}")
    log(f"Assistant message ID: {assistant_msg_id}")

    # Now execute code as a sibling of the assistant response (same parent = user msg)
    code = 'print("Hello from Run button!")\nprint(2 + 2)'
    exec_result = execute_code(session_id, user_msg_id, code)

    if not exec_result:
        test_fail("Execute code", "No response from execute-code endpoint")
        return

    log(f"Execute code response: {json.dumps(exec_result, indent=2)}")

    # Verify stdout
    if "Hello from Run button!" in exec_result.get("stdout", ""):
        test_pass("stdout contains expected output")
    else:
        test_fail("stdout check", f"Expected 'Hello from Run button!' in stdout, got: {exec_result.get('stdout')}")

    # Verify message was created
    new_msg_id = exec_result.get("message_id")
    if new_msg_id:
        test_pass(f"New message created with ID {new_msg_id}")
    else:
        test_fail("Message creation", "No message_id in response")
        return

    # Verify parent_message_id matches
    if exec_result.get("parent_message_id") == user_msg_id:
        test_pass("Parent message ID matches (sibling relationship)")
    else:
        test_fail(
            "Parent check",
            f"Expected parent {user_msg_id}, got {exec_result.get('parent_message_id')}",
        )

    # Verify it appears in chat history as a sibling
    detail = get_chat_session_detail(session_id)
    if not detail:
        test_fail("Load chat history", "Could not load session detail")
        return

    messages = detail.get("messages", [])
    log(f"Total messages in session: {len(messages)}")

    # Find messages with same parent (siblings = user msg's children)
    siblings = [m for m in messages if m.get("parent_message") == user_msg_id]
    log(f"Siblings under parent {user_msg_id}: {len(siblings)}")

    if len(siblings) >= 2:
        test_pass(f"Found {len(siblings)} siblings (1/{len(siblings)}, 2/{len(siblings)} navigation)")
    else:
        test_fail(
            "Sibling check",
            f"Expected >= 2 siblings under parent {user_msg_id}, found {len(siblings)}",
        )

    # Check the new execution message is in the siblings
    exec_msg = next((m for m in siblings if m.get("message_id") == new_msg_id), None)
    if exec_msg:
        test_pass("Execution result message found in chat history")
        log(f"  Message content preview: {exec_msg.get('message', '')[:200]}")
    else:
        test_fail("Execution message in history", f"Message {new_msg_id} not found in siblings")


def test_2_execution_with_plot():
    """Test code execution that generates a plot (file output)."""
    print("\n=== Test 2: Code Execution with Plot ===")

    session_id = create_chat_session()
    if not session_id:
        test_fail("Create chat session", "Could not create session")
        return

    log(f"Chat session: {session_id}")

    # Send a message
    result = send_message(session_id, "Show me a chart")
    if not result or not result.get("user_message_id"):
        test_fail("Send message", f"No user_message_id returned: {result}")
        return

    parent_msg_id = result["user_message_id"]

    # Execute matplotlib code
    code = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.figure(figsize=(6, 4))
plt.bar(['A', 'B', 'C'], [10, 20, 15])
plt.title('Test Chart from Run Button')
plt.savefig('chart.png', dpi=72)
plt.close()
print("Chart saved successfully")
"""

    exec_result = execute_code(session_id, parent_msg_id, code)
    if not exec_result:
        test_fail("Execute plot code", "No response")
        return

    log(f"stdout: {exec_result.get('stdout', '')}")
    log(f"stderr: {exec_result.get('stderr', '')[:200]}")
    log(f"files: {json.dumps(exec_result.get('files', []), indent=2)}")

    if "Chart saved successfully" in exec_result.get("stdout", ""):
        test_pass("Plot code executed successfully")
    else:
        test_fail("Plot execution", f"Unexpected stdout: {exec_result.get('stdout')}")

    files = exec_result.get("files", [])
    if files:
        test_pass(f"Generated {len(files)} file(s): {[f.get('name') for f in files]}")
    else:
        log("Note: No files returned (matplotlib may not be available in sandbox)")


def test_3_session_reuse():
    """Test that multiple executions in same chat reuse the sandbox session."""
    print("\n=== Test 3: Session Reuse (Variables Persist) ===")

    session_id = create_chat_session()
    if not session_id:
        test_fail("Create chat session", "Could not create session")
        return

    log(f"Chat session: {session_id}")

    result = send_message(session_id, "Let me test variables")
    if not result or not result.get("user_message_id"):
        test_fail("Send message", f"No user_message_id: {result}")
        return

    parent_msg_id = result["user_message_id"]

    # First execution — define a variable
    exec1 = execute_code(session_id, parent_msg_id, "my_var = 42\nprint(f'Set my_var = {my_var}')")
    if not exec1:
        test_fail("First execution", "Failed")
        return

    if "my_var = 42" in exec1.get("stdout", ""):
        test_pass("First execution: variable set")
    else:
        test_fail("First execution", f"Unexpected: {exec1.get('stdout')}")

    # Second execution — read the variable (should persist in same sandbox)
    exec2 = execute_code(session_id, parent_msg_id, "print(f'Read my_var = {my_var}')")
    if not exec2:
        test_fail("Second execution", "Failed")
        return

    if "my_var = 42" in exec2.get("stdout", ""):
        test_pass("Second execution: variable persists across executions (session reuse)")
    else:
        test_fail("Session reuse", f"Variable not found: {exec2.get('stdout')}")

    # Verify all executions created sibling messages
    detail = get_chat_session_detail(session_id)
    if detail:
        messages = detail.get("messages", [])
        siblings = [m for m in messages if m.get("parent_message") == parent_msg_id]
        log(f"Total siblings under parent {parent_msg_id}: {len(siblings)}")
        if len(siblings) >= 3:  # original assistant + 2 executions
            test_pass(f"All executions saved as siblings ({len(siblings)} total)")
        else:
            test_fail("Sibling count", f"Expected >= 3, got {len(siblings)}")


def test_4_error_handling():
    """Test error handling for invalid code."""
    print("\n=== Test 4: Error Handling ===")

    session_id = create_chat_session()
    if not session_id:
        test_fail("Create chat session", "Could not create session")
        return

    result = send_message(session_id, "Test error handling")
    if not result or not result.get("user_message_id"):
        test_fail("Send message", f"No user_message_id: {result}")
        return

    parent_msg_id = result["user_message_id"]

    # Execute code with syntax error
    exec_result = execute_code(session_id, parent_msg_id, "1/0  # Division by zero")
    if not exec_result:
        test_fail("Error execution", "No response")
        return

    stderr = exec_result.get("stderr", "")
    if "ZeroDivisionError" in stderr:
        test_pass("Error captured in stderr")
    else:
        test_fail("Error capture", f"Expected ZeroDivisionError in stderr, got: {stderr[:200]}")

    # Message should still be saved even with errors
    if exec_result.get("message_id"):
        test_pass("Error result saved as message")
    else:
        test_fail("Error message save", "No message_id for error execution")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test execute-code endpoint")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print(f"Base URL: {CONFIG['base_url']}")
    print(f"API Key: {CONFIG['api_key'][:8]}...")

    test_1_basic_execution()
    test_2_execution_with_plot()
    test_3_session_reuse()
    test_4_error_handling()

    print(f"\n{'='*50}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
