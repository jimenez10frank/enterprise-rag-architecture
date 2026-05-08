# AI usage during development

> Required by `ASSESSMENT.md`: explain **what AI generated**, **what you wrote**, and **what you learned**. This file is a **living log** — expand it each session so Phase 6 is not written from memory alone.

---

## Tools used

| Tool | Role |
|------|------|
| **Cursor** (agent mode) | Repository-wide edits, running tests, scaffolding modules, refactors aligned with `TRAPS.md` / `STACK.md`. |
| **Claude / ChatGPT** (optional, per `WORKFLOW.md`) | Teaching passes for **concept docs** — you write `docs/concepts/` in your own words after/dialogue, not copy-paste. |
| **Claude Code** | Same class of assistance as Cursor when noted in session summaries (`PROGRESS.md`). |

---

## What AI generated vs what you (human) must own

| Area | Typical AI contribution | What you should **own** (understanding + defense) |
|------|-------------------------|---------------------------------------------------|
| **Boilerplate** | Package layout, test scaffolds, CI YAML patterns | Why each module boundary exists (`PROJECT_STRUCTURE.md`). |
| **TRAP-aligned code** | Qdrant filter placement, RRF, reranker top-K wiring | **Why** post-filter leaks (TRAP 2); **why** RRF not alpha (TRAP 4). |
| **LangGraph** | Node wiring, conditional edges, Pydantic state | Three-way grader semantics and escalation vs guessing (TRAP 7). |
| **Concept docs** | Explanations in chat | **Your** prose in `docs/concepts/` + self-check questions. |
| **ADRs** | Draft ADR bodies from project context | **Accept/reject** decisions; add organizational constraints. |

**Non-delegable:** Claiming exam readiness without reading `TRAPS.md` + being able to explain RBAC pre-filter and citation enforcement aloud.

---

## Prompt patterns that worked

From `WORKFLOW.md`:

- **Session start:** Read `ASSESSMENT.md` → `PROGRESS.md` first; no code until aligned.
- **Sub-phase:** Paste ROADMAP goal + “do not violate TRAP X” constraints.
- **Review:** “Flag technical inaccuracies only” on your own concept drafts.

Record **one real prompt + outcome** per week below when you have a standout example:

- _TODO — add examples during Phase 5–6._

---

## Phase-by-phase log (high level)

| Phase | AI role (summary) | Your verification |
|-------|-------------------|-------------------|
| 0 | Env, Docker, CI, skeleton | Ran infra locally; CI green. |
| 1 | Tutoring for eleven concepts | You wrote or reviewed each concept file. |
| 2 | Chunker, embed cache, Qdrant setup, ingest CLI | TRAP 1 guard tests; RBAC integration tests. |
| 3 | BM25, dense, RRF, rerank, `retrieve()` | 51 tests; no alpha fusion. |
| 4 | LangGraph CRAG, citation validation, test doubles | 67 tests; routing tested with stubs. |
| 5–6 | _Upcoming_ | Cache + API + Ragas + design doc + README |

Session-level detail is mirrored in **`PROGRESS.md` → Last session summary**.

---

## What was hard *despite* AI

Honest bullets (fill as you go — evaluators value this):

- Balancing **ROADMAP literalism** (50 real docs) vs **velocity** → captured as **ADR-011**.
- Dependency/API churn (e.g. Qdrant client) requiring **tests** and doc updates, not blind codegen.
- Keeping **RBAC** out of LLM prompts while still passing **`user_roles`** only into retrieval.

---

## What you learned (running list)

_Add bullets over time; AI-assisted learning still counts if you can teach it back._

- RBAC at **query** stage vs after retrieval.
- Why **RRF** beats score fusion for BM25 + cosine ranks.
- CRAG **ambiguous** vs **irrelevant** routing.
- Citation enforcement needs **schema + code validation**, not prompts alone.

---

## Links

- Architectural decisions: [`docs/decisions/DECISIONS_INDEX.md`](./decisions/DECISIONS_INDEX.md)
- Non-negotiables: [`TRAPS.md`](../TRAPS.md)
- Live progress: [`PROGRESS.md`](../PROGRESS.md)
