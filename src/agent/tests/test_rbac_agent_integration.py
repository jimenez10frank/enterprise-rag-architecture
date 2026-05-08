"""Agent + RBAC integration (Phase 5.2): no FIOD leakage via empty retrieval.

When the only corpus match is FIOD-classified, helpdesk RBAC pre-filters exclude
it at BM25 and Qdrant stages (TRAP 2). The grader sees an empty context,
grades ``irrelevant``, and we escalate — never attributing classified content.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from src.agent.graph import AgentNodeOverrides, build_agent_graph
from src.agent.state import AgentState
from src.config import settings
from src.ingestion.schema import Chunk, ChunkMetadata
from src.retrieval.bm25 import BM25Index

_COLLECTION = "legal_docs_agent_rbac_test"
_DIM = 8
_UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _qdrant_available() -> bool:
    try:
        c = QdrantClient(url="http://localhost:6333", timeout=2)
        c.get_collections()
        return True
    except Exception:
        return False


skip_if_no_qdrant = pytest.mark.skipif(
    not _qdrant_available(),
    reason="Qdrant not reachable at localhost:6333",
)


def _fake_vector(seed: int, dim: int = _DIM) -> list[float]:
    import math

    return [math.sin(seed * i + 1) for i in range(dim)]


def _only_fiod_chunk() -> Chunk:
    meta = ChunkMetadata(
        doc_id="AGENT_RBAC_doc",
        wet="Test Wet",
        classification="fiod",
        allowed_roles=["fiod"],
        source_file="secret.html",
        artikel="99",
        lid=1,
    )
    return Chunk(
        chunk_id="agent_rbac_fiod_only",
        text="geheime fiod staatsgeheim alphaone regeling",
        metadata=meta,
    )


def _stub_decompose(state: AgentState) -> dict[str, Any]:
    return {"decomposed_questions": [state.original_question]}


@pytest.fixture
def agent_rbac_qdrant(monkeypatch: pytest.MonkeyPatch) -> Generator[QdrantClient, None, None]:
    """Isolated collection with a single FIOD vector; patches settings + embed_query."""
    if not _qdrant_available():
        pytest.skip("Qdrant not available")

    monkeypatch.setattr(settings, "qdrant_collection", _COLLECTION)
    monkeypatch.setattr(settings, "embedding_dimensions", _DIM)

    v = _fake_vector(7)

    def _fixed_embed(_q: str) -> list[float]:
        return v

    monkeypatch.setattr("src.retrieval.dense.embed_query", _fixed_embed)

    client = QdrantClient(url="http://localhost:6333")
    if client.collection_exists(_COLLECTION):
        client.delete_collection(_COLLECTION)

    client.create_collection(
        collection_name=_COLLECTION,
        vectors_config=VectorParams(size=_DIM, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=_COLLECTION,
        field_name="allowed_roles",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    ch = _only_fiod_chunk()
    payload = {"chunk_id": ch.chunk_id, "text": ch.text, **ch.metadata.model_dump(mode="json")}
    client.upsert(
        collection_name=_COLLECTION,
        points=[
            PointStruct(
                id=str(uuid.uuid5(_UUID_NS, ch.chunk_id)),
                vector=v,
                payload=payload,
            ),
        ],
    )

    yield client

    client.delete_collection(_COLLECTION)


@skip_if_no_qdrant
def test_helpdesk_escalates_when_only_match_is_fiod(
    agent_rbac_qdrant: QdrantClient,
) -> None:
    """FIOD-only chunk is invisible to helpdesk; agent must not cite it."""
    chunk = _only_fiod_chunk()
    bm25 = BM25Index([chunk])
    graph = build_agent_graph(
        bm25,
        agent_rbac_qdrant,
        skip_rerank=True,
        node_overrides=AgentNodeOverrides(decompose=_stub_decompose),
    )

    state = AgentState(
        original_question="Wat zegt de regeling over staatsgeheim alphaone?",
        user_roles=["helpdesk"],
    )
    out = graph.invoke(state)

    assert out["retrieved_chunks"] == []
    assert out["grade"] == "irrelevant"
    fa = out["final_answer"]
    assert fa is not None
    assert fa.unanswerable is True
