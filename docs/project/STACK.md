# STACK.md — Tech Stack with Rationale

> Every choice here is defensible. When asked "why this and not X?", the answer is in this file. Do not deviate without explicit approval.

---

## Language & runtime

### Python 3.11+
The production AI/ML ecosystem is Python. Type hints have matured to the point my TypeScript habits transfer cleanly. 3.11 specifically: better error messages, faster startup, exception groups (useful for retry/fallback logic in the agent).

### `uv` for package management
Modern, fast (Rust-based) replacement for pip + venv + pip-tools. Lock file is reproducible. Industry signal that the developer keeps up with current tooling. Alternative considered: Poetry. Rejected because uv is faster, simpler, and is what most new 2025+ Python projects ship with.

```bash
# What we'll use:
uv init
uv add langchain langgraph qdrant-client ...
uv run pytest
```

---

## RAG framework

### LangChain (building blocks) + LangGraph (agent loop)
- **LangChain** for: document loaders, text splitters (we override the default), retriever interfaces, prompt templates, output parsers. Industry-standard glue.
- **LangGraph** for: the CRAG state machine in Module 3. It has graph-based control flow with explicit edges/conditions and is the cleanest way to express "if grader says ambiguous, route to rewrite node, else route to generation."

**Why not LlamaIndex?** Better for ingestion in some ways but no equivalent to LangGraph for the agent loop. Mixing both adds cognitive overhead without payoff at this scale.

**Why not raw OpenAI SDK + custom orchestration?** Doable, but reimplementing what LangGraph gives us for free is bad use of time on this project. LangGraph traces are also visible in LangSmith, which is the demo signal.

---

## Vector database

### Qdrant (Docker, locally)
- Rust core: fast, low memory overhead.
- First-class metadata filtering with payload indexes (critical for RBAC — see TRAPS.md TRAP 2).
- Built-in scalar and binary quantization.
- Full HNSW parameter control (`m`, `ef_construct`, `ef`).
- Open source, self-hostable (matters for Tax Authority data residency).
- Excellent Python client.

**Configuration committed for the demo:**
```python
{
  "vectors": {"size": 3072, "distance": "Cosine"},
  "hnsw_config": {"m": 32, "ef_construct": 256},
  "quantization_config": {
    "scalar": {"type": "int8", "quantile": 0.99, "always_ram": True}
  },
  "optimizers_config": {"default_segment_number": 2}
}
```

**Why not pgvector?** Past ~10M vectors, recall and metadata-filter performance degrade. I already used pgvector at Growora — this is the place to demonstrate awareness that production scale needs purpose-built tools. (See TRAPS.md TRAP 3.)

