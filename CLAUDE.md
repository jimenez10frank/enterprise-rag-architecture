# CLAUDE.md — Project Context for AI Agents

> This file is auto-loaded by Claude Code at every session start. It is the source of truth for how to work on this repo.

## What this project is

A production-grade RAG system for Dutch legal and fiscal documents.
Designed to answer complex legal questions with zero hallucination tolerance,
strict role-based access control, and citation enforcement on every claim.

Built on a corpus of Dutch legislation (Wet IB 2001, Wet OB 1968),
case law (ECLI rulings), and policy documents. Scalable to 20M+ vector chunks.

**The full system requirements are in `ASSESSMENT.md`. Read it first.**

The output is **a GitHub repo** containing:

1. Working code demonstrating each module on a small corpus (~50 real legal documents)
2. A design document specifying the production-scale configuration
3. A writeup of how AI was used during development

This is evaluated on **architectural judgment**, not raw code volume. They want to see _why_ every choice was made.

## How to work with me (the human)

**My constraints:**

- I want to deeply understand what we build, not just have working code
- Technical follow-up questions should be fully answerable
- Cost is not a primary concern — pick the best tool, not the cheapest
- I want every architectural decision documented so I can defend it

**Therefore:**

- Before introducing a new concept, point me to or write the doc in `docs/concepts/`
- Explain WHY in code comments, not just WHAT
- After implementing each sub-phase, give me 3 comprehension questions to verify I understood
- Never use a library or pattern without flagging it for me first
- Keep functions small, named clearly — code readability is being evaluated
- Type-hint everything (mypy strict mode)

## Mandatory file reading order at session start

When a new session begins, read in this order before doing anything:

1. `ASSESSMENT.md` — what we are building and why (system requirements)
2. `CLAUDE.md` (this file) — working agreement
3. `TRAPS.md` — non-negotiable design gotchas, NEVER violate
4. `STACK.md` — committed tech choices and rationale
5. `ROADMAP.md` — phase plan with sub-phases
6. `PROGRESS.md` — current state of the project (what's done, what's next)
7. `PROJECT_STRUCTURE.md` — directory layout
8. `WORKFLOW.md` — how we collaborate, prompt patterns, definition of done

After reading, before any code change, you MUST:

- Summarize the current phase and sub-phase from `PROGRESS.md`
- Confirm the next concrete step you intend to take
- List any contradictions or ambiguities you noticed across the docs
- Ask me 1-3 clarifying questions if anything is unclear

Do not write code in your first response of a session. Read, summarize, align, then code.

## Hard rules

These are derived from `TRAPS.md`. Read that file for the full reasoning. The short version:

1. **NEVER use `RecursiveCharacterTextSplitter` or any character-based splitter for legal documents.** The chunker MUST parse legal hierarchy (artikel → lid → sub-bepaling) and preserve it as metadata on every chunk. Standard splitters destroy hierarchical context.

2. **NEVER apply RBAC after retrieval or at the LLM layer.** RBAC must be a pre-filter on metadata at the vector query stage, before HNSW search runs. Post-retrieval filtering is a data leak. The reasoning is mathematical and is the most critical concept in this project.

3. **NEVER use pgvector for the production-scale design.** At 20M+ chunks pgvector's recall and latency degrade. We use Qdrant. Note in the design doc that pgvector is fine for our 10M-vector demo scale but not for production.

4. **NEVER use alpha-weighted score fusion for hybrid search.** BM25 and dense scores are not on the same scale. Use Reciprocal Rank Fusion (RRF) with k=60. RRF uses ranks, not raw scores, which is the only mathematically defensible approach without per-query score normalization.

5. **NEVER use a semantic cache threshold below 0.97 for fiscal/legal data.** "Box 1 tariff 2024" and "Box 1 tariff 2025" are >0.92 similar and must NOT cache hit. Also key the cache on user role to prevent RBAC bypass via cache.

6. **NEVER let the LLM produce uncited claims.** Use structured output (Pydantic schema with `claim` + `source_chunk_id`). Prompting alone is insufficient — enforce via the schema.

7. **NEVER skip the comprehension questions step.** After every sub-phase, before marking it done in `PROGRESS.md`, ask me 3 questions and wait for my answers. If I get them wrong, we revisit before moving on.

## Stack (committed)

See `STACK.md` for full rationale. Quick reference:

- Python 3.11+, `uv` for package management
- LangChain (building blocks) + LangGraph (CRAG state machine)
- Qdrant (vector DB, Docker locally)
- OpenAI `text-embedding-3-large` (embeddings) + `gpt-4o-mini` (dev LLM)
- Cohere `rerank-multilingual-v3.0` (reranker)
- `rank_bm25` (sparse retrieval)
- Redis Stack (semantic cache)
- FastAPI (API layer)
- Ragas (evaluation)
- pytest + ruff + mypy (quality)
- LangSmith (tracing, optional but recommended)
- Docker + docker-compose (local infra)
- GitHub Actions (CI)

If you want to deviate from this stack, STOP and ask me first. Do not silently substitute.

## Code style

- Type hints on every function signature, mypy strict
- `ruff` for formatting and linting (config in `pyproject.toml`)
- Pydantic models for all data structures crossing module boundaries
- Module-level docstrings explaining the WHY of the module
- Function docstrings only when the function's purpose isn't obvious from name + signature
- No comments that restate what the code does; comments explain reasoning, tradeoffs, gotchas
- Tests live next to the code: `src/ingestion/chunker.py` → `src/ingestion/test_chunker.py`

## Session lifecycle

**Start of session:**

1. Read all 8 mandatory files (above)
2. Summarize state, confirm next step, ask any questions

**During session:**

1. Work in small sub-phases as listed in `ROADMAP.md`
2. After each sub-phase: tests pass, comprehension questions asked, `PROGRESS.md` updated
3. New architectural decisions go in `docs/decisions/NNN-title.md` as ADRs

**End of session:**

1. Update `PROGRESS.md`: move completed items, write a Last Session Summary
2. Commit and push (with descriptive commit messages)
3. State explicitly what the next session should start with

## When you are uncertain

Ask. Do not guess at architectural decisions. Do not silently choose between two valid options. These are judgment calls — surface them, don't hide them.
