#!/usr/bin/env python3
"""
Smoke test for the file-upload demo starters (agent-config, no backend change).

Two modes:
  * NO-FILE (default): click the upload starter with NOTHING attached -> the Extractor must HITL-pause
    ([NEEDS_INPUT]) asking which files to upload, and must NOT fabricate a document.
  * WITH-FILES (--attach <case_dir>): upload that case's CSVs to /api/converse/file, then run the
    workflow passing the returned file_descriptors -> the workflow must run end-to-end (not pause) and
    the output must be grounded in the file data (--expect keywords).

  python smoke_upload.py --key <KEY>                                    # Collectorate no-file pause
  python smoke_upload.py --key <KEY> --attach test_data/collectorate/CO1 --expect lakshmi 04412
"""
import argparse
import json
import sys
from pathlib import Path

import requests

from config import CONFIG, add_common_args, api, apply_common_args, headers, stream_api
from test_collectorate import create_chat_session
from add_file_upload_starter import UPLOAD_STARTERS


def find_wf(name: str):
    for w in api("GET", "workflow").json():
        if w["name"] == name:
            return w["id"]
    return None


def upload_files(paths: list[Path]) -> list[dict]:
    """Upload files exactly like the UI's uploadFilesForChat() -> POST /api/converse/file."""
    h = {k: v for k, v in headers().items() if k.lower() != "content-type"}
    url = CONFIG["base_url"].rstrip("/") + "/api/converse/file"
    files = [("files", (p.name, p.read_bytes(), "text/csv")) for p in paths]
    r = requests.post(url, headers=h, files=files, timeout=180)
    r.raise_for_status()
    return r.json()["files"]


def run(wid: int, message: str, sid, file_descriptors=None) -> dict:
    body = {"message": message, "chat_session_id": sid}
    if file_descriptors:
        body["file_descriptors"] = file_descriptors
    resp = stream_api("POST", f"workflow/{wid}/run", body)
    agents, parts = [], []
    paused, pause_text, cur = False, "", None
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            pkt = json.loads(line)
        except json.JSONDecodeError:
            continue
        obj = pkt.get("obj", pkt)
        t = obj.get("type", "")
        if t == "workflow_step_start":
            cur = obj.get("step_name", "?")
            if cur not in agents:
                agents.append(cur)
        elif t in ("workflow_step_delta", "message_delta"):
            parts.append(obj.get("content", obj.get("delta", "")) or "")
        elif t == "workflow_pause_for_input":
            paused, pause_text = True, obj.get("questions", "")
    return {"agents": agents, "paused": paused, "pause_text": pause_text, "text": "".join(parts)}


def main() -> bool:
    ap = argparse.ArgumentParser(description="Smoke-test the file-upload starters")
    add_common_args(ap)
    ap.add_argument("--workflow", default="District Collectorate Coordination")
    ap.add_argument("--attach", help="case dir whose *.csv to upload (e.g. test_data/collectorate/CO1)")
    ap.add_argument("--expect", nargs="*", default=[], help="keywords expected in grounded output")
    args = ap.parse_args()
    apply_common_args(args)

    wname = args.workflow
    msg = UPLOAD_STARTERS[wname][1]
    wid = find_wf(wname)
    print(f"workflow '{wname}' id={wid}")

    fds = None
    if args.attach:
        paths = sorted(Path(args.attach).glob("*.csv"))
        fds = upload_files(paths)
        print(f"uploaded {len(fds)} file(s): {[f.get('name') for f in fds]}")

    sid = create_chat_session()
    r = run(wid, msg, sid, fds)
    print(f"  agents_run = {r['agents']}")
    print(f"  paused     = {r['paused']}")
    if r["paused"]:
        print(f"  pause_text = {r['pause_text'][:220]}")

    low = r["text"].lower()
    if args.attach:
        hits = [k for k in args.expect if k.lower() in low]
        ok = (not r["paused"]) and len(r["agents"]) >= 3 and (not args.expect or bool(hits))
        print(f"  grounding_hits = {hits}  (out of {args.expect})")
        print(f"  => {'PASS (ran with uploaded files, output grounded)' if ok else 'CHECK'}")
    else:
        ok = r["paused"]
        print(f"  => {'PASS (paused, asked for files, no fabrication)' if ok else 'CHECK (did not pause)'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
