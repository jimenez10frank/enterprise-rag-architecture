# 04 — BM25 vs Dense Retrieval

## What it is

These are two fundamentally different ways to match a query to documents.

**BM25** is a keyword-frequency model. It scores documents based on how often query terms appear, normalized by document length and corpus-wide term frequency. No neural network — pure statistics. It cannot understand synonyms or meaning.

**Dense retrieval** embeds both the query and documents into a vector space. Documents close in meaning rank highly, even with zero word overlap. It understands semantics but can miss exact terms.

## Why we need both

Our query types make this obvious:

| Query type | BM25 handles it | Dense handles it |
|------------|----------------|-----------------|
| "ECLI:NL:HR:2023:1234" | ✓ exact match | ✗ meaningless string to embedder |
| "artikel 3.114 lid 2" | ✓ exact match | ✗ may miss if chunk says "derde lid" |
| "mag ik mijn auto aftrekken als zzp'er?" | ✗ keyword mismatch | ✓ semantic match to chunk about "zakelijke kosten voertuigen" |
| "aftrekbaarheid thuiswerkkosten" | partial | ✓ finds "werkruimte aan huis" semantically |

The system requirements explicitly mention both ECLI references and semantic concepts. Neither retriever alone is sufficient. We run both and fuse with RRF.

## Key parameters

**BM25** (via `rank_bm25` Python library):
- `k1=1.5` — term frequency saturation. After seeing a term ~3 times, more occurrences add little. 1.5 is the BM25 paper default, works well for legal text.
- `b=0.75` — length normalization. Shorter documents don't get unfairly penalized. 0.75 is the standard.
- Tokenization: lowercase + basic Dutch stopword removal. Do NOT stem Dutch legal terms (stemming "aftrekbaarheid" → "aftrek" might match wrong articles).

**Dense:**
- Model: `text-embedding-3-large` / `bge-m3` (see `01-vectors-and-embeddings.md`).
- Top-K: retrieve top-50 per retriever. We retrieve generously for the reranker to work with.

## Production consideration

`rank_bm25` is in-process Python. Fine for hundreds to low thousands of chunks. At 20M chunks, the BM25 index needs to be a real service: Elasticsearch or OpenSearch. Documented in the design doc, not implemented for the demo.

## Concrete example

Query: "belastingvrije voet inkomstenbelasting 2024"

- BM25 scores highly: any chunk with "belastingvrije", "inkomstenbelasting", "2024" as exact tokens.
- Dense scores highly: chunks about "heffingskorting", "belastingschijven", "tarieven box 1" — semantically related but different words.
- After RRF fusion: both types of chunks appear in the combined top-50, giving the reranker and LLM a complete picture.

## How it appears in our code

TODO — see `src/retrieval/bm25_retriever.py` and `src/retrieval/dense_retriever.py` once Phase 3 is implemented.

## Self-check questions

1. BM25 scores an ECLI case reference at rank 1. Dense retrieval ranks that same chunk at rank 47. What happens after RRF fusion and why?
2. Why don't we stem Dutch legal terms before indexing in BM25?
3. Why is `rank_bm25` acceptable for the demo but not for production at 20M chunks?
