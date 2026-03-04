"""
Craft (Build Mode) Integration Test
=====================================

Tests the Craft/Build system end-to-end: session creation, message sending,
agent response streaming, file listing, and session cleanup.

Uses the same API client pattern as workflow_creator tests.

Prerequisites:
    - ENABLE_CRAFT=true (both build-time and runtime)
    - opencode CLI installed in api_server container
    - Server running at base_url (default: http://localhost:3000)

Usage:
    python test_craft.py                         # Run all tests
    python test_craft.py --test session          # Only session lifecycle
    python test_craft.py --test message          # Only message send/stream
    python test_craft.py --test full             # Full: create → message → files → cleanup
    python test_craft.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time

import requests as req_lib
from urllib.parse import urljoin

from config import (
    CONFIG,
    add_common_args,
    api,
    apply_common_args,
    headers,
    stream_api,
)

# Session creation involves sandbox provisioning which can take a while
BUILD_API_TIMEOUT = 120  # seconds


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


def build_api(method: str, path: str, data: dict | None = None, params: dict | None = None):
    """Call a Build API endpoint (prefixed with build/) with longer timeout."""
    url = urljoin(CONFIG["base_url"] + "/", f"api/build/{path.lstrip('/')}")
    return req_lib.request(
        method, url, headers=headers(), json=data, params=params,
        timeout=BUILD_API_TIMEOUT,
    )


def build_stream_api(method: str, path: str, data: dict | None = None):
    """Call a Build API streaming endpoint (prefixed with build/)."""
    url = urljoin(CONFIG["base_url"] + "/", f"api/build/{path.lstrip('/')}")
    return req_lib.request(
        method, url, headers=headers(), json=data,
        timeout=300, stream=True,
    )


# ── Craft Feature Check ─────────────────────────────────────────────────────


def check_craft_enabled() -> bool:
    """Verify Craft is enabled via the settings endpoint."""
    resp = api("GET", "settings")
    if resp.status_code != 200:
        print(f"[ERROR] Could not fetch settings: {resp.status_code}")
        return False

    settings = resp.json()
    enabled = settings.get("onyx_craft_enabled", False)
    if not enabled:
        print("[ERROR] Craft is NOT enabled (settings.onyx_craft_enabled = false)")
        print("        Set ENABLE_CRAFT=true in .env and rebuild api_server.")
        return False

    print("  [OK] Craft is enabled")
    return True


# ── Test: Session Lifecycle ──────────────────────────────────────────────────


def test_session_lifecycle() -> tuple[bool, str | None]:
    """Test creating, listing, and deleting a build session.

    Returns:
        (passed, session_id) — session_id is returned for reuse if not cleaned up.
    """
    print("\n" + "=" * 60)
    print("TEST: Session Lifecycle (create -> get -> list -> delete)")
    print("=" * 60)

    passed = True
    session_id = None

    # 1. Create session
    print("\n  [1/5] Creating session...")
    resp = build_api("POST", "sessions", {
        "name": "Craft Integration Test",
        "demo_data_enabled": True,
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create session: {resp.status_code} {resp.text[:300]}")
        return False, None

    session = resp.json()
    session_id = session.get("id")
    status = session.get("status")
    sandbox = session.get("sandbox")
    loaded = session.get("session_loaded_in_sandbox")

    print(f"  [OK] Session created: id={session_id}")
    print(f"       status={status}, sandbox={sandbox is not None}, loaded={loaded}")

    if not session_id:
        print("  [FAIL] No session ID in response")
        return False, None

    # 2. Get session details
    print("\n  [2/5] Getting session details...")
    resp = build_api("GET", f"sessions/{session_id}")
    if resp.status_code != 200:
        print(f"  [FAIL] Get session: {resp.status_code}")
        passed = False
    else:
        detail = resp.json()
        print(f"  [OK] Session name: {detail.get('name')}")
        print(f"       Status: {detail.get('status')}")
        print(f"       NextJS port: {detail.get('nextjs_port')}")

    # 3. List sessions (note: empty sessions without messages are excluded from listing)
    print("\n  [3/5] Listing sessions...")
    resp = build_api("GET", "sessions")
    if resp.status_code != 200:
        print(f"  [FAIL] List sessions: {resp.status_code}")
        passed = False
    else:
        sessions = resp.json().get("sessions", resp.json())
        if isinstance(sessions, list):
            found = any(s.get("id") == session_id for s in sessions)
            print(f"  [OK] Listed {len(sessions)} sessions (with messages)")
            if not found:
                print("  [INFO] Our empty session not in list (expected - no messages yet)")
        else:
            print(f"  [OK] Sessions response: {type(sessions)}")

    # 4. Update name
    print("\n  [4/5] Updating session name...")
    resp = build_api("PUT", f"sessions/{session_id}/name", {"name": "Craft Test (updated)"})
    if resp.status_code != 200:
        print(f"  [WARN] Update name: {resp.status_code} (non-critical)")
    else:
        print("  [OK] Name updated")

    # 5. Delete session
    print("\n  [5/5] Deleting session...")
    resp = build_api("DELETE", f"sessions/{session_id}")
    if resp.status_code in (200, 204):
        print("  [OK] Session deleted")
    else:
        print(f"  [FAIL] Delete session: {resp.status_code} {resp.text[:200]}")
        passed = False

    return passed, session_id


# ── Test: Send Message & Stream ──────────────────────────────────────────────


def test_message_stream(session_id: str | None = None) -> tuple[bool, str | None]:
    """Test sending a message and streaming the agent response.

    Creates a new session if session_id is not provided.

    Returns:
        (passed, session_id)
    """
    print("\n" + "=" * 60)
    print("TEST: Message Send & Stream")
    print("=" * 60)

    created_session = False

    # Create session if needed
    if not session_id:
        print("\n  [Setup] Creating session for message test...")
        resp = build_api("POST", "sessions", {
            "name": "Craft Message Test",
            "demo_data_enabled": True,
        })
        if resp.status_code != 200:
            print(f"  [FAIL] Create session: {resp.status_code} {resp.text[:300]}")
            return False, None
        session_id = resp.json().get("id")
        created_session = True
        print(f"  [OK] Session: {session_id}")

    # Send message
    test_message = "Create a simple hello world web page with a blue background and white centered text that says 'Hello from Craft Test'"
    print(f"\n  [Sending] \"{test_message[:80]}...\"")
    print("  " + "-" * 50)

    resp = build_stream_api("POST", f"sessions/{session_id}/send-message", {
        "content": test_message,
    })

    if resp.status_code != 200:
        print(f"  [FAIL] Send message: {resp.status_code} {resp.text[:500]}")
        return False, session_id

    # Parse SSE stream (format: "event: message\ndata: {json}\n\n")
    passed = True
    packet_counts: dict[str, int] = {}
    has_agent_message = False
    has_tool_calls = False
    total_text = ""
    error_packets = []
    start_time = time.time()

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        # SSE format: skip "event:" lines, parse "data:" lines
        if line.startswith("event:"):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line:
            continue
        try:
            packet = json.loads(line)
            ptype = packet.get("type", "unknown")
            packet_counts[ptype] = packet_counts.get(ptype, 0) + 1

            if ptype == "agent_message_chunk":
                content = packet.get("content", "")
                if isinstance(content, dict):
                    text = content.get("text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = ""
                if text:
                    has_agent_message = True
                    total_text += text
                    _safe_print(f"  {text}", end="")

            elif ptype == "agent_thought_chunk":
                content = packet.get("content", "")
                if isinstance(content, dict):
                    text = content.get("text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = ""
                if text:
                    _safe_print(f"  [thought] {text[:100]}", end="")

            elif ptype == "tool_call_start":
                tool_name = packet.get("tool_name", packet.get("name", "?"))
                has_tool_calls = True
                _safe_print(f"\n  [tool_call_start] {tool_name}")

            elif ptype == "tool_call_progress":
                status = packet.get("status", "?")
                _safe_print(f"  [tool_call_progress] status={status}")

            elif ptype == "prompt_response":
                _safe_print("\n  [prompt_response] Agent finished processing")

            elif ptype == "error":
                msg = packet.get("message", str(packet))
                error_packets.append(msg)
                _safe_print(f"\n  [ERROR] {msg[:200]}")

            elif ptype in ("agent_plan_update", "current_mode_update"):
                _safe_print(f"\n  [{ptype}]")

            # Synthetic Onyx packets (saved to DB)
            elif ptype in ("agent_message", "agent_thought"):
                content = packet.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
                if text and ptype == "agent_message":
                    has_agent_message = True
                    total_text += text

        except json.JSONDecodeError:
            _safe_print(f"  [RAW] {line[:150]}")

    duration = time.time() - start_time
    print(f"\n\n  " + "-" * 50)
    print(f"  Duration: {duration:.1f}s")
    print(f"  Packet counts: {json.dumps(packet_counts, indent=2)}")
    print(f"  Total text length: {len(total_text)} chars")

    # Validate results
    if error_packets:
        print(f"\n  [FAIL] Received {len(error_packets)} error packets:")
        for e in error_packets[:3]:
            print(f"    - {e[:200]}")
        passed = False

    if has_agent_message:
        print("  [OK] Received agent message content")
    else:
        print("  [WARN] No agent message content received (may be tool-only response)")

    if has_tool_calls:
        print("  [OK] Agent made tool calls (likely file edits)")
    else:
        print("  [WARN] No tool calls detected")

    if not has_agent_message and not has_tool_calls and not error_packets:
        print("  [FAIL] No meaningful response received")
        passed = False

    return passed, session_id


# ── Test: File System ────────────────────────────────────────────────────────


def test_file_system(session_id: str) -> bool:
    """Test listing files and directories in a session's workspace."""
    print("\n" + "=" * 60)
    print("TEST: File System Operations")
    print("=" * 60)

    passed = True

    # List root directory
    print("\n  [1/3] Listing session files (root)...")
    resp = build_api("GET", f"sessions/{session_id}/files?path=")
    if resp.status_code != 200:
        # Try with explicit path param
        resp = build_api("GET", f"sessions/{session_id}/files", params={"path": ""})
    if resp.status_code != 200:
        print(f"  [WARN] List files: {resp.status_code} (sandbox may not have outputs yet)")
    else:
        data = resp.json()
        entries = data.get("entries", data) if isinstance(data, dict) else data
        if isinstance(entries, list):
            print(f"  [OK] Root has {len(entries)} entries:")
            for entry in entries[:10]:
                name = entry.get("name", "?")
                etype = entry.get("type", "?")
                print(f"       {etype}: {name}")
        else:
            print(f"  [OK] Files response: {str(data)[:200]}")

    # Check webapp info
    print("\n  [2/3] Checking webapp info...")
    resp = build_api("GET", f"sessions/{session_id}/webapp-info")
    if resp.status_code != 200:
        print(f"  [WARN] Webapp info: {resp.status_code}")
    else:
        info = resp.json()
        print(f"  [OK] has_webapp={info.get('has_webapp')}")
        print(f"       webapp_url={info.get('webapp_url')}")
        print(f"       status={info.get('status')}")
        print(f"       ready={info.get('ready')}")

    # List messages
    print("\n  [3/3] Listing session messages...")
    resp = build_api("GET", f"sessions/{session_id}/messages")
    if resp.status_code != 200:
        print(f"  [WARN] List messages: {resp.status_code}")
    else:
        data = resp.json()
        messages = data.get("messages", data) if isinstance(data, dict) else data
        if isinstance(messages, list):
            print(f"  [OK] {len(messages)} messages stored:")
            for msg in messages[:5]:
                mtype = msg.get("type", "?")
                turn = msg.get("turn_index", "?")
                meta = msg.get("message_metadata", {})
                ptype = meta.get("type", "?") if isinstance(meta, dict) else "?"
                print(f"       turn={turn} type={mtype} packet_type={ptype}")
        else:
            print(f"  [OK] Messages: {str(data)[:200]}")

    return passed


