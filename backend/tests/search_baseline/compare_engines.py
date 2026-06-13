"""Compare Vespa vs OpenSearch retrieval on the same corpus + queries.

Used *after* the corpus has been seeded into both engines (seed with
``ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true`` so docs land in both). For each
baseline query it runs the identical harness against each engine and reports
overlap@k and a normalized rank-correlation, so we can quantify how closely
OpenSearch reproduces the Vespa baseline.

Run from ``backend/``:

    ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true python -m tests.search_baseline.compare_engines
"""

from dataclasses import dataclass
from typing import Any

from onyx.configs.constants import DocumentSource
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.engine.sql_engine import SqlEngine
from tests.search_baseline import corpus
from tests.search_baseline.harness import BaselineHit
from tests.search_baseline.harness import get_index
from tests.search_baseline.harness import KEYWORD_ALPHA
from tests.search_baseline.harness import run_search
from tests.search_baseline.harness import SEMANTIC_ALPHA


@dataclass
class Case:
    name: str
    kwargs: dict[str, Any]


CASES: list[Case] = [
    Case("kubernetes", {"query": "how do I deploy containers to a kubernetes cluster"}),
    Case("parental_leave", {"query": "how much paid parental leave do new parents get"}),
    Case("expense_report", {"query": "how to submit an expense report for reimbursement"}),
    Case("async_keyword", {"query": "asyncio event loop coroutines", "hybrid_alpha": KEYWORD_ALPHA}),
    Case("async_semantic", {"query": "asyncio event loop coroutines", "hybrid_alpha": SEMANTIC_ALPHA}),
    Case("kb_engineering", {"query": "technical guide", "document_sets": [corpus.KB_ENGINEERING]}),
    Case("source_file", {"query": "guide policy report", "source_types": [DocumentSource.FILE]}),
    Case("time_recent", {"query": "guide policy report process", "time_cutoff": corpus.TIME_CUTOFF_BETWEEN}),
]


def overlap_at_k(a: list[str], b: list[str], k: int) -> float:
    sa, sb = set(a[:k]), set(b[:k])
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def normalized_footrule(a: list[str], b: list[str]) -> float:
    """Spearman footrule over the intersection, normalized to [0, 1].

    1.0 = identical ordering of the common docs, 0.0 = fully reversed.
    """
    common = [d for d in a if d in set(b)]
    n = len(common)
    if n <= 1:
        return 1.0
    rank_a = {d: i for i, d in enumerate([d for d in a if d in set(b)])}
    rank_b = {d: i for i, d in enumerate([d for d in b if d in set(a)])}
    total = sum(abs(rank_a[d] - rank_b[d]) for d in common)
    max_total = (n * n) // 2  # max footrule for a permutation of length n
    return 1.0 - (total / max_total if max_total else 0.0)


def main() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        pass

    rows: list[tuple[str, float, float, int, int]] = []
    with get_session_with_current_tenant() as db_session:
        vespa = get_index("vespa", db_session)
        opensearch = get_index("opensearch", db_session)

        for case in CASES:
            v_hits: list[BaselineHit] = run_search(vespa, db_session=db_session, **case.kwargs)
            o_hits: list[BaselineHit] = run_search(opensearch, db_session=db_session, **case.kwargs)
            v_ids = [h.document_id for h in v_hits]
            o_ids = [h.document_id for h in o_hits]
            rows.append(
                (
                    case.name,
                    overlap_at_k(v_ids, o_ids, 5),
                    normalized_footrule(v_ids, o_ids),
                    len(v_ids),
                    len(o_ids),
                )
            )

    print(f"\n{'case':<22}{'overlap@5':>12}{'rank_corr':>12}{'vespa_n':>10}{'os_n':>8}")
    print("-" * 64)
    for name, ov, rc, vn, on in rows:
        print(f"{name:<22}{ov:>12.2f}{rc:>12.2f}{vn:>10}{on:>8}")
    if rows:
        avg_ov = sum(r[1] for r in rows) / len(rows)
        avg_rc = sum(r[2] for r in rows) / len(rows)
        print("-" * 64)
        print(f"{'AVERAGE':<22}{avg_ov:>12.2f}{avg_rc:>12.2f}")


if __name__ == "__main__":
    main()
