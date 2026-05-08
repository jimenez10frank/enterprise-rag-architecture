# TRAPS.md — Non-Negotiable Gotchas

> This project has specific design traps. Each one is a "tell" — does the design reflect production understanding, or is it generic RAG? Falling into any of these produces a weaker system. This file exists so everyone knows exactly what NOT to do, and what TO do, with reasoning.

> **Every trap is a deliberate design test.** When tempted to take a shortcut, re-read the trap.

---

## TRAP 1 — Hierarchical chunking

**The trap:** Use `RecursiveCharacterTextSplitter`, `TokenTextSplitter`, or any character/token-based splitter on legal documents.

**Why it's a trap:** The system requirements explicitly state: *"Standard recursive text splitters destroy the hierarchical context of legal documents."* Using one anyway shows the requirement was not understood.

**The correct approach:**
- Parse the document's legal hierarchy: `Wet → Hoofdstuk → Afdeling → Artikel → Lid → Sub-bepaling`.
- Each chunk is bounded by structure (typically one `lid` or one short `artikel`), not character count.
- Every chunk carries this metadata in its payload, so the LLM can output `"Wet IB 2001, Artikel 3.114, lid 2"` as its citation:
  ```python
  class ChunkMetadata(BaseModel):
      wet: str           # "Wet inkomstenbelasting 2001"
      hoofdstuk: str     # "3"
      afdeling: str | None
      artikel: str       # "3.114"
      lid: int | None    # 2
      sub: str | None    # "a", "b", etc.
      classification: Literal["public", "internal", "fiod"]
      allowed_roles: list[str]
      doc_id: str
      source_url: str
      effective_date: date | None
  ```
- For case law (jurisprudence), the hierarchy is different: `ECLI → r.o. (rechtsoverweging) number`. The chunker must detect document type and apply the right schema.

**Acceptable shortcut for the demo:** If a document doesn't fit the schema cleanly (e.g., e-learning material), fall back to semantic chunking (split on headings/paragraphs) but still preserve `doc_id`, `classification`, and `allowed_roles`. Document this fallback explicitly in the design doc.

---

## TRAP 2 — RBAC pipeline stage (the most-tested concept)

**The trap:** Filter documents by user role *after* retrieval, or *in the LLM prompt*.

**Why it's a trap:** The assignment asks: *"at what stage of the RAG pipeline must this filtering occur to prevent data leaks mathematically?"* The word "mathematically" is the giveaway — there is one correct answer.

**The correct approach:** RBAC must be a **pre-filter on metadata at the vector query stage**, before HNSW search runs. In Qdrant terms:

```python
client.search(
    collection_name="docs",
    query_vector=q_vec,
    query_filter=Filter(  # <-- THIS RUNS BEFORE HNSW SEARCH
        must=[
            FieldCondition(
                key="allowed_roles",
                match=MatchAny(any=user.roles),
            )
        ]
    ),
    limit=50,
)
```

**The mathematical reasoning (be ready to explain this verbally):**

- **Post-retrieval filtering is a leak.** If we retrieve top-50 first and then filter, classified chunks competed in the similarity ranking. Their existence influenced *which* unclassified chunks made the top 50 (because nearest-neighbor scores are relative to the corpus). The user can deduce the existence of classified content from the *gaps* in results. With enough probing queries, an attacker reconstructs the classified embedding space.
- **LLM-level filtering is a leak.** The classified text was already in the model's context window. Even if we instruct the model not to use it, the generation distribution is conditioned on it. Side-channel attacks can extract it.
- **Pre-filter at the vector query stage is the only safe placement.** The HNSW graph is traversed with the metadata predicate active — classified vectors are not even visited. The user's query never "sees" classified content. Mathematically, the result set is identical to one produced from a corpus that never contained the classified documents.

**Implementation requirements:**
- The filter MUST be enforced server-side (in Qdrant), not in Python after the response.
- The semantic cache MUST also be keyed on user role — otherwise a helpdesk user could hit a cached answer originally generated for a fraud investigator. (See TRAP 5.)
- The grader and generator nodes in LangGraph receive only filtered chunks; they have no way to see classified content even via a bug, because it never left Qdrant.

---

## TRAP 3 — Vector database choice

**The trap:** Use pgvector for the production design because it was used in a prior project (Growora).

**Why it's a trap:** pgvector is fine at small scale. At 20M+ vectors (the assignment's stated scale), pgvector's recall/latency tradeoff degrades sharply unless heavily tuned, and metadata filtering is far less efficient than purpose-built vector DBs.

