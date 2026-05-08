# 013 — Semantic cache: Redis LIST buckets + linear scan (demo)

## Context

Phase 5.1 requires a role-keyed semantic cache at ≥0.97 cosine similarity with corpus versioning and TTL. Redis Stack supports RediSearch vector KNN; plain Redis does not.

## Decision

Implement buckets `semantic_cache:{role_hash}:{corpus_version}` as Redis LISTs of JSON records `{embedding, answer, normalized_question}`. On read, scan the bucket and take the best cosine similarity.

## Consequences

- **Pros:** Works on any Redis deployment (no module-specific index setup); trivial to debug; `docs/project/TRAPS.md` TRAP 5 allows manual cosine for the demo.
- **Cons:** O(n) per bucket — replace with RediSearch KNN when buckets grow beyond hundreds of entries per role.

## Status

Accepted (2026-05-08).
