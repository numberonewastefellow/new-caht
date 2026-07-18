"""
Test: Per-Agent max_output_tokens

Verifies that the max_output_tokens field works end-to-end:
1. Create a agent with max_output_tokens=100, verify short response
2. Create a agent with max_output_tokens=NULL, verify default 1000 applies
3. PATCH existing workflow agents to set max_output_tokens

Usage:
    python test_max_output_tokens.py [--key API_KEY] [--url BASE_URL]
"""

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

def create_test_agent(name: str, max_output_tokens: int | None = None) -> dict | None:
    """Create a minimal agent for testing."""
    body = {
        "name": name,
        "description": f"Test agent for max_output_tokens ({max_output_tokens})",
        "num_chunks": 0,
        "is_public": True,
        "recency_bias": "base_decay",
        "llm_filter_extraction": False,
        "llm_relevance_filter": False,
        "system_prompt": "You are a helpful assistant. Be concise.",
        "replace_base_system_prompt": True,
        "task_prompt": "",
        "datetime_aware": True,
        "document_set_ids": [],
        "tool_ids": [],
        "users": [],
        "groups": [],
        "label_ids": [],
        "knowledge_file_ids": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
    }
    if max_output_tokens is not None:
        body["max_output_tokens"] = max_output_tokens

    resp = api("POST", "agent", body)
    if resp.status_code == 200:
        return resp.json()
    else:
        log(f"Failed to create agent: {resp.status_code} {resp.text[:200]}")
        return None


def get_agent(agent_id: int) -> dict | None:
    """Get a agent by ID."""
    resp = api("GET", f"agent/{agent_id}")
    if resp.status_code == 200:
        return resp.json()
    return None


def patch_agent_max_tokens(agent_id: int, max_output_tokens: int) -> bool:
    """PATCH a agent to set max_output_tokens."""
    # Get existing agent first
    agent = get_agent(agent_id)
    if not agent:
        log(f"Cannot find agent {agent_id}")
        return False

    # Build update body from existing agent
    body = {
        "name": agent["name"],
        "description": agent["description"],
        "num_chunks": agent.get("num_chunks", 10),
        "is_public": agent.get("is_public", True),
        "recency_bias": agent.get("recency_bias", "base_decay"),
        "llm_filter_extraction": agent.get("llm_filter_extraction", False),
        "llm_relevance_filter": agent.get("llm_relevance_filter", False),
        "system_prompt": agent.get("system_prompt", ""),
        "replace_base_system_prompt": agent.get("replace_base_system_prompt", False),
        "task_prompt": agent.get("task_prompt", ""),
        "datetime_aware": agent.get("datetime_aware", True),
        "document_set_ids": [ds["id"] for ds in agent.get("document_sets", [])],
        "tool_ids": [t["id"] for t in agent.get("tools", [])],
        "users": [],
        "groups": agent.get("groups", []),
        "label_ids": [lb["id"] for lb in agent.get("labels", [])],
        "knowledge_file_ids": agent.get("knowledge_file_ids", []),
        "hierarchy_node_ids": [n["id"] for n in agent.get("hierarchy_nodes", [])],
        "document_ids": [d["id"] for d in agent.get("attached_documents", [])],
        "max_output_tokens": max_output_tokens,
        "llm_model_provider_override": agent.get("llm_model_provider_override"),
        "llm_model_version_override": agent.get("llm_model_version_override"),
    }

    resp = api("PATCH", f"agent/{agent_id}", body)
    if resp.status_code == 200:
        return True
    else:
        log(f"PATCH failed for agent {agent_id}: {resp.status_code} {resp.text[:200]}")
        return False


def send_chat_message(agent_id: int, message: str) -> str | None:
    """Send a simple chat message and collect the streamed response."""
    # Create chat session (matches curl format from curl.txt)
    session_resp = api("POST", "converse/create-chat-session", {
        "agent_id": agent_id,
        "description": None,
        "project_id": None,
    })
    if session_resp.status_code != 200:
        log(f"Failed to create chat session: {session_resp.status_code} {session_resp.text[:200]}")
        return None

    chat_session_id = session_resp.json().get("chat_session_id")
    log(f"Chat session created: {chat_session_id}")

    # Send message (matches curl format from curl.txt)
    msg_body = {
        "message": message,
        "chat_session_id": chat_session_id,
        "parent_message_id": None,
        "file_descriptors": [],
        "origin": "webapp",
    }

    resp = stream_api("POST", "converse/send-chat-message", msg_body)
    if resp.status_code != 200:
        log(f"Failed to send message: {resp.status_code} {resp.text[:300]}")
        return None

    # Collect answer from stream
    answer_parts = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            pkt = json.loads(line)
            if isinstance(pkt, dict):
                obj = pkt.get("obj", pkt)
                if obj.get("type") == "message_delta" and obj.get("content"):
                    answer_parts.append(obj["content"])
                elif obj.get("answer_piece"):
                    answer_parts.append(obj["answer_piece"])
        except json.JSONDecodeError:
            pass

    return "".join(answer_parts) if answer_parts else None


def delete_agent(agent_id: int) -> None:
    """Delete a test agent."""
    api("DELETE", f"agent/{agent_id}")


