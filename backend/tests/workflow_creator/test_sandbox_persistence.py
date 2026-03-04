"""
Sandbox Persistence Test
========================

Verifies that the Code Interpreter sandbox persists variables and files
across multiple messages within the same chat session (ChatGPT-style behavior).

Test flow:
  Message 1: Set x = 42 and create a DataFrame — force PythonTool
  Message 2: Print x + 100 and show DataFrame shape — force PythonTool
  Message 3: Create chart from persisted DataFrame — force PythonTool

Each message uses forced_tool_id to guarantee PythonTool is called
(bypasses LLM's decision of whether to use the tool).

Usage:
    python test_sandbox_persistence.py
    python test_sandbox_persistence.py --persona-id 303
    python test_sandbox_persistence.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time

from config import (
    CONFIG,
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def create_chat_session(persona_id: int) -> str | None:
    """Create a chat session and return its UUID."""
    resp = api("POST", "chat/create-chat-session", {"persona_id": persona_id})
    if resp.status_code != 200:
        print(f"[ERROR] Could not create chat session: {resp.status_code} {resp.text[:300]}")
        return None
    data = resp.json()
    session_id = str(data.get("chat_session_id", ""))
    if session_id:
        return session_id
    print(f"[ERROR] No chat_session_id in response: {data}")
    return None


def find_python_tool_id() -> int | None:
    """Find the PythonTool's DB ID."""
    resp = api("GET", "tool")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list tools: {resp.status_code}")
        return None
    for t in resp.json():
        if t.get("in_code_tool_id", "").lower() == "pythontool":
            return t["id"]
    print("[ERROR] PythonTool not found on server")
    return None


def find_persona_with_python(python_tool_id: int) -> int | None:
    """Find a persona that has PythonTool enabled."""
    resp = api("GET", "persona")
    if resp.status_code != 200:
        return None
    for p in resp.json():
        tool_ids = [t.get("id") for t in p.get("tools", [])]
        if python_tool_id in tool_ids:
            return p["id"]
    return None


def send_message(
    chat_session_id: str,
    message: str,
    parent_message_id: int | None,
    forced_tool_id: int | None = None,
) -> dict:
    """Send a chat message and parse the streaming response.

    Returns dict with keys:
        code: list of code strings executed
        stdout: list of stdout strings
        stderr: list of stderr strings
        answer: str (LLM text response)
        parent_message_id: int (for chaining messages)
        files: list of file info dicts
    """
    body = {
        "message": message,
        "chat_session_id": chat_session_id,
        "parent_message_id": parent_message_id,
        "file_descriptors": [],
        "internal_search_filters": {},
        "deep_research": False,
        "origin": "webapp",
    }
    if forced_tool_id is not None:
        body["forced_tool_id"] = forced_tool_id

    resp = stream_api("POST", "chat/send-chat-message", body)
    if resp.status_code != 200:
        print(f"[ERROR] send-chat-message returned {resp.status_code}: {resp.text[:500]}")
        return {"code": [], "stdout": [], "stderr": [], "answer": "", "parent_message_id": parent_message_id, "files": []}

    result = {
        "code": [],
        "stdout": [],
        "stderr": [],
        "answer": "",
        "parent_message_id": parent_message_id,
        "files": [],
    }

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            data = json.loads(line)
            obj = data.get("obj", data)
            ptype = obj.get("type", "")

            if ptype == "python_tool_start":
                code = obj.get("code", "")
                if code:
                    result["code"].append(code)

            elif ptype == "python_tool_delta":
                stdout = obj.get("stdout", "")
                stderr = obj.get("stderr", "")
                if stdout:
                    result["stdout"].append(stdout)
                if stderr:
                    result["stderr"].append(stderr)
                files = obj.get("files", [])
                if files:
                    result["files"].extend(files)

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                result["answer"] += content

            elif ptype == "message_id":
                result["parent_message_id"] = obj.get("message_id")

        except json.JSONDecodeError:
            pass

    return result


def check_sandbox_session_id(chat_session_id: str) -> str | None:
    """Query DB for the sandbox_session_id of a chat session."""
    import subprocess

    cmd = (
        f'docker exec onyx-relational_db-1 psql -U postgres -d postgres -t -c '
        f'"SELECT sandbox_session_id FROM chat_session WHERE id = \'{chat_session_id}\'"'
    )
    try:
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        return out if out else None
    except Exception as e:
        print(f"  [WARN] Could not check DB: {e}")
        return None


# ── Main Test ────────────────────────────────────────────────────────────────


