# 006. Structured-output citation enforcement

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 4

## Context

The assessment demands **exact citations** per claim and **zero hallucination tolerance**. Prompting alone is statistically unreliable under load.

## Options considered

### Option A: Prompt-only (“always cite your sources”)

- **Cons:** Non-deterministic omissions and fabricated citations (`docs/project/TRAPS.md` TRAP 6).

### Option B: Pydantic `Answer` + OpenAI structured output + post-validation

- **Description:** Schema forces **claims** and **citations**; Python checks `chunk_id ∈ retrieved`, **artikel** consistency, **quote** evidence in chunk text.
- **Pros:** Defence in depth — schema + programmatic checks + one repair LLM turn before escalate.

## Decision

We chose **Option B** (`src/agent/state.py`, `src/agent/nodes/generate.py`).

Reasoning:

- Matches assessment + TRAP 6.
- Quote check uses **verbatim or longest-run fuzzy ≥ 0.9** to tolerate whitespace drift while blocking fabrication.

## Consequences

**What this makes easy:** CI tests on `validate_answer()` without calling LLMs.

**What this makes hard:** Stricter prompts increase escalate rate until the retriever is strong — acceptable tradeoff.

## References

- `docs/project/TRAPS.md` TRAP 6
- `src/agent/state.py`, `src/agent/nodes/generate.py`
