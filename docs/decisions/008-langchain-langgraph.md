# 008. LangChain + LangGraph over LlamaIndex (or bespoke orchestration)

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 0 (deps); 4 (LangGraph graph)

## Context

Module 3 of the assessment asks for a **CRAG state machine**. We need explicit **nodes**, **conditional edges**, and **observability** (LangSmith) without rewriting orchestration tooling from scratch.

## Options considered

### Option A: LlamaIndex-centric stack

- **Cons:** Weaker first-class story for **graph control-flow** vs LangGraph for the CRAG loop (`docs/project/STACK.md`).

### Option B: Raw OpenAI SDK + hand-rolled state machine

- **Pros:** Minimal dependencies.
- **Cons:** Reimplements tracing, branching, and state merge logic — poor use of time vs “judgment” rubric.

### Option C: LangChain primitives + **LangGraph** for the agent

- **Pros:** Industry-default glue + explicit graph for CRAG; traces map to nodes.

## Decision

We chose **Option C**.

Reasoning:

- Matches `docs/project/STACK.md` and Phase 4 `src/agent/graph.py` implementation.

## Consequences

**What this makes easy:** LangSmith node-level traces for demo narrative.

**What this makes hard:** Dependency churn (e.g. qdrant-client API updates) — mitigate with tests.

## References

- `docs/project/STACK.md` (RAG framework)
- `src/agent/graph.py`
