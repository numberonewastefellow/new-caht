"""Pure retrieval metrics (doc level, binary relevance) and statistics helpers.

All ranking functions take a ranked list of *already normalised* doc names
(see ``normalize_doc_name`` / ``dedupe_ranked_docs``) and a collection of gold
names. Ranks are 1-based.
"""

import math
import random
from collections.abc import Collection
from collections.abc import Iterable
from collections.abc import Sequence

BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20261030


def normalize_doc_name(name: str) -> str:
    """Case-insensitive, whitespace-trimmed doc name used for gold matching."""
    return name.strip().casefold()


def dedupe_ranked_docs(names: Iterable[str]) -> list[str]:
    """Collapse chunk hits to docs: keep each doc at its first (best) rank."""
    seen: set[str] = set()
    ranked: list[str] = []
    for name in names:
        key = normalize_doc_name(name)
        if key in seen:
            continue
        seen.add(key)
        ranked.append(key)
    return ranked


def gold_ranks(ranked: Sequence[str], gold: Iterable[str]) -> list[int | None]:
    """1-based rank of each gold doc (in the given gold order), None if absent."""
    position = {name: idx + 1 for idx, name in enumerate(ranked)}
    return [position.get(normalize_doc_name(g)) for g in gold]


def _gold_set(gold: Iterable[str]) -> set[str]:
    gold_set = {normalize_doc_name(g) for g in gold}
    if not gold_set:
        raise ValueError("A question needs at least one gold doc")
    return gold_set


def recall_at_k(ranked: Sequence[str], gold: Collection[str], k: int) -> float:
    gold_set = _gold_set(gold)
    found = gold_set.intersection(ranked[:k])
    return len(found) / len(gold_set)


def hit_at_k(ranked: Sequence[str], gold: Collection[str], k: int) -> float:
    gold_set = _gold_set(gold)
    return 1.0 if gold_set.intersection(ranked[:k]) else 0.0


def reciprocal_rank(ranked: Sequence[str], gold: Collection[str]) -> float:
    gold_set = _gold_set(gold)
    for idx, name in enumerate(ranked):
        if name in gold_set:
            return 1.0 / (idx + 1)
    return 0.0


def ndcg_at_k(ranked: Sequence[str], gold: Collection[str], k: int) -> float:
    """Binary-relevance nDCG@k with the standard log2(rank + 1) discount."""
    gold_set = _gold_set(gold)
    dcg = sum(
        1.0 / math.log2(idx + 2)
        for idx, name in enumerate(ranked[:k])
        if name in gold_set
    )
    ideal_hits = min(len(gold_set), k)
    idcg = sum(1.0 / math.log2(idx + 2) for idx in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def retrieval_metric_set(
    ranked: Sequence[str], gold: Collection[str]
) -> dict[str, float]:
    """The metric set reported per question in retrieval / product mode."""
    return {
        "recall@5": recall_at_k(ranked, gold, 5),
        "recall@10": recall_at_k(ranked, gold, 10),
        "mrr": reciprocal_rank(ranked, gold),
        "ndcg@10": ndcg_at_k(ranked, gold, 10),
        "hit@5": hit_at_k(ranked, gold, 5),
    }


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (same convention as numpy's default)."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    if not 0 <= q <= 100:
        raise ValueError("q must be within [0, 100]")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q / 100.0
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return float(ordered[lower])
    frac = pos - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * frac)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def bootstrap_delta_ci(
    before: Sequence[float],
    after: Sequence[float],
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Paired bootstrap CI of mean(after - before).

    ``before[i]`` and ``after[i]`` must be the same question. Returns
    ``(delta, ci_low, ci_high)``. Deterministic for a fixed seed.
    """
    if len(before) != len(after):
        raise ValueError("Paired bootstrap needs equal-length samples")
    if not before:
        return 0.0, 0.0, 0.0
    diffs = [a - b for a, b in zip(after, before)]
    delta = mean(diffs)
    rng = random.Random(seed)
    n = len(diffs)
    resampled_means = [
        mean([diffs[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples)
    ]
    tail = (1.0 - confidence) / 2.0 * 100.0
    return (
        delta,
        percentile(resampled_means, tail),
        percentile(resampled_means, 100.0 - tail),
    )
