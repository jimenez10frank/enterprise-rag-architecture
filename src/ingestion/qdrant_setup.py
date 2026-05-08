"""Qdrant collection setup and search parameter helpers.

Creates the collection with the HNSW and quantization parameters committed
in docs/project/STACK.md. Idempotent: safe to call on an already-existing collection.

Production parameters (and why):
  m=32            Higher recall for legal domain (vs generic m=16). Legal
                  queries need precision; the extra memory cost is worth it.
  ef_construct=256 Build-time quality/speed tradeoff. 400 gives marginally
                   better quality but triples build time. 256 is the sweet spot.
  scalar int8     4× memory reduction (~234 GB → ~58 GB at 20M vectors).
                  ~2-3% recall hit recovered by rescoring.
  always_ram=True Vectors must stay in RAM to hit sub-100ms latency.
  rescore=True    Re-score top candidates with full float32 after int8 ANN.
  oversampling=2.0 Fetch 2× candidates for rescoring, then trim to limit.

See docs/concepts/02-hnsw.md and docs/concepts/03-quantization.md.
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    PayloadSchemaType,
    QuantizationSearchParams,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    SearchParams,
    VectorParams,
)

from src.config import settings

logger = logging.getLogger(__name__)

# Fields that are queried as filters — indexed for sub-millisecond predicate eval.
# RBAC depends on allowed_roles being indexed; without it Qdrant does a full scan.
_PAYLOAD_INDEXES: list[tuple[str, PayloadSchemaType]] = [
    ("classification", PayloadSchemaType.KEYWORD),
    ("allowed_roles", PayloadSchemaType.KEYWORD),
    ("wet", PayloadSchemaType.KEYWORD),
    ("effective_date", PayloadSchemaType.DATETIME),
]


def create_collection(client: QdrantClient, *, recreate: bool = False) -> None:
    """Create the Qdrant collection with committed production parameters.

    Args:
        client: Qdrant client instance.
        recreate: If True, drop and recreate an existing collection.
                  Use only in development / test teardown — never in production.
    """
    collection_name = settings.qdrant_collection

    if recreate and client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        logger.info("Deleted collection '%s' for recreation.", collection_name)

    if client.collection_exists(collection_name):
        logger.info("Collection '%s' already exists — skipping creation.", collection_name)
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.embedding_dimensions,
            distance=Distance.COSINE,
        ),
        hnsw_config=HnswConfigDiff(
            m=32,
            ef_construct=256,
        ),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(
                type=ScalarType.INT8,
                quantile=0.99,
                always_ram=True,
            )
        ),
    )
    logger.info("Created collection '%s'.", collection_name)

    for field_name, schema_type in _PAYLOAD_INDEXES:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=schema_type,
        )
        logger.info("Created payload index on '%s'.", field_name)


def get_search_params() -> SearchParams:
    """Search parameters that enable quantization rescoring.

    oversampling=2.0: fetch 2× the requested limit via int8 ANN, then
    re-score with full float32 precision. Recovers the ~2-3% recall hit
    from scalar quantization at the cost of 2× distance computations in
    the rescore pass (which is fast — just float multiplications, no graph
    traversal).
    """
    return SearchParams(
        quantization=QuantizationSearchParams(
            ignore=False,
            rescore=True,
            oversampling=2.0,
        )
    )
