# ROADMAP.md — Phase-by-Phase Build Plan

> Every phase has sub-phases. Every sub-phase has a single concrete goal and a definition of done. Move sequentially. Do not skip ahead.

> **Definition of Done for every sub-phase:**
> 1. The goal is implemented and works.
> 2. Tests pass (where applicable).
> 3. Comprehension questions asked and answered correctly.
> 4. `PROGRESS.md` updated.
> 5. New decisions recorded as ADRs in `docs/decisions/`.
> 6. Commit made with descriptive message.

---

## Phase 0 — Foundation (target: 0.5 day)

**Goal:** Empty repo, working dev environment, infrastructure spinning up. Zero business logic.

### 0.1 — Git repository
- Create private GitHub repo `legal-rag-nl`.
- Initial commit: this set of MD files at the root and in `docs/`.
- `.gitignore` for Python (use GitHub's standard template + `.env`, `__pycache__`, `.venv`, `dist/`, `*.egg-info`, `.ruff_cache`, `.mypy_cache`, `qdrant_storage/`).
- README placeholder (will write properly in Phase 6).

### 0.2 — Python environment
- Verify Python 3.11+ available.
- `uv init` to create `pyproject.toml`.
- Add baseline dev dependencies: `pytest`, `ruff`, `mypy`, `pre-commit`.
- Configure `ruff` and `mypy` (strict) in `pyproject.toml`.
- `uv sync` to lock versions.

### 0.3 — pre-commit hooks
- `.pre-commit-config.yaml`: ruff, mypy, trailing-whitespace, end-of-file-fixer, check-large-files.
- `pre-commit install` and verify it runs on a test commit.

### 0.4 — Docker compose for infrastructure
- `docker-compose.yml` with services:
  - `qdrant` (image: `qdrant/qdrant:latest`), ports 6333 + 6334, volume mount for persistence.
  - `redis` (image: `redis/redis-stack:latest`), port 6379, volume mount.
- `make up` / `make down` Makefile targets (or just use docker-compose commands directly).
- Verify Qdrant dashboard at `http://localhost:6333/dashboard` and Redis Stack RedisInsight at `http://localhost:8001`.

### 0.5 — Environment variables
- `.env.example` with placeholders: `OPENAI_API_KEY`, `COHERE_API_KEY`, `LANGSMITH_API_KEY` (optional), `QDRANT_URL`, `REDIS_URL`.
- `src/config.py` with a `Settings` Pydantic class loading from env.
- `.env` in `.gitignore`. Fill in real keys locally.

### 0.6 — Project skeleton
- Create directory structure per `PROJECT_STRUCTURE.md`.
- Empty `__init__.py` files where appropriate.
- One trivial test (`test_smoke.py`) that just `assert 1 + 1 == 2`. Verify pytest runs.

### 0.7 — First CI workflow
- `.github/workflows/ci.yml`: install with uv, run ruff, mypy, pytest.
- Push and verify it passes.

**Phase 0 done when:** `docker-compose up`, `pytest`, `ruff check`, `mypy` all succeed locally and CI is green.

---

## Phase 1 — Concept docs (target: 1 day, NO CODE)

**Goal:** Write one concept doc per topic in `docs/concepts/`, in your own words, before any related code is written. Each doc is 200-500 words. The agent's role is to *teach* the concept first, then *quiz*, then review the draft.

For each concept:
1. Ask (in regular Claude chat, not Code) for an explanation tailored to a TS dev.
2. Read it, ask follow-ups, until comfortable.
3. Write `docs/concepts/NN-topic.md` in your own words.
4. Paste it back to the agent, which gives feedback (clarifications, missing nuances).
5. Revise, commit.

### 1.1 — Vectors and embeddings
What an embedding is, what cosine similarity means, why dimensionality matters, why dense vectors capture semantics.

### 1.2 — HNSW (Hierarchical Navigable Small World)
What it is, why it's used over brute-force, what `m`, `ef_construct`, `ef` mean, how recall vs latency trade off.

### 1.3 — Quantization (scalar, binary, product)
Why memory matters at 20M vectors, how scalar quantization works (int8 buckets), the recall hit, how rescoring with `oversampling` recovers precision.

### 1.4 — BM25 vs dense retrieval
What BM25 measures (term frequency, inverse document frequency, length normalization), what it catches that dense misses (exact tokens like ECLI references), what dense catches that BM25 misses (synonyms, paraphrases).

### 1.5 — Reciprocal Rank Fusion
Why scores aren't comparable, how RRF works mathematically, why `k=60`, when alpha-weighted fusion is wrong (and when it's acceptable).

