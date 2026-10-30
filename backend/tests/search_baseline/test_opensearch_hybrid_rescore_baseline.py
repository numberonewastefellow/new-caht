"""OpenSearch retrieval baseline with the hybrid rescore switched ON.

Same corpus and production path as test_opensearch_baseline.py, but with
OPENSEARCH_HYBRID_RESCORE_ENABLED patched on and the rescore clock frozen at
FROZEN_NOW, so goldens do not drift as the corpus dates age. Goldens live in
baselines/opensearch/hybrid_rescore/ and are separate from the flag-off goldens
(which must stay unchanged).

Record goldens:  BASELINE_MODE=record pytest tests/search_baseline/test_opensearch_hybrid_rescore_baseline.py
Assert:          pytest tests/search_baseline/test_opensearch_hybrid_rescore_baseline.py
"""

from datetime import datetime
from datetime import timezone

import pytest
from sqlalchemy.orm import Session

import om.configs.app_configs as app_configs
from om.document_index.opensearch import opensearch_document_index as osdi
from tests.search_baseline import corpus
from tests.search_baseline.harness import BaselineHit
from tests.search_baseline.harness import get_index
from tests.search_baseline.harness import hit_doc_ids
from tests.search_baseline.harness import run_search
from tests.search_baseline.snapshot import _baseline_path
from tests.search_baseline.snapshot import assert_matches
from tests.search_baseline.snapshot import is_record_mode

ENGINE = "opensearch"
GOLDEN_ENGINE = "opensearch/hybrid_rescore"
# corpus.RECENT_DATE is ~17 days old here (factor ~0.98); OLD_DATE is floored.
FROZEN_NOW = datetime(2026, 2, 1, tzinfo=timezone.utc)

pytestmark = pytest.mark.usefixtures("seeded_corpus_opensearch")


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[no-untyped-def,override]
        return FROZEN_NOW if tz is None else FROZEN_NOW.astimezone(tz)


@pytest.fixture(autouse=True)
def _rescore_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", True)
    monkeypatch.setattr(osdi, "datetime", _FrozenDatetime)


def _search(db_session: Session, **kwargs) -> list[BaselineHit]:
    index = get_index(ENGINE, db_session)
    kwargs.setdefault("document_sets", corpus.ALL_KBS)
    return run_search(index, db_session=db_session, **kwargs)


def _snap(name: str, hits: list[BaselineHit]) -> None:
    if not is_record_mode() and not _baseline_path(name, GOLDEN_ENGINE).exists():
        pytest.skip(
            f"No flag-on golden {name!r} yet; record with BASELINE_MODE=record."
        )
    assert_matches(name, hits, engine=GOLDEN_ENGINE)


def test_rescore_query_kubernetes_deploy(db_session: Session) -> None:
    hits = _search(
        db_session, query="how do I deploy containers to a kubernetes cluster"
    )
    assert hits[0].document_id == "eng-k8s-deploy", hit_doc_ids(hits)[:3]
    _snap("query_kubernetes_deploy", hits)


def test_rescore_query_parental_leave(db_session: Session) -> None:
    hits = _search(db_session, query="how much paid parental leave do new parents get")
    assert hits[0].document_id == "hr-parental-leave", hit_doc_ids(hits)[:3]
    _snap("query_parental_leave", hits)


def test_rescore_mixed_dates(db_session: Session) -> None:
    # Broad query over the whole corpus: old docs get the 0.75 floor, recent
    # ones ~0.98, so recent docs should move up versus the flag-off order.
    # Pinned by the golden (inspect it when recording).
    hits = _search(db_session, query="guide policy report process")
    assert hits
    _snap("mixed_dates_guide_policy", hits)
