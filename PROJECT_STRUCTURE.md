# PROJECT_STRUCTURE.md — Directory Layout

> Authoritative reference for where files go. Update this if new directories are introduced.

---

## Top-level layout

```
legal-rag-nl/
├── README.md                      ← Front door. Quick-start + links.
├── CLAUDE.md                      ← Agent context (auto-read by Claude Code).
├── ASSESSMENT.md                  ← System requirements and scope.
├── TRAPS.md                       ← Critical gotchas. Re-read every session.
├── STACK.md                       ← Tech choices and rationale.
├── ROADMAP.md                     ← Phase plan with sub-phases.
├── PROGRESS.md                    ← Living state tracker.
├── PROJECT_STRUCTURE.md           ← This file.
├── WORKFLOW.md                    ← Prompt patterns for Claude Code.
├── pyproject.toml                 ← Python project config (uv, ruff, mypy, pytest).
├── uv.lock                        ← Reproducible dep versions.
├── .python-version                ← 3.11
├── .env.example                   ← Required env vars (template).
├── .env                           ← Local secrets (NOT committed).
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml             ← Qdrant + Redis Stack + (optional) FastAPI.
├── Makefile                       ← `make up`, `make down`, `make ingest`, etc.
│
├── .github/
│   └── workflows/
│       ├── ci.yml                 ← ruff, mypy, pytest on every push.
│       └── eval.yml               ← Ragas eval on main branch (manual trigger).
│
├── docs/
│   ├── concepts/                  ← My learning notes (Phase 1).
│   │   ├── 01-vectors-and-embeddings.md
│   │   ├── 02-hnsw.md
│   │   ├── 03-quantization.md
│   │   ├── 04-bm25-vs-dense.md
│   │   ├── 05-rrf.md
│   │   ├── 06-reranking.md
│   │   ├── 07-hierarchical-chunking.md
│   │   ├── 08-rbac-pre-filter.md
│   │   ├── 09-langgraph-crag.md
│   │   ├── 10-semantic-cache.md
│   │   └── 11-rag-evaluation.md
│   │
│   ├── decisions/                 ← ADRs. Numbered, not deleted.
│   │   ├── 001-qdrant-over-pgvector.md
│   │   ├── 002-rrf-over-alpha-fusion.md
│   │   ├── 003-pre-filter-rbac.md
│   │   └── ...
│   │
│   ├── design/
│   │   ├── architecture.md        ← The submitted design doc.
│   │   └── diagrams/              ← Mermaid sources, exported PNGs.
│   │
│   └── AI_USAGE.md                ← How AI was used during the project.
│
├── src/                           ← All Python code.
│   ├── __init__.py
│   ├── config.py                  ← Pydantic Settings, env loading.
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── schema.py              ← Chunk, ChunkMetadata Pydantic models.
│   │   ├── chunker.py             ← Hierarchical legal chunker.
│   │   ├── test_chunker.py
│   │   ├── embed.py               ← Embedding pipeline (OpenAI, with caching).
│   │   ├── test_embed.py
│   │   └── qdrant_setup.py        ← Collection creation, index params.
│   │
│   ├── retrieval/
│   │   ├── __init__.py            ← Top-level retrieve(query, roles).
│   │   ├── bm25.py                ← Sparse retriever.
│   │   ├── dense.py               ← Qdrant query with RBAC filter.
│   │   ├── fusion.py              ← RRF.
│   │   ├── rerank.py              ← Cohere reranker.
│   │   └── tests/
│   │       ├── test_bm25.py
│   │       ├── test_dense.py
│   │       ├── test_fusion.py
│   │       ├── test_rerank.py
│   │       └── test_e2e_retrieve.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py               ← AgentState Pydantic model.
│   │   ├── graph.py               ← LangGraph build + compile.
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── decompose.py
│   │   │   ├── retrieve.py
│   │   │   ├── grade.py
│   │   │   ├── rewrite.py
│   │   │   ├── escalate.py
│   │   │   └── generate.py
│   │   └── tests/
│   │       └── test_graph.py
│   │
│   ├── ops/
│   │   ├── __init__.py
│   │   ├── cache.py               ← Redis semantic cache.
│   │   └── test_cache.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                ← FastAPI app.
│   │   ├── routes.py
│   │   ├── auth.py                ← Role header parsing.
│   │   └── test_api.py
│   │
│   └── eval/
│       ├── __init__.py
│       ├── ragas_runner.py
│       └── test_ragas_runner.py
│
├── scripts/                       ← Top-level CLI entry points.
│   ├── ingest.py                  ← Ingestion pipeline (Phase 2.7).
│   ├── eval.py                    ← Run Ragas locally.
│   └── generate_golden.py         ← Helper to bootstrap the golden set.
│
└── data/                          ← Source documents and derived artifacts.
    ├── raw/                       ← Downloaded legal docs (HTML/PDF).
    │   └── README.md              ← Source URLs and download dates.
    ├── embeddings/                ← Cached embeddings (gitignored).
    └── golden/
        └── golden_set.jsonl       ← Hand-curated Q&A pairs.
```

---

## Conventions

### Tests next to code
Tests live next to the module they test (`chunker.py` → `test_chunker.py`). For modules with several tests, use a `tests/` subdirectory inside the package.

### One responsibility per file
A module is a unit of cohesion. If `chunker.py` grows to 400+ lines, split (e.g., `chunker_legal.py`, `chunker_ecli.py`, `chunker_fallback.py`).

### Top-level scripts in `scripts/`, not `src/`
`scripts/` are CLI entry points (`python scripts/ingest.py`). `src/` is library code, never run directly.

### Data directories
- `data/raw/` — committed (we want the demo corpus to be reproducible).
- `data/embeddings/` — gitignored (large, regenerable).
- `data/golden/` — committed (the eval set is part of the required artifacts).

### Imports
- Absolute imports only (`from src.retrieval import retrieve`), no relative imports.
- Type-checked at strict mode. No `Any` without a comment explaining why.

### Async vs sync
- API layer (FastAPI) is async.
- Core retrieval and agent logic is sync (LangGraph supports both; sync is simpler for this scope).
- Embedding and Qdrant calls are sync. Document why we did not parallelize (simpler, demo scale doesn't need it).

---

## Naming

- Files and directories: `lowercase_with_underscores.py`.
- Classes: `PascalCase`.
- Functions and variables: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Pydantic models that represent external API shapes: suffix with `Request` / `Response`.
- Pydantic models that represent internal data: just the noun (`Chunk`, `Answer`).

---

## Things that do NOT belong in this repo

- API keys, secrets, real Belastingdienst data.
- Generated artifacts (embeddings, large data files) — gitignore them.
- Personal scratch notes — keep those elsewhere.
- Output from old runs — clean up before commit.
- Commented-out code — delete it. Git remembers.