### 1.6 — Reranking (cross-encoders)
Difference between bi-encoder (used in retrieval) and cross-encoder (used in reranking), why cross-encoders are slower but more accurate, why we retrieve broadly and rerank aggressively.

### 1.7 — Hierarchical chunking for legal documents
Why character splitters fail, how legal hierarchy maps to metadata, how citations are produced from metadata, the schema for `ChunkMetadata`.

### 1.8 — RBAC at the retrieval layer
Why post-filter leaks information, why LLM-level filtering leaks, why pre-filter at the vector query stage is the only safe placement, how Qdrant payload filters compose with HNSW search.

### 1.9 — LangGraph and CRAG
What a state machine is in this context, why CRAG is more robust than linear RAG, what nodes/edges/conditional edges look like, how state flows through.

### 1.10 — Semantic caching
Why threshold matters, why year-versioned data needs high thresholds, why cache must be RBAC-keyed, why corpus_version invalidation matters.

### 1.11 — RAG evaluation
What Faithfulness, Context Precision, Context Recall, Answer Relevancy each measure. How a golden set is built. Why Faithfulness is the deploy-blocker for legal/fiscal.

**Phase 1 done when:** all 11 concept docs exist, each has been quizzed, and the index in `CONCEPTS.md` lists all of them.

---

## Phase 2 — Ingestion pipeline (target: 2 days)

**Goal:** Take 50 real Belastingdienst legal documents, parse them with hierarchical structure preserved, embed them, load them into Qdrant.

### 2.1 — Source documents
- Download 50 real articles from `wetten.overheid.nl` covering:
  - Wet IB 2001 (income tax) — 30 articles across multiple chapters/paragraphs.
  - Wet OB 1968 (VAT) — 10 articles.
  - 5 ECLI court rulings on fiscal matters.
  - 5 Belastingdienst public policy documents (handboeken).
- Save to `data/raw/`. Include a `data/raw/README.md` documenting source URLs and date of download.
- For RBAC demo purposes, randomly assign 5 of these to `classification: "fiod"` (simulated classified docs) so we can demonstrate the role filter working. Document this is a simulation.

### 2.2 — Chunk metadata schema
- Define `ChunkMetadata` Pydantic model in `src/ingestion/schema.py` (see TRAPS.md TRAP 1 for the full schema).
- Define `Chunk` model: `content: str`, `chunk_id: str`, `metadata: ChunkMetadata`.
- Tests for schema serialization/deserialization.

### 2.3 — Hierarchical chunker
- `src/ingestion/chunker.py`.
- Parse `wetten.overheid.nl` HTML structure: detect `<artikel>`, `<lid>`, `<lijst>` patterns.
- Detect ECLI document structure separately (`r.o.` rechtsoverwegingen).
- Fallback to semantic chunking (split on headings) for documents that don't match either schema, with `doc_type: "unstructured"` flag.
- Each chunk's `chunk_id` is deterministic: `f"{doc_id}#{artikel}#{lid or 0}#{i}"`.
- **NEVER use RecursiveCharacterTextSplitter.** (See TRAPS.md TRAP 1.)

### 2.4 — Chunker tests
- Single-article document → expected chunks with correct artikel/lid metadata.
- Multi-paragraph article → one chunk per `lid`.
- ECLI ruling → one chunk per `r.o.`.
- Unstructured doc → falls back gracefully with `doc_type: unstructured`.

