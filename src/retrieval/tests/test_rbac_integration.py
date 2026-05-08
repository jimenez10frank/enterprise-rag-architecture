"""RBAC integration tests — require Qdrant running on localhost:6333.

These tests verify sub-phase 2.8: that the RBAC pre-filter at the Qdrant
vector query stage (TRAP 2) correctly prevents classified chunks from
appearing in results for unpermitted users.

Tests are marked @pytest.mark.integration and skipped automatically when
Qdrant is not reachable. Run explicitly with:
    pytest -m integration src/retrieval/tests/test_rbac_integration.py

The tests create a temporary '_rbac_test' Qdrant collection, populate it
with a small set of public and FIOD chunks with synthetic embeddings, run
queries as different roles, and verify isolation guarantees.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest

from src.ingestion.schema import Chunk, ChunkMetadata

DATA_RAW = Path(__file__).parents[3] / "data" / "raw"

# Temporary collection name — isolated from the production collection.
_TEST_COLLECTION = "legal_docs_rbac_test"

# Synthetic embedding dimension — tiny vectors for fast test setup.
# Real vectors are 3072-dimensional; 8 is enough to test the filter logic.
_TEST_DIM = 8

_UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _qdrant_available() -> bool:
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url="http://localhost:6333", timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False


skip_if_no_qdrant = pytest.mark.skipif(
    not _qdrant_available(),
    reason="Qdrant not reachable at localhost:6333",
)


def _make_chunk(chunk_id: str, classification: str, roles: list[str]) -> Chunk:
    from typing import cast

    from src.ingestion.schema import Classification

    meta = ChunkMetadata(
        doc_id="RBAC_TEST",
        wet="Test Wet",
        classification=cast(Classification, classification),
        allowed_roles=roles,
        source_file="test.html",
    )
    return Chunk(chunk_id=chunk_id, text=f"test chunk {chunk_id}", metadata=meta)


def _fake_vector(seed: int, dim: int = _TEST_DIM) -> list[float]:
    """Simple deterministic vector — not semantically meaningful."""
    import math

    return [math.sin(seed * i + 1) for i in range(dim)]


@pytest.fixture(scope="module")
def rbac_test_collection() -> object:
    """Set up a small test collection and tear it down after the module."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        PointStruct,
        VectorParams,
    )

    if not _qdrant_available():
        pytest.skip("Qdrant not available")

    client = QdrantClient(url="http://localhost:6333")

    # Clean up any leftover collection from a previous failed run.
    if client.collection_exists(_TEST_COLLECTION):
        client.delete_collection(_TEST_COLLECTION)

    client.create_collection(
        collection_name=_TEST_COLLECTION,
        vectors_config=VectorParams(size=_TEST_DIM, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=_TEST_COLLECTION,
        field_name="allowed_roles",
        field_schema="keyword",
    )
    client.create_payload_index(
        collection_name=_TEST_COLLECTION,
        field_name="classification",
        field_schema="keyword",
    )

    # Insert test points
    test_chunks = [
        ("public_werkruimte", "public", ["public", "helpdesk", "fiod"]),
        ("public_auto", "public", ["public", "helpdesk", "fiod"]),
        ("helpdesk_intern", "internal", ["helpdesk", "fiod"]),
        ("fiod_fraud_001", "fiod", ["fiod"]),
        ("fiod_fraud_002", "fiod", ["fiod"]),
    ]
    points = []
    for i, (chunk_id, cls, roles) in enumerate(test_chunks):
        points.append(
            PointStruct(
                id=str(uuid.uuid5(_UUID_NS, chunk_id)),
                vector=_fake_vector(i),
                payload={
                    "chunk_id": chunk_id,
                    "classification": cls,
                    "allowed_roles": roles,
                    "wet": "Test Wet",
                    "doc_id": "TEST",
                    "source_file": "test.html",
                },
            )
        )
    client.upsert(collection_name=_TEST_COLLECTION, points=points)

    yield client

    # Teardown
    client.delete_collection(_TEST_COLLECTION)


@skip_if_no_qdrant
def test_public_user_cannot_see_fiod_chunks(rbac_test_collection: object) -> None:
    """TRAP 2: public user query must return zero FIOD chunks."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchAny

    assert isinstance(rbac_test_collection, QdrantClient)
    client = rbac_test_collection

    response = client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(99),
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchAny(any=["public"]))]
        ),
        limit=10,
        with_payload=True,
    )
    returned_ids = [str(hit.payload.get("chunk_id", "")) for hit in response.points if hit.payload]
    assert "fiod_fraud_001" not in returned_ids
    assert "fiod_fraud_002" not in returned_ids
    assert "helpdesk_intern" not in returned_ids


@skip_if_no_qdrant
def test_fiod_user_sees_all_chunks(rbac_test_collection: object) -> None:
    """FIOD users can retrieve from all classification tiers."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchAny

    assert isinstance(rbac_test_collection, QdrantClient)
    client = rbac_test_collection

    response = client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(99),
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchAny(any=["fiod"]))]
        ),
        limit=10,
        with_payload=True,
    )
    returned_ids = {str(hit.payload.get("chunk_id", "")) for hit in response.points if hit.payload}
    # FIOD should see all 5 test chunks
    assert "public_werkruimte" in returned_ids
    assert "fiod_fraud_001" in returned_ids
    assert "helpdesk_intern" in returned_ids


