"""Cross-encoder reranker (Cohere rerank-multilingual-v3.0).

Takes the fused top-50 from RRF and reranks to top-8 using a cross-encoder
that sees (query, document) pairs jointly. Cross-encoders capture fine-grained
relevance that bi-encoder similarity scores miss — critical for Dutch legal text
where user vocabulary diverges from statute vocabulary.

Pipeline position (TRAP 8):
  Dense top-50 + BM25 top-50 → RRF top-50 → Reranker top-8 → LLM

Retrieve generously (recall), rerank aggressively (precision). The reranker
is the precision filter; the retrievers are the recall filters. If you only
retrieve top-5 and rerank to top-5 you cannot promote a relevant chunk that
landed at rank 23 in the initial retrieval.

Production note: replace with self-hosted BAAI/bge-reranker-v2-m3 for any
classified content — sending classified document text to Cohere's API is a
data residency violation. See docs/project/TRAPS.md TRAP 10 (same reasoning applies).

See docs/concepts/06-reranking.md.
"""

from __future__ import annotations

import logging

import cohere

from src.config import settings
from src.ingestion.schema import Chunk

logger = logging.getLogger(__name__)


def rerank_chunks(
    query: str,
    chunks: list[Chunk],
    top_k: int | None = None,
) -> list[Chunk]:
    """Rerank a list of chunks by cross-encoder relevance to the query.

    Args:
        query: The user's original question.
        chunks: Candidate chunks from RRF fusion (should be ~50).
        top_k: Number of results to return. Defaults to settings.reranker_top_k (8).

    Returns:
        Top-K chunks, sorted by descending relevance score.
    """
    if not chunks:
        return []

    effective_top_k = top_k if top_k is not None else settings.reranker_top_k
    effective_top_k = min(effective_top_k, len(chunks))

    client = cohere.Client(api_key=settings.cohere_api_key)
    documents = [c.text for c in chunks]

    response = client.rerank(
        model=settings.reranker_model,
        query=query,
        documents=documents,
        top_n=effective_top_k,
    )

    reranked: list[Chunk] = []
    for result in response.results:
        reranked.append(chunks[result.index])

    logger.debug(
        "Reranked %d → %d chunks for query: %.60s...",
        len(chunks),
        len(reranked),
        query,
    )
    return reranked
