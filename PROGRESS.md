# PROGRESS.md — Living State Tracker

> Update this at the END of every Claude Code session. The agent reads this at the START of every session. This is how state survives across sessions.

> **Update protocol at end of session:**
> 1. Move completed sub-phases from "Doing now" to "Done".
> 2. Move next sub-phases from "Next" to "Doing now".
> 3. Add new entries to "Decisions made" if any architectural choice was made.
> 4. Update "Last session summary" with what was accomplished.
> 5. Add to "Open questions" anything that needs my input next session.

---

## Current phase

**Phase 4 — CRAG agent (LangGraph state machine)**
Started: 2026-05-08
Target completion: TBD

---

## Done

- [x] **0.1** — GitHub repo `legal-rag-nl` created, MD files committed, `.gitignore` in place.
- [x] **0.2** — `uv` installed, `pyproject.toml` written with full dep list, ruff + mypy strict config, 143 packages locked in `uv.lock`.
- [x] **0.3** — `.pre-commit-config.yaml` created (ruff, mypy, standard hooks), hooks installed.
- [x] **0.4** — `docker-compose.yml` written; Qdrant (port 6333/6334) and Redis Stack (port 6379/8001) verified up and healthy.
- [x] **0.5** — `.env.example` with all required vars; `src/config.py` with Pydantic Settings singleton (0.97 cache threshold enforced via `ge` constraint).
- [x] **0.6** — Full directory skeleton from `PROJECT_STRUCTURE.md` created; empty `__init__.py` files in all packages; `src/test_smoke.py` passes.
- [x] **0.7** — `.github/workflows/ci.yml` written (uv install → ruff → mypy → pytest on every push).
- [x] **1.1** — Concept doc: vectors and embeddings (`docs/concepts/01-vectors-and-embeddings.md`).
- [x] **1.2** — Concept doc: HNSW (`docs/concepts/02-hnsw.md`).
- [x] **1.3** — Concept doc: quantization (`docs/concepts/03-quantization.md`).
- [x] **1.4** — Concept doc: BM25 vs dense (`docs/concepts/04-bm25-vs-dense.md`).
- [x] **1.5** — Concept doc: RRF (`docs/concepts/05-rrf.md`).
- [x] **1.6** — Concept doc: reranking and cross-encoders (`docs/concepts/06-reranking.md`).
- [x] **1.7** — Concept doc: hierarchical chunking (`docs/concepts/07-hierarchical-chunking.md`).
- [x] **1.8** — Concept doc: RBAC at the retrieval layer (`docs/concepts/08-rbac-pre-filter.md`).
- [x] **1.9** — Concept doc: LangGraph and CRAG (`docs/concepts/09-langgraph-crag.md`).
- [x] **1.10** — Concept doc: semantic caching (`docs/concepts/10-semantic-cache.md`).
- [x] **1.11** — Concept doc: RAG evaluation (`docs/concepts/11-rag-evaluation.md`).
- [x] **2.1** — 16 synthetic HTML legal docs (13 public Wet IB 2001 + 3 FIOD internal) + README in `data/raw/`.
- [x] **2.2** — `ChunkMetadata` and `Chunk` Pydantic models in `src/ingestion/schema.py`. Three-tier RBAC: public/internal/fiod, `allowed_roles` list on every chunk.
- [x] **2.3** — Hierarchical chunker in `src/ingestion/chunker.py`. Parses Wet→Hoofdstuk→Afdeling→Artikel→Lid→Sub. One lid = one chunk. No character/token splitters (TRAP 1).
- [x] **2.4** — 21 chunker tests in `src/ingestion/test_chunker.py`. TRAP 1 guard (asserts no character splitter class names in source). FIOD classification/role isolation verified. All pass.
- [x] **2.5** — Disk-cached embedding pipeline in `src/ingestion/embed.py`. Batch size 100, cache at `data/embeddings/<chunk_id>.json`.
- [x] **2.6** — Qdrant collection setup in `src/ingestion/qdrant_setup.py`. m=32, ef_construct=256, scalar int8 quantization (quantile=0.99, always_ram=True). Payload indexes on classification, allowed_roles, wet, effective_date.
- [x] **2.7** — Bulk ingestion script at `scripts/ingest.py`. Flags: --recreate, --dry-run, --force-embed. Deterministic point IDs via uuid5.
- [x] **2.8** — RBAC smoke test: 5 integration tests in `src/retrieval/tests/test_rbac_integration.py`. Verified public cannot see FIOD, helpdesk cannot see FIOD, FIOD sees all, filter is server-side (pre-HNSW), latency under 500ms.
- [x] **3.1** — BM25 index in `src/retrieval/bm25.py`. RBAC filter before scoring. IDF=0 edge case documented in tests (need ≥3 docs). 14 tests pass.
- [x] **3.2** — Dense retrieval in `src/retrieval/dense.py`. FieldCondition on allowed_roles runs inside Qdrant before HNSW (TRAP 2). Updated to qdrant-client 1.17 API (`query_points()` not `search()`).
- [x] **3.3** — RRF fusion in `src/retrieval/fusion.py`. Pure rank-based, k=60, `rrf_from_scored()` strips raw scores before fusing. 10 tests including `test_rrf_not_alpha_weighted` (TRAP 4). All pass.
- [x] **3.4** — Cohere reranker in `src/retrieval/rerank.py`. `rerank-multilingual-v3.0`. Top-50 → top-8 (TRAP 8).
- [x] **3.5** — End-to-end `retrieve()` in `src/retrieval/__init__.py`. Lazy imports to avoid Settings() at module load. TYPE_CHECKING guards for type annotations.
- [x] **3.6** — Full retrieval test suite: 10 fusion + 14 BM25 + 5 RBAC integration = **51 tests, all passing**.

