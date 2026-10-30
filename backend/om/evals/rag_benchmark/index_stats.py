"""Chunk counts per document (the L1 chunker's footprint) and index store size."""

import statistics
from typing import Any

import requests

from om.evals.rag_benchmark.api_client import RagBenchmarkApiClient
from om.evals.rag_benchmark.models import DatasetManifest
from om.evals.rag_benchmark.models import DocIndexStats
from om.evals.rag_benchmark.models import IndexStats


def summarize_chunks(docs: list[DocIndexStats]) -> dict[str, dict[str, float]]:
    by_type: dict[str, list[int]] = {}
    for doc in docs:
        if doc.num_chunks is not None:
            by_type.setdefault(doc.doc_type, []).append(doc.num_chunks)
            by_type.setdefault("all", []).append(doc.num_chunks)
    return {
        doc_type: {
            "docs": float(len(counts)),
            "min": float(min(counts)),
            "median": float(statistics.median(counts)),
            "max": float(max(counts)),
            "total": float(sum(counts)),
        }
        for doc_type, counts in sorted(by_type.items())
    }


def opensearch_store_size(
    base_url: str, auth: tuple[str, str] | None = None, verify: bool = False
) -> int:
    """Sum of ``store.size`` (bytes) over non-system indices. Scratch stack only:
    there the index holds nothing but the benchmark corpus."""
    response = requests.get(
        f"{base_url.rstrip('/')}/_cat/indices",
        params={"format": "json", "bytes": "b"},
        auth=auth,
        verify=verify,
        timeout=30,
    )
    response.raise_for_status()
    rows: list[dict[str, Any]] = response.json()
    return sum(
        int(row.get("store.size") or 0)
        for row in rows
        if not str(row.get("index", "")).startswith(".")
    )


def collect_index_stats(
    client: RagBenchmarkApiClient,
    manifest: DatasetManifest,
    doc_ids: dict[str, str],
    opensearch_url: str | None = None,
    opensearch_auth: tuple[str, str] | None = None,
) -> IndexStats:
    docs: list[DocIndexStats] = []
    for entry in manifest.files:
        doc_id = doc_ids.get(entry.file_name)
        stats = DocIndexStats(
            semantic_identifier=entry.file_name,
            document_id=doc_id or "",
            doc_type=entry.doc_type,
        )
        if doc_id:
            try:
                info = client.document_size_info(doc_id)
                stats.num_chunks = int(info["num_chunks"])
                stats.num_tokens = int(info["num_tokens"])
            except Exception:  # noqa: BLE001 - a missing doc is reported as None
                pass
        docs.append(stats)
    store_size = (
        opensearch_store_size(opensearch_url, opensearch_auth)
        if opensearch_url
        else None
    )
    return IndexStats(
        docs=docs,
        total_chunks=sum(d.num_chunks or 0 for d in docs),
        chunks_by_doc_type=summarize_chunks(docs),
        store_size_bytes=store_size,
    )
