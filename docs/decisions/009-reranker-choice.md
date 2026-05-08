# 009. Cohere reranker (demo) vs self-hosted cross-encoder (production)

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 3

## Context

The assessment wants **high precision** after hybrid retrieval. Bi-encoders (embeddings) alone are weaker at fine-grained relevance than **cross-encoders**, but cross-encoders are **slow** — so we **retrieve broadly** and **rerank aggressively** (`TRAPS.md` TRAP 8).

## Options considered

### Option A: No reranker

- **Cons:** Violates precision target; wastes top-K headroom.

### Option B: Cohere `rerank-multilingual-v3.0` for demo

- **Pros:** Strong Dutch; simple API; matches `STACK.md`.
- **Cons:** Classified text must not leave perimeter in production.

### Option C: Self-hosted `BAAI/bge-reranker-v2-m3` in production

- **Pros:** Data residency; predictable cost at scale.

## Decision

**Demo:** **Option B** (`src/retrieval/rerank.py`).
**Production design:** **Option C** (documented in Phase 6 doc; not required in repo code).

Pipeline numbers: **top-50 per retriever → RRF top-50 → rerank to top-8** for the LLM.

## Consequences

**What this makes easy:** Clear story on `skip_rerank` for offline/CI paths.

**What this makes hard:** API rate limits — document throughput limits in design doc.

## References

- `TRAPS.md` TRAP 8
- `STACK.md` (Reranking)
- `src/retrieval/rerank.py`, `src/retrieval/__init__.py`
