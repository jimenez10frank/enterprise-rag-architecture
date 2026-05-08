# 012. Pydantic `AgentState` and `AgentNodeOverrides` for LangGraph CRAG

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 4

## Context

LangGraph requires an explicit **state schema**. Tests must exercise **routing** (relevant / ambiguous / irrelevant) and **retry** logic without mandating OpenAI, Cohere, or Qdrant on every developer machine.

## Options considered

### Option A: TypedDict-only state + integration tests only

- **Cons:** Duplicates shapes vs Pydantic models used for LLM structured output; weaker validation at boundaries.

### Option B: **Pydantic `AgentState`** as the graph schema + **optional injectable node callables**

- **Pros:** Single canonical model (`src/agent/state.py`); production graph uses real nodes; tests pass stub callables via `AgentNodeOverrides` (`src/agent/graph.py`).

## Decision

We chose **Option B**.

Reasoning:

- Keeps **TRAP 7** routing testable in CI with **no network**.
- Does not weaken RBAC: stubs replace LLM nodes, not Qdrant filters — retrieval tests still cover RBAC separately.

## Consequences

**What this makes easy:** Fast regression tests for graph topology.

**What this makes hard:** Overrides must stay **narrow** — do not stub out `retrieve` when testing real RBAC integration.

## References

- `src/agent/graph.py`, `src/agent/state.py`
- `src/agent/tests/test_graph.py`
