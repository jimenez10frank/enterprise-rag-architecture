"""Tests for ``SemanticCache`` (TRAP 5 — 0.97 threshold, RBAC-keyed buckets)."""

from __future__ import annotations

import math
import os

import pytest
import redis

from src.agent.state import Answer, Citation, CitedClaim
from src.ops.cache import SemanticCache, _cosine_similarity, compute_role_hash, normalize_question


def test_normalize_question_collapses_whitespace() -> None:
    assert normalize_question("  Hello   World  ") == "hello world"


def test_compute_role_hash_order_invariant() -> None:
    assert compute_role_hash(["helpdesk", "public"]) == compute_role_hash(["public", "helpdesk"])


def test_cosine_known_pair() -> None:
    a = [1.0, 0.0]
    b = [0.94, math.sqrt(1.0 - 0.94**2)]
    assert abs(_cosine_similarity(a, b) - 0.94) < 1e-9


def test_cache_rejects_sub_097_threshold() -> None:
    with pytest.raises(ValueError, match="0.97"):
        SemanticCache(redis_client=None, threshold=0.90)


def test_cache_hit_same_embedding_same_roles() -> None:
    cache = SemanticCache(redis_client=None, corpus_version="vtest")
    emb = [1.0, 0.0, 0.0]
    answer = Answer(
        claims=[
            CitedClaim(
                claim="test",
                citations=[
                    Citation(chunk_id="x", artikel="1", lid=1, quote="foo"),
                ],
            ),
        ],
        confidence="high",
    )
    cache.store(emb, ["helpdesk"], "wat is aftrek", answer)
    got = cache.get_match(emb, ["helpdesk"])
    assert got is not None
    assert got.claims[0].claim == "test"


def test_near_miss_below_097_is_miss() -> None:
    cache = SemanticCache(redis_client=None, corpus_version="vtest")
    e1 = [1.0, 0.0]
    e2 = [0.94, math.sqrt(1.0 - 0.94**2)]
    answer = Answer(
        claims=[
            CitedClaim(
                claim="cached",
                citations=[Citation(chunk_id="x", artikel="1", quote="q")],
            ),
        ],
    )
    cache.store(e1, ["helpdesk"], "box 1 2024", answer)
    assert cache.get_match(e2, ["helpdesk"]) is None


def test_role_isolation_identical_embedding() -> None:
    cache = SemanticCache(redis_client=None, corpus_version="vtest")
    emb = [0.0, 1.0, 0.0]
    answer = Answer(
        claims=[
            CitedClaim(
                claim="secret",
                citations=[Citation(chunk_id="x", artikel="1", quote="q")],
            ),
        ],
    )
    cache.store(emb, ["fiod"], "zelfde vraag", answer)
    assert cache.get_match(emb, ["helpdesk"]) is None


def test_corpus_version_bump_invalidates() -> None:
    emb = [1.0, 1.0, 0.0]
    answer = Answer(
        claims=[
            CitedClaim(
                claim="v1",
                citations=[Citation(chunk_id="x", artikel="1", quote="q")],
            ),
        ],
    )
    c1 = SemanticCache(redis_client=None, corpus_version="v1")
    c1.store(emb, ["public"], "q", answer)
    c2 = SemanticCache(redis_client=None, corpus_version="v2")
    assert c2.get_match(emb, ["public"]) is None


@pytest.mark.skipif(
    not os.environ.get("INTEGRATION_REDIS"),
    reason="Set INTEGRATION_REDIS=1 and run Redis locally for this test",
)
def test_redis_roundtrip() -> None:
    client = redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )
    client.flushdb()
    cache = SemanticCache(
        redis_client=client,
        corpus_version="redis_roundtrip",
        ttl_seconds=3600,
    )
    emb = [1.0, 0.0, 0.0, 0.0]
    answer = Answer(
        claims=[
            CitedClaim(
                claim="redis",
                citations=[Citation(chunk_id="c", artikel="9", quote="rq")],
            ),
        ],
    )
    cache.store(emb, ["public"], "foo", answer)
    got = cache.get_match(emb, ["public"])
    assert got is not None
    assert got.claims[0].claim == "redis"
    client.flushdb()
