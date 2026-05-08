# 001. Qdrant over pgvector (production scale)

**Date:** 2026-05-08
**Status:** Accepted
**Phase introduced:** 0–2 (concept); implemented in 2.6–3

## Context

The assessment targets hundreds of thousands of documents and **20M+ chunks** at production scale. The vector database must support efficient **metadata-filtered HNSW search** (RBAC pre-filter before graph traversal), tunable HNSW parameters, and quantization options without exhausting memory.

## Options considered

### Option A: pgvector on PostgreSQL

- **Description:** Store vectors in Postgres alongside relational data.
- **Pros:** Familiar ops, single DB for small teams; fine at moderate scale.
- **Cons:** At 20M+ vectors, recall/latency and filter performance degrade versus purpose-built vector DBs unless heavily tuned (see `TRAPS.md` TRAP 3).

### Option B: Qdrant (self-hostable, Rust core)

- **Description:** Dedicated vector DB with first-class payload indexes and HNSW tuning.
- **Pros:** Strong metadata filtering + quantization; matches assessment narrative on scale.
- **Cons:** Another service to run; team must learn Qdrant ops.

### Option C: Managed-only (e.g. Pinecone)

- **Description:** Fully managed vectors.
- **Pros:** Low ops burden.
- **Cons:** Harder to demonstrate parameter tuning and data-residency story required by the brief.

## Decision

We chose **Option B (Qdrant)** for the **production design and demo implementation**.

Reasoning:

- Assessment asks for explicit **HNSW** and **quantization** parameters — Qdrant exposes these directly (`STACK.md`).
- **RBAC** must be a **server-side pre-filter** at query time; Qdrant payload indexes align with that (`TRAPS.md` TRAP 2).
- pgvector remains **acceptable for smaller deployments** but is **not** the production recommendation at 20M+ chunks.

## Consequences

**What this makes easy:** Documenting recall/latency tradeoffs with `m`, `ef_construct`, `ef`, and scalar int8 quantization in the Phase 6 architecture doc.

**What this makes hard:** Local dev must run Docker Qdrant (mitigated by `docker-compose.yml`).

**Rollback path:** If org standardizes on pgvector-only, write a superseding ADR and migrate collection design — expect rework on filter paths and index tuning.

## References

- `TRAPS.md` TRAP 3
- `STACK.md` (Vector database)
- `src/ingestion/qdrant_setup.py`