def run_test(persona_id: int | None = None):
    print("\n" + "=" * 60)
    print("SANDBOX PERSISTENCE TEST")
    print("=" * 60)

    # Find PythonTool ID for forcing tool use
    python_tool_id = find_python_tool_id()
    if not python_tool_id:
        sys.exit(1)
    print(f"  PythonTool ID: {python_tool_id}")

    # Find or use specified persona
    if persona_id is None:
        persona_id = find_persona_with_python(python_tool_id)
        if persona_id is None:
            print("[ERROR] No persona with PythonTool found")
            sys.exit(1)
    print(f"  Persona ID: {persona_id}")

    # Create chat session
    chat_session_id = create_chat_session(persona_id)
    if not chat_session_id:
        sys.exit(1)
    print(f"  Chat Session: {chat_session_id}")

    # ── Message 1: Set variables ─────────────────────────────────────────
    print("\n" + "-" * 60)
    print("MESSAGE 1: Set x = 42, create DataFrame")
    print("-" * 60)

    msg1 = send_message(
        chat_session_id=chat_session_id,
        message=(
            "Execute this Python code exactly:\n"
            "```python\n"
            "import pandas as pd\n"
            "x = 42\n"
            "df = pd.DataFrame({'product': ['A','B','C'], 'revenue': [100, 200, 300]})\n"
            "print(f'x = {x}')\n"
            "print(f'df shape: {df.shape}')\n"
            "print(df.to_string())\n"
            "```"
        ),
        parent_message_id=None,
        forced_tool_id=python_tool_id,
    )

    print(f"  Code executed: {len(msg1['code'])} blocks")
    for code in msg1["code"]:
        print(f"    >>> {code[:100]}...")
    print(f"  Stdout: {msg1['stdout']}")
    print(f"  Stderr: {msg1['stderr']}")

    # Check if x=42 appears in output
    msg1_ok = any("x = 42" in s for s in msg1["stdout"])
    print(f"  Result: {'PASS - x = 42 confirmed' if msg1_ok else 'FAIL - x = 42 not found in output'}")

    if not msg1_ok:
        print("\n[FAIL] Message 1 didn't execute properly. Aborting.")
        sys.exit(1)

    # Check DB for sandbox_session_id
    sandbox_id = check_sandbox_session_id(chat_session_id)
    print(f"  sandbox_session_id in DB: {sandbox_id}")

    # Brief pause
    time.sleep(2)

    # ── Message 2: Use persisted variables ───────────────────────────────
    print("\n" + "-" * 60)
    print("MESSAGE 2: Use persisted x and df (should still exist)")
    print("-" * 60)

    msg2 = send_message(
        chat_session_id=chat_session_id,
        message=(
            "Execute this Python code exactly:\n"
            "```python\n"
            "print(f'x + 100 = {x + 100}')\n"
            "print(f'df shape: {df.shape}')\n"
            "total = df['revenue'].sum()\n"
            "print(f'Total revenue: {total}')\n"
            "```"
        ),
        parent_message_id=msg1["parent_message_id"],
        forced_tool_id=python_tool_id,
    )

    print(f"  Code executed: {len(msg2['code'])} blocks")
    for code in msg2["code"]:
        print(f"    >>> {code[:100]}...")
    print(f"  Stdout: {msg2['stdout']}")
    print(f"  Stderr: {msg2['stderr']}")

    # Check if x+100=142 and total revenue=600 appear
    msg2_stdout = " ".join(msg2["stdout"])
    has_142 = "142" in msg2_stdout
    has_600 = "600" in msg2_stdout
    has_error = any("NameError" in s or "not defined" in s for s in msg2["stderr"])

    if has_142 and has_600 and not has_error:
        print(f"  Result: PASS - Variables persisted! x+100=142, total=600")
    elif has_error:
        print(f"  Result: FAIL - NameError: variables did NOT persist across messages")
    else:
        print(f"  Result: UNCLEAR - Expected 142 and 600 in output")

    # Brief pause
    time.sleep(2)

    # ── Message 3: Create chart from persisted DataFrame ─────────────────
    print("\n" + "-" * 60)
    print("MESSAGE 3: Create chart from persisted DataFrame")
    print("-" * 60)

    msg3 = send_message(
        chat_session_id=chat_session_id,
        message=(
            "Execute this Python code exactly:\n"
            "```python\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots(figsize=(8, 5))\n"
            "ax.bar(df['product'], df['revenue'], color=['#3b82f6', '#10b981', '#f59e0b'])\n"
            "ax.set_title(f'Revenue by Product (total={df[\"revenue\"].sum()}, x={x})')\n"
            "ax.set_ylabel('Revenue ($)')\n"
            "plt.savefig('revenue_chart.png', dpi=150, bbox_inches='tight')\n"
            "plt.close()\n"
            "print('Chart saved successfully')\n"
            "```"
        ),
        parent_message_id=msg2["parent_message_id"],
        forced_tool_id=python_tool_id,
    )

    print(f"  Code executed: {len(msg3['code'])} blocks")
    print(f"  Stdout: {msg3['stdout']}")
    print(f"  Stderr: {msg3['stderr']}")
    print(f"  Files: {msg3['files']}")

    msg3_stdout = " ".join(msg3["stdout"])
    msg3_ok = "Chart saved" in msg3_stdout or "successfully" in msg3_stdout
    msg3_error = any("NameError" in s or "not defined" in s for s in msg3["stderr"])
    has_file = len(msg3["files"]) > 0

    if msg3_ok and not msg3_error:
        print(f"  Result: PASS - Chart created using persisted df and x!")
    elif msg3_error:
        print(f"  Result: FAIL - NameError: variables did NOT persist to message 3")
    else:
        print(f"  Result: UNCLEAR - Check output above")

    # ── Final Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"  Message 1 (set variables):       {'PASS' if msg1_ok else 'FAIL'}")
    print(f"  Message 2 (reuse variables):     {'PASS' if has_142 and has_600 and not has_error else 'FAIL'}")
    print(f"  Message 3 (chart from df):       {'PASS' if msg3_ok and not msg3_error else 'FAIL'}")
    print(f"  File generated:                  {'YES' if has_file else 'NO'}")
    print(f"  sandbox_session_id persisted:    {'YES' if sandbox_id else 'NO'}")

    all_pass = msg1_ok and has_142 and has_600 and not has_error and msg3_ok and not msg3_error
    print(f"\n  {'ALL TESTS PASSED - Sandbox persistence works!' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 60 + "\n")

    return all_pass


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test Code Interpreter sandbox persistence across messages",
    )
    parser.add_argument(
        "--persona-id", type=int, default=None,
        help="Persona ID with PythonTool enabled (auto-detected if omitted)",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    success = run_test(persona_id=args.persona_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
