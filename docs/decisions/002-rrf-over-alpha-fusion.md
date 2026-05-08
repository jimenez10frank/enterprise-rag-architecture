# 002. Reciprocal Rank Fusion (RRF) over alpha-weighted fusion

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 1 (concept); implemented in 3.3

## Context

Hybrid retrieval combines **BM25** (sparse) and **dense** vectors. Their **raw scores are not comparable** (different scales, different semantics). The assessment asks explicitly how to fuse results for a legal domain mixing exact references (ECLI, article numbers) and semantic questions.

## Options considered

### Option A: Alpha-weighted linear fusion

- **Description:** `score = α * dense + (1-α) * sparse` after ad hoc normalization.
- **Pros:** Simple to implement; familiar from tutorials.
- **Cons:** Brittle without per-query normalization; BM25 unbounded vs bounded cosine — **mathematically weak** for mixed query types (`TRAPS.md` TRAP 4).

### Option B: Reciprocal Rank Fusion (RRF), k=60

- **Description:** Fuse using **inverse rank** contributions `1/(k+rank)` from each ranked list.
- **Pros:** Scale-free; robust; standard `k=60` from literature; extends to >2 rankers.
- **Cons:** Requires both retrievers to return ranked lists (we already do).

## Decision

We chose **Option B (RRF, k=60)**.

Reasoning:

- Legal retrieval must handle **both** exact-token and semantic queries without a separate “query type classifier”; RRF composes naturally.
- Meets the **non-negotiable** constraint in `TRAPS.md` TRAP 4.

## Consequences

**What this makes easy:** Clear test that we never ship alpha fusion (`test_rrf_not_alpha_weighted`).

**What this makes hard:** If we add a third ranker (e.g. late interaction), we must document rank list hygiene (dedupe, tie-breaks).

**Rollback path:** Supersede with a new ADR only if we adopt a **documented** calibrated fusion method — not silent alpha tuning.

## References

- `TRAPS.md` TRAP 4
- `docs/concepts/05-rrf.md`
- `src/retrieval/fusion.py`
