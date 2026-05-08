"""Offline tests for the grader shortcut path."""

from __future__ import annotations

from src.agent.nodes.grade import run_grade
from src.agent.state import AgentState
from src.ingestion.schema import ROLE_PUBLIC


def test_grade_without_chunks_skips_llm() -> None:
    st = AgentState(
        original_question="anything",
        user_roles=[ROLE_PUBLIC],
        retrieved_chunks=[],
    )
    out = run_grade(st)
    assert out["grade"] == "irrelevant"
    assert "No chunks" in str(out["grade_reasoning"])
