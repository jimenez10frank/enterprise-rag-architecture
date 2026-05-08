# docs/concepts/README.md — Concept Doc Index

> These are my learning notes, written in my own words during Phase 1. Each is 200-500 words. Each gets revised as my understanding deepens during implementation.
>
> **The agent does not write these.** The agent teaches the topic in regular Claude.ai chat, then quizzes me, then reviews my draft. The act of writing is the learning.

---

## Reading order (also implementation order)

| # | Topic | Status | Used in phase |
|---|-------|--------|---------------|
| 01 | [Vectors and embeddings](./01-vectors-and-embeddings.md) | Done | 2 |
| 02 | [HNSW algorithm](./02-hnsw.md) | Done | 2 |
| 03 | [Quantization (scalar, binary, product)](./03-quantization.md) | Done | 2 |
| 04 | [BM25 vs dense retrieval](./04-bm25-vs-dense.md) | Done | 3 |
| 05 | [Reciprocal Rank Fusion](./05-rrf.md) | Done | 3 |
| 06 | [Reranking and cross-encoders](./06-reranking.md) | Done | 3 |
| 07 | [Hierarchical chunking for legal documents](./07-hierarchical-chunking.md) | Done | 2 |
| 08 | [RBAC at the retrieval layer](./08-rbac-pre-filter.md) | Done | 2, 3, 5 |
| 09 | [LangGraph and CRAG](./09-langgraph-crag.md) | Done | 4 |
| 10 | [Semantic caching](./10-semantic-cache.md) | Done | 5 |
| 11 | [RAG evaluation (Faithfulness, Context Precision, ...)](./11-rag-evaluation.md) | Done | 5 |

---

## Doc template

Each concept doc follows this structure (target 200-500 words):

```markdown
# NN. [Topic]

## What it is
[1-2 sentence definition.]

## Why it matters for our use case
[Why this concept matters specifically for RAG over Dutch legal documents
at 20M-chunk scale. Generic explanations are not useful — tie it to
the system requirements.]

## Key parameters / decisions
[What knobs are there? What are sensible defaults? When do you tune them?]

## A concrete example with numbers
[Make it real. "If we have a 3072-dim embedding and 20M vectors, raw
storage is 20M × 3072 × 4 bytes = 246 GB. Scalar int8 quantization brings
that to ~62 GB."]

## How it appears in our code
[Pointer to the file and function in src/ where this concept is implemented.
Each numbered concept doc in this folder includes an implementation pointer when relevant.]

## What I had to look up to write this
[Honesty section. Useful for the AI usage writeup later.]

## Self-check questions I can answer
[3-5 questions I can answer. If I can't, the doc isn't done.]
```

---

## How to write a concept doc (the routine)

1. **Learn (regular Claude.ai chat).** Use the prompt from [`WORKFLOW.md`](../project/WORKFLOW.md) to get a tailored explanation.
2. **Read until comfortable.** Ask follow-ups. No code yet.
3. **Close the chat.** Open this `docs/concepts/NN-topic.md` file fresh.
4. **Write in your own words.** No copy-paste. If you can't write a sentence without copying, go back to step 1.
5. **Self-check questions.** Write 3-5 questions you can answer. These become the comprehension quiz template.
6. **Paste the doc into Claude Code** with: *"Read this and flag anything inaccurate or missing. Don't suggest stylistic changes — these are my notes in my voice."*
7. **Revise based on feedback.** Commit.
8. **Update this index** to mark the doc as Done.

---

## Why this matters

Understanding what was built is the core criterion. The concept docs are the artifact that proves that understanding. They are also the primary review material before any technical discussion.

If a concept doc is skipped or copy-pasted, it shows in any technical discussion.