**Why not Pinecone/Weaviate/Milvus?** Pinecone is managed (can't show parameter tuning). Weaviate is fine but heavier and the system doesn't need the added complexity. Milvus is overkill for a demo.

---

## Embeddings

### Demo: OpenAI `text-embedding-3-large` (3072 dims)
Strongest multilingual quality available via API. Dutch legal text needs the multilingual capability. Fast, cheap, high-quality.

### Production: `BAAI/bge-m3` (self-hosted)
Documented in design doc. Multilingual, supports dense+sparse+colbert in one model, MIT licensed, runs on a single GPU. Self-hosting is non-negotiable for classified data. (See TRAPS.md TRAP 10.)

---

## LLM (generation)

### Demo: OpenAI `gpt-4o-mini`
Fast, cheap, structured output support, sufficient for demo. Used for: grader, query decomposer, generator.

### Production: `gpt-4o` or `claude-sonnet-4` for the generator; `gpt-4o-mini` for grader/decomposer (where speed matters more than depth)
Documented in design doc. Self-hosted alternative for classified content: Llama 3.3 70B Instruct via vLLM. Documented but not implemented for the demo.

---

## Reranking

### Cohere `rerank-multilingual-v3.0`
- Industry-standard quality.
- Strong Dutch.
- Free tier covers demo usage.
- Single API call, simple integration.

### Production alternative: `BAAI/bge-reranker-v2-m3` (self-hosted)
Same reasoning as embeddings — classified content cannot leave the cluster. Document in design doc, do not implement for demo.

**Reranker top-K configuration:** retrieve top-50 (per retriever), RRF to top-50 fused, rerank to top-8 for the LLM. (See TRAPS.md TRAP 8.)

---

## Sparse retrieval

### `rank_bm25` (Python, in-process)
For demo scale (hundreds to low thousands of chunks): perfect. Tiny dependency, no extra service.

### Production: Elasticsearch or OpenSearch
Documented in design doc. At 20M chunks the BM25 index needs to be a real service.

---

## Cache

### Redis Stack (with vector index)
The vector index module enables HNSW-based similarity search on cached query embeddings, which is exactly what the semantic cache needs. Runs in Docker.

**Cache key schema:**
```
cache_key = f"{role_hash}:{corpus_version}:{normalized_question_hash}"
```

Plus a separate vector index of `{embedding -> cache_key}` for similarity lookup. Threshold ≥ 0.97. (See TRAPS.md TRAP 5.)

---

## API layer

### FastAPI
Well-suited for this project. Gives us:
- Pydantic-based request/response validation (matches our internal data models).
- Automatic OpenAPI/Swagger docs (demo signal).
- Async support out of the box.
- Easy auth middleware for role headers.

Two endpoints minimum:
- `POST /query` — accepts question + role, returns cited answer.
- `GET /health` — readiness check (Qdrant + Redis + LLM connectivity).

---

## Evaluation

### Ragas
Industry-standard RAG eval library. Computes Faithfulness, Context Precision, Context Recall, Answer Relevancy. Integrates with LangChain.

**Golden dataset:** 50-100 question/answer pairs hand-curated from the demo corpus, with correct citations. Lives in `data/golden/golden_set.jsonl`. CI runs Ragas against it; Faithfulness < 0.95 fails the build.

---

## Observability

### LangSmith (LangChain's tracing)
Free tier covers the demo. Every LangGraph run is traced — node-by-node visibility. Enables the design-doc claim "we observe per-node latency in production."

### Standard logging
Python `logging` module with structured JSON output. Module-level loggers. No print statements.

---

## Local infrastructure

### Docker + docker-compose
One `docker-compose.yml` spins up:
- Qdrant on `localhost:6333` (HTTP) and `:6334` (gRPC).
- Redis Stack on `localhost:6379`.
- The FastAPI app (with hot reload in dev).

Containerization is a requirement for cloud deployment. Docker presence in the repo is non-optional.

---

## Quality tooling

### `ruff` (lint + format)
Replaces Black + isort + flake8 + pyupgrade + many others. Fast, single config block in `pyproject.toml`. Industry default for new Python projects.

### `mypy` (strict mode)
Type checking is non-optional. Every function has return-type hints. Every Pydantic model is properly typed. mypy strict catches bugs before runtime.

### `pytest`
Standard testing framework. Tests live next to the code (`src/ingestion/chunker.py` → `src/ingestion/test_chunker.py`).

### `pre-commit`
Hooks: ruff, mypy, trailing whitespace, large files. Runs on every commit. Prevents bad commits from entering the repo.

---

## CI/CD

### GitHub Actions
Workflow on push and PR:
1. Install with `uv sync`.
2. `ruff check`.
3. `mypy --strict`.
4. `pytest`.
5. Ragas eval against golden set (only on main branch and on label).

Status badges in README.

---

## What we are NOT using (and why, when asked)

- **pgvector** — fine at Growora scale, fails at 20M vectors. (TRAP 3.)
- **Pinecone** — managed, can't show parameter tuning.
- **LlamaIndex** — using LangChain + LangGraph instead; mixing both is unnecessary complexity.
- **DeepEval** — Ragas has more momentum and covers our metrics.
- **Vanilla SQLAlchemy / Postgres** — Qdrant handles vectors, Redis handles cache. Postgres adds nothing for this scope.
- **Celery / RQ / background workers** — not needed; the agent loop is synchronous from the user's perspective. Async ingestion is fine without a job queue at this scale.
- **Helm / Kubernetes manifests** — design doc mentions production deployment patterns but we don't ship k8s manifests. Out of scope.
- **Auth0 / proper OAuth** — RBAC in the demo uses a header-based role token (`X-User-Role`). The design doc specifies real auth (OIDC via Azure AD) for production.
- **Multi-tenant infra** — single tenant for demo. Mention multi-tenant patterns in design doc only if asked.

---

## Versions (pin in `pyproject.toml`)

Use latest stable at project start. Lock file (`uv.lock`) committed to the repo. When asked "why this version" — the answer is "latest stable at project start, locked for reproducibility."