### 2.5 — Embedding pipeline
- `src/ingestion/embed.py`.
- Use OpenAI `text-embedding-3-large` (3072 dims).
- Batch up to 100 chunks per API call.
- Retry with exponential backoff on rate limit errors.
- Cache embeddings on disk (`data/embeddings/{chunk_id}.json`) so re-runs don't re-embed.

### 2.6 — Qdrant collection setup
- `src/ingestion/qdrant_setup.py`.
- Create collection with HNSW params (`m=32`, `ef_construct=256`), scalar quantization (int8, quantile=0.99, always_ram=True), cosine distance, 3072 vector dim.
- Create payload indexes on: `classification`, `allowed_roles`, `wet`, `effective_date`, `doc_type`.
- Idempotent: re-running the script doesn't error if collection exists.

### 2.7 — Bulk ingestion
- `scripts/ingest.py` — top-level CLI script.
- Walks `data/raw/`, calls chunker, calls embedder, upserts to Qdrant.
- Progress bar (tqdm).
- Logs: number of documents, number of chunks, elapsed time, average chunk size.

### 2.8 — Smoke test retrieval
- Simple Qdrant query: "thuiswerk aftrek" → returns chunks from relevant artikelen.
- Verify metadata is intact in the returned payload.
- Verify the RBAC test case: query as `helpdesk` role excludes the 5 simulated FIOD chunks.

**Phase 2 done when:** `python scripts/ingest.py` populates Qdrant with ~200-500 chunks from 50 documents, all with correct hierarchical metadata, and the RBAC pre-filter test passes.

---

## Phase 3 — Retrieval (target: 1.5 days)

**Goal:** Hybrid retrieval (BM25 + dense) with RRF fusion, reranking on top.

### 3.1 — BM25 index
- `src/retrieval/bm25.py`.
- Use `rank_bm25` (BM25Okapi).
- Build the index from the same chunk corpus loaded into Qdrant.
- Persist tokenized corpus to disk for fast reload.
- Dutch tokenization: simple whitespace + lowercase + diacritic-normalize is fine for the demo. Document that production would use a Dutch-aware tokenizer.

### 3.2 — Dense retrieval (with RBAC filter)
- `src/retrieval/dense.py`.
- Function: `dense_search(query: str, user_roles: list[str], top_k: int = 50) -> list[ScoredChunk]`.
- Embed query with the same model used for ingestion.
- Qdrant search with `query_filter` enforcing `allowed_roles` overlap with `user_roles`.
- Returns ranked list of `ScoredChunk(chunk_id, score, payload)`.

### 3.3 — RRF fusion
- `src/retrieval/fusion.py`.
- Function: `rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]`.
- Tests with synthetic rankings to verify behavior.
- Tests with overlapping and disjoint result sets.

### 3.4 — Cohere reranker integration
- `src/retrieval/rerank.py`.
- Function: `rerank(query: str, candidates: list[Chunk], top_k: int = 8) -> list[Chunk]`.
- Calls Cohere `rerank-multilingual-v3.0`.
- Handle empty candidate list.
- Retry on transient errors.

### 3.5 — End-to-end retrieve()
- `src/retrieval/__init__.py`.
- Function: `retrieve(query: str, user_roles: list[str]) -> list[Chunk]`.
- Orchestrates: BM25 top-50 + dense top-50 → RRF top-50 → rerank to top-8.
- Both retrievers honor RBAC pre-filter (BM25 filters in-process, dense via Qdrant `query_filter`).
- Returns the final 8 chunks ready for the LLM.

### 3.6 — Retrieval tests
- Exact-match query (`ECLI:NL:HR:2023:123`) → BM25 surfaces the right chunk, dense alone might miss it, hybrid catches it.
- Semantic query ("thuiswerk aftrek") → dense surfaces the right chunks.
- RBAC test: helpdesk role cannot retrieve fiod-classified chunks even with high-similarity queries.
- Latency benchmark: log p50/p95 over 20 queries. Should be well under 1.5s TTFT budget.

**Phase 3 done when:** `retrieve()` returns 8 well-ranked chunks in <500ms p95, with RBAC enforced, and the test suite passes.

---

## Phase 4 — Agentic generation with LangGraph (target: 2 days)

