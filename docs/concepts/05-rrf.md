# 05 — Reciprocal Rank Fusion (RRF)

## What it is

RRF is a way to combine multiple ranked lists into one. Each document gets a score based on its position (rank) in each list, not its raw score. The formula for one document appearing in one ranked list is:

```
score contribution = 1 / (k + rank)
```

Sum these contributions across all lists. Higher total = higher final rank. `k=60` is the value from the original Cormack et al. (2009) paper and is the industry default.

## Why we use RRF and not alpha-weighted fusion

Alpha fusion: `final = α × dense_score + (1-α) × bm25_score`

The problem: BM25 scores are unbounded above (a document with 50 exact matches scores much higher than one with 5). Cosine similarity is bounded `[-1, 1]`. There is no α that correctly balances these two scales across all queries. Long queries inflate BM25 scores; short queries don't. Per-query normalization (min-max, z-score) is fragile.

RRF uses ranks, not raw scores. Rank 1 in BM25 and rank 1 in dense both contribute equally, regardless of what the underlying scores were. This is mathematically defensible without any normalization heuristics. (See TRAP 4.)

## Key parameters

- `k=60` — the smoothing constant. Higher values reduce the weight of top ranks; lower values make it winner-take-all. 60 is the empirically validated default from the original paper. Don't change it without a clear reason.
- Input: top-50 from dense + top-50 from BM25.
- Output: top-50 fused, then handed to the reranker.

## The formula in code

```python
def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

This is the complete implementation from [`TRAPS.md`](../project/TRAPS.md). It's that simple.

## Concrete example

| doc_id | BM25 rank | Dense rank | RRF score |
|--------|-----------|------------|-----------|
| A | 1 | 3 | 1/61 + 1/63 = 0.01639 + 0.01587 = **0.03226** |
| B | 5 | 1 | 1/65 + 1/61 = 0.01538 + 0.01639 = **0.03177** |
| C | 2 | 47 | 1/62 + 1/107 = 0.01613 + 0.00935 = **0.02548** |
| D | — | 2 | 0 + 1/62 = **0.01613** |

Document A wins the fusion even though it wasn't rank 1 in dense — it consistently appeared near the top of both lists. Document D (dense-only) still makes the fused ranking at a reasonable position.

## Extensibility

RRF trivially extends to 3+ retrievers. Adding HyDE results or a late-interaction (ColBERT) retriever later is just adding another list to the function. No α to retune.

## How it appears in our code

TODO — see `src/retrieval/fusion.py` once Phase 3 is implemented.

## Self-check questions

1. BM25 returns a score of 47.3 for document X; cosine similarity is 0.82 for the same document. Explain why you cannot directly average these two numbers.
2. What would happen if I set `k=5` instead of `k=60`?
3. A document ranks 1st in BM25 but doesn't appear at all in the dense top-50. What is its RRF score and why?
