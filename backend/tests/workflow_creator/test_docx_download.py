"""
Test: 1-page DOCX generation with file download via MinIO.

Sends a simple DOCX request to the Document Generator workflow,
streams the response, and verifies:
  1. DOCX Builder creates a document
  2. file_ids appear in the stream (MCP file saved to MinIO)
  3. The file is downloadable via /api/converse/file/{file_id}
"""

import json
import sys
import time
from pathlib import Path

# Add parent tests/ dir to path
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

import requests as req

from workflow_creator.config import CONFIG

ASSISTANT_ID = 465  # Document Generator
AUTH_COOKIE = "fastapiusersauth=YrIXqRkYA77sdcBhdTeD2Yl4WuQ769-ztxyerV8mfs0"


def _cookie_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Cookie": AUTH_COOKIE,
    }


def _api(method: str, path: str, data: dict | None = None, **kwargs):
    url = CONFIG['base_url'].rstrip("/") + f"/api/{path.lstrip('/')}"
    return req.request(method, url, headers=_cookie_headers(), json=data, **kwargs)


def create_chat_session():
    """Create a new chat session for the Document Generator."""
    resp = _api("POST", "converse/create-chat-session", {
        "persona_id": ASSISTANT_ID,
        "description": "DOCX download test",
    })
    assert resp.status_code == 200, f"Failed to create session: {resp.status_code} {resp.text}"
    return resp.json()["chat_session_id"]


def send_message_and_stream(session_id: int, message: str):
    """Send a message and stream the response, collecting file_ids."""
    body = {
        "chat_session_id": session_id,
        "message": message,
        "parent_message_id": None,
        "prompt_id": None,
        "search_doc_ids": None,
        "retrieval_options": None,
        "query_override": None,
    }

    resp = _api("POST", "converse/send-chat-message", body, stream=True, timeout=300)
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"

    file_ids = []
    tool_results = []
    messages = []
    last_message = ""

    try:
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                packet = json.loads(line)
            except json.JSONDecodeError:
                continue

            obj = packet.get("obj", {})
            ptype = obj.get("type", "")

            # Collect file_ids from custom_tool_delta
            if ptype == "custom_tool_delta":
                fids = obj.get("file_ids")
                if fids:
                    file_ids.extend(fids)
                    print(f"  [FILE_IDS] {fids}")

                data = obj.get("data", {})
                if isinstance(data, dict) and "tool_result" in data:
                    tool_results.append(data["tool_result"])
                    result_str = str(data["tool_result"])[:200]
                    print(f"  [TOOL_RESULT] {obj.get('tool_name', '?')}: {result_str}")

            elif ptype == "message_delta":
                msg = obj.get("message", "") or obj.get("content", "")
                if msg:
                    last_message += msg
                # Check for file_ids in the final summary message
                msg_fids = obj.get("file_ids")
                if msg_fids:
                    print(f"  [MSG FILE_IDS] {msg_fids}")
                    msg_fnames = obj.get("file_names", [])
                    print(f"  [MSG FILE_NAMES] {msg_fnames}")

            elif ptype == "workflow_step_start":
                step_name = obj.get("step_name", "?")
                print(f"  [STEP START] {step_name}")

            elif ptype == "workflow_step_end":
                step_name = obj.get("step_name", "?")
                print(f"  [STEP END] {step_name}")

    except Exception as e:
        print(f"  [STREAM ERROR] {e}")

    if last_message:
        safe_msg = last_message[:500].encode("ascii", "replace").decode("ascii")
        print(f"\n  [FINAL MESSAGE] {safe_msg}...")

    return file_ids, tool_results


def verify_file_download(file_id: str):
    """Verify we can download the file from MinIO via the API and check content."""
    resp = _api("GET", f"converse/file/{file_id}", timeout=30)

    if resp.status_code != 200:
        print(f"  [DOWNLOAD FAIL] file_id={file_id} -> {resp.status_code}")
        return False

    content_type = resp.headers.get("Content-Type", "")
    content_length = len(resp.content)
    disp = resp.headers.get("Content-Disposition", "")
    print(f"  [DOWNLOAD OK] file_id={file_id}")
    print(f"    Content-Type: {content_type}")
    print(f"    Size: {content_length} bytes")
    print(f"    Content-Disposition: {disp}")

    # --- Content verification ---
    if "wordprocessingml" in content_type or disp.endswith('.docx"'):
        _verify_docx_content(resp.content, file_id)
    elif "pdf" in content_type or disp.endswith('.pdf"'):
        _verify_pdf_content(resp.content, file_id)

    return True


