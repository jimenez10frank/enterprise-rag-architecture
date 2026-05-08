"""LangGraph CRAG wiring: decompose → retrieve → grade → generate | rewrite | escalate."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agent.nodes.decompose import run_decompose
from src.agent.nodes.escalate import run_escalate
from src.agent.nodes.generate import run_generate
from src.agent.nodes.grade import run_grade
from src.agent.nodes.retrieve import make_retrieve_node
from src.agent.nodes.rewrite import run_rewrite
from src.agent.state import AgentState

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

    from src.retrieval.bm25 import BM25Index


@dataclass(frozen=True)
class AgentNodeOverrides:
    """Optional callable replacements for tests (same signatures as production nodes)."""

    decompose: Callable[[AgentState], dict[str, Any]] | None = None
    retrieve: Callable[[AgentState], dict[str, Any]] | None = None
    grade: Callable[[AgentState], dict[str, Any]] | None = None
    rewrite: Callable[[AgentState], dict[str, Any]] | None = None
    escalate: Callable[[AgentState], dict[str, Any]] | None = None
    generate: Callable[[AgentState], dict[str, Any]] | None = None


def _as_node_runnable(fn: Callable[[AgentState], dict[str, Any]]) -> Runnable[AgentState, Any]:
    """LangGraph runs plain callables; type stubs only list Runnable/_Node for `add_node`."""
    return cast(Runnable[AgentState, Any], fn)


def route_after_grade(state: AgentState) -> str:
    """Conditional router: single rewrite attempt for ambiguous (TRAPS.md TRAP 7)."""
    g = state.grade
    if g == "relevant":
        return "generate"
    if g == "irrelevant":
        return "escalate"
    if g == "ambiguous":
        if state.retry_count < 1:
            return "rewrite"
        return "escalate"
    return "escalate"


def build_agent_graph(
    bm25_index: BM25Index,
    qdrant_client: QdrantClient,
    *,
    skip_rerank: bool = False,
    node_overrides: AgentNodeOverrides | None = None,
) -> CompiledStateGraph[AgentState, Any, AgentState, AgentState]:
    """Compile the CRAG graph. Use `node_overrides` in unit tests to stub LLM nodes."""
    ov = node_overrides or AgentNodeOverrides()
    retrieve_node = ov.retrieve or make_retrieve_node(
        bm25_index,
        qdrant_client,
        skip_rerank=skip_rerank,
    )

    graph = StateGraph(AgentState)
    graph.add_node("decompose", _as_node_runnable(ov.decompose or run_decompose))
    graph.add_node("retrieve", _as_node_runnable(retrieve_node))
    graph.add_node("grade", _as_node_runnable(ov.grade or run_grade))
    graph.add_node("rewrite", _as_node_runnable(ov.rewrite or run_rewrite))
    graph.add_node("escalate", _as_node_runnable(ov.escalate or run_escalate))
    graph.add_node("generate", _as_node_runnable(ov.generate or run_generate))

    graph.add_edge(START, "decompose")
    graph.add_edge("decompose", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges(
        "grade",
        route_after_grade,
        {
            "generate": "generate",
            "rewrite": "rewrite",
            "escalate": "escalate",
        },
    )
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)
    graph.add_edge("escalate", END)

    return graph.compile()
