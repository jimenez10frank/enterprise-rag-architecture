# 09 — LangGraph and Corrective RAG (CRAG)

## What it is

LangGraph is a framework for building stateful agent loops as explicit directed graphs. Nodes are Python functions that read and write a shared state object. Edges are transitions between nodes, optionally conditional. The graph runs until it reaches a terminal node.

CRAG (Corrective Retrieval-Augmented Generation) is the pattern we implement with LangGraph. The core idea: don't blindly generate from retrieved context. First grade the context quality. If it's insufficient, correct — either by rewriting the query, decomposing it, or refusing to answer.

## Why it matters for this project

Two reasons:

1. **Zero-hallucination tolerance.** Generating from weak or irrelevant context produces hallucinations. CRAG gives us an explicit check before generation. If the grader says "irrelevant," we return "I cannot answer this from the available sources" rather than guessing.

2. **Complex multi-part queries.** Dutch tax questions like "Wat is de aftrekbaarheid van thuiswerkkosten voor een zzp'er die ook parttime in loondienst is, en hoe verandert dat per 2025?" can't be answered from a single retrieval. Query decomposition breaks this into sub-questions, retrieves for each, and synthesizes.

## The graph structure

```
[Entry]
   ↓
[Query Decomposition Node]  ← breaks complex queries into sub-questions
   ↓
[Retrieval Node]            ← dense + BM25 + RRF + rerank for each sub-question
   ↓
[Grader Node]               ← three-way: Relevant / Ambiguous / Irrelevant
   ↓
  ┌──────────────────────────────────────┐
  │                                      │
Relevant                           Ambiguous                    Irrelevant
  ↓                                   ↓                             ↓
[Generation Node]          [Query Rewrite Node]           [Unanswerable Node]
  ↓                                   ↓                             ↓
[Citation Validation]       [Retrieval Node again]        return "cannot answer"
  ↓                                   ↓
[Response]                     if still ambiguous:
                               [Unanswerable Node]
```

## The three-way grader — why not binary?

The assessment explicitly requires three grades. A binary "good/bad" misses the key distinction:

- **Relevant** → we have what we need, generate.
- **Ambiguous** → context exists but might not fully answer the question. Rewrite the query, retry once. If still ambiguous, escalate.
- **Irrelevant** → context is clearly off-topic. Do NOT generate. Return a structured "unanswerable" response. This is the correct behavior in a zero-hallucination system. A wrong fiscal answer is worse than no answer.

The grader is a small, cheap LLM call (gpt-4o-mini):
```python
class GradeResult(BaseModel):
    grade: Literal["relevant", "ambiguous", "irrelevant"]
    reasoning: str
    missing_info: str | None
```

## State schema

```python
class AgentState(TypedDict):
    original_question: str
    sub_questions: list[str]
    retrieved_chunks: list[RetrievedChunk]
    grade: GradeResult | None
    answer: Answer | None
    retry_count: int
    user_roles: list[str]
```

The `user_roles` field flows through the entire graph — every retrieval node reads it to enforce RBAC.

## LangGraph vs raw Python

I could implement this as a Python function with if/else branches. The reason to use LangGraph:

- State is explicit and typed. No hidden global mutable state.
- Graph edges are visible — the routing logic is inspectable.
- LangSmith traces the graph node-by-node. I can see exactly which node was reached and why for every query.
- Adding a new node (e.g., a HyDE expansion node) means adding an edge, not refactoring nested if/else.

## How it appears in our code

TODO — see `src/agent/graph.py`, `src/agent/nodes/`, `src/agent/state.py` once Phase 4 is implemented.

## Self-check questions

1. The grader returns "ambiguous." Walk through the complete sequence of nodes that execute before a response is returned to the user.
2. Why does `user_roles` need to be part of `AgentState` rather than a global or environment variable?
3. Why is returning "I cannot answer this" preferable to generating a best-effort answer when the grader says "irrelevant"?
