# 003. RBAC as a pre-filter at the vector query stage

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 2–3 (payload + Qdrant filter); reinforced in 4 (agent never role-filters)

## Context

The scenario includes **classified FIOD-style** content. Helpdesk users must not retrieve or **infer existence of** restricted chunks. The assessment explicitly asks **at which pipeline stage** filtering must occur to prevent leaks **“mathematically.”**

## Options considered

### Option A: Post-retrieval filter in application code

- **Description:** Retrieve top-K, then drop unauthorized chunks.
- **Pros:** Easy to code.
- **Cons:** **Information leakage** via ranking neighbourhood / score gaps (`TRAPS.md` TRAP 2).

### Option B: Prompt-level “do not use classified”

- **Description:** Retrieve broadly; instruct the LLM to ignore unauthorized material.
- **Cons:** Classified text may still enter context → **side-channel risk**; fails zero-hallucination bar.

### Option C: Server-side metadata **pre-filter** before HNSW / scoring

- **Description:** Qdrant `query_filter` on `allowed_roles`; BM25 filters before ranking in-process.
- **Pros:** Restricted vectors never compete in the same ranking as allowed vectors for that principal.

## Decision

We chose **Option C**.

Reasoning:

- Matches the **only** placement that satisfies the assignment’s “mathematical” framing: unauthorized partitions are not visited/scored in the user’s search space.
- Demo implementation: `dense.py` (Qdrant), `bm25.py` (pre-score filter). Phase 4 agent passes `user_roles` only into `retrieve()` — **not** into an LLM “permission brain.”

## Consequences

**What this makes easy:** Integration tests that prove FIOD payloads never return for `public`/`helpdesk` roles.

**What this makes hard:** Semantic cache (Phase 5) must be **role-keyed** or cache becomes an RBAC bypass (`TRAPS.md` TRAP 5).

**Rollback path:** None compatible with assessment — reversing this would fail the security story.

## References

- `TRAPS.md` TRAP 2
- `docs/concepts/08-rbac-pre-filter.md`
- `src/retrieval/dense.py`, `src/retrieval/bm25.py`
