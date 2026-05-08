# 004. Three-way retrieval grader (relevant / ambiguous / irrelevant)

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 4

## Context

Linear RAG generates even when context is weak → **hallucination**. The assessment requires a **CRAG** loop with explicit fallback actions. A binary “good/bad” grader cannot express “maybe right topic but missing critical year” vs “wrong corpus entirely.”

## Options considered

### Option A: Binary relevance

- **Description:** Relevant vs not; single retry.
- **Cons:** Collapses **ambiguous** (recoverable with rewrite) and **irrelevant** (should refuse) into one bucket (`docs/project/TRAPS.md` TRAP 7).

### Option B: Three-way labels with distinct edges

- **Description:** `relevant` → generate; `ambiguous` → one rewrite + re-retrieve, then escalate; `irrelevant` → escalate without generation.
- **Pros:** Matches requirements and Belastingdienst “wrong answer worse than no answer” posture.

## Decision

We chose **Option B**, implemented in LangGraph conditional routing from `src/agent/graph.py`.

Reasoning:

- **Irrelevant:** no generation from untrusted context.
- **Ambiguous:** bounded corrective loop (single retry via `retry_count`).
- **Relevant:** proceed to structured generation + citation validation.

## Consequences

**What this makes easy:** LangSmith traces show **which branch** fired per query (operational debugging).

**What this makes hard:** Grader calibration — may need golden “ambiguous” examples in Phase 5 dataset.

**Rollback path:** Only if product owner accepts binary routing; would require new ADR and assessment alignment.

## References

- `docs/project/TRAPS.md` TRAP 7
- `docs/concepts/09-langgraph-crag.md`
- `src/agent/nodes/grade.py`, `src/agent/graph.py`
