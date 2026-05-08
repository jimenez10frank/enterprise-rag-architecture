# 06 — Reranking and Cross-Encoders

## What it is

A reranker takes a query and a candidate document and scores them together as a pair. This is different from the initial retrieval step where query and documents are embedded independently (bi-encoders). A cross-encoder reads the concatenated `[query, document]` string and outputs a single relevance score. Because it sees both at once, it captures fine-grained semantic relationships that bi-encoders miss. The cost: it's slow — you can't pre-compute document representations. That's why rerankers are only used on the small candidate set after initial retrieval.

## Why it matters for this project

Initial retrieval (dense + BM25 + RRF) optimizes for recall — we want the relevant chunk somewhere in the top-50. Reranking optimizes for precision — we need the top-8 passed to the LLM to actually be relevant.

A cross-encoder reading "mag ik mijn auto aftrekken?" alongside "artikel 3.16a Wet IB 2001 — zakelijke kosten personenauto" understands the direct relationship in ways a bi-encoder score at query time cannot. This is especially valuable for Dutch legal text where the vocabulary gap between user question and statute text is large.

## The pipeline

```
Dense retriever:  top-50
BM25 retriever:   top-50
       ↓
RRF fusion:       top-50 combined
       ↓
Cohere reranker:  top-50 in → top-8 out
       ↓
LLM generation:   top-8 as context
```

Retrieve generously (recall), rerank aggressively (precision). This is TRAP 8.

## Key parameters

- **Model (demo):** `cohere/rerank-multilingual-v3.0` — strong Dutch, free tier covers demo usage, single API call.
- **Model (production):** `BAAI/bge-reranker-v2-m3` — self-hosted, same data residency reasoning as embeddings. Runs on a small GPU. Documented in design doc, not implemented for demo.
- **Input K:** 50 (from RRF fusion output).
- **Output K:** 8 (passed to the LLM).
- Why top-8 to LLM: GPT-4o-mini context windows can handle more, but sending 50 chunks degrades generation quality (LLMs struggle to synthesize long, noisy context). 8 tightly relevant chunks is better than 50 loosely relevant ones.

## Why not just retrieve top-8 directly?

If the retriever's top-8 misses the truly relevant chunk (which was at rank 23 in dense but rank 2 in BM25), no amount of reranking can fix it — you can only rerank what you retrieved. Retrieving top-50 gives the reranker room to promote the right answer. This is the fundamental principle: retrieval = recall, reranking = precision.

## Concrete example

After RRF fusion, top-3 fused results for "belastingvrije som 2024":
1. Chunk A — mentions "heffingskorting" and "belastingschijven" (semantically close, ranked high by dense)
2. Chunk B — exact text: "De algemene heffingskorting bedraagt in 2024 € 3.362" (BM25 ranked it 8th)
3. Chunk C — mentions "tarieven box 1 2024" (partially relevant)

After cross-encoder reranking, Chunk B jumps to rank 1. The reranker understood that Chunk B directly answers the question despite BM25 ranking it lower than the bi-encoder did.

## How it appears in our code

TODO — see `src/retrieval/reranker.py` once Phase 3 is implemented.

## Self-check questions

1. What is the fundamental difference between a bi-encoder and a cross-encoder? Which is used for initial retrieval and which for reranking, and why?
2. If I retrieve top-5 and rerank to top-5, why is this worse than retrieving top-50 and reranking to top-8?
3. Why can't we use Cohere's reranker in production for the Tax Authority's classified documents?