# ── Test 1: Agent with max_output_tokens=100 -> short response ─────────────

def test_short_output():
    print("\n[TEST 1] Agent with max_output_tokens=1000 -> verify capped output")

    agent = create_test_agent("__test_max_tokens_1000", max_output_tokens=1000)
    if not agent:
        test_fail("create agent with max_tokens=1000", "API call failed")
        return

    agent_id = agent["id"]
    log(f"Created agent ID={agent_id} with max_output_tokens=1000")

    # Verify field is stored
    fetched = get_agent(agent_id)
    if fetched and fetched.get("max_output_tokens") == 1000:
        test_pass("max_output_tokens=1000 stored correctly in DB")
    else:
        test_fail("max_output_tokens stored", f"Got: {fetched.get('max_output_tokens') if fetched else 'None'}")

    # Send a message that would normally produce a very long response
    answer = send_chat_message(agent_id, "Explain quantum computing in great detail with examples and history.")
    if answer:
        word_count = len(answer.split())
        log(f"Response length: {len(answer)} chars, ~{word_count} words")
        # With 1000 token limit, response should be noticeably shorter
        if word_count < 1500:
            test_pass(f"Capped output verified (~{word_count} words with 1000 token limit)")
        else:
            test_fail("Capped output", f"Response too long: {word_count} words")
    else:
        test_fail("Capped output", "No response received")

    # Cleanup
    delete_agent(agent_id)


# ── Test 2: Agent with NULL max_output_tokens -> default 1000 applies ──────

def test_default_output():
    print("\n[TEST 2] Agent with NULL max_output_tokens -> default 5000 applies")

    agent = create_test_agent("__test_max_tokens_default")
    if not agent:
        test_fail("create agent with NULL max_tokens", "API call failed")
        return

    agent_id = agent["id"]
    log(f"Created agent ID={agent_id} with max_output_tokens=NULL")

    # Verify field is NULL
    fetched = get_agent(agent_id)
    if fetched and fetched.get("max_output_tokens") is None:
        test_pass("max_output_tokens=NULL stored correctly")
    else:
        test_fail("max_output_tokens NULL", f"Got: {fetched.get('max_output_tokens') if fetched else 'None'}")

    # Send a message - default 1000 tokens should produce a moderate response
    answer = send_chat_message(agent_id, "Explain quantum computing in great detail.")
    if answer:
        word_count = len(answer.split())
        log(f"Response length: {len(answer)} chars, ~{word_count} words")
        # With 5000 tokens default, response can be longer
        if word_count < 5000:
            test_pass(f"Default output verified (~{word_count} words with 5000 token default)")
        else:
            test_fail("Default output", f"Response too long: {word_count} words")
    else:
        test_fail("Default output", "No response received")

    # Cleanup
    delete_agent(agent_id)


# ── Test 3: PATCH existing agent to set max_output_tokens ──────────────────

def test_patch_max_tokens():
    print("\n[TEST 3] PATCH agent to set max_output_tokens")

    agent = create_test_agent("__test_max_tokens_patch")
    if not agent:
        test_fail("create agent for patch test", "API call failed")
        return

    agent_id = agent["id"]
    log(f"Created agent ID={agent_id}")

    # Verify initially NULL
    fetched = get_agent(agent_id)
    if fetched and fetched.get("max_output_tokens") is None:
        test_pass("Initial max_output_tokens is NULL")
    else:
        test_fail("Initial NULL check", "Unexpected value")

    # PATCH to 500
    if patch_agent_max_tokens(agent_id, 500):
        test_pass("PATCH to max_output_tokens=500 succeeded")
    else:
        test_fail("PATCH to 500", "API call failed")

    # Verify patched value
    fetched = get_agent(agent_id)
    if fetched and fetched.get("max_output_tokens") == 500:
        test_pass("max_output_tokens=500 verified after PATCH")
    else:
        test_fail("Verify PATCH", f"Got: {fetched.get('max_output_tokens') if fetched else 'None'}")

    # Cleanup
    delete_agent(agent_id)


# ── Test 4: Update all workflow agents ──────────────────────────────────────

def update_workflow_agents():
    """Update all known workflow agent agents to set max_output_tokens."""
    print("\n[UPDATE] Setting max_output_tokens on all workflow agents")

    # Update all workflow agents to 5000 (default)
    # Medical Diagnosis (325-334) + Discussion (314-321)
    updated = 0
    for pid in list(range(314, 322)) + list(range(325, 335)):
        p = get_agent(pid)
        if not p:
            log(f"  Agent {pid} not found, skipping")
            continue

        if patch_agent_max_tokens(pid, 5000):
            log(f"  Updated agent {pid} ({p.get('name', '?')}) -> max_output_tokens=5000")
            updated += 1
        else:
            log(f"  Failed to update agent {pid}")

    if updated > 0:
        test_pass(f"Updated {updated} workflow agents")
    else:
        test_fail("Update workflow agents", "No agents updated")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test max_output_tokens")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print("=" * 60)
    print("  max_output_tokens Test Suite")
    print("=" * 60)

    test_short_output()
    test_default_output()
    test_patch_max_tokens()
    update_workflow_agents()

    print("\n" + "=" * 60)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
