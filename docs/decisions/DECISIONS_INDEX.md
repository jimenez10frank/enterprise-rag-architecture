# docs/decisions/README.md — Architectural Decision Records

> Every architectural choice gets an ADR. They are numbered sequentially, immutable once accepted, and superseded (never edited) when reversed.
>
> The point: when "why did you pick X?" comes up, the answer is in `docs/decisions/`. Not in chat history — in the repo.

---

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| 001 | [Qdrant over pgvector](./001-qdrant-over-pgvector.md) | Pre-committed | TBD |
| 002 | [RRF over alpha-weighted fusion](./002-rrf-over-alpha-fusion.md) | Pre-committed | TBD |
| 003 | [Pre-filter RBAC at vector query stage](./003-pre-filter-rbac.md) | Pre-committed | TBD |
| 004 | [Three-way grader (relevant / ambiguous / irrelevant)](./004-three-way-grader.md) | Pre-committed | TBD |
| 005 | [Semantic cache threshold ≥ 0.97 for fiscal data](./005-semantic-cache-threshold.md) | Pre-committed | TBD |
| 006 | [Structured-output citation enforcement](./006-citation-enforcement.md) | Pre-committed | TBD |
| 007 | [Self-hostable embedding model for production](./007-embedding-data-residency.md) | Pre-committed | TBD |
| 008 | [LangChain + LangGraph over LlamaIndex](./008-langchain-langgraph.md) | Pre-committed | TBD |
| 009 | [Cohere reranker for demo, BGE for production](./009-reranker-choice.md) | Pre-committed | TBD |
| 010 | [Faithfulness as CI deploy-blocker](./010-faithfulness-ci-gate.md) | Pre-committed | TBD |

> Pre-committed: derived from `TRAPS.md` and `STACK.md` at project start. Each gets a full ADR file written during the relevant phase, with rationale fleshed out, current status confirmed, and the date stamped.

---

## Template (`NNN-short-title.md`)

```markdown
# NNN. [Short Title]

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Superseded by ADR-XXX]
**Phase introduced:** [phase number from ROADMAP.md]

## Context

What is the problem we are deciding about? What's the situation that forces
a decision? Mention any relevant constraints (assessment requirements, scale
targets, data residency, performance budgets, etc.).

## Options Considered

### Option A: [name]
- **Description:** what it is.
- **Pros:** what we'd gain.
- **Cons:** what we'd lose.

### Option B: [name]
- **Description:** what it is.
- **Pros:** what we'd gain.
- **Cons:** what we'd lose.

### Option C: [name]
- **Description:** what it is.
- **Pros:** what we'd gain.
- **Cons:** what we'd lose.

## Decision

We chose **Option [X]**.

Reasoning:
- [Reason 1, ideally tied to a specific system requirement]
- [Reason 2]
- [Reason 3]

## Consequences

**What this makes easy:**
- [...]

**What this makes hard:**
- [...]

**Rollback path if we reverse this:**
- [...]

## References

- `TRAPS.md` TRAP [N]
- `STACK.md` section [...]
- [external links to papers, blog posts, docs]
```

---

## When to write an ADR

Write one when:
- Choosing a library or framework over alternatives.
- Setting a parameter that has tradeoffs (HNSW `m`, RRF `k`, cache threshold, reranker top-K).
- Defining the shape of an API or data model that other modules will depend on.
- Making a security or data-handling decision.
- Deciding to defer something (writing "we will not implement X for the demo, but production would do X" is itself a decision worth recording).

Don't write one when:
- The choice is obvious and uncontroversial (e.g., "we use pytest for tests").
- The choice is a coding-style preference with no architectural impact.

---

## When an ADR is wrong

ADRs are immutable once accepted. If a decision is reversed:
1. Write a new ADR explaining the new decision.
2. In the new ADR's header: `Status: Accepted, supersedes ADR-NNN`.
3. In the old ADR's header: change to `Status: Superseded by ADR-MMM`.
4. Do NOT edit the old ADR's body. The history matters.

---

## Why this matters

The focus is on judgment, not code volume. The ADR folder is the artifact that displays judgment. A repo with 10 thoughtful ADRs is a stronger signal than a repo with 5,000 lines of perfect code. The answer to "why this and not X?" should be: "ADR-007 covers it, here's the link."
