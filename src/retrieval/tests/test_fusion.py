"""Unit tests for RRF fusion — offline, no infrastructure required.

These tests verify the mathematical properties of RRF and that we are
NOT using alpha-weighted score fusion. All tests run in CI.
"""

from __future__ import annotations

from src.retrieval.fusion import rrf, rrf_from_scored

# ---------------------------------------------------------------------------
# Core RRF correctness
# ---------------------------------------------------------------------------


def test_rrf_single_list_ranking() -> None:
    """Documents appear in score-descending order matching their input rank."""
    result = rrf([["A", "B", "C"]])
    ids = [r[0] for r in result]
    assert ids == ["A", "B", "C"]
    # Scores should be descending
    scores = [r[1] for r in result]
    assert scores[0] > scores[1] > scores[2]


def test_rrf_two_lists_boost_appearing_in_both() -> None:
    """A doc appearing in both lists outscores one appearing in only one."""
    result = rrf([["A", "B"], ["B", "C"]])
    scores = dict(result)
    # B appears in both → higher score than A or C (each in one list)
    assert scores["B"] > scores["A"]
    assert scores["B"] > scores["C"]


def test_rrf_k60_score_at_rank_1() -> None:
    """Rank-1 contribution is exactly 1/(60+1) = 1/61."""
    result = rrf([["X"]])
    assert abs(result[0][1] - 1.0 / 61) < 1e-10


def test_rrf_empty_inputs() -> None:
    assert rrf([]) == []
    assert rrf([[]]) == []
    assert rrf([[], []]) == []


def test_rrf_no_duplicates_in_output() -> None:
    """Each chunk_id appears at most once in the output."""
    result = rrf([["A", "B", "C"], ["A", "B", "D"]])
    ids = [r[0] for r in result]
    assert len(ids) == len(set(ids))


def test_rrf_formula_exact() -> None:
    """Verify the exact RRF formula for a two-list example from the paper."""
    # Doc A: rank 1 in list 1, rank 2 in list 2
    # Score = 1/(60+1) + 1/(60+2) = 1/61 + 1/62
    result = rrf([["A", "B"], ["B", "A"]])
    scores = dict(result)
    expected_a = 1.0 / 61 + 1.0 / 62
    expected_b = 1.0 / 62 + 1.0 / 61  # same for B since it's rank 2/1
    assert abs(scores["A"] - expected_a) < 1e-10
    assert abs(scores["B"] - expected_b) < 1e-10


def test_rrf_custom_k() -> None:
    """Custom k changes the score magnitudes but not the relative ranking."""
    default = rrf([["A", "B"]])
    custom = rrf([["A", "B"]], k=100)
    # A still beats B
    assert custom[0][0] == "A"
    # Scores are smaller with higher k
    assert custom[0][1] < default[0][1]


def test_rrf_from_scored_preserves_rank_order() -> None:
    """rrf_from_scored discards raw scores and uses only rank position."""
    # Both these inputs have the same rank order but wildly different scores
    result_high = rrf_from_scored([[("A", 9999.0), ("B", 8888.0)]])
    result_low = rrf_from_scored([[("A", 0.9), ("B", 0.1)]])
    # RRF output should be identical — raw scores don't matter
    assert result_high == result_low


def test_rrf_not_alpha_weighted() -> None:
    """Verify RRF output is NOT influenced by the magnitude of input scores.

    Alpha fusion would give different results when we scale BM25 scores by
    100× while keeping dense scores constant. RRF must produce the same
    ranking in both cases.

    This is the key mathematical correctness check for TRAP 4.
    """
    # Same rank order, wildly different score magnitudes
    bm25_normal: list[tuple[str, float]] = [("A", 5.0), ("B", 3.0), ("C", 1.0)]
    bm25_inflated: list[tuple[str, float]] = [("A", 500.0), ("B", 300.0), ("C", 100.0)]
    dense: list[tuple[str, float]] = [("B", 0.95), ("A", 0.80), ("C", 0.70)]

    result_normal = rrf_from_scored([bm25_normal, dense])
    result_inflated = rrf_from_scored([bm25_inflated, dense])

    # Must produce identical results — raw scores must not matter
    assert result_normal == result_inflated, (
        "RRF output changed when input scores were scaled. "
        "This means the implementation is doing score-weighted fusion (TRAP 4 violated), "
        f"not rank fusion.\nnormal: {result_normal}\ninflated: {result_inflated}"
    )


def test_rrf_three_retrievers_composable() -> None:
    """RRF trivially extends to 3+ retrievers without parameter re-tuning."""
    r1 = ["A", "B", "C"]
    r2 = ["B", "C", "D"]
    r3 = ["C", "A", "E"]
    result = rrf([r1, r2, r3])
    scores = dict(result)
    # C appears in all 3 lists → highest score
    assert scores["C"] == max(scores.values())
    # E appears in only 1 list, at rank 3 → one of the lowest
    assert scores["E"] < scores["C"]
