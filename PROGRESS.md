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

**Phase 1 — Concept docs**
Started: 2026-05-08
Target completion: 2026-05-09

---

## Done

- [x] **0.1** — GitHub repo `legal-rag-nl` created, MD files committed, `.gitignore` in place.
- [x] **0.2** — `uv` installed, `pyproject.toml` written with full dep list, ruff + mypy strict config, 143 packages locked in `uv.lock`.
- [x] **0.3** — `.pre-commit-config.yaml` created (ruff, mypy, standard hooks), hooks installed.
- [x] **0.4** — `docker-compose.yml` written; Qdrant (port 6333/6334) and Redis Stack (port 6379/8001) verified up and healthy.
- [x] **0.5** — `.env.example` with all required vars; `src/config.py` with Pydantic Settings singleton (0.97 cache threshold enforced via `ge` constraint).
- [x] **0.6** — Full directory skeleton from `PROJECT_STRUCTURE.md` created; empty `__init__.py` files in all packages; `src/test_smoke.py` passes.
- [x] **0.7** — `.github/workflows/ci.yml` written (uv install → ruff → mypy → pytest on every push).

---

## Doing now

- [ ] **1.1** — Concept doc: vectors and embeddings. *(I read + write; agent teaches and reviews.)*

---

## Next (in order)

- [ ] **1.2** — Concept doc: HNSW.
- [ ] **1.3** — Concept doc: quantization.
- [ ] **1.4** — Concept doc: BM25 vs dense.
- [ ] **1.5** — Concept doc: RRF.
- [ ] **1.6** — Concept doc: reranking and cross-encoders.
- [ ] **1.7** — Concept doc: hierarchical chunking.
- [ ] **1.8** — Concept doc: RBAC at the retrieval layer.
- [ ] **1.9** — Concept doc: LangGraph and CRAG.
- [ ] **1.10** — Concept doc: semantic caching.
- [ ] **1.11** — Concept doc: RAG evaluation.
- [ ] **2.1** — Source 50 real legal documents from wetten.overheid.nl.
- [ ] **2.2** — Define ChunkMetadata schema.
- [ ] **2.3** — Build hierarchical chunker.
- [ ] **2.4** — Chunker tests.
- [ ] **2.5** — Embedding pipeline with caching.
- [ ] **2.6** — Qdrant collection setup.
- [ ] **2.7** — Bulk ingestion script.
- [ ] **2.8** — Smoke-test retrieval, RBAC test.
- [ ] **3.1** — BM25 index.
- [ ] **3.2** — Dense retrieval with RBAC pre-filter.
- [ ] **3.3** — RRF fusion.
- [ ] **3.4** — Cohere reranker integration.
- [ ] **3.5** — End-to-end retrieve().
- [ ] **3.6** — Retrieval tests.
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

**2026-05-08:** Phase 0 completed in one session. Installed `uv` (was not present), ran `uv init`, replaced stub `pyproject.toml` with full production config. All 143 dependencies locked. Pre-commit hooks installed. Docker Compose up with Qdrant (healthz confirmed) and Redis Stack (ping confirmed). `src/config.py` with Pydantic Settings and 0.97 cache threshold enforced at the type level. Full directory skeleton matching `PROJECT_STRUCTURE.md` created. Smoke test passes. GitHub Actions CI workflow written. Fixed stale doc issues: repo name updated to `legal-rag-nl` across all docs, `0.95` → `0.97` cache threshold in CLAUDE.md.

Next session starts with **sub-phase 1.1** — learn about vectors and embeddings (via Claude.ai chat), write `docs/concepts/01-vectors-and-embeddings.md` in your own words, then paste it here for review.

---

## Velocity log

_Track how long each phase actually took vs. the target. Useful for scheduling the remaining phases._

| Phase | Target | Actual | Notes |
|-------|--------|--------|-------|
| 0     | 0.5d   | ~2h    | uv install added time; otherwise smooth |
| 1     | 1d     | -      | -     |
| 2     | 2d     | -      | -     |
| 3     | 1.5d   | -      | -     |
| 4     | 2d     | -      | -     |
| 5     | 1.5d   | -      | -     |
| 6     | 1.5d   | -      | -     |
| **Total** | **10d** | -  | -     |
