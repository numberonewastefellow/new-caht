"""Dump per-file chunk counts + chunk text for one workspace (read-only).

Reads `knowledge_file` rows for the workspace from Postgres and the matching chunks
from the OpenSearch chunk index, both via `docker exec` into the running stack.

Usage:
  python chunk_dump.py --workspace-id 4 --label before --out d:/tmp/batch1-live
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

PG_CONTAINER = "virtualai-relational_db-1"
OS_CONTAINER = "virtualai-opensearch-1"
OS_INDEX = "chunk_nomic_ai_nomic_embed_text_v1"


def workspace_files(workspace_id: int) -> list[dict[str, str]]:
    sql = (
        "select kf.id, kf.name, kf.status, coalesce(kf.chunk_count::text,'') "
        "from knowledge_file kf join workspace__knowledge_file w "
        f"on w.knowledge_file_id = kf.id where w.workspace_id = {int(workspace_id)} order by kf.name"
    )
    out = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "postgres", "-At", "-F", "\t", "-c", sql],
        capture_output=True, text=True, check=True, encoding="utf-8",
    ).stdout
    rows = []
    for line in out.splitlines():
        kf_id, name, status, chunk_count = line.split("\t")
        rows.append({"id": kf_id, "name": name, "status": status, "db_chunk_count": chunk_count})
    return rows


def opensearch_chunks(document_id: str) -> list[dict]:
    query = json.dumps({
        "size": 500,
        "_source": ["chunk_index", "chunk_text"],
        "query": {"terms": {"document_id": [document_id]}},
        "sort": [{"chunk_index": "asc"}],
    })
    cmd = (
        'curl -sk -u admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} '
        f'"https://localhost:9200/{OS_INDEX}/_search" -H "Content-Type: application/json" -d @-'
    )
    out = subprocess.run(
        ["docker", "exec", "-i", OS_CONTAINER, "sh", "-c", cmd],
        input=query, capture_output=True, text=True, check=True, encoding="utf-8",
    ).stdout
    return [h["_source"] for h in json.loads(out)["hits"]["hits"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-id", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default="d:/tmp/batch1-live")
    args = ap.parse_args()

    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for f in workspace_files(args.workspace_id):
        chunks = opensearch_chunks(f["id"])
        lengths = [len(c.get("chunk_text", "")) for c in chunks]
        report.append({**f, "index_chunk_count": len(chunks), "chunk_chars": lengths, "chunks": chunks})
        print(f"{f['name']}: status={f['status']} db_chunks={f['db_chunk_count']} index_chunks={len(chunks)} "
              f"chars min/max={min(lengths, default=0)}/{max(lengths, default=0)}")
    (out_dir / "chunks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