**Goal:** CRAG state machine that grades retrieval and routes to one of three fallback paths, with cited generation.

### 4.1 — Agent state schema
- `src/agent/state.py`.
- Pydantic model `AgentState`:
  - `original_question: str`
  - `user_roles: list[str]`
  - `decomposed_questions: list[str] | None`
  - `retrieved_chunks: list[Chunk]`
  - `grade: Literal["relevant", "ambiguous", "irrelevant"] | None`
  - `grade_reasoning: str | None`
  - `retry_count: int = 0`
  - `final_answer: Answer | None`

### 4.2 — Query decomposition node
- `src/agent/nodes/decompose.py`.
- LLM call (gpt-4o-mini, structured output) that takes a complex question and returns either a single question (if not multi-part) or a list of sub-questions.
- Detection: if returned list has > 1 question, downstream retrieves for each.

### 4.3 — Retrieval node
- `src/agent/nodes/retrieve.py`.
- Calls `retrieve()` from Phase 3 for each (decomposed) question.
- Aggregates and de-duplicates chunks across sub-questions.

### 4.4 — Grader node
- `src/agent/nodes/grade.py`.
- LLM call (gpt-4o-mini, structured output `GradeResult(grade, reasoning, missing_info)`).
- Three-way grade: `relevant` / `ambiguous` / `irrelevant`. (See TRAPS.md TRAP 7.)

### 4.5 — Conditional edges and fallback nodes
- `src/agent/graph.py`.
- LangGraph with edges:
  - `decompose → retrieve → grade`
  - `grade --[relevant]--> generate`
  - `grade --[ambiguous, retry_count < 1]--> rewrite_query → retrieve` (loop once)
  - `grade --[ambiguous, retry_count >= 1]--> escalate`
  - `grade --[irrelevant]--> escalate`
- `escalate` returns a structured "I cannot answer this from the available sources" response.

### 4.6 — Generation node with citation enforcement
- `src/agent/nodes/generate.py`.
- LLM call with `response_format=Answer` (structured output, see TRAPS.md TRAP 6).
- Post-validation:
  - Every `chunk_id` in citations exists in retrieved set.
  - Every quote is a substring (or fuzzy match ≥ 0.9) of the cited chunk content.
- If validation fails, retry once with stricter prompt, then escalate.

### 4.7 — End-to-end agent tests
- Single-shot query that should grade as `relevant` → generates cited answer.
- Vague query that should grade as `ambiguous` → triggers rewrite, retries.
- Out-of-domain query (e.g., "What's the weather?") → grades as `irrelevant` → escalates.
- Multi-part query → decomposes, retrieves per part, generates synthesized answer.

**Phase 4 done when:** the LangGraph runs end-to-end on representative queries with correct routing and validated citations, and traces are visible in LangSmith.

---

## Phase 5 — Production ops layer (target: 1.5 days)

**Goal:** Semantic cache, FastAPI wrapper, Ragas eval harness.

### 5.1 — Semantic cache
- `src/ops/cache.py`.
- Redis Stack with vector index on cached query embeddings.
- Cache key: `{role_hash}:{corpus_version}:{question_normalized_hash}`.
- Threshold: ≥ 0.97 cosine similarity. (See TRAPS.md TRAP 5.)
- TTL: 24h.
- Tests:
  - Hit: same question, same role → cached answer returned.
  - Near-miss: same role, similar but different question (0.94 similarity) → cache miss.
  - Role isolation: different role → cache miss even with identical question.
  - Corpus invalidation: bumping corpus_version invalidates all keys.

### 5.2 — RBAC verification
- Already enforced in Phase 3 retrieval. This sub-phase is verification + documentation.
- Integration test: user with `helpdesk` role asks a question whose only relevant chunk is FIOD-classified → system answers "I cannot answer this" (irrelevant grade) instead of leaking. Verify in LangSmith trace that the FIOD chunk is never in the agent state.

### 5.3 — FastAPI wrapper
- `src/api/main.py`.
- `POST /query` endpoint:
  - Request: `{question: str}` plus `X-User-Role` header.
  - Response: structured `Answer` (claims with citations) or escalation message.
  - Latency budget: log per-request total, surface in response headers.
