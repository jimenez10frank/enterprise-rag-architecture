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

**Phase 6 — complete (implementation + docs in repo).**
Manual steps remaining (not automated): record **Loom** and paste URL into `README.md`; on GitHub set repo **description + topics**; tag **`v1.0`** and publish release when ready.

Started: 2026-05-08
Target completion: done in-tree; release polish is owner-driven

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
- [x] **4.1** — Agent state schema (`src/agent/state.py`): `AgentState`, `Answer`, `Citation`, `GradeResult`, `DecompositionResult`; Pydantic validation for cited vs unanswerable answers (TRAP 6).
- [x] **4.2** — Query decomposition node (`src/agent/nodes/decompose.py`): gpt-4o-mini structured output → one or more sub-questions.
- [x] **4.3** — Retrieval node (`src/agent/nodes/retrieve.py`): calls Phase 3 `retrieve()` per sub-question, dedupes chunks; `skip_rerank` for tests/offline.
- [x] **4.4** — Grader node (`src/agent/nodes/grade.py`): three-way `relevant` / `ambiguous` / `irrelevant`; empty context short-circuit (no LLM).
- [x] **4.5** — LangGraph (`src/agent/graph.py`): `decompose → retrieve → grade` with conditional edges; ambiguous + `retry_count < 1` → `rewrite → retrieve`; else irrelevant/ambiguous-exhausted → `escalate`; relevant → `generate`. `AgentNodeOverrides` for test doubles.
- [x] **4.6** — Generation (`src/agent/nodes/generate.py`): structured `Answer`, post-validation (chunk_id, artikel consistency, verbatim quote / fuzzy longest-run ≥0.9); one repair pass then escalate.
- [x] **4.7** — Agent tests: `test_state.py`, `test_graph.py` (routing + stubbed e2e), `test_generate_validation.py`, `test_grade_offline.py` — **67 tests** total suite (including prior 51).
- [x] **4.x** — Shared `src/agent/llm_factory.py` (OpenAI structured output wiring).
- [x] **5.1** — Semantic cache: `src/ops/cache.py` (Redis LIST buckets by `role_hash` + `corpus_version`, cosine ≥ 0.97, 24h TTL). Tests `src/ops/test_cache.py`. ADR **013**.
- [x] **5.2** — Agent RBAC integration: `src/agent/tests/test_rbac_agent_integration.py` (helpdesk + FIOD-only corpus → empty retrieval → irrelevant → escalate).
- [x] **5.3** — FastAPI: `src/api/main.py` (`POST /query` with `X-User-Role`, `GET /health`, cache, `X-Process-Time-Ms` / `X-Cache` headers), `src/api/auth.py`, tests `src/api/test_api.py`.
- [x] **5.4** — Ragas harness: `src/eval/ragas_runner.py`, CLI `scripts/eval.py` (`--skip-rerank`, `--faithfulness-min`), tests `src/eval/test_ragas_runner.py`.
- [x] **5.5** — Golden set: `data/golden/golden_set.jsonl` (18 rows: answered, escalated, RBAC, OOD).
- [x] **5.6** — Workflow `.github/workflows/eval.yml` (main + manual; Qdrant + Redis service containers; ingest + Ragas gate when `OPENAI_API_KEY` present).
- [x] **6.1** — Architecture design doc: `docs/design/architecture.md` (four ASSESSMENT modules, mermaid diagrams, parameters, TRAPS matrix, demo vs production, future work).
- [x] **6.2** — README rewrite: project summary, quick start, architecture mermaid, links, CI badge, Loom placeholder.
- [x] **6.3** — AI usage writeup completed for submission: `docs/AI_USAGE.md` (tools, prompts, phase table, difficulties, learnings).
- [x] **6.4** — Loom: README section + script pointer to `ROADMAP.md` Phase 6.4; **owner records video and pastes URL**.
- [x] **6.5** — Codebase TODOs in `src/` none; **pytest** green locally (2026-05-08). Lint/type-check as in GitHub Actions. **Not committed** per session request. **v1.0 tag / GitHub topics** remain manual.

---

## Doing now

_None — all roadmap sub-phases delivered in repository._

---

## Open questions

_Things that need my input before continuing. Add as they arise._

- [ ] Optional **comprehension Q&A** for Phase 6 closure per `WORKFLOW.md` (human ritual).

---

## Decisions made

_Architectural decisions live as ADRs in `docs/decisions/`. Summaries also appear in `docs/decisions/DECISIONS_INDEX.md` (includes **alignment table** vs `ASSESSMENT.md`)._

- **001–010:** Core stack and TRAP-aligned choices (Qdrant, RRF, RBAC pre-filter, three-way grader, cache threshold, citations, embeddings split, LangGraph, reranker, Faithfulness CI) — see index.
- **011:** Interim **synthetic** demo corpus (`data/raw/`) vs full real harvest in `ROADMAP` 2.1 — scope documented for reviewers.
- **012:** Pydantic `AgentState` + `AgentNodeOverrides` for testable LangGraph routing.
- **013:** Redis LIST + per-bucket linear scan for semantic cache at demo scale (upgrade path: RediSearch KNN).
- **AI / process log:** `docs/AI_USAGE.md` (Phase 6 submission refresh).
- **Legacy bullets:** Repo name `legal-rag-nl`; cache threshold **0.97** canonical; Python **3.12.5** (local) / CI **3.11**.

