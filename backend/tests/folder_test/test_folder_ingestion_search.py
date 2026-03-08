"""
Integration Test: Folder Connector — Ingestion & Search
=========================================================

End-to-end test that verifies:
1. Folder connector can be created via API
2. Indexing ingests documents into Vespa
3. Chat search retrieves relevant chunks from folder documents
4. LLM answers contain expected information from the test data

Requires a running VirtualAI deployment (API server, Vespa, embedding model).

Usage:
    python test_folder_ingestion_search.py
    python test_folder_ingestion_search.py --url http://host:3000 --key YOUR_KEY
    python test_folder_ingestion_search.py --no-cleanup    # Keep connector after test
    python test_folder_ingestion_search.py --folder /path   # Use custom folder instead of test_data/
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent tests/ dir to path so we can import from agents_creator / workflow_creator
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from agents_creator.config import (  # noqa: E402
    CONFIG,
    add_common_args,
    api,
    apply_common_args,
)
from workflow_creator.config import stream_api  # noqa: E402

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
TEST_DATA_DIR = ROOT_DIR / "test_data"

# ── Test Definitions ─────────────────────────────────────────────────────────
# Loaded from test_data/test_queries.json — each entry has:
#   question, expected_answer, expected_keywords, min_keyword_matches, source_file

QUERIES_JSON = TEST_DATA_DIR / "test_queries.json"


def load_search_tests() -> list[dict]:
    """Load test queries from JSON file and add description field."""
    with open(QUERIES_JSON, encoding="utf-8") as f:
        tests = json.load(f)
    for t in tests:
        t["description"] = f"Q{t['id']}: {t['question'][:50]}"
    return tests


# ── Connector Setup ─────────────────────────────────────────────────────────


def create_folder_connector(folder_path: str) -> tuple[int, int, int]:
    """Create folder connector + credential + CC pair.

    Returns (connector_id, credential_id, cc_pair_id).
    """
    print("\n[SETUP] Creating folder connector...")
    suffix = int(time.time()) % 100000  # unique suffix to avoid name collisions

    # 1. Create connector
    resp = api("POST", "manage/admin/connector", {
        "name": f"Folder Integration Test {suffix}",
        "source": "folder",
        "input_type": "load_state",
        "connector_specific_config": {
            "folder_paths": [folder_path],
            "recursive": True,
        },
        "access_type": "public",
        "groups": [],
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create connector: {resp.status_code} {resp.text[:300]}")
        sys.exit(1)
    connector_id = resp.json()["id"]
    print(f"  [OK] Connector created (ID={connector_id})")

    # 2. Create credential (empty for folder)
    resp = api("POST", "manage/credential", {
        "name": f"Folder Test Credential {suffix}",
        "source": "folder",
        "credential_json": {},
        "admin_public": True,
        "curator_public": True,
        "groups": [],
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create credential: {resp.status_code} {resp.text[:300]}")
        sys.exit(1)
    credential_id = resp.json()["id"]
    print(f"  [OK] Credential created (ID={credential_id})")

    # 3. Link connector + credential (CC pair)
    resp = api("PUT", f"manage/connector/{connector_id}/credential/{credential_id}", {
        "name": f"Folder Test CC Pair {suffix}",
        "access_type": "public",
        "groups": [],
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create CC pair: {resp.status_code} {resp.text[:300]}")
        sys.exit(1)
    cc_pair_id = resp.json().get("data", 0)
    print(f"  [OK] CC Pair created (ID={cc_pair_id})")

    return connector_id, credential_id, cc_pair_id


def trigger_indexing(connector_id: int, credential_id: int) -> None:
    """Trigger indexing run for the folder connector."""
    print("\n[INDEX] Triggering indexing...")
    resp = api("POST", "manage/admin/connector/run-once", {
        "connector_id": connector_id,
        "credential_ids": [credential_id],
        "from_beginning": True,
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Trigger indexing: {resp.status_code} {resp.text[:300]}")
        sys.exit(1)
    print(f"  [OK] Indexing triggered: {resp.json().get('message', '')}")


def wait_for_indexing(timeout: int = 120, cc_pair_id: int | None = None) -> bool:
    """Poll indexing status until folder connector is done.

    Returns True if indexing completed with docs_indexed > 0.
    The API response format is:
        [{"source": "folder", "summary": {...}, "indexing_statuses": [{
            "cc_pair_id": 6, "name": "Folder Test CC Pair",
            "docs_indexed": 3, "in_progress": false,
            "last_finished_status": "success", ...
        }]}]
    """
    print(f"[INDEX] Waiting for indexing to complete (timeout={timeout}s)...")
    start = time.time()

    while time.time() - start < timeout:
        resp = api("POST", "manage/admin/connector/indexing-status", {
            "get_all_connectors": True,
            "source": "folder",
        })
        if resp.status_code != 200:
            print(f"  [WARN] Status check failed: {resp.status_code}")
            time.sleep(5)
            continue

        data = resp.json()
        # data is a list of source groups; each has "indexing_statuses"
        if isinstance(data, dict):
            data = [data]

        for source_group in data:
            statuses = source_group.get("indexing_statuses", [])
            for status in statuses:
                # Match by cc_pair_id if provided, otherwise match by name
                if cc_pair_id is not None:
                    if status.get("cc_pair_id") != cc_pair_id:
                        continue
                else:
                    name = status.get("name", "")
                    connector = status.get("connector", {})
                    connector_name = connector.get("name", "") if isinstance(connector, dict) else ""
                    if ("Folder Integration Test" not in name
                            and "Folder Integration Test" not in connector_name
                            and "Folder Test CC Pair" not in name
                            and "Folder Test" not in name):
                        continue

                docs_indexed = status.get("docs_indexed", 0)
                in_progress = status.get("in_progress", True)
                last_status = status.get(
                    "last_finished_status",
                    status.get("last_status", ""),
                )

                elapsed = int(time.time() - start)
                print(f"  [{elapsed}s] cc_pair={status.get('cc_pair_id')}, docs={docs_indexed}, in_progress={in_progress}, status={last_status}")

                if not in_progress and docs_indexed > 0:
                    print(f"  [OK] Indexing complete: {docs_indexed} docs indexed")
                    return True

                if not in_progress and last_status == "failed":
                    print("  [FAIL] Indexing failed")
                    return False

        time.sleep(5)

    print(f"  [FAIL] Indexing timed out after {timeout}s")
    return False


# ── Chat / Search ────────────────────────────────────────────────────────────


def create_chat_session() -> str:
    """Create a new chat session. Returns session_id."""
    resp = api("POST", "chat/create-chat-session", {
        "persona_id": 0,
        "description": None,
        "project_id": None,
    })
    if resp.status_code != 200:
        print(f"  [FAIL] Create chat session: {resp.status_code} {resp.text[:300]}")
        return ""
    return resp.json().get("chat_session_id", "")


def send_search_query(session_id: str, question: str) -> dict:
    """Send a chat message with forced search tool and parse the streaming response.

    Returns dict with:
        retrieved_docs: list of doc dicts from search_tool_documents_delta
        final_documents: list of doc dicts from message_start
        answer: str (concatenated message_delta content)
        completed: bool
        error: str or None
    """
    body = {
        "message": question,
        "chat_session_id": session_id,
        "parent_message_id": None,
        "file_descriptors": [],
        "internal_search_filters": {
            "source_type": ["folder"],
            "document_set": None,
            "time_cutoff": None,
            "tags": [],
        },
        "deep_research": False,
        "forced_tool_id": 1,  # Internal Search tool
        "origin": "webapp",
    }

    resp = stream_api("POST", "chat/send-chat-message", body)

    result = {
        "retrieved_docs": [],
        "final_documents": [],
        "answer": "",
        "completed": False,
        "error": None,
    }

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        return result

    answer_parts = []

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)

            # Check for top-level error
            if packet.get("error"):
                result["error"] = packet["error"][:300]
                continue

            obj = packet.get("obj", packet)
            ptype = obj.get("type", "")

            if ptype == "search_tool_documents_delta":
                docs = obj.get("documents", [])
                result["retrieved_docs"].extend(docs)

            elif ptype == "message_start":
                final_docs = obj.get("final_documents", [])
                if isinstance(final_docs, list):
                    result["final_documents"] = final_docs

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                if content:
                    answer_parts.append(content)

            elif ptype == "stop":
                result["completed"] = True

        except json.JSONDecodeError:
            pass

    result["answer"] = "".join(answer_parts)
    return result


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_search_test(test_def: dict) -> dict:
    """Run a single search test and return pass/fail result."""
    question = test_def["question"]
    expected_keywords = test_def["expected_keywords"]
    min_matches = test_def["min_keyword_matches"]
    description = test_def["description"]

    print(f"\n  TEST: {description}")
    print(f"    Q: \"{question}\"")

    # Create a fresh chat session for each question
    session_id = create_chat_session()
    if not session_id:
        return {"status": "FAIL", "reason": "Could not create chat session", "description": description}

    result = send_search_query(session_id, question)

    if result["error"]:
        return {"status": "FAIL", "reason": f"Error: {result['error']}", "description": description}

    issues = []
    answer_lower = result["answer"].lower()

    # Check 1: Did we get any retrieved documents?
    if not result["retrieved_docs"] and not result["final_documents"]:
        issues.append("No documents retrieved from Vespa")

    # Check 2: Do retrieved docs contain folder source documents?
    folder_docs_found = False
    for doc in result["retrieved_docs"]:
        source = doc.get("source_type", "")
        if source == "folder":
            folder_docs_found = True
            break
    if not folder_docs_found and result["retrieved_docs"]:
        # Check final_documents as fallback
        for doc in result["final_documents"]:
            source = doc.get("source_type", "")
            if source == "folder":
                folder_docs_found = True
                break
    if not folder_docs_found and (result["retrieved_docs"] or result["final_documents"]):
        issues.append("No folder-source documents in retrieved results")

    # Check 3: Do expected keywords appear in the answer?
    matched_keywords = []
    for kw in expected_keywords:
        if kw.lower() in answer_lower:
            matched_keywords.append(kw)

    if len(matched_keywords) < min_matches:
        issues.append(
            f"Only {len(matched_keywords)}/{min_matches} keywords matched: "
            f"{matched_keywords} (expected from: {expected_keywords})"
        )

    # Check 4: Did the stream complete?
    if not result["completed"]:
        issues.append("Stream did not complete (no 'stop' packet)")

    # Print results
    n_docs = len(result["retrieved_docs"])
    answer_preview = result["answer"][:200].replace("\n", " ")
    # Encode safely for Windows console (cp1252)
    answer_preview = answer_preview.encode("ascii", errors="replace").decode("ascii")
    print(f"    Docs retrieved: {n_docs}")
    print(f"    Keywords matched: {len(matched_keywords)}/{len(expected_keywords)} {matched_keywords}")
    print(f"    Answer: {answer_preview}...")

    if issues:
        print(f"    [FAIL] {'; '.join(issues)}")
        return {"status": "FAIL", "reason": "; ".join(issues), "description": description}

    print(f"    [PASS]")
    return {"status": "PASS", "reason": "", "description": description}


# ── Cleanup ──────────────────────────────────────────────────────────────────


def cleanup_connector(connector_id: int, credential_id: int) -> None:
    """Delete the test connector and credential."""
    print("\n[CLEANUP] Removing test connector and credential...")

    # Delete connector (this also removes CC pairs)
    resp = api("DELETE", f"manage/admin/connector/{connector_id}")
    if resp.status_code == 200:
        print(f"  [OK] Connector {connector_id} deleted")
    else:
        print(f"  [WARN] Delete connector: {resp.status_code} {resp.text[:200]}")

    # Delete credential
    resp = api("DELETE", f"manage/credential/{credential_id}")
    if resp.status_code in (200, 204):
        print(f"  [OK] Credential {credential_id} deleted")
    else:
        print(f"  [WARN] Delete credential: {resp.status_code} {resp.text[:200]}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Integration test: Folder Connector ingestion & search"
    )
    add_common_args(parser)
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep the test connector after the test (for manual inspection)",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Custom folder path to index (default: test_data/ in this directory)",
    )
    parser.add_argument(
        "--docker-path",
        type=str,
        default=None,
        help="Folder path as seen INSIDE Docker container (skips local existence check)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Max seconds to wait for indexing (default: 120)",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip connector creation and indexing — only run search tests "
             "(assumes folder docs are already indexed)",
    )
    args = parser.parse_args()
    apply_common_args(args)

    # Determine the folder path for the connector (as seen by the API server).
    # If --docker-path is given, use it directly (the server runs inside Docker).
    # Otherwise use --folder or the local test_data/ directory.
    if args.docker_path:
        folder_path = args.docker_path
        local_check = False
    else:
        folder_path = args.folder or str(TEST_DATA_DIR.resolve())
        local_check = True

    print(f"=" * 60)
    print(f"Folder Connector Integration Test")
    print(f"  Server: {CONFIG['base_url']}")
    print(f"  Folder: {folder_path}")
    if args.docker_path:
        print(f"  (Docker container path — skipping local existence check)")
    print(f"=" * 60)

    # Verify test data exists locally (skip if using Docker path)
    if local_check:
        if not Path(folder_path).is_dir():
            print(f"\n[ERROR] Folder not found: {folder_path}")
            sys.exit(1)
        files = list(Path(folder_path).rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        print(f"  Files in folder: {file_count}")
    else:
        print(f"  (Folder existence will be validated by the API server)")

    # Phase 1: Setup connector and index (or skip if --skip-setup)
    connector_id = None
    credential_id = None

    if args.skip_setup:
        print("\n[SETUP] Skipping connector creation (--skip-setup)")
        print("  Assuming folder documents are already indexed in Vespa.")
    else:
        connector_id, credential_id, cc_pair_id = create_folder_connector(folder_path)
        trigger_indexing(connector_id, credential_id)

        if not wait_for_indexing(timeout=args.timeout, cc_pair_id=cc_pair_id):
            print("\n[ABORT] Indexing did not complete. Cannot run search tests.")
            if not args.no_cleanup:
                cleanup_connector(connector_id, credential_id)
            sys.exit(1)

    # Phase 2: Run search tests
    search_tests = load_search_tests()
    print(f"\n{'=' * 60}")
    print(f"SEARCH TESTS ({len(search_tests)} questions)")
    print(f"{'=' * 60}")

    results = []
    for test_def in search_tests:
        result = run_search_test(test_def)
        results.append(result)

    # Phase 3: Summary
    print(f"\n{'=' * 60}")
    print(f"RESULTS SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    for r in results:
        status = r["status"]
        desc = r["description"]
        reason = r.get("reason", "")
        icon = "PASS" if status == "PASS" else "FAIL"
        line = f"  [{icon}] {desc}"
        if reason:
            line += f" — {reason}"
        print(line)

    print(f"\n  Total: {passed}/{total} passed, {failed} failed")

    # Phase 4: Cleanup
    if not args.no_cleanup and connector_id is not None:
        cleanup_connector(connector_id, credential_id)
    else:
        reason = "--skip-setup" if connector_id is None else "--no-cleanup"
        print(f"\n[INFO] Skipping cleanup ({reason}). Connector ID={connector_id}")

    # Exit code
    if failed > 0:
        print(f"\n[RESULT] FAILED ({failed} test(s) failed)")
        sys.exit(1)
    else:
        print(f"\n[RESULT] ALL PASSED ({passed}/{total})")
        sys.exit(0)


if __name__ == "__main__":
    main()