# ── Test: Rate Limit Check ───────────────────────────────────────────────────


def test_rate_limit() -> bool:
    """Test the rate limit endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Rate Limit Check")
    print("=" * 60)

    resp = build_api("GET", "limit")
    if resp.status_code != 200:
        print(f"  [WARN] Rate limit check: {resp.status_code} (may not be configured)")
        return True  # Non-critical

    data = resp.json()
    print(f"  [OK] Rate limit info:")
    print(f"       is_limited: {data.get('is_limited')}")
    print(f"       limit_type: {data.get('limit_type')}")
    print(f"       messages_used: {data.get('messages_used')}")
    print(f"       limit: {data.get('limit')}")
    return True


# ── Full Integration Test ────────────────────────────────────────────────────


def test_full_integration() -> bool:
    """Full Craft integration test: create → message → files → cleanup."""
    print("\n" + "=" * 60)
    print("FULL INTEGRATION TEST: Craft End-to-End")
    print("=" * 60)

    results = []
    session_id = None
    start_time = time.time()

    # 1. Create session
    print("\n  [Step 1/5] Creating build session...")
    resp = build_api("POST", "sessions", {
        "name": "Craft Full Integration Test",
        "demo_data_enabled": True,
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create session: {resp.status_code} {resp.text[:300]}")
        results.append(("Create Session", False))
        return False

    session = resp.json()
    session_id = session.get("id")
    print(f"  [OK] Session: {session_id}")
    results.append(("Create Session", True))

    # 2. Send message (simple task)
    print("\n  [Step 2/5] Sending message to agent...")
    message = "Create a web page with a heading that says 'Integration Test' and a paragraph that says 'This was built by the Craft agent.'"
    print(f"  Message: \"{message[:80]}...\"")

    resp = build_stream_api("POST", f"sessions/{session_id}/send-message", {
        "content": message,
    })

    msg_passed = False
    if resp.status_code == 200:
        packet_count = 0
        has_content = False
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            # SSE format: skip "event:" lines, parse "data:" lines
            if line.startswith("event:"):
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line:
                continue
            try:
                packet = json.loads(line)
                ptype = packet.get("type", "")
                packet_count += 1
                if ptype in ("agent_message_chunk", "agent_message"):
                    has_content = True
                if ptype == "tool_call_start":
                    has_content = True
                    tool = packet.get("tool_name", packet.get("name", "?"))
                    _safe_print(f"  [tool] {tool}")
                if ptype == "error":
                    _safe_print(f"  [error] {packet.get('message', '')[:150]}")
            except json.JSONDecodeError:
                pass

        msg_passed = packet_count > 0 and has_content
        print(f"  [{'OK' if msg_passed else 'FAIL'}] Received {packet_count} packets, has_content={has_content}")
    else:
        print(f"  [FAIL] Send message: {resp.status_code}")

    results.append(("Send Message", msg_passed))

    # 3. Wait for agent to finish, then check files
    print("\n  [Step 3/5] Checking workspace files...")
    time.sleep(2)  # Brief wait for filesystem to settle

    files_passed = test_file_system(session_id)
    results.append(("File System", files_passed))

    # 4. Check messages were persisted
    print("\n  [Step 4/5] Verifying message persistence...")
    resp = build_api("GET", f"sessions/{session_id}/messages")
    persist_passed = False
    if resp.status_code == 200:
        data = resp.json()
        messages = data.get("messages", data) if isinstance(data, dict) else data
        if isinstance(messages, list) and len(messages) >= 1:
            persist_passed = True
            print(f"  [OK] {len(messages)} messages persisted")
        else:
            print(f"  [FAIL] Expected messages, got: {str(data)[:200]}")
    else:
        print(f"  [FAIL] Get messages: {resp.status_code}")
    results.append(("Message Persistence", persist_passed))

    # 5. Cleanup
    print("\n  [Step 5/5] Cleaning up session...")
    resp = build_api("DELETE", f"sessions/{session_id}")
    cleanup_passed = resp.status_code in (200, 204)
    print(f"  [{'OK' if cleanup_passed else 'FAIL'}] Delete: {resp.status_code}")
    results.append(("Cleanup", cleanup_passed))

    total_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

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
        description="Integration tests for Craft (Build Mode)",
    )
    parser.add_argument(
        "--test",
        choices=["session", "message", "files", "rate-limit", "full", "all"],
        default="all",
        help="Which test to run (default: all)",
    )
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)

    # Pre-flight: check Craft is enabled
    print("\n" + "=" * 60)
    print("PRE-FLIGHT: Checking Craft Availability")
    print("=" * 60)

    if not check_craft_enabled():
        sys.exit(1)

    test_name = args.test
    all_passed = True

    if test_name in ("session", "all"):
        passed, _ = test_session_lifecycle()
        all_passed = all_passed and passed

    if test_name in ("message", "all"):
        passed, _ = test_message_stream()
        all_passed = all_passed and passed

    if test_name in ("rate-limit", "all"):
        passed = test_rate_limit()
        all_passed = all_passed and passed

    if test_name == "full":
        passed = test_full_integration()
        all_passed = all_passed and passed

    if test_name == "files":
        print("\n  [INFO] Files test requires an existing session with content.")
        print("  Use --test full for the complete flow.")

    print()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
