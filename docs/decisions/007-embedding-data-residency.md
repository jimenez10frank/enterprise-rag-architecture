# 007. Embedding choice: OpenAI demo vs self-hosted production

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 2–3 (demo path implemented; production path design-only)

## Context

`TRAPS.md` TRAP 10: sending **classified** text to third-party embedding APIs is typically **incompatible** with data residency and insider-data policies. The assessment still expects a **working demo** on predominantly public legal text.

## Options considered

### Option A: OpenAI `text-embedding-3-large` everywhere

- **Pros:** Best API quality for Dutch legal phrasing in the demo.
- **Cons:** Unacceptable for real classified chunks in production.

### Option B: Demo OpenAI; production **self-hosted** multilingual encoder (e.g. BGE-M3)

- **Pros:** Satisfies demo velocity while documenting the **real** production constraint.
- **Cons:** Two vector spaces → **separate collections** if both ever coexist; no mixing incomparable embeddings.

## Decision

We chose **Option B** as the **documented split**:

- **Demo:** OpenAI `text-embedding-3-large` (3072-d), wired in `src/ingestion/embed.py`.
- **Production (design):** Self-hosted `BAAI/bge-m3` (or approved alternative) for classified + sensitive workloads.

Reasoning:

- Aligns assessment security narrative with pragmatic demo delivery.

## Consequences

**What this makes easy:** Clear ADR to cite in Phase 6 architecture doc under data residency.

**What this makes hard:** Any future “single collection” shortcut must be rejected in review.

## References

- `TRAPS.md` TRAP 10
- `STACK.md` (Embeddings)
- `src/ingestion/embed.py`