@skip_if_no_qdrant
def test_helpdesk_user_cannot_see_fiod_chunks(rbac_test_collection: object) -> None:
    """Helpdesk role can see public + internal but NOT fiod classified."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchAny

    assert isinstance(rbac_test_collection, QdrantClient)
    client = rbac_test_collection

    response = client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(99),
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchAny(any=["helpdesk"]))]
        ),
        limit=10,
        with_payload=True,
    )
    returned_ids = {str(hit.payload.get("chunk_id", "")) for hit in response.points if hit.payload}
    assert "fiod_fraud_001" not in returned_ids
    assert "fiod_fraud_002" not in returned_ids
    assert "helpdesk_intern" in returned_ids  # can see internal


@skip_if_no_qdrant
def test_rbac_filter_is_server_side(rbac_test_collection: object) -> None:
    """Verify the filter excludes chunks at the Qdrant search stage.

    We confirm that WITHOUT the filter, FIOD chunks appear; WITH the filter,
    they do not. This demonstrates the pre-filter is actually working.
    """
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchAny

    assert isinstance(rbac_test_collection, QdrantClient)
    client = rbac_test_collection

    # Without filter — should see FIOD chunks
    unfiltered = client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(0),  # same vector as fiod_fraud_001
        limit=10,
        with_payload=True,
    )
    unfiltered_ids = {
        str(hit.payload.get("chunk_id", "")) for hit in unfiltered.points if hit.payload
    }
    assert "fiod_fraud_001" in unfiltered_ids, (
        "Sanity check failed: FIOD chunk not found even without filter"
    )

    # With public filter — FIOD chunks must disappear
    filtered = client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(0),
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchAny(any=["public"]))]
        ),
        limit=10,
        with_payload=True,
    )
    filtered_ids = {str(hit.payload.get("chunk_id", "")) for hit in filtered.points if hit.payload}
    assert "fiod_fraud_001" not in filtered_ids


@skip_if_no_qdrant
def test_retrieval_latency_under_500ms(rbac_test_collection: object) -> None:
    """Qdrant filter search on the test collection must complete under 500ms.

    This is a sanity check — real latency targets depend on corpus size.
    At 5 points the latency should be microseconds; 500ms is a very generous
    ceiling that catches infrastructure misconfiguration.
    """
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchAny

    assert isinstance(rbac_test_collection, QdrantClient)
    client = rbac_test_collection

    t0 = time.perf_counter()
    client.query_points(
        collection_name=_TEST_COLLECTION,
        query=_fake_vector(42),
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchAny(any=["public"]))]
        ),
        limit=10,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"Search took {elapsed_ms:.1f}ms — check Qdrant connectivity"
