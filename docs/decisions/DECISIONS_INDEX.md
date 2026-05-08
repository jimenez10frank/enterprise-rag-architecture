# Architectural Decision Records — Index

> Every architectural choice gets an ADR. They are numbered sequentially. If reversed, add a **new** ADR that supersedes the old one — do not erase history (`WORKFLOW.md` / template below).

---

## Alignment with `ASSESSMENT.md` (authoritative requirements)

| Module (assessment) | Required focus | Repo status (Phase 5 entry) | Notes |
|---------------------|----------------|----------------------------|--------|
| **1 — Ingestion & structuring** | Hierarchical chunking; vector DB + HNSW + quantization at scale | **Implemented on demo corpus** | Chunker preserves Wet→Lid hierarchy + metadata (`TRAPS` 1). Qdrant setup matches committed params (`001`). **Gap:** corpus is **synthetic HTML** per `011`, not the full ~50 real harvest in `ROADMAP` 2.1 — acceptable for vertical slice if called out in final design/README. |
| **2 — Retrieval** | Hybrid BM25+dense; fusion; rerank; top-K story | **Implemented** | RRF k=60 (`002`); top-50+50 → fuse → rerank to top-8 (`009`, `TRAPS` 8); RBAC pre-filter (`003`). |
| **3 — Agentic RAG / CRAG** | Decomposition / HyDE; LangGraph; grader + fallbacks | **Implemented (decomposition + CRAG)** | LangGraph graph with **three-way** grader (`004`, `008`). **HyDE** documented as future complement in `TRAPS` / concepts — not code yet. |
| **4 — Ops, security, eval** | Semantic cache ≥ safe threshold; RBAC stage; Ragas + CI | **Implemented (demo)** | Threshold + Redis cache (`005`, `013`). FastAPI + golden set + Ragas harness + eval workflow (`010`). RBAC agent verification test (`003`). |

**Overall direction:** The implementation order **follows** `ROADMAP.md` and respects `TRAPS.md` (non-negotiables are reflected in code + tests). The main **honest delta** from the **letter** of Phase 2.1 is the **synthetic demo corpus** (`011`); everything else is **on track** for the “working slice + production design doc” outcome described in `ASSESSMENT.md` § “What this means for scope.”

**Process note:** `ROADMAP.md` asks for comprehension Q&A per sub-phase and ADRs as you go — ADRs **001–013** are now filled; conversational quizzes are **human–agent workflow** (`WORKFLOW.md`), not stored in git.

---

## ADR index

| # | Title | Status | Implemented / target phase | File |
|---|-------|--------|---------------------------|------|
| 001 | Qdrant over pgvector (production scale) | Accepted | 2–3 | [001-qdrant-over-pgvector.md](./001-qdrant-over-pgvector.md) |
| 002 | RRF over alpha-weighted fusion | Accepted | 3 | [002-rrf-over-alpha-fusion.md](./002-rrf-over-alpha-fusion.md) |
| 003 | Pre-filter RBAC at vector query stage | Accepted | 2–4 | [003-pre-filter-rbac.md](./003-pre-filter-rbac.md) |
| 004 | Three-way grader (relevant / ambiguous / irrelevant) | Accepted | 4 | [004-three-way-grader.md](./004-three-way-grader.md) |
| 005 | Semantic cache threshold ≥ 0.97 | Accepted | 0 (config); **5.1** cache | [005-semantic-cache-threshold.md](./005-semantic-cache-threshold.md) |
| 006 | Structured-output citation enforcement | Accepted | 4 | [006-citation-enforcement.md](./006-citation-enforcement.md) |
| 007 | Demo OpenAI embeddings vs self-hosted production | Accepted | 2–3 (demo) | [007-embedding-data-residency.md](./007-embedding-data-residency.md) |
| 008 | LangChain + LangGraph | Accepted | 4 | [008-langchain-langgraph.md](./008-langchain-langgraph.md) |
| 009 | Cohere reranker (demo) vs BGE (production design) | Accepted | 3 | [009-reranker-choice.md](./009-reranker-choice.md) |
| 010 | Faithfulness as CI deploy-blocker | Accepted | **5.4–5.6** | [010-faithfulness-ci-gate.md](./010-faithfulness-ci-gate.md) |
| 011 | Synthetic demo corpus (interim) | Accepted | 2 | [011-demo-corpus-synthetic.md](./011-demo-corpus-synthetic.md) |
| 012 | Pydantic AgentState + test node overrides | Accepted | 4 | [012-agent-state-and-test-overrides.md](./012-agent-state-and-test-overrides.md) |
| 013 | Redis LIST buckets for semantic cache (demo scale) | Accepted | 5.1 | [013-semantic-cache-redis-buckets.md](./013-semantic-cache-redis-buckets.md) |

---

## AI usage documentation

Human-authored narrative (per assessment) lives in **`docs/AI_USAGE.md`**. This index focuses on **product/architecture** ADRs; process and tooling choices for AI pair-programming are captured there so evaluators see both **what** we decided and **how** the repo was built.

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

## Decision

We chose **Option [X]**.

Reasoning:
- [Reason 1, ideally tied to a specific system requirement]
- [Reason 2]

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
```

---

## When to write an ADR

Write one when:

- Choosing a library or framework over alternatives.
- Setting a parameter that has tradeoffs (HNSW `m`, RRF `k`, cache threshold, reranker top-K).
- Defining the shape of an API or data model that other modules will depend on.
- Making a security or data-handling decision.
- Scoping or deferring work (e.g. synthetic corpus vs real harvest) such that the delta must be **visible to reviewers**.

---

## When an ADR is wrong

ADRs are immutable once accepted. If a decision is reversed:

1. Write a new ADR explaining the new decision.
2. In the new ADR's header: `Status: Accepted, supersedes ADR-NNN`.
3. In the old ADR's header: change to `Status: Superseded by ADR-MMM`.
4. Do NOT edit the old ADR's body.

---

## Why this matters

The focus is on **judgment**, not code volume. The ADR folder is the artifact that displays judgment. The answer to “why this and not X?” should be: “**ADR-00N** covers it.”