---

## Last session summary

**2026-05-08 (session 6 — Phase 6):** Delivered **`docs/design/architecture.md`** (full production-scale design mapped to `ASSESSMENT.md` + every `TRAPS.md` item), **`README.md`** front page (badges → `jimenez10frank/Enterprise-RAG-Architecture`, quick start, doc map, Loom placeholder), **`docs/AI_USAGE.md`** submission structure with real prompt examples and phase ownership table. Minor doc polish: `CONCEPTS_INDEX.md` template line, Faithfulness **≥ 0.95** gate called out in architecture; fixed CRAG mermaid note syntax. **Verification:** `python -m pytest` → **82 passed, 1 skipped** on Windows (global Python 3.12; `ruff`/`mypy` modules not installed in that interpreter — **CI** in `.github/workflows/ci.yml` still runs lint + type-check). **No git commit** per request. **Still manual:** Loom URL in README, GitHub description/topics, `git tag v1.0`.

**2026-05-08 (session 5):** Phase **5** completed end-to-end (not committed per request). Semantic cache (TRAP 5: ≥0.97, role + corpus buckets), FastAPI + cache headers, 18-row golden `jsonl`, Ragas runner (Faithfulness mean gate on **answered** subset), `eval.yml` on `main` with optional API key skip. New tests: ops cache, API (TestClient + lifespan), eval loader/builder, agent RBAC integration. Full suite: **82 pytest** passed, **1 skipped** (optional Redis integration). **Comprehension Q&A** for Phase 5 per `WORKFLOW.md` / `ROADMAP.md` is still for the human to close before ticking ritual “done.”

**2026-05-08 (session 4):** Phase 4 completed. LangGraph CRAG pipeline with Pydantic `AgentState`, decomposition, hybrid retrieval per sub-question, three-way grading (TRAP 7), single rewrite loop, escalation without LLM generation from bad context, and generation with citation validation + one repair attempt (TRAP 6). RBAC remains pre-filter only inside `retrieve()` (TRAP 2). `build_agent_graph(bm25, qdrant, ...)` compiles the graph; `AgentNodeOverrides` enables fully stubbed routing tests without OpenAI/Qdrant. Suite: **67 pytest** tests passing (not committed per session request).

**2026-05-08 (session 3):** Phase 2 (ingestion) and Phase 3 (retrieval) completed in full. 16 synthetic HTML legal docs created. Hierarchical chunker preserves Wet→Lid hierarchy as metadata. BM25 + dense + RRF (k=60) + Cohere reranker wired into a single `retrieve()` entry point. RBAC enforced at two complementary stages: BM25 pre-filters before scoring; Qdrant pre-filters before HNSW traversal (TRAP 2). All 51 tests pass. Key fix: qdrant-client 1.17 removed `client.search()` — updated to `client.query_points()` in both `dense.py` and the RBAC integration tests.

**2026-05-08 (session 2):** Phase 1 completed. All 11 concept docs written in `docs/concepts/`. Each covers the concept as it applies specifically to this project: concrete numbers (m=32, ef_construct=256, threshold=0.97, k=60, top-50→top-8), the mathematical reasoning behind each TRAP, and 3 self-check questions per doc. Phase 2 is now current.

---

**2026-05-08 (session 1):** Phase 0 completed. Installed `uv` (was not present), ran `uv init`, replaced stub `pyproject.toml` with full production config. All 143 dependencies locked. Pre-commit hooks installed. Docker Compose up with Qdrant (healthz confirmed) and Redis Stack (ping confirmed). `src/config.py` with Pydantic Settings and 0.97 cache threshold enforced at the type level. Full directory skeleton matching `PROJECT_STRUCTURE.md` created. Smoke test passes. GitHub Actions CI workflow written. Fixed stale doc issues: repo name updated to `legal-rag-nl` across all docs, `0.95` → `0.97` cache threshold in CLAUDE.md.

---

## Velocity log

| Phase | Target | Actual | Notes |
|-------|--------|--------|-------|
| 0 | 0.5d | ~2h | uv install added time; otherwise smooth |
| 1 | 1d | ~1h | All 11 concept docs written in one session |
| 2 | 2d | ~2h | Synthetic corpus + chunker + embed + Qdrant setup + ingestion script |
| 3 | 1.5d | ~2h | BM25 + dense + RRF + reranker + retrieve() + 51 tests; qdrant-client 1.17 API migration |
| 4 | 2d | ~1 session | LangGraph CRAG + tests |
| 5 | 1.5d | ~1 session | Cache, API, golden+Ragas, eval workflow |
| 6 | 1.5d | ~1 session | Design README AI_USAGE; Loom/video + v1.0 tag manual |
| **Total** | **10d** | - | |
