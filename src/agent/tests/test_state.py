"""Unit tests for agent Pydantic schemas — no LLM, no infra."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.state import Answer, Citation, CitedClaim, DecompositionResult, GradeResult
from src.ingestion.schema import ROLE_PUBLIC


def test_answer_requires_claims_when_not_unanswerable() -> None:
    with pytest.raises(ValidationError):
        Answer(claims=[], confidence="high", unanswerable=False)


def test_answer_allows_unanswerable_without_claims() -> None:
    a = Answer(
        claims=[],
        confidence="low",
        unanswerable=True,
        unanswerable_reason="No sources",
    )
    assert a.unanswerable is True
    assert not a.claims


def test_cited_claim_min_one_citation() -> None:
    with pytest.raises(ValidationError):
        CitedClaim(claim="x", citations=[])


def test_citation_quote_max_length() -> None:
    with pytest.raises(ValidationError):
        Citation(chunk_id="c1", artikel="1", quote="x" * 501)


def test_decomposition_strips_and_rejects_all_empty() -> None:
    d = DecompositionResult(questions=["  a  ", " b "])
    assert d.questions == ["a", "b"]
    with pytest.raises(ValidationError):
        DecompositionResult(questions=["", "  "])


def test_grade_result_three_way() -> None:
    g = GradeResult(grade="ambiguous", reasoning="brak", missing_info="dates")
    assert g.grade == "ambiguous"
    assert g.missing_info == "dates"


def test_public_role_literal_unused_here() -> None:
    """Sanity: ingestion roles remain importable for graph tests."""
    assert ROLE_PUBLIC == "public"
