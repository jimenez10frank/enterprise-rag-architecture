# 10 — Semantic Cache

## What it is

A semantic cache stores previous query-answer pairs and returns a cached answer when a new query is "similar enough" to a stored one. "Similar enough" is measured by cosine similarity between the query embeddings, not string equality. This avoids re-running the entire RAG pipeline for semantically identical questions.

## Why it matters for this project

Semantic caching in a legal/fiscal system is more dangerous than in most domains. The reason: year-versioned data.

"Wat is het Box 1 tarief voor 2024?" and "Wat is het Box 1 tarief voor 2025?" embed at ~0.93-0.95 cosine similarity. A standard cache threshold (0.85 or 0.90) would serve last year's answer to this year's question. In a zero-hallucination tolerance system advising on tax obligations, that is a fiscal advice error.

This is why our threshold is **≥ 0.97**, not 0.85 or 0.90. (See TRAP 5.)

## The cache key — three components

This is the key insight: the cache key is not just the query embedding. It has three components:

```
cache_lookup_vector = query_embedding   (for similarity search)
cache_key = f"{role_hash}:{corpus_version}:{normalized_question_hash}"
```

1. **`role_hash`** — a helpdesk user must not hit a FIOD user's cached answer. The RBAC guarantee must extend into the cache. Without this, the cache is a side-channel that bypasses the pre-filter.

2. **`corpus_version`** — when new legislation is ingested (e.g., annual tax law updates), bump this version. The entire cache invalidates. Cheap insurance against stale answers after a law change.

3. **`normalized_question_hash`** — deterministic hash of the lowercased, whitespace-normalized question. Used as a secondary exact-match gate after the similarity check passes.

## Threshold justification

| Threshold | "Box 1 tarief 2024" → "Box 1 tarief 2025" similarity | Result |
|-----------|------------------------------------------------------|--------|
| 0.85 | ~0.93 > 0.85 | Cache hit — **wrong answer** |
| 0.90 | ~0.93 > 0.90 | Cache hit — **wrong answer** |
| 0.97 | ~0.93 < 0.97 | Cache miss — correct pipeline runs |

The tradeoff is cache hit rate. At 0.97, only nearly-identical questions hit the cache. This is the right tradeoff: the system is for legal/fiscal advice, not for maximizing cache efficiency.

## TTL

24-48 hours. Even if the threshold is correct and the corpus version is unchanged, tax rules have effective dates and can change on short notice. Short TTL is insurance.

## What gets stored in the cache

```python
class CacheEntry(BaseModel):
    query_embedding: list[float]      # for similarity lookup
    normalized_question: str
    answer: Answer                    # full Pydantic answer with citations
    citations: list[Citation]
    generation_timestamp: datetime
    corpus_version: str
    role_hash: str
```

## Implementation

Redis Stack with its HNSW vector index module. The vector index supports cosine similarity search on the stored query embeddings. On a cache hit, we return the stored `Answer` directly. On a miss, the full pipeline runs and the result is stored.

For the demo: a simpler implementation using a Redis sorted set with manual cosine comparison is acceptable. Document both approaches.

## How it appears in our code

TODO — see `src/cache/semantic_cache.py` once Phase 5 is implemented.

## Self-check questions

1. A FIOD user asks "tekenen van belastingfraude — top 5 indicatoren" and the answer is cached. A helpdesk user asks the same question and gets a similarity of 0.99 against that cache entry. What happens and why?
2. A new version of Wet IB 2001 is ingested on January 1, 2025. What must happen to the cache and why?
3. Why is 0.97 the right threshold for this domain even though it means fewer cache hits compared to 0.85?
