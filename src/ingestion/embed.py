"""Embedding pipeline with disk caching.

Calls OpenAI text-embedding-3-large in batches and caches results to
data/embeddings/<chunk_id>.json. Re-running ingestion after a partial
failure resumes from the cache rather than re-billing the API.

Production note: swap the model for BAAI/bge-m3 (self-hosted) for any
classified content. Sending classified text to the OpenAI API is a data
residency / GDPR violation for the Belastingdienst. See TRAPS.md TRAP 10.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from src.config import settings
from src.ingestion.schema import Chunk

logger = logging.getLogger(__name__)

# OpenAI allows up to 2048 inputs per call; 100 is a conservative safe batch.
_BATCH_SIZE = 100


def _cache_path(cache_dir: Path, chunk_id: str) -> Path:
    # Chunk IDs may contain slashes or characters invalid in filenames on some
    # OS — replace them. IDs in this project only use [a-zA-Z0-9_-] so this is
    # currently a no-op, but it's cheap insurance for future changes.
    safe_id = chunk_id.replace("/", "_").replace("\\", "_")
    return cache_dir / f"{safe_id}.json"


def _load_cached(cache_dir: Path, chunk_id: str) -> list[float] | None:
    p = _cache_path(cache_dir, chunk_id)
    if not p.exists():
        return None
    data: list[float] = json.loads(p.read_text(encoding="utf-8"))
    return data


def _save_cached(cache_dir: Path, chunk_id: str, embedding: list[float]) -> None:
    _cache_path(cache_dir, chunk_id).write_text(json.dumps(embedding), encoding="utf-8")


def embed_chunks(
    chunks: list[Chunk],
    cache_dir: Path,
    *,
    force: bool = False,
) -> dict[str, list[float]]:
    """Embed a list of chunks, using disk cache to avoid redundant API calls.

    Args:
        chunks: Chunks to embed. Order is preserved for progress display.
        cache_dir: Directory for per-chunk .json cache files.
        force: Re-embed even if a cached result exists.

    Returns:
        Mapping from chunk_id to embedding vector (3072 floats).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=settings.openai_api_key)

    results: dict[str, list[float]] = {}
    to_embed: list[Chunk] = []

    for chunk in chunks:
        if not force:
            cached = _load_cached(cache_dir, chunk.chunk_id)
            if cached is not None:
                results[chunk.chunk_id] = cached
                continue
        to_embed.append(chunk)

    if not to_embed:
        logger.info("All %d embeddings served from cache.", len(results))
        return results

    logger.info(
        "Embedding %d chunks via API (%d served from cache).",
        len(to_embed),
        len(results),
    )

    for i in tqdm(range(0, len(to_embed), _BATCH_SIZE), desc="Embedding"):
        batch = to_embed[i : i + _BATCH_SIZE]
        texts = [c.text for c in batch]

        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
            dimensions=settings.embedding_dimensions,
        )

        for chunk, emb_obj in zip(batch, response.data, strict=False):
            vec: list[float] = emb_obj.embedding
            results[chunk.chunk_id] = vec
            _save_cached(cache_dir, chunk.chunk_id, vec)

    return results