---

## Doing now

- [ ] **4.1** — Agent state schema.
- [ ] **4.1** — Agent state schema.
- [ ] **4.2** — Query decomposition node.
- [ ] **4.3** — Retrieval node.
- [ ] **4.4** — Grader node (three-way).
- [ ] **4.5** — Conditional edges and fallback nodes.
- [ ] **4.6** — Generation node with citation enforcement.
- [ ] **4.7** — End-to-end agent tests.
- [ ] **5.1** — Semantic cache (RBAC-keyed, 0.97 threshold).
- [ ] **5.2** — RBAC integration test.
- [ ] **5.3** — FastAPI wrapper.
- [ ] **5.4** — Ragas evaluation harness.
- [ ] **5.5** — Golden dataset (15-20 Q&A pairs).
- [ ] **5.6** — CI integration of Ragas.
- [ ] **6.1** — Architecture design document.
- [ ] **6.2** — README rewrite.
- [ ] **6.3** — AI usage writeup.
- [ ] **6.4** — Loom demo (3 min).
- [ ] **6.5** — Final cleanup, tag v1.0, share the repo link.

---

## Open questions

_Things that need my input before continuing. Add as they arise._

- [ ] None.

---

## Decisions made

_Architectural decisions made during the project. Each one also gets a full ADR in `docs/decisions/`._

- **Repo name:** `legal-rag-nl`.
- **Cache threshold:** 0.97 is the single canonical value — CLAUDE.md stale 0.95 corrected.
- **Python version:** 3.12.5 (above the 3.11 minimum; no changes needed).
- See `docs/decisions/` for full ADR entries (written as decisions are made in later phases).

---

## Last session summary

**2026-05-08 (session 3):** Phase 2 (ingestion) and Phase 3 (retrieval) completed in full. 16 synthetic HTML legal docs created. Hierarchical chunker preserves Wet→Lid hierarchy as metadata. BM25 + dense + RRF (k=60) + Cohere reranker wired into a single `retrieve()` entry point. RBAC enforced at two complementary stages: BM25 pre-filters before scoring; Qdrant pre-filters before HNSW traversal (TRAP 2). All 51 tests pass. Key fix: qdrant-client 1.17 removed `client.search()` — updated to `client.query_points()` in both `dense.py` and the RBAC integration tests.

Next session starts with **sub-phase 4.1** — agent state schema (LangGraph TypedDict for the CRAG state machine).

**2026-05-08 (session 2):** Phase 1 completed. All 11 concept docs written in `docs/concepts/`. Each covers the concept as it applies specifically to this project: concrete numbers (m=32, ef_construct=256, threshold=0.97, k=60, top-50→top-8), the mathematical reasoning behind each TRAP, and 3 self-check questions per doc. Phase 2 is now current.

---

**2026-05-08 (session 1):** Phase 0 completed. Installed `uv` (was not present), ran `uv init`, replaced stub `pyproject.toml` with full production config. All 143 dependencies locked. Pre-commit hooks installed. Docker Compose up with Qdrant (healthz confirmed) and Redis Stack (ping confirmed). `src/config.py` with Pydantic Settings and 0.97 cache threshold enforced at the type level. Full directory skeleton matching `PROJECT_STRUCTURE.md` created. Smoke test passes. GitHub Actions CI workflow written. Fixed stale doc issues: repo name updated to `legal-rag-nl` across all docs, `0.95` → `0.97` cache threshold in CLAUDE.md.

---

## Velocity log

_Track how long each phase actually took vs. the target. Useful for scheduling the remaining phases._

| Phase | Target | Actual | Notes |
|-------|--------|--------|-------|
| 0     | 0.5d   | ~2h    | uv install added time; otherwise smooth |
| 1     | 1d     | ~1h    | All 11 concept docs written in one session |
| 2     | 2d     | ~2h    | Synthetic corpus + chunker + embed + Qdrant setup + ingestion script |
| 3     | 1.5d   | ~2h    | BM25 + dense + RRF + reranker + retrieve() + 51 tests; qdrant-client 1.17 API migration |
| 4     | 2d     | -      | -     |
| 5     | 1.5d   | -      | -     |
| 6     | 1.5d   | -      | -     |
| **Total** | **10d** | -  | -     |
