"""Query decomposition: split multi-part Dutch tax/legal questions into sub-queries."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.llm_factory import structured_llm
from src.agent.state import AgentState, DecompositionResult

_DECOMPOSE_SYSTEM = """You are a query analyzer for a Dutch tax and legal RAG system.
If the user's question has multiple distinct parts (different topics, years, or legal tests),
split it into separate sub-questions that can be retrieved independently.
If the question is already atomic, return a list with exactly one string (the same question,
optionally clarified slightly without changing legal meaning).
Output only structured data; never answer the substantive legal question."""


def run_decompose(state: AgentState) -> dict[str, object]:
    """LLM: produce one or more retrieval queries from the original question."""
    llm = structured_llm(DecompositionResult, temperature=0.0)
    messages = [
        SystemMessage(content=_DECOMPOSE_SYSTEM),
        HumanMessage(content=state.original_question),
    ]
    result: DecompositionResult = llm.invoke(messages)
    return {"decomposed_questions": result.questions}