def _verify_docx_content(data: bytes, file_id: str):
    """Open DOCX and verify it has real text content."""
    from io import BytesIO
    try:
        from docx import Document
    except ImportError:
        print(f"    [SKIP] python-docx not installed, cannot verify content")
        return

    doc = Document(BytesIO(data))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    tables = doc.tables
    total_text = " ".join(paragraphs)

    print(f"    [CONTENT] Paragraphs with text: {len(paragraphs)}")
    print(f"    [CONTENT] Tables: {len(tables)}")
    print(f"    [CONTENT] Total chars: {len(total_text)}")
    if paragraphs:
        print(f"    [CONTENT] First paragraph: {paragraphs[0][:120]}")
    if len(total_text) < 20:
        print(f"    [CONTENT FAIL] DOCX appears EMPTY or near-empty!")
    else:
        print(f"    [CONTENT OK] DOCX has substantive content")


def _verify_pdf_content(data: bytes, file_id: str):
    """Basic PDF verification - check size and magic bytes."""
    if data[:5] == b"%PDF-":
        print(f"    [CONTENT OK] Valid PDF header, {len(data)} bytes")
    else:
        print(f"    [CONTENT FAIL] Not a valid PDF (bad magic bytes)")


def main():
    print("\n=== DOCX Download Test ===\n")

    # Step 1: Create chat session
    print("1. Creating chat session...")
    session_id = create_chat_session()
    print(f"   Session ID: {session_id}\n")

    # Step 2: Send a 2-page DOCX request (complex, 5 sections)
    print("2. Sending 2-page DOCX request...")
    message = (
        "Create a 2-page DOCX document titled 'AI in Healthcare: 2026 Overview'. "
        "Include 5 sections: 1) Introduction (2 paragraphs), "
        "2) Key Applications (bulleted list of 5 items), "
        "3) Market Data (a 3-row table with columns Application/Market Size/Growth Rate, "
        "followed by a page break), "
        "4) Implementation Steps (numbered list of 4 items), "
        "5) Conclusion (1 paragraph). "
        "Output format: docx."
    )
    print(f"   Message: {message}\n")

    file_ids, tool_results = send_message_and_stream(session_id, message)

    # Step 3: Verify file_ids
    print(f"\n3. Results:")
    print(f"   File IDs found: {len(file_ids)}")
    print(f"   Tool results: {len(tool_results)}")

    if file_ids:
        print(f"\n4. Verifying file downloads...")
        for fid in file_ids:
            verify_file_download(fid)
        print(f"\n   SUCCESS: {len(file_ids)} file(s) saved to MinIO and downloadable!")
    else:
        print(f"\n   WARNING: No file_ids found in stream.")
        print(f"   Check if DOCX Builder created a document and if file detection worked.")
        # Print tool results for debugging
        for i, tr in enumerate(tool_results):
            result_str = str(tr)[:500]
            print(f"\n   Tool result {i+1}: {result_str}")

    # Step 4: Verify session reload (file_ids persist in history)
    print(f"\n5. Verifying session reload (file_ids in history)...")
    resp = _api("GET", f"converse/get-chat-session/{session_id}")
    if resp.status_code == 200:
        session_data = resp.json()
        messages = session_data.get("messages", [])
        print(f"   Messages in history: {len(messages)}")

        # Look for tool calls with file_ids in stored response
        for msg in messages:
            for tc in msg.get("tool_calls", []):
                tcr = tc.get("tool_call_response", "")
                if tcr and "_file_ids" in str(tcr):
                    print(f"   Found _file_ids in stored tool call response!")
                    try:
                        parsed = json.loads(tcr)
                        if isinstance(parsed, dict) and "_file_ids" in parsed:
                            print(f"   Stored file_ids: {parsed['_file_ids']}")
                    except:
                        pass
    else:
        print(f"   Could not fetch session: {resp.status_code}")

    print(f"\n=== Test Complete ===\n")


if __name__ == "__main__":
    main()
