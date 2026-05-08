"""Retrieval node: hybrid retrieve per sub-question, deduplicate chunks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from src.agent.state import AgentState
from src.ingestion.schema import Chunk

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

    from src.retrieval.bm25 import BM25Index


def make_retrieve_node(
    bm25_index: BM25Index,
    qdrant_client: QdrantClient,
    *,
    skip_rerank: bool = False,
) -> Callable[[AgentState], dict[str, Any]]:
    """Close over RBAC-aware retrieval dependencies (Phase 3 `retrieve`)."""

    def retrieve_node(state: AgentState) -> dict[str, Any]:
        from src.retrieval import retrieve

        qs = state.decomposed_questions
        if not qs:
            qs = [state.original_question]

        seen: set[str] = set()
        merged: list[Chunk] = []
        for q in qs:
            chunks = retrieve(
                q,
                state.user_roles,
                bm25_index,
                qdrant_client,
                skip_rerank=skip_rerank,
            )
            for c in chunks:
                if c.chunk_id not in seen:
                    seen.add(c.chunk_id)
                    merged.append(c)
        return {"retrieved_chunks": merged}

    return retrieve_node
