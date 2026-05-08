"""Semantic query cache backed by Redis (docs/project/TRAPS.md TRAP 5).

We bucket entries by ``(role_hash, corpus_version)`` so helpdesk users never
reuse answers computed for FIOD-only contexts, and corpus bumps invalidate
prior snapshots cheaply.

Redis layout (demo scale): each bucket is a LIST of JSON objects
``{embedding, answer, normalized_question}``. Lookups scan the bucket and pick
the best cosine similarity. Redis Stack KNN (RediSearch + vector field) is the
production upgrade when buckets grow large; at dozens of entries per role the
linear scan is negligible and avoids module-specific index setup in dev.

Threshold default is 0.97 — see ``settings.semantic_cache_threshold``.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import redis

from src.agent.state import Answer
from src.config import settings


def normalize_question(text: str) -> str:
    """Stable surface form for logging; retrieval matching uses embeddings only."""
    return " ".join(text.strip().lower().split())


def compute_role_hash(user_roles: list[str]) -> str:
    """Deterministic short id from sorted roles (order of header list must not matter)."""
    key = ",".join(sorted({r.strip().lower() for r in user_roles if r.strip()}))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        msg = "Embeddings must have the same dimensionality"
        raise ValueError(msg)
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _bucket_key(role_hash: str, corpus_version: str) -> str:
    return f"semantic_cache:{role_hash}:{corpus_version}"


class SemanticCache:
    """Role- and corpus-scoped semantic cache with optional Redis persistence."""

    def __init__(
        self,
        redis_client: redis.Redis[str] | None = None,
        *,
        corpus_version: str | None = None,
        threshold: float | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self._redis = redis_client
        self._memory: dict[str, list[dict[str, Any]]] | None = {} if redis_client is None else None
        self._corpus_version = (
            corpus_version if corpus_version is not None else settings.corpus_version
        )
        self._threshold = settings.semantic_cache_threshold if threshold is None else threshold
        self._ttl = settings.semantic_cache_ttl_seconds if ttl_seconds is None else ttl_seconds
        if self._threshold < 0.97:
            msg = "semantic_cache_threshold must be >= 0.97 for legal/fiscal data"
            raise ValueError(msg)

    def _key_for_roles(self, user_roles: list[str]) -> str:
        return _bucket_key(compute_role_hash(user_roles), self._corpus_version)

    def get_match(
        self,
        query_embedding: list[float],
        user_roles: list[str],
    ) -> Answer | None:
        """Return a cached answer if the best same-bucket embedding >= threshold."""
        key = self._key_for_roles(user_roles)
        records: list[dict[str, Any]]
        if self._memory is not None:
            records = list(self._memory.get(key, []))
        else:
            assert self._redis is not None
            raw_list = self._redis.lrange(key, 0, -1)
            records = [json.loads(x) for x in raw_list]

        best_sim = -1.0
        best_answer: dict[str, Any] | None = None
        for rec in records:
            sim = _cosine_similarity(query_embedding, rec["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_answer = rec["answer"]
        if best_sim >= self._threshold and best_answer is not None:
            return Answer.model_validate(best_answer)
        return None

    def store(
        self,
        query_embedding: list[float],
        user_roles: list[str],
        normalized_question: str,
        answer: Answer,
    ) -> None:
        """Persist a query/answer pair under the caller's role bucket."""
        key = self._key_for_roles(user_roles)
        payload = {
            "embedding": query_embedding,
            "normalized_question": normalized_question,
            "answer": answer.model_dump(mode="json"),
        }
        if self._memory is not None:
            self._memory.setdefault(key, []).append(payload)
            return
        assert self._redis is not None
        pipe = self._redis.pipeline()
        pipe.lpush(key, json.dumps(payload))
        pipe.expire(key, self._ttl)
        pipe.execute()
