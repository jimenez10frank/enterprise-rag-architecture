# 005. Semantic cache threshold ≥ 0.97 for fiscal/legal data

**Date:** 2026-05-08
**Status:** Accepted (implementation pending Phase 5)
**Phase introduced:** 0 (`Settings` constraint); ops in 5.1

## Context

FAQ-style caching saves cost and latency, but tax questions are **year- and law-versioned**. Superficially similar questions (“Box 1 tarief 2024” vs “2025”) can have **high embedding similarity** but **different correct answers**. Low thresholds create **silent fiscal wrong answers.**

## Options considered

### Option A: Threshold ~0.85–0.92 (“generous” hit rate)

- **Cons:** Unacceptable false hits on near-duplicate policy questions (`TRAPS.md` TRAP 5).

### Option B: Threshold **≥ 0.97** + role hash + corpus version key

- **Pros:** Trades hit rate for correctness; aligns with zero-hallucination posture.
- **Cons:** Fewer cache hits (acceptable for this domain).

## Decision

We chose **Option B**.

Reasoning:

- Enforced at the **type/config** level: `semantic_cache_threshold` in `src/config.py` uses `ge=0.97`.
- Cache keys must include **role** and **corpus_version** when implemented (`STACK.md`), or RBAC / stale-law bugs follow.

## Consequences

**What this makes easy:** Clear story in Module 4 (assessment) on why “common ML defaults” fail for fiscal data.

**What this makes hard:** Requires Redis vector or manual similarity with careful normalization in Phase 5 tests.

## References

- `TRAPS.md` TRAP 5
- `STACK.md` (Cache)
- `src/config.py`