- `GET /health` endpoint:
  - Pings Qdrant, Redis, OpenAI.
  - Returns 200 if all healthy, 503 otherwise.
- Pydantic validation on requests.
- Auto-generated OpenAPI docs at `/docs`.

### 5.4 — Ragas evaluation harness
- `src/eval/ragas_runner.py`.
- Loads `data/golden/golden_set.jsonl` (curate 15-20 Q&A pairs with correct citations during this phase).
- Runs the full agent on each question.
- Computes Faithfulness, Context Precision, Context Recall, Answer Relevancy.
- Outputs a results table.

### 5.5 — Golden dataset
- `data/golden/golden_set.jsonl`.
- 15-20 hand-curated questions covering:
  - Exact-match (ECLI) questions.
  - Semantic concept questions.
  - Multi-part questions.
  - Ambiguous questions (should escalate).
  - Out-of-domain questions (should escalate).
  - RBAC-restricted questions per role.
- Each entry: `question`, `expected_answer_summary`, `expected_chunk_ids`, `user_role`, `expected_outcome` (`answered` | `escalated`).

### 5.6 — CI integration
- Ragas eval added to GitHub Actions on `main` branch only (it costs API calls).
- Faithfulness < 0.95 fails the build.
- Other metrics produce warnings, not failures.

**Phase 5 done when:** API is callable, cache works, RBAC integration test passes, Ragas eval produces a baseline score on the golden set with Faithfulness ≥ 0.95.

---

## Phase 6 — Polish & final artifacts (target: 1.5 days)

**Goal:** The repo presents itself well.

### 6.1 — Architecture design document
- `docs/design/architecture.md`.
- Sections matching the four system modules.
- Each module:
  - Conceptual architecture (with mermaid diagram).
  - Specific configuration parameters (HNSW, quantization, RRF k, reranker top-K, cache threshold, eval thresholds).
  - Pseudo-code where the assignment asks for it.
  - Production-scale notes (what differs from the demo).
  - Trade-offs explicitly addressed.
- Each `TRAPS.md` item is addressed in the right module section.

### 6.2 — README rewrite
- Front-page README:
  - One-paragraph project description.
  - Quick-start: `git clone`, `cp .env.example .env`, `docker-compose up`, `uv sync`, `python scripts/ingest.py`, `uvicorn src.api.main:app`.
  - Architecture diagram (mermaid or image).
  - Link to `docs/design/architecture.md`.
  - Link to `docs/AI_USAGE.md`.
  - Link to `docs/concepts/` for the concept docs.
  - Status badges: CI, ruff, mypy, tests passing.

### 6.3 — AI usage writeup
- `docs/AI_USAGE.md`.
- Structure:
  - **Tools used:** Claude Code, Cursor, Claude.ai chat, [any others].
  - **What AI generated, what I wrote:** per-phase breakdown.
  - **Prompt patterns used:** the templates from `WORKFLOW.md`, with a couple of real examples.
  - **What I learned:** concrete list of concepts that were new and are now understood.
  - **What was hard despite AI:** honest reflection.
- This writeup is required.

### 6.4 — Loom demo (3 minutes)
- Walk through:
  - The architecture (one-minute overview).
  - One real query end-to-end, showing the LangSmith trace.
  - One escalation case (irrelevant grade).
  - One RBAC case (helpdesk hits a FIOD-restricted query).
- Link in the README.

### 6.5 — Final cleanup
- All TODOs resolved or moved to a "future work" section in the design doc.
- `ruff check`, `mypy`, `pytest` all green.
- Repo description and topics set on GitHub.
- Tag a `v1.0` release.
- Share the repo link.

**Phase 6 done when:** A stranger could clone the repo, run it, understand the architecture, and see how AI was used.

---

## Total target: 10-11 working days

This assumes ~6-8 focused hours per day. Adjust `PROGRESS.md` based on actual pace. If a phase runs over, raise it — do not silently skip steps to catch up. The traps will not forgive shortcuts.
