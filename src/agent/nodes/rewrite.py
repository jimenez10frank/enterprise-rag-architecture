"""Query rewrite node: one corrective retrieval attempt for ambiguous grades."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.llm_factory import structured_llm
from src.agent.state import AgentState, DecompositionResult

_REWRITE_SYSTEM = """You rewrite Dutch tax/legal questions for vector and BM25 retrieval.
The prior retrieval pass was ambiguous — improve the query using the grader's reasoning.
Produce one or more focused sub-questions. Do not answer the legal question."""


def run_rewrite(state: AgentState) -> dict[str, object]:
    """LLM: emit refined sub-questions and bump retry_count (single allowed retry)."""
    llm = structured_llm(DecompositionResult, temperature=0.0)
    prior_qs = state.decomposed_questions or [state.original_question]
    human = (
        f"Original question:\n{state.original_question}\n\n"
        f"Prior retrieval queries:\n{prior_qs}\n\n"
        f"Grader reasoning:\n{state.grade_reasoning or ''}\n\n"
        f"Missing info note:\n{state.missing_info or ''}\n\n"
        "Provide improved retrieval queries."
    )
    messages = [SystemMessage(content=_REWRITE_SYSTEM), HumanMessage(content=human)]
    result: DecompositionResult = llm.invoke(messages)
    return {
        "decomposed_questions": result.questions,
        "retry_count": state.retry_count + 1,
    }
