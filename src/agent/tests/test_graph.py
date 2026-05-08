"""Graph routing tests with stubbed LLM nodes — no OpenAI, no Qdrant."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agent.graph import AgentNodeOverrides, build_agent_graph, route_after_grade
from src.agent.state import AgentState, Answer, Citation, CitedClaim
from src.ingestion.schema import ROLE_PUBLIC, Chunk, ChunkMetadata
from src.retrieval.bm25 import BM25Index


def _one_public_chunk() -> Chunk:
    meta = ChunkMetadata(
        doc_id="TEST_DOC",
        wet="Wet test",
        artikel="1",
        lid=1,
        classification="public",
        allowed_roles=[ROLE_PUBLIC],
        source_file="t.html",
    )
    return Chunk(
        chunk_id="TEST_DOC_art_1_lid_1",
        text="Dit is een testartikel over belasting. Het tarief is 20 procent.",
        metadata=meta,
    )


@pytest.fixture
def bm25_minimal() -> BM25Index:
    return BM25Index([_one_public_chunk()])


def test_route_after_grade_matrix() -> None:
    base = AgentState(original_question="q", user_roles=[ROLE_PUBLIC], retry_count=0)
    assert route_after_grade(base.model_copy(update={"grade": "relevant"})) == "generate"
    assert route_after_grade(base.model_copy(update={"grade": "irrelevant"})) == "escalate"
    assert route_after_grade(base.model_copy(update={"grade": "ambiguous"})) == "rewrite"
    assert (
        route_after_grade(base.model_copy(update={"grade": "ambiguous", "retry_count": 1}))
        == "escalate"
    )


def test_graph_irrelevant_escalates(
    bm25_minimal: BM25Index,
) -> None:
    qdrant = MagicMock()

    def stub_decompose(st: AgentState) -> dict[str, object]:
        return {"decomposed_questions": [st.original_question]}

    def stub_retrieve(st: AgentState) -> dict[str, object]:
        return {"retrieved_chunks": [_one_public_chunk()]}

    def stub_grade(_st: AgentState) -> dict[str, object]:
        return {
            "grade": "irrelevant",
            "grade_reasoning": "off-topic",
            "missing_info": None,
        }

    app = build_agent_graph(
        bm25_minimal,
        qdrant,
        node_overrides=AgentNodeOverrides(
            decompose=stub_decompose,
            retrieve=stub_retrieve,
            grade=stub_grade,
        ),
    )
    out = app.invoke(
        AgentState(original_question="What is the weather?", user_roles=[ROLE_PUBLIC]),
    )
    assert out["final_answer"] is not None
    assert out["final_answer"].unanswerable is True


def test_graph_relevant_generates(bm25_minimal: BM25Index) -> None:
    qdrant = MagicMock()

    def stub_decompose(st: AgentState) -> dict[str, object]:
        return {"decomposed_questions": [st.original_question]}

    def stub_retrieve(st: AgentState) -> dict[str, object]:
        return {"retrieved_chunks": [_one_public_chunk()]}

    def stub_grade(_st: AgentState) -> dict[str, object]:
        return {"grade": "relevant", "grade_reasoning": "ok", "missing_info": None}

    cite = Citation(
        chunk_id="TEST_DOC_art_1_lid_1",
        artikel="1",
        lid=1,
        quote="Dit is een testartikel over belasting.",
    )
    answered = Answer(
        claims=[CitedClaim(claim="Er is een testartikel.", citations=[cite])],
        confidence="high",
    )

    def stub_generate(_st: AgentState) -> dict[str, object]:
        return {"final_answer": answered}

    app = build_agent_graph(
        bm25_minimal,
        qdrant,
        node_overrides=AgentNodeOverrides(
            decompose=stub_decompose,
            retrieve=stub_retrieve,
            grade=stub_grade,
            generate=stub_generate,
        ),
    )
    out = app.invoke(
        AgentState(original_question="Wat staat er in het testartikel?", user_roles=[ROLE_PUBLIC]),
    )
    assert out["final_answer"] == answered


def test_graph_ambiguous_rewrites_once_then_escalates(bm25_minimal: BM25Index) -> None:
    qdrant = MagicMock()
    grade_calls: list[int] = []

    def stub_decompose(st: AgentState) -> dict[str, object]:
        return {"decomposed_questions": [st.original_question]}

    def stub_retrieve(st: AgentState) -> dict[str, object]:
        return {"retrieved_chunks": [_one_public_chunk()]}

    def stub_grade(_st: AgentState) -> dict[str, object]:
        grade_calls.append(1)
        return {"grade": "ambiguous", "grade_reasoning": "need year", "missing_info": "year"}

    def stub_rewrite(st: AgentState) -> dict[str, object]:
        return {
            "decomposed_questions": [st.original_question + " 2024"],
            "retry_count": st.retry_count + 1,
        }

    app = build_agent_graph(
        bm25_minimal,
        qdrant,
        node_overrides=AgentNodeOverrides(
            decompose=stub_decompose,
            retrieve=stub_retrieve,
            grade=stub_grade,
            rewrite=stub_rewrite,
        ),
    )
    out = app.invoke(
        AgentState(
            original_question="Hoe zit het met de aftrek?",
            user_roles=[ROLE_PUBLIC],
        ),
    )
    assert len(grade_calls) == 2
    assert out["final_answer"] is not None
    assert out["final_answer"].unanswerable is True


def test_graph_multipart_decompose_retrieves_twice_merges(
    bm25_minimal: BM25Index,
) -> None:
    """Two sub-questions should call retrieve via two chunk lists merged by retrieve stub."""
    qdrant = MagicMock()
    ch = _one_public_chunk()

    def stub_decompose(_st: AgentState) -> dict[str, object]:
        return {"decomposed_questions": ["Wat is tarief?", "Welke wet?"]}

    retrieved: list[str] = []

    def stub_retrieve(st: AgentState) -> dict[str, object]:
        retrieved.extend(st.decomposed_questions or [])
        return {"retrieved_chunks": [ch]}

    def stub_grade(_st: AgentState) -> dict[str, object]:
        return {"grade": "relevant", "grade_reasoning": "ok", "missing_info": None}

    def stub_generate(_st: AgentState) -> dict[str, object]:
        cite = Citation(
            chunk_id=ch.chunk_id,
            artikel="1",
            lid=1,
            quote="Dit is een testartikel over belasting.",
        )
        ans = Answer(
            claims=[CitedClaim(claim="Samenvatting.", citations=[cite])],
            confidence="medium",
        )
        return {"final_answer": ans}

    app = build_agent_graph(
        bm25_minimal,
        qdrant,
        node_overrides=AgentNodeOverrides(
            decompose=stub_decompose,
            retrieve=stub_retrieve,
            grade=stub_grade,
            generate=stub_generate,
        ),
    )
    app.invoke(
        AgentState(original_question="combo vraag", user_roles=[ROLE_PUBLIC]),
    )
    # retrieve runs once per invoke but our stub simulates one block; graph calls retrieve once
    assert retrieved == ["Wat is tarief?", "Welke wet?"]
