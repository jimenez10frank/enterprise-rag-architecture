"""API tests with stubbed agent and embeddings — no live Qdrant/OpenAI in CRUD paths."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.agent.state import Answer, Citation, CitedClaim
from src.api.main import AppDeps, create_app
from src.ops.cache import SemanticCache


def _answered() -> Answer:
    return Answer(
        claims=[
            CitedClaim(
                claim="testantwoord",
                citations=[Citation(chunk_id="c1", artikel="1", lid=1, quote="citaat")],
            ),
        ],
        confidence="high",
    )


def _make_deps_factory(graph_invoke: MagicMock) -> Callable[[], AppDeps]:
    def _factory() -> AppDeps:
        cache = SemanticCache(redis_client=None, corpus_version="api_test")
        graph = MagicMock()
        graph.invoke = graph_invoke
        return AppDeps(
            bm25_index=MagicMock(),
            qdrant=MagicMock(),
            cache=cache,
            graph=graph,
        )

    return _factory


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    invoke_mock = MagicMock()
    invoke_mock.side_effect = lambda state: {
        "final_answer": _answered(),
        "retrieved_chunks": [],
    }

    monkeypatch.setattr(
        "src.api.main.embed_query",
        lambda _q: [1.0, 0.0, 0.0],
    )

    application = create_app(deps_factory=_make_deps_factory(invoke_mock))
    with TestClient(application) as test_client:
        yield test_client


def test_query_requires_role_header(client: TestClient) -> None:
    response = client.post("/query", json={"question": "Wat is aftrek?"})
    assert response.status_code == 400


def test_query_returns_answer_and_miss_header(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={"question": "Wat is aftrek?"},
        headers={"X-User-Role": "public"},
    )
    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["answer"]["claims"][0]["claim"] == "testantwoord"
    assert response.headers.get("X-Cache") == "MISS"
    assert "X-Process-Time-Ms" in response.headers


def test_query_semantic_cache_hit_second_request(client: TestClient) -> None:
    headers = {"X-User-Role": "public"}
    r1 = client.post("/query", json={"question": "zelfde cached vraag"}, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/query", json={"question": "zelfde cached vraag"}, headers=headers)
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT"
