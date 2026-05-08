# 010. Ragas Faithfulness as deploy-blocker (CI)

**Date:** 2026-05-08
**Status:** Accepted (implementation pending Phase 5.4–5.6)
**Phase introduced:** 1 (concept); 5 (harness + CI)

## Context

Module 4 of the assessment requires **automatic evaluation** before rolling new models. For legal/fiscal answers, **Faithfulness** (“claims grounded in context”) is the metric that maps directly to hallucination risk.

## Options considered

### Option A: Metrics as informational only

- **Cons:** Regressions ship silently.

### Option B: **Faithfulness < 0.95 fails CI**; other metrics warn

- **Pros:** Matches `TRAPS.md` TRAP 11 and `STACK.md` evaluation section.

## Decision

We chose **Option B** for the **target CI policy** once the golden set exists.

Reasoning:

- **Context precision/recall/relevancy** flag noise for human review; **faithfulness** is the binary safety latch.

## Consequences

**What this makes easy:** Defensible release gate in Phase 6 architecture narrative.

**What this makes hard:** Golden set curation workload; API cost for eval on `main` — scope to labeled runs (`ROADMAP.md`).

## References

- `TRAPS.md` TRAP 11
- `STACK.md` (Evaluation)
- `docs/concepts/11-rag-evaluation.md`
