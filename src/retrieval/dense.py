"""Dense retriever with RBAC pre-filter.

Queries Qdrant with an RBAC pre-filter that runs BEFORE the HNSW graph
is traversed. Classified chunks are never visited during search — they
cannot influence rankings, and their existence cannot be inferred from
result gaps.

This is the mathematically safe RBAC placement. See TRAPS.md TRAP 2 and
docs/concepts/08-rbac-pre-filter.md for the full reasoning.

NEVER move the filter to a post-retrieval Python step:
  - Post-retrieval: classified chunks compete in HNSW → existence leaks via gaps.
  - LLM-level: classified text is in the context window → side-channel exposure.
  - Pre-filter (this module): classified vectors are not visited → zero leakage.
"""

from __future__ import annotations

import logging

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, QueryResponse, ScoredPoint

from src.config import settings
from src.ingestion.schema import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


def embed_query(query: str) -> list[float]:
    """Embed a single query string with the configured model.

    Using the same model as ingestion is non-negotiable: vectors from
    different models are not comparable. See docs/concepts/01-vectors-and-embeddings.md.
    """
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=[query],
        dimensions=settings.embedding_dimensions,
    )
    # Avoid cast() — OpenAI stubs differ across environments (redundant-cast vs no-any-return).
    emb = response.data[0].embedding
    return [float(x) for x in emb]


def _scored_point_to_chunk(hit: ScoredPoint) -> Chunk | None:
    """Reconstruct a Chunk from a Qdrant ScoredPoint payload."""
    if hit.payload is None:
        return None
    try:
        chunk_id = str(hit.payload["chunk_id"])
        meta = ChunkMetadata.model_validate(hit.payload)
        # Dense search doesn't return the original text — use a placeholder.
        # The full text is available if with_payload=True and text was stored.
        text = str(hit.payload.get("text", ""))
        return Chunk(chunk_id=chunk_id, text=text, metadata=meta)
    except Exception as exc:
        logger.warning("Failed to reconstruct chunk from payload: %s", exc)
        return None


def dense_search(
    client: QdrantClient,
    query_vector: list[float],
    user_roles: list[str],
    top_k: int = 50,
    search_params: object = None,
) -> list[tuple[str, float]]:
    """Search Qdrant with RBAC pre-filter and return (chunk_id, score) pairs.

    The FieldCondition on allowed_roles runs INSIDE the Qdrant server,
    before the HNSW graph traversal begins. This is a server-side guarantee,
    not a client-side Python filter applied after the fact.

    Args:
        client: Qdrant client instance.
        query_vector: Embedded query (must match the collection's vector size).
        user_roles: Roles held by the querying user.
        top_k: Number of results to return (should be 50 per STACK.md).
        search_params: Optional SearchParams (e.g. with quantization rescoring).

    Returns:
        List of (chunk_id, cosine_score) tuples, descending by score.
    """
    from qdrant_client.models import SearchParams as QdrantSearchParams

    rbac_filter = Filter(
        must=[
            FieldCondition(
                key="allowed_roles",
                match=MatchAny(any=user_roles),
            )
        ]
    )

    if isinstance(search_params, QdrantSearchParams):
        response: QueryResponse = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=rbac_filter,
            limit=top_k,
            with_payload=True,
            search_params=search_params,
        )
    else:
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=rbac_filter,
            limit=top_k,
            with_payload=True,
        )

    output: list[tuple[str, float]] = []
    for hit in response.points:
        payload = hit.payload or {}
        chunk_id = str(payload.get("chunk_id", str(hit.id)))
        output.append((chunk_id, float(hit.score)))

    return output
