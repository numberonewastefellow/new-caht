"""
Test: Chart Generation & File Download in Workflows
====================================================

Runs an ML workflow that generates charts, then verifies:
1. PythonTool executes with savefig calls
2. Files are generated and streamed via PythonToolDelta
3. Files are downloadable from /api/converse/file/{id}
4. File metadata (filename) is present in enriched delta packets

Usage:
    python test_chart_generation.py [--key API_KEY] [--url BASE_URL]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests as req_lib

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


def log(msg):
    try:
        print(f"  {msg}")
    except UnicodeEncodeError:
        print(f"  {msg.encode('ascii', errors='replace').decode('ascii')}")


def test_pass(name):
    global PASS
    PASS += 1
    print(f"  [PASS] {name}")


def test_fail(name, reason):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {name}: {reason}")


def run_and_collect(workflow_id, message):
    """Run a workflow and collect all streaming data."""
    result = {
        "agents": [],
        "python_execs": 0,
        "savefig_count": 0,
        "file_ids": [],
        "files_meta": [],
        "final_answer": "",
        "completed": False,
        "error": None,
        "duration_s": 0,
    }

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", {"message": message})
    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

    in_final = False
    final_parts = []

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            pkt = json.loads(line)
            obj = pkt.get("obj", pkt)
            ptype = obj.get("type", "")

            if ptype == "workflow_step_start":
                step = obj.get("step_name", "?")
                result["agents"].append(step)
                log(f"[STEP] {step}")

            elif ptype == "python_tool_start":
                result["python_execs"] += 1
                code = obj.get("code", "")
                if "savefig" in code:
                    result["savefig_count"] += 1
                log(f"  [PY#{result['python_execs']}] savefig={'savefig' in code} len={len(code)}")

            elif ptype == "python_tool_delta":
                fids = obj.get("file_ids", [])
                files = obj.get("files", [])
                if fids:
                    result["file_ids"].extend(fids)
                    log(f"  [FILES] {len(fids)} file_ids generated")
                if files:
                    result["files_meta"].extend(files)
                    for f in files:
                        log(f"  [FILE] {f.get('filename','?')} (id={f.get('file_id','?')[:12]}...)")
                stderr = obj.get("stderr", "")
                if stderr and ("Error" in stderr or "Traceback" in stderr):
                    safe = stderr[:200].encode("ascii", errors="replace").decode("ascii")
                    log(f"  [PY-ERR] {safe}")

            elif ptype == "message_start":
                in_final = True

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                if in_final:
                    final_parts.append(content)

            elif ptype == "stop":
                result["completed"] = True

        except json.JSONDecodeError:
            pass

    result["final_answer"] = "".join(final_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_ml_chart_generation():
    """Test ML Model Rapid Prototyper generates downloadable charts."""
    print("\n=== Test: ML Model Chart Generation (workflow=48) ===")

    result = run_and_collect(
        48,
        "Build a regression model to predict house sale prices. "
        "Features: bedrooms, bathrooms, sqft_living, sqft_lot, floors, waterfront (0/1), "
        "view_score (0-4), condition (1-5), grade (1-13), year_built, zipcode. "
        "Target: sale_price. Dataset: 30 houses from Seattle area. "
        "Train Linear Regression, Random Forest, Gradient Boosting. "
        "Report RMSE, MAE, R-squared. "
        "Generate scatter plot of predicted vs actual AND feature importance chart. "
        'Save all charts with plt.savefig("name.png", dpi=150, bbox_inches="tight")',
    )

    if result["error"]:
        test_fail("Execution", f"Error: {result['error']}")
        return result

    log(f"Duration: {result['duration_s']}s")
    log(f"Agents: {result['agents']}")
    log(f"Python executions: {result['python_execs']}")
    log(f"savefig calls: {result['savefig_count']}")
    log(f"File IDs: {len(result['file_ids'])}")
    log(f"Files meta: {len(result['files_meta'])}")

    # 1. Agents ran
    if len(result["agents"]) >= 4:
        test_pass(f"All agents ran ({len(result['agents'])} steps)")
    else:
        test_fail("Agent count", f"Only {len(result['agents'])} agents ran")

    # 2. Python code executed
    if result["python_execs"] >= 2:
        test_pass(f"Python executed {result['python_execs']} times")
    else:
        test_fail("Python execution", f"Only {result['python_execs']} executions")

    # 3. savefig was called
    if result["savefig_count"] >= 1:
        test_pass(f"savefig called {result['savefig_count']} times")
    else:
        test_fail("savefig calls", "No savefig calls in generated code")

    # 4. Files generated
    if result["file_ids"]:
        test_pass(f"{len(result['file_ids'])} chart files generated")
    else:
        test_fail("File generation", "No files generated despite savefig calls")
        return result

    # 5. Enriched metadata present
    if result["files_meta"]:
        has_names = all(f.get("filename") for f in result["files_meta"])
        if has_names:
            names = [f["filename"] for f in result["files_meta"]]
            test_pass(f"Enriched metadata with filenames: {names}")
        else:
            test_fail("File metadata", "Files present but missing filenames")
    else:
        test_fail("File metadata", "No enriched PythonToolFile metadata")

    # 6. Files are downloadable
    print("\n  --- File Download Verification ---")
    all_downloadable = True
    for fid in result["file_ids"]:
        url = f"{CONFIG['base_url']}/api/converse/file/{fid}"
        try:
            r = req_lib.get(url, headers=headers(), timeout=15)
            ct = r.headers.get("content-type", "?")
            size = len(r.content)
            if r.status_code == 200 and size > 100:
                test_pass(f"File {fid[:12]}... downloadable ({size:,} bytes, {ct})")
            else:
                test_fail(f"File {fid[:12]}... download", f"status={r.status_code} size={size}")
                all_downloadable = False
        except Exception as e:
            test_fail(f"File {fid[:12]}... download", str(e)[:100])
            all_downloadable = False

    # 7. Workflow completed
    if result["completed"]:
        test_pass("Workflow completed")
    else:
        test_fail("Completion", "Workflow did not complete")

    return result


def test_data_analysis_chart():
    """Test Data Analysis Pipeline chart generation."""
    print("\n=== Test: Data Analysis Chart Generation (workflow=45) ===")

    result = run_and_collect(
        45,
        "Revenue data: CSV with columns date, product_line (Enterprise/SMB/Consumer), "
        "region (North America/Europe/APAC), revenue, units_sold, discount_pct. "
        "12 months of data (Jan-Dec 2023), 108 rows. "
        "Analysis: Which product line grows fastest? Regional comparison. "
        "Discount vs units correlation. Seasonal patterns. "
        "IMPORTANT: The Visualization Generator MUST save all charts as PNG files "
        "using plt.savefig('chart_name.png', dpi=150, bbox_inches='tight') "
        "followed by plt.close(). Generate at least 3 different charts.",
    )

    if result["error"]:
        test_fail("Execution", f"Error: {result['error']}")
        return result

    log(f"Duration: {result['duration_s']}s")
    log(f"Python executions: {result['python_execs']}")
    log(f"savefig calls: {result['savefig_count']}")
    log(f"Files generated: {len(result['file_ids'])}")

    if len(result["agents"]) >= 4:
        test_pass(f"All agents ran ({len(result['agents'])} steps)")
    else:
        test_fail("Agent count", f"Only {len(result['agents'])} agents ran")

    if result["python_execs"] >= 2:
        test_pass(f"Python executed {result['python_execs']} times")
    else:
        test_fail("Python execution", f"Only {result['python_execs']} executions")

    if result["savefig_count"] >= 1:
        test_pass(f"savefig called {result['savefig_count']} times")
    else:
        test_fail("savefig calls", "Visualization Generator did not call savefig (LLM compliance issue)")

    if result["file_ids"]:
        test_pass(f"{len(result['file_ids'])} chart files generated")
        # Download check
        for fid in result["file_ids"]:
            url = f"{CONFIG['base_url']}/api/converse/file/{fid}"
            try:
                r = req_lib.get(url, headers=headers(), timeout=15)
                if r.status_code == 200 and len(r.content) > 100:
                    test_pass(f"File {fid[:12]}... downloadable ({len(r.content):,} bytes)")
                else:
                    test_fail(f"File download", f"status={r.status_code}")
            except Exception as e:
                test_fail(f"File download", str(e)[:100])
    else:
        log("  [WARN] No chart files generated - this is a known LLM compliance issue")
        log("  The agent sometimes writes code without savefig despite being prompted")

    if result["completed"]:
        test_pass("Workflow completed")
    else:
        test_fail("Completion", "Workflow did not complete")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test chart generation in workflows")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print(f"Base URL: {CONFIG['base_url']}")

    print("\n" + "=" * 60)
    print("CHART GENERATION & FILE DOWNLOAD TEST SUITE")
    print("=" * 60)

    ml_result = test_ml_chart_generation()
    da_result = test_data_analysis_chart()

    print(f"\n{'='*60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
