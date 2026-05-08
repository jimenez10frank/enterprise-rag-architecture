"""Bulk ingestion script: HTML → Qdrant.

Reads all HTML files from data/raw/, chunks them hierarchically, embeds
them via OpenAI, and upserts the vectors + metadata to Qdrant.

Usage:
    python scripts/ingest.py                # normal run (uses disk cache)
    python scripts/ingest.py --recreate     # drop and rebuild the collection
    python scripts/ingest.py --dry-run      # chunk + embed only, skip Qdrant

The embedding cache in data/embeddings/ means re-running after a partial
failure costs $0 — only un-cached chunks call the API.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path

# Ensure project root is importable when running as a plain script.
sys.path.insert(0, str(Path(__file__).parents[1]))

from tqdm import tqdm

from src.config import settings
from src.ingestion.chunker import chunk_directory
from src.ingestion.embed import embed_chunks
from src.ingestion.qdrant_setup import create_collection
from src.ingestion.schema import Chunk

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parents[1] / "data" / "raw"
CACHE_DIR = Path(__file__).parents[1] / "data" / "embeddings"

# Namespace for deterministic UUID generation from chunk_ids.
# Using NAMESPACE_DNS is conventional; the value doesn't matter as long as it's stable.
_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _chunk_id_to_point_id(chunk_id: str) -> str:
    """Convert a human-readable chunk_id to a Qdrant-compatible UUID string.

    Qdrant point IDs must be either unsigned integers or UUID strings.
    We use UUID5 (deterministic from the chunk_id) so that:
      - Re-ingestion produces the same point IDs → upserts are idempotent.
      - The original chunk_id is still stored in the payload for retrieval.
    """
    return str(uuid.uuid5(_UUID_NAMESPACE, chunk_id))


def _upsert_to_qdrant(
    client: object,  # QdrantClient — typed loosely to avoid import at top for --dry-run
    chunks: list[Chunk],
    embeddings: dict[str, list[float]],
    batch_size: int = 64,
) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    assert isinstance(client, QdrantClient)

    points_with_embeddings = [
        (chunk, embeddings[chunk.chunk_id]) for chunk in chunks if chunk.chunk_id in embeddings
    ]

    skipped = len(chunks) - len(points_with_embeddings)
    if skipped:
        logger.warning("%d chunks had no embedding — skipped.", skipped)

    for i in tqdm(
        range(0, len(points_with_embeddings), batch_size),
        desc="Upserting to Qdrant",
    ):
        batch = points_with_embeddings[i : i + batch_size]
        points = [
            PointStruct(
                id=_chunk_id_to_point_id(chunk.chunk_id),
                vector=embedding,
                payload={
                    # Store chunk_id in payload for retrieval-time lookup.
                    "chunk_id": chunk.chunk_id,
                    **chunk.metadata.model_dump(mode="json"),
                },
            )
            for chunk, embedding in batch
        ]
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
        )

    logger.info(
        "Upserted %d points to '%s'.", len(points_with_embeddings), settings.qdrant_collection
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest legal documents into Qdrant.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk and embed only — skip Qdrant upsert.",
    )
    parser.add_argument(
        "--force-embed",
        action="store_true",
        help="Re-embed even if disk cache exists.",
    )
    args = parser.parse_args()

    # --- Step 1: Chunk ---
    logger.info("Chunking HTML files from %s", RAW_DIR)
    chunks = chunk_directory(RAW_DIR)
    logger.info(
        "Produced %d chunks from %d HTML files.", len(chunks), len(list(RAW_DIR.glob("*.html")))
    )

    # Log classification breakdown
    by_class: dict[str, int] = {}
    for c in chunks:
        by_class[c.metadata.classification] = by_class.get(c.metadata.classification, 0) + 1
    for cls, count in sorted(by_class.items()):
        logger.info("  %s: %d chunks", cls, count)

    # --- Step 2: Embed ---
    logger.info("Embedding chunks (cache dir: %s)", CACHE_DIR)
    embeddings = embed_chunks(chunks, CACHE_DIR, force=args.force_embed)
    logger.info("Embeddings ready: %d/%d", len(embeddings), len(chunks))

    if args.dry_run:
        logger.info("--dry-run: skipping Qdrant upsert.")
        return

    # --- Step 3: Qdrant setup + upsert ---
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.qdrant_url)
    create_collection(client, recreate=args.recreate)
    _upsert_to_qdrant(client, chunks, embeddings)
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
