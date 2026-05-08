# AI usage during development

> Required by `ASSESSMENT.md`: explain **what AI generated**, **what you wrote**, and **what you learned**. This file is the submission-ready writeup for Phase 6.3; session-level detail also appears in [`PROGRESS.md`](../PROGRESS.md).

---

## Tools used

| Tool | Role |
|------|------|
| **Cursor** (agent mode) | End-to-end implementation: modules under `src/`, tests, Docker/CI YAML, scripts, docs aligned with `TRAPS.md` and `STACK.md`. |
| **Claude / ChatGPT** (optional) | Teaching passes for **concept docs** per `WORKFLOW.md`: explanations in chat, then **your** prose in `docs/concepts/`. |
| **Claude Code** | Same class of assistance as Cursor when noted in progress summaries. |

No single tool owned “architecture”: constraints came from **`ASSESSMENT.md`**, **`TRAPS.md`**, and human review.

---

## What AI generated vs what you (the human) must own

| Area | Typical AI contribution | What you should **own** (understanding + defense) |
|------|-------------------------|-----------------------------------------------------|
| **Boilerplate** | Package layout, pytest structure, GitHub Actions patterns | Why module boundaries match `PROJECT_STRUCTURE.md`. |
| **TRAP-aligned code** | Qdrant filter placement, RRF, reranker top-K, cache key shape | **Why** post-retrieval RBAC leaks (TRAP 2); **why** RRF not alpha fusion (TRAP 4). |
| **LangGraph** | Node wiring, conditional edges, `AgentNodeOverrides` for tests | Three-way grader semantics; when to escalate vs retry (TRAP 7). |
| **Concept docs** | Explanations in chat | **Your** wording in `docs/concepts/`; self-check questions you can answer aloud. |
| **ADRs / design doc** | Drafts from project context | Accept/reject trade-offs; align with org constraints (e.g. data residency). |
| **Phase 6 polish** | README, `docs/design/architecture.md` structure | Accuracy check against real `src/` behavior; Loom script and recording. |

**Non-delegable:** Explaining RBAC pre-filter and citation enforcement without reading **`TRAPS.md`**.

---

## Prompt patterns used (from `WORKFLOW.md`, with examples)

### Session start (alignment before code)

Paste the ritual from `WORKFLOW.md`: read `ASSESSMENT.md` → `PROGRESS.md` → `TRAPS.md` → … then summarize phase, next step, contradictions, questions — **no code in the first reply**.

**Example (abbreviated):** *“Read PROGRESS.md and TRAPS.md. We are on Phase 5.3. Next: FastAPI `/query` with `X-User-Role`. List any conflict between STACK.md and the latest qdrant-client API before coding.”*

Outcome: agent surfaced API migration (`query_points` vs `search`) before editing `dense.py`.

### Sub-phase with explicit TRAP pins

Use the roadmap sub-phase **plus** trap numbers so shortcuts are visible.

**Example:** *“Implement `src/retrieval/fusion.py` for ROADMAP 3.3. TRAP 4: RRF only, k=60; no alpha-weighted fusion. Add tests for overlapping and disjoint rankings.”*

Outcome: `test_rrf_not_alpha_weighted` and rank-only fusion stayed enforced.

### Mid-implementation correction

**Example:** *“Stop: RBAC must not be a Python filter after Qdrant returns. Show where the Filter is attached to the query in `dense.py`.”*

Outcome: pre-HNSW filter placement stayed correct.

### Review of human-written docs

**Example:** *“Read `docs/concepts/08-rbac-pre-filter.md`. Flag technical inaccuracies only; do not rewrite my voice.”*

Outcome: nuance fixes without flattening the learner’s phrasing.

---

## Phase-by-phase breakdown (AI vs you)

| Phase | What AI / Cursor typically generated | What you verified or wrote |
|-------|--------------------------------------|----------------------------|
| **0** | `pyproject.toml`, Docker Compose, CI skeleton, `Settings` | Ran `docker compose up`, pytest locally; confirmed `.env.example`. |
| **1** | Tutoring in chat | Eleven concept files **in your words** + `CONCEPTS_INDEX.md`. |
| **2** | `ChunkMetadata`, hierarchical chunker, embed cache, Qdrant setup, `scripts/ingest.py` | TRAP 1 guard tests; FIOD vs public RBAC in chunker tests. |
| **3** | BM25 + dense + RRF + Cohere rerank + `retrieve()` | 51 tests; confirmed no score fusion; qdrant-client 1.17 migration. |
| **4** | LangGraph CRAG, grade/generate nodes, citation validation | Routing tests with stubs; three-way grader behavior. |
| **5** | Semantic cache, FastAPI, Ragas runner, golden `jsonl`, `eval.yml` | Cache TRAP 5 thresholds; Faithfulness gate semantics; API headers. |
| **6** | `docs/design/architecture.md`, README, this `AI_USAGE.md` refresh | Cross-check numbers against `src/config.py` and `qdrant_setup.py`; record Loom link when filmed. |

---

## What was hard *despite* AI

- **ROADMAP literalism** (50 live `wetten` docs) vs delivery time → captured as **ADR-011** (synthetic demo corpus with honest scope note).
- **Library churn** (e.g. Qdrant client surface) → fixes driven by tests and runtime errors, not by trusting generated snippets.
- **Keeping RBAC out of the LLM** while still passing `user_roles` only into retrieval/cache — easy to “helpfully” leak role hints into prompts; required deliberate boundaries in `retrieve.py` / API layer.
- **Evaluation cost**: Ragas + full agent on golden set needs keys and time; CI is gated and documented accordingly.

---

## What you learned (concrete list)

- RBAC belongs at **vector query** time, not after retrieval — the “gap leakage” argument is the exam answer.
- **RRF** avoids score calibration between BM25 and cosine; `k=60` is the standard default.
- **Semantic cache** must use a **high** threshold (here ≥ 0.97) and **role** (and corpus) keying for fiscal/legal text.
- **Structured output + post-validation** beats “please cite your sources” for citations.
- **CRAG** needs **three** grades: ambiguous is not the same as irrelevant; rewrite budget must be bounded.
- **Faithfulness** is the right **deploy blocker** metric for legal RAG; the others are diagnostic.

---

## Phase 6 completion note

- **Design doc:** [`docs/design/architecture.md`](./design/architecture.md)
- **README:** quick start, badges, links to concepts, decisions, and this file
- **Demo:** Loom URL placeholder in README until you record
- **Release hygiene:** `v1.0` tag and GitHub topics — manual steps listed in [`PROGRESS.md`](../PROGRESS.md) (not done by agent)

---

## Links

- Architectural decisions: [`docs/decisions/DECISIONS_INDEX.md`](./decisions/DECISIONS_INDEX.md)
- Non-negotiables: [`TRAPS.md`](../TRAPS.md)
- Live progress: [`PROGRESS.md`](../PROGRESS.md)
- System overview (submitted design): [`docs/design/architecture.md`](./design/architecture.md)
