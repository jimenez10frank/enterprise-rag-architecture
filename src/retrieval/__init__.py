"""End-to-end retrieval pipeline: BM25 + dense → RRF → rerank.

Orchestrates the full retrieval chain that feeds the CRAG agent:

  1. BM25 search (top-50, role-filtered) — catches exact statute/ECLI matches.
  2. Dense search (top-50, RBAC pre-filter in Qdrant) — catches semantic matches.
  3. RRF fusion with k=60 — produces a combined top-50. Never alpha-weighted.
  4. Cohere cross-encoder reranks top-50 → top-8 for LLM context.

RBAC is enforced at two complementary stages:
  - Dense: Qdrant pre-filter (server-side, before HNSW traversal — TRAP 2).
  - BM25: role-filtered before scoring (safe because BM25 scores are local).

The function in this module is the single entry point used by the LangGraph
retrieval node. It accepts explicit parameters rather than reading from global
state so that tests can inject mocks and the agent can pass per-request roles.

See docs/concepts/ for deep dives on each component.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

    from src.ingestion.schema import Chunk
    from src.retrieval.bm25 import BM25Index

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    user_roles: list[str],
    bm25_index: BM25Index,
    qdrant_client: QdrantClient,
    *,
    retrieval_top_k: int = 50,
    reranker_top_k: int = 8,
    skip_rerank: bool = False,
) -> list[Chunk]:
    """Retrieve the most relevant chunks for a query, respecting RBAC.

    Args:
        query: The user's question (natural language Dutch).
        user_roles: Roles held by the querying user (e.g. ['public']).
        bm25_index: Pre-built BM25 index over the corpus.
        qdrant_client: Connected Qdrant client.
        retrieval_top_k: Number of candidates per retriever (default 50).
        reranker_top_k: Final number of chunks to pass to the LLM (default 8).
        skip_rerank: If True, return RRF top-K without calling Cohere.
                     Useful in tests / offline mode.

    Returns:
        Top-K Chunk objects, sorted by descending relevance.
    """
    # Lazy imports so that importing this package doesn't trigger Settings()
    # instantiation at module load time (which requires API keys in .env).
    # Chunk is only referenced in deferred annotations; keep it in TYPE_CHECKING.
    from src.retrieval.dense import dense_search, embed_query  # noqa: PLC0415
    from src.retrieval.fusion import rrf_from_scored  # noqa: PLC0415
    from src.retrieval.rerank import rerank_chunks  # noqa: PLC0415

    t0 = time.perf_counter()

    # --- 1. BM25 sparse retrieval (role-filtered before scoring) ---
    bm25_results = bm25_index.search(query, user_roles, top_k=retrieval_top_k)
    t_bm25 = time.perf_counter()

    # --- 2. Dense retrieval (RBAC pre-filter in Qdrant, before HNSW) ---
    query_vector = embed_query(query)
    dense_results = dense_search(
        client=qdrant_client,
        query_vector=query_vector,
        user_roles=user_roles,
        top_k=retrieval_top_k,
    )
    t_dense = time.perf_counter()

    # --- 3. RRF fusion (k=60, using ranks not raw scores) ---
    fused = rrf_from_scored([bm25_results, dense_results])
    fused_top = fused[:retrieval_top_k]
    t_rrf = time.perf_counter()

    # Resolve chunk_ids to Chunk objects via BM25 index (in-memory lookup).
    id_to_chunk: dict[str, Chunk] = {c.chunk_id: c for c in bm25_index._chunks}  # noqa: SLF001
    candidate_chunks: list[Chunk] = []
    for chunk_id, _ in fused_top:
        chunk = id_to_chunk.get(chunk_id)
        if chunk is not None:
            candidate_chunks.append(chunk)

    if not candidate_chunks:
        logger.warning("No chunks resolved from fusion for query: %.60s", query)
        return []

    if skip_rerank:
        logger.debug(
            "BM25 %.3fs | Dense %.3fs | RRF %.3fs | (rerank skipped)",
            t_bm25 - t0,
            t_dense - t_bm25,
            t_rrf - t_dense,
        )
        return candidate_chunks[:reranker_top_k]

    # --- 4. Cross-encoder rerank (Cohere) ---
    final = rerank_chunks(query, candidate_chunks, top_k=reranker_top_k)
    t_end = time.perf_counter()

    logger.info(
        "retrieve() | BM25 %.3fs | Dense %.3fs | RRF %.3fs | Rerank %.3fs | total %.3fs",
        t_bm25 - t0,
        t_dense - t_bm25,
        t_rrf - t_dense,
        t_end - t_rrf,
        t_end - t0,
    )
    return final