**The correct approach:**
- Production: **Qdrant** (Rust-based, excellent metadata filtering with payload indexes, scalar/binary quantization built-in, mature HNSW parameter control).
- Acceptable alternatives to mention: Weaviate, Milvus.
- Do NOT mention: pgvector, FAISS-only setups, Pinecone (managed, can't show parameter tuning).

**Required configuration parameters in the design doc:**
- HNSW `m`: 16 for general use, 32 if recall is critical (legal domain leans 32).
- HNSW `ef_construct`: 200-400 (higher = slower index build, better recall).
- HNSW `ef` (search-time): 128-256 (tune per query latency budget).
- Quantization: scalar (4x memory reduction, ~2-3% recall hit) for the bulk of the corpus, with `rescore=True` and `oversampling=2.0` to recover precision. Mention binary quantization as an option for archived/historical documents.
- Payload indexes on: `classification`, `allowed_roles`, `wet`, `effective_date`.
- Sharding strategy at production scale: shard by `wet` or `document_type` to keep working sets cache-resident.

---

## TRAP 4 — Hybrid search fusion strategy

**The trap:** Use alpha-weighted score fusion: `final_score = alpha * dense + (1-alpha) * sparse`.

**Why it's a trap:** BM25 scores and dense cosine similarities are not on the same scale. BM25 is unbounded above; cosine similarity is bounded `[-1, 1]`. Alpha fusion requires per-query score normalization (min-max or z-score), which is fragile and varies wildly with query length. It is the wrong answer.

**The correct approach: Reciprocal Rank Fusion (RRF) with k=60.**

```python
def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Combine multiple ranked lists into a single ranking via RRF."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Why RRF is correct:**
- Uses ranks, not raw scores — score-scale incomparability is moot.
- `k=60` is the value from the original Cormack et al. paper; it's the industry default.
- Robust to score outliers and per-query variance.
- Composable: trivially extends to >2 retrievers (e.g., adding a colbert-style late-interaction model later).

For the legal domain specifically: BM25 catches exact matches (ECLI references, statute numbers). Dense catches semantic concepts ("deductibility of home office expenses"). The system requirements explicitly mention both query types — RRF handles both without needing to detect query type.

---

## TRAP 5 — Semantic cache threshold

**The trap:** Use a "common sense" threshold like 0.85 or 0.90 for the semantic cache.

**Why it's a trap:** Tax data is **year-versioned and law-versioned**. Consider:
- "What is the Box 1 tariff for 2024?" embeds at ~0.93-0.95 similarity to "What is the Box 1 tariff for 2025?"
- "Wat is de drempel voor de zelfstandigenaftrek?" varies year over year — same question, different correct answer.

A 0.85 threshold returns last year's answer to this year's question. That is a fiscal advice error in a zero-hallucination system. Failure.

**The correct approach:**
- Threshold: **≥ 0.97** for fiscal/legal data. This trades cache hit rate for correctness, which is the right tradeoff in this domain.
- Cache key includes the user's `role_hash` (NOT just the embedding). A helpdesk user must not hit a fraud investigator's cached answer. (Connects to TRAP 2.)
- Cache key includes a `corpus_version` field. When new legislation is ingested, bump the corpus version → entire cache invalidates. Cheap insurance against stale answers after a law change.
- TTL: short (24-48h). Tax laws change; even if the threshold is correct, freshness matters.
- The cache stores: query embedding, normalized question text, generated answer, citations, generation timestamp, corpus_version, role_hash.

**Implementation:** Redis Stack with vector index (HNSW on the cached query embeddings), or a simple Redis sorted set with manual cosine comparison for the demo. Document both.

---

## TRAP 6 — Citation enforcement

**The trap:** Tell the LLM via prompt to cite sources, then trust it to do so.

**Why it's a trap:** Prompting is statistical, not deterministic. Under load, with complex queries, the model will sometimes omit citations or fabricate them. Zero-hallucination tolerance means structural enforcement.

**The correct approach: structured output with Pydantic + function calling.**

```python
class Citation(BaseModel):
    chunk_id: str
    artikel: str
    lid: int | None
    quote: str = Field(..., max_length=300)

class CitedClaim(BaseModel):
    claim: str
    citations: list[Citation] = Field(..., min_length=1)

class Answer(BaseModel):
    claims: list[CitedClaim]
    confidence: Literal["high", "medium", "low"]
    unanswerable: bool = False
    unanswerable_reason: str | None = None
```

The LLM is invoked with `response_format=Answer` (OpenAI structured output) or equivalent function-calling schema. The schema **forces** every claim to carry at least one citation. Post-generation, validate that every `chunk_id` in citations exists in the retrieved set; if not, reject the response and either retry or escalate.

**Defensive checks beyond the schema:**
- Validate each `chunk_id` exists in the retrieved context.
- Validate each `quote` is a substring (or close fuzzy match) of the chunk content. If the model paraphrases beyond a threshold, reject.
- If `unanswerable=True`, return that to the user verbatim. Never let a "soft answer" through.

---

## TRAP 7 — CRAG fallback design

**The trap:** Implement the grader as a binary "good/bad" classifier with a single retry on bad.

**Why it's a trap:** The requirements explicitly call for **three** classifications: `Relevant`, `Ambiguous`, `Irrelevant`, each with **defined fallback actions**. A binary grader misses this.

**The correct approach: three-way grader with three distinct fallback paths.**

```
Retrieved context grade:
├── Relevant   → proceed to generation
├── Ambiguous  → query rewrite/decomposition node, retry retrieval ONCE,
│                if still ambiguous: escalate to "needs human" response
└── Irrelevant → DO NOT generate from weak context (hallucination risk).
                 Two options, document both, pick one as default:
                   (a) explicit "I cannot answer this from the available
                       sources" response with a prompt to escalate
                   (b) external web search fallback (only for non-classified
                       queries — RBAC implications: web results bypass our
                       trusted corpus, must be flagged in the answer)
                 Default for the Tax Authority context: option (a).
                 A wrong fiscal answer is worse than no answer.
```

The grader itself is a small LLM call (cheap model — `gpt-4o-mini` is fine here) producing a structured `GradeResult(grade, reasoning, missing_info)`.

---

## TRAP 8 — Reranker top-K tuning

**The trap:** Retrieve top-5, rerank to top-5. ("Why rerank? They're already the top 5.")

**Why it's a trap:** A reranker can only choose from what the initial retriever surfaced. If the retriever's top-5 are mediocre and the truly relevant chunk was at rank 23, reranking top-5 cannot promote it.

**The correct approach:**
- Initial retrieval (per retriever): top-50 dense, top-50 BM25.
- RRF fusion to a combined top-50.
- Cross-encoder rerank (Cohere `rerank-multilingual-v3.0` or `BAAI/bge-reranker-v2-m3`) the top-50 down to top-8.
- Pass top-8 to the LLM for generation.

The numbers are tunable but the principle is: **retrieve generously, rerank aggressively.** The reranker is the precision filter; the retrievers are the recall filters.

For the design doc, also note that at production scale the Cohere API rate limits matter; self-hosted `bge-reranker-v2-m3` on a small GPU is the production choice. Cohere is fine for the demo.

---

## TRAP 9 — Query decomposition vs HyDE (knowing when to use which)

**The trap:** Use one technique because it's the only one we read about, regardless of query type.

**The correct approach (mention both in design, implement decomposition):**

- **Query Decomposition** for **multi-part** questions: *"Wat is de aftrekbaarheid van thuiswerkkosten voor een zzp'er die ook parttime in loondienst is, en hoe verandert dat per 2025?"* → decompose into 3 sub-questions, retrieve for each, synthesize.
- **HyDE** for **vague semantic queries** where the user's vocabulary doesn't match the corpus: *"Mag ik mijn werkruimte aftrekken?"* → generate a hypothetical correct answer first ("De aftrekbaarheid van een werkruimte aan huis is geregeld in artikel..."), embed THAT, search with the hypothetical embedding. Useful when the user is a layperson but the corpus is in formal legal Dutch.

For this project: implement **decomposition** (it directly maps to the "complex, multi-part tax questions" requirement) and document HyDE as a complementary technique with concrete trigger conditions in the design doc.

---

## TRAP 10 — Embedding model and data residency

**The trap:** Specify OpenAI `text-embedding-3-large` for production without caveat.

**Why it's a trap:** The Belastingdienst handles classified citizen data. Sending classified text to OpenAI's API is likely a data residency / GDPR / national security violation. This is a critical constraint to get right.

**The correct approach:**
- Demo: OpenAI `text-embedding-3-large` (3072 dims, multilingual, strong Dutch).
- Production: self-hostable model — `BAAI/bge-m3` (multilingual, supports dense+sparse+colbert, runs on a single GPU, MIT-licensed). Mention `intfloat/multilingual-e5-large-instruct` as alternative.
- Document the data residency reasoning explicitly in `docs/decisions/`.
- Note that the embedding model choice affects RBAC: classified document embeddings must be generated by the self-hosted model only; the OpenAI-generated embeddings (for public / e-learning content) and the self-hosted ones must be in **separate collections** (their vector spaces are not comparable).

---

## TRAP 11 — Faithfulness vs Context Precision (knowing what each measures)

**The trap:** List Ragas metrics without explaining what they measure or why they matter for this domain.

**The correct approach (have ready a one-line explanation of each):**
- **Faithfulness:** Does every claim in the answer trace back to the retrieved context? (Detects LLM hallucination.) For legal/fiscal: must be ≥ 0.95 to pass. CI gate.
- **Context Precision:** Of the chunks we retrieved, how many were actually relevant? (Detects retriever noise.) Target ≥ 0.85.
- **Context Recall:** Did we retrieve all the relevant chunks? (Detects retriever misses.) Target ≥ 0.80.
- **Answer Relevancy:** Does the answer actually address the question? (Detects topic drift.) Target ≥ 0.85.

In the design doc, specify: a regression on Faithfulness in CI is a deploy-blocker. The other three are warnings that require human review. The golden dataset has 50-100 question/answer pairs with curated correct citations; new embedding model and new LLM versions are evaluated against it before production rollout.

---

## How to use this file

- At session start (per `CLAUDE.md`), read this file in full.
- Before implementing any module, re-read the relevant trap.
- If a code suggestion would violate any trap above, STOP and raise it. Do not silently shortcut.
- The design doc must address each trap explicitly — they define the production requirements.
