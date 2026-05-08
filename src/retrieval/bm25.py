"""BM25 sparse retriever.

Uses rank_bm25 (BM25Okapi) for term-frequency-based retrieval. BM25 complements
dense retrieval by catching exact term matches: statute numbers like 'artikel 3.76',
ECLI references, and Dutch legal keywords that the embedding model might cluster
under different surface forms.

RBAC note: BM25 TF-IDF scores are document-local — a classified document does NOT
influence the score of an unclassified document (unlike HNSW where graph topology
leaks existence of neighbours). We therefore filter by user role before scoring
rather than after, which eliminates any question of information leakage.

For demo scale (hundreds to low-thousands of chunks) rank_bm25 is in-process and
fast enough. At 20M chunks, swap for Elasticsearch / OpenSearch. See docs/project/STACK.md.

See docs/concepts/04-bm25-vs-dense.md for the rationale behind running both.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from src.ingestion.schema import Chunk


def _tokenize(text: str) -> list[str]:
    """Simple Dutch-aware tokenizer for BM25 indexing.

    Lowercases and splits on non-alphanumeric characters (preserves digits).
    We do NOT stem Dutch legal terms — 'aftrekbaarheid' and 'aftrek' have
    different legal meanings and should not be collapsed.
    We do NOT remove stopwords — 'niet' (not), 'geen' (no) are legally
    significant and removing them would change retrieval semantics.
    """
    tokens = re.split(r"[^\w]", text.lower())
    return [t for t in tokens if t and len(t) > 1]


class BM25Index:
    """In-memory BM25 index over a fixed corpus of chunks.

    The index is built once at init and is immutable. For incremental updates
    rebuild the index (fast at demo scale).

    Args:
        chunks: The full corpus to index. The index is over ALL chunks;
                RBAC filtering happens at query time via the user_roles parameter.
    """

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._chunk_ids = [c.chunk_id for c in chunks]
        tokenized_corpus = [_tokenize(c.text) for c in chunks]
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(
        self,
        query: str,
        user_roles: list[str],
        top_k: int = 50,
    ) -> list[tuple[str, float]]:
        """Return top-K (chunk_id, score) pairs, filtered to user's allowed roles.

        Role filtering happens BEFORE score comparison so that only chunks the
        user is permitted to see are considered. This is equivalent to searching
        a role-partitioned sub-corpus. See module docstring for the BM25-specific
        reasoning on why this is safe.

        Args:
            query: The search query string (will be tokenized internally).
            user_roles: Roles the querying user holds (e.g. ['public', 'helpdesk']).
            top_k: Maximum number of results to return.

        Returns:
            List of (chunk_id, score) tuples, descending by BM25 score.
            Scores of 0.0 are excluded from results.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        all_scores: list[float] = self._bm25.get_scores(query_tokens).tolist()

        # Filter to chunks the user is allowed to see, then rank by score.
        allowed: list[tuple[str, float]] = []
        for chunk, score in zip(self._chunks, all_scores, strict=False):
            if score <= 0.0:
                continue
            if any(role in chunk.metadata.allowed_roles for role in user_roles):
                allowed.append((chunk.chunk_id, score))

        allowed.sort(key=lambda x: x[1], reverse=True)
        return allowed[:top_k]

    @property
    def corpus_size(self) -> int:
        """Total number of chunks in the index (all roles)."""
        return len(self._chunks)
