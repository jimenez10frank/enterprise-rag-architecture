"""FastAPI HTTP surface for the CRAG legal RAG agent (Phase 5.3).

Startup loads the demo corpus from ``data/raw/`` into a BM25 index and connects
to Qdrant for dense search. The LangGraph compiled in ``build_agent_graph`` is
invoked per request. Semantic cache (Redis) sits in front of the graph; misses
embed the question, run the pipeline, then store the final ``Answer`` in the
role-scoped bucket.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import httpx
import redis
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from src.agent.graph import build_agent_graph
from src.agent.state import AgentState, Answer
from src.api.auth import roles_from_header
from src.config import settings
from src.ingestion.chunker import chunk_directory
from src.ops.cache import SemanticCache, normalize_question
from src.retrieval.bm25 import BM25Index
from src.retrieval.dense import embed_query

logger = logging.getLogger(__name__)


@dataclass
class AppDeps:
    """Dependencies created at application lifespan."""

    bm25_index: BM25Index
    qdrant: QdrantClient
    cache: SemanticCache
    graph: Any  # CompiledStateGraph


def build_app_deps() -> AppDeps:
    """Load corpus, clients, graph — called once on startup."""
    raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    chunks = chunk_directory(raw_dir)
    bm25 = BM25Index(chunks)
    qdrant = QdrantClient(url=settings.qdrant_url)
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    cache = SemanticCache(redis_client=redis_client)
    graph = build_agent_graph(bm25, qdrant, skip_rerank=False)
    return AppDeps(
        bm25_index=bm25,
        qdrant=qdrant,
        cache=cache,
        graph=graph,
    )


class QueryRequest(BaseModel):
    """Body for ``POST /query``."""

    question: str = Field(..., min_length=1, description="User question (Dutch legal/tax)")


class QueryResponse(BaseModel):
    """Structured answer or escalation payload (mirrors ``Answer``)."""

    answer: Answer


router = APIRouter()


def _get_deps(request: Request) -> AppDeps:
    return request.app.state.deps  # type: ignore[no-any-return]


@router.get("/health")
async def health(response: Response) -> dict[str, str]:
    """Liveness: Qdrant, Redis, OpenAI must respond."""
    out: dict[str, str] = {}

    try:
        client = QdrantClient(url=settings.qdrant_url, timeout=5)
        client.get_collections()
        out["qdrant"] = "ok"
        client.close()
    except Exception as exc:  # noqa: BLE001 — health aggregate
        out["qdrant"] = f"error: {exc}"

    try:
        r = redis.Redis.from_url(settings.redis_url, socket_timeout=5)
        if not r.ping():
            out["redis"] = "error: ping returned False"
        else:
            out["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        out["redis"] = f"error: {exc}"

    key = settings.openai_api_key
    if not key:
        out["openai"] = "error: OPENAI_API_KEY not set"
    else:
        try:
            with httpx.Client(timeout=10.0) as http:
                resp = http.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                resp.raise_for_status()
            out["openai"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["openai"] = f"error: {exc}"

    checks = ("qdrant", "redis", "openai")
    if not all(out.get(k) == "ok" for k in checks):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return out


@router.post("/query", response_model=QueryResponse)
async def post_query(
    request: Request,
    response: Response,
    body: QueryRequest,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> QueryResponse:
    """Run RAG pipeline with semantic cache and role-scoped retrieval."""
    roles = roles_from_header(x_user_role)
    deps = _get_deps(request)
    t0 = time.perf_counter()

    query_embedding = embed_query(body.question)
    cached = deps.cache.get_match(query_embedding, roles)
    if cached is not None:
        logger.info("semantic_cache hit for roles=%s", roles)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
        response.headers["X-Cache"] = "HIT"
        return QueryResponse(answer=cached)

    invoke_state = AgentState(original_question=body.question, user_roles=roles)
    graph_out = deps.graph.invoke(invoke_state)
    final = graph_out["final_answer"]
    if final is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent produced no final answer",
        )

    deps.cache.store(
        query_embedding,
        roles,
        normalize_question(body.question),
        final,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    response.headers["X-Cache"] = "MISS"
    return QueryResponse(answer=final)


def create_app(
    *,
    deps_factory: Callable[[], AppDeps] | None = None,
) -> FastAPI:
    """Build the ASGI app. ``deps_factory`` enables tests to inject fakes."""

    factory = deps_factory or build_app_deps

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=logging.INFO)
        app.state.deps = factory()
        yield
        deps_final: AppDeps = app.state.deps
        deps_final.qdrant.close()

    application = FastAPI(
        title="legal-rag-nl",
        description="Dutch legal / fiscal RAG with RBAC and citation enforcement",
        lifespan=lifespan,
        version="0.1.0",
    )
    application.include_router(router)
    return application


app = create_app()
