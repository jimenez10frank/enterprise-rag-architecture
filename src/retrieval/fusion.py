"""Reciprocal Rank Fusion (RRF) for hybrid search result combination.

Combines BM25 (sparse) and dense ranked lists into a single ranking without
alpha-weighted score fusion. Alpha fusion is wrong here because BM25 scores
(unbounded above) and cosine similarities (bounded [-1, 1]) are not on the
same scale. RRF uses ranks, not raw scores, making it scale-agnostic and
mathematically defensible. See docs/project/TRAPS.md TRAP 4.

The implementation is the exact formula from the original paper:
  Cormack, Clarke, Buettcher (SIGIR 2009)
  "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"

k=60 is the empirically validated constant from that paper and is the
industry standard. Do not change it without benchmarking on the eval set.

See docs/concepts/05-rrf.md for the derivation and a worked example.
"""

from __future__ import annotations

_DEFAULT_K = 60


def rrf(
    rankings: list[list[str]],
    *,
    k: int = _DEFAULT_K,
) -> list[tuple[str, float]]:
    """Combine multiple ranked lists via Reciprocal Rank Fusion.

    Each document receives a score contribution of 1/(k + rank) from each
    list in which it appears. Scores are summed across lists, then sorted
    descending. Documents not appearing in any list receive score 0.

    This function does NOT apply RBAC filtering — callers are responsible
    for ensuring that each input ranking list already respects the user's
    access roles.

    Args:
        rankings: Ordered lists of chunk_ids, one list per retriever.
                  First element of each list = rank 1 = highest score.
        k: Smoothing constant (default 60, from the Cormack et al. paper).
           Higher values reduce the weight advantage of rank 1 over rank 2.

    Returns:
        List of (chunk_id, rrf_score) tuples, descending by score.

    Example:
        >>> rrf([["A", "B", "C"], ["B", "A", "D"]])
        [('B', 0.032...), ('A', 0.031...), ('C', 0.016...), ('D', 0.016...)]
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def rrf_from_scored(
    scored_lists: list[list[tuple[str, float]]],
    *,
    k: int = _DEFAULT_K,
) -> list[tuple[str, float]]:
    """RRF from pre-scored (chunk_id, score) lists.

    Convenience wrapper when callers have (id, score) pairs from BM25 or
    dense retrieval. Scores are discarded — only rank order is used.

    Args:
        scored_lists: Each element is a list of (chunk_id, score) sorted
                      descending by score (i.e. rank 1 first).
        k: RRF smoothing constant.

    Returns:
        List of (chunk_id, rrf_score) tuples, descending by RRF score.
    """
    rank_lists = [[chunk_id for chunk_id, _ in lst] for lst in scored_lists]
    return rrf(rank_lists, k=k)
