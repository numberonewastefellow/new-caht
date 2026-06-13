"""Golden-snapshot save/load/assert for retrieval baselines.

Each baseline is an ordered list of ``BaselineHit`` stored as JSON under
``baselines/<engine>/<name>.json``. The primary invariant we assert is the
ordered list of ``(document_id, chunk_id)`` keys; scores are stored for
diagnostics and can be compared with a tolerance when requested.

Modes (env ``BASELINE_MODE``):
  - ``record``  : (re)write the golden file and pass. Use to (re)generate goldens.
  - otherwise   : assert current hits match the stored golden (default).
"""

import json
import os
from pathlib import Path

from tests.search_baseline.harness import BaselineHit

BASELINES_DIR = Path(__file__).parent / "baselines"


def _baseline_path(name: str, engine: str) -> Path:
    return BASELINES_DIR / engine / f"{name}.json"


def is_record_mode() -> bool:
    return os.environ.get("BASELINE_MODE", "").lower() == "record"


def save_baseline(name: str, hits: list[BaselineHit], engine: str = "vespa") -> Path:
    path = _baseline_path(name, engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "engine": engine,
        "hits": [h.model_dump() for h in hits],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_baseline(name: str, engine: str = "vespa") -> list[BaselineHit]:
    path = _baseline_path(name, engine)
    if not path.exists():
        raise FileNotFoundError(
            f"No baseline for {name!r} (engine={engine}). "
            f"Run with BASELINE_MODE=record to create it: {path}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [BaselineHit(**h) for h in payload["hits"]]


def _keys(hits: list[BaselineHit]) -> list[tuple[str, int]]:
    return [h.key for h in hits]


def assert_matches(
    name: str,
    hits: list[BaselineHit],
    *,
    engine: str = "vespa",
    compare_scores: bool = False,
    score_tol: float = 1e-3,
) -> None:
    """Assert ``hits`` match the stored golden, or record it in record mode.

    Always compares the ordered (document_id, chunk_id) list. When
    ``compare_scores`` is set, also asserts each score is within ``score_tol``.
    """
    if is_record_mode():
        path = save_baseline(name, hits, engine=engine)
        print(f"[record] wrote baseline {name} -> {path} ({len(hits)} hits)")
        return

    expected = load_baseline(name, engine=engine)

    actual_keys = _keys(hits)
    expected_keys = _keys(expected)
    assert actual_keys == expected_keys, (
        f"Ranking changed for baseline {name!r}.\n"
        f"  expected (doc_id, chunk_id): {expected_keys}\n"
        f"  actual   (doc_id, chunk_id): {actual_keys}"
    )

    if compare_scores:
        for exp, act in zip(expected, hits):
            if exp.score is None or act.score is None:
                assert exp.score == act.score, (
                    f"Score nullability changed for {act.key} in {name!r}: "
                    f"{exp.score} != {act.score}"
                )
                continue
            assert abs(exp.score - act.score) <= score_tol, (
                f"Score drifted for {act.key} in {name!r}: "
                f"{exp.score} vs {act.score} (tol={score_tol})"
            )
