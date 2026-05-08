"""Context grader: three-way relevance before generation (docs/project/TRAPS.md TRAP 7)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.llm_factory import structured_llm
from src.agent.state import AgentState, GradeResult

_GRADE_SYSTEM = """You grade retrieved legal/tax excerpts for a Dutch RAG system.

- relevant: the excerpts clearly contain information needed to answer the user's question.
- ambiguous: excerpts are on-topic but incomplete, conflicting, or missing critical details
  (e.g. year, taxpayer situation) — a different retrieval query might help.
- irrelevant: excerpts do not address the question (wrong law, wrong topic, or empty context).

Return structured output only. Be conservative: if context is empty, grade irrelevant."""


def _format_chunks_for_grader(state: AgentState) -> str:
    lines: list[str] = []
    for i, ch in enumerate(state.retrieved_chunks, start=1):
        label = ch.metadata.citation_label()
        lines.append(f"--- Chunk {i} | id={ch.chunk_id} | {label} ---\n{ch.text}\n")
    if not lines:
        return "(no chunks retrieved)"
    return "\n".join(lines)


def run_grade(state: AgentState) -> dict[str, Any]:
    """LLM: classify retrieval quality for the original question."""
    if not state.retrieved_chunks:
        return {
            "grade": "irrelevant",
            "grade_reasoning": "No chunks were retrieved for grading.",
            "missing_info": None,
        }

    llm = structured_llm(GradeResult, temperature=0.0)
    ctx = _format_chunks_for_grader(state)
    human = (
        f"User question:\n{state.original_question}\n\nRetrieved context:\n{ctx}\n\n"
        "Grade the context with respect to the question."
    )
    messages = [SystemMessage(content=_GRADE_SYSTEM), HumanMessage(content=human)]
    result: GradeResult = llm.invoke(messages)
    return {
        "grade": result.grade,
        "grade_reasoning": result.reasoning,
        "missing_info": result.missing_info,
    }
