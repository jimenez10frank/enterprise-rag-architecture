# 02 — HNSW (Hierarchical Navigable Small World)

## What it is

HNSW is the index structure Qdrant uses to answer "find me the K most similar vectors to this query vector" fast. Without an index, finding the nearest neighbor in 20M vectors means computing 20M cosine similarities — that's too slow. HNSW builds a multi-layer graph where upper layers have long-range connections and lower layers have fine-grained connections. Search starts at the top, hops toward the answer, then refines in lower layers. It trades a tiny amount of recall for massive speed gains.

## Why it matters for this project

Two reasons specific to us:

1. **RBAC pre-filtering.** The reason we must filter at the vector query stage (before HNSW search runs) is that HNSW traverses only a subset of the graph. If classified vectors are excluded by a metadata predicate at query time, the HNSW traversal never reaches them. They don't influence the rankings. This is the mathematical guarantee behind our RBAC design.

2. **Scale.** At 20M vectors, exact nearest-neighbor search is infeasible in real time. HNSW gives us sub-100ms retrieval. pgvector's HNSW implementation at this scale loses recall unless heavily tuned — that's why we use Qdrant (see TRAP 3).

## Key parameters

| Parameter | Our value | What it controls |
|-----------|-----------|-----------------|
| `m` | 32 | Connections per node per layer. Higher = better recall, more memory. 16 is general-purpose; 32 is the right call for a legal domain where recall is critical. |
| `ef_construct` | 256 | How many candidates to explore while building the index. Higher = slower build, better index quality. 400 is the max sensible value; 256 is our balance. |
| `ef` (search-time) | 128–256 | How many candidates to explore during query. Higher = better recall, higher latency. Tune this against our latency budget. |

These live in `STACK.md` as our committed configuration.

## Concrete example

Index has 1M Dutch legal chunks. Query vector comes in for "aftrek eigen woning."

- Layer 2 (sparse): 3 hops across 8 candidates — narrows to ~50 clusters.
- Layer 1 (medium): 12 hops across 40 candidates — narrows to ~200 candidates.
- Layer 0 (dense): 30 hops across 150 candidates — returns top-50 by cosine.

Total: ~200 distance computations instead of 1,000,000. Recall at `ef=128` is typically ~95%.

## The RBAC connection

When we pass a `query_filter` with `allowed_roles` to Qdrant, the filter runs during HNSW traversal. The graph nodes for classified vectors are still there structurally, but the traversal skips them when it encounters a filtered-out node. This is fundamentally different from retrieving everything and then filtering — in that scenario, classified vectors affect which unclassified vectors make the top-K because similarity is relative.

## How it appears in our code

TODO — see `src/vectorstore/collection.py` once Phase 2 is implemented (collection creation with `hnsw_config`).

## Self-check questions

1. If I set `ef_construct=50` (way too low), what breaks at query time and why?
2. Why is `m=32` more appropriate for a legal corpus than `m=16`?
3. Explain in one sentence why RBAC must be a pre-filter at the HNSW stage rather than post-retrieval filtering.
