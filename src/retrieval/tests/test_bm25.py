"""Unit tests for BM25 retriever — offline, no infrastructure required."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.chunker import chunk_directory
from src.ingestion.schema import Chunk, ChunkMetadata
from src.retrieval.bm25 import BM25Index, _tokenize

DATA_RAW = Path(__file__).parents[3] / "data" / "raw"


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def test_tokenize_lowercases() -> None:
    tokens = _tokenize("Artikel 3.16 Werkruimte")
    assert all(t == t.lower() for t in tokens)


def test_tokenize_splits_on_punctuation() -> None:
    tokens = _tokenize("artikel 3.16, lid 2: werkruimte")
    assert "artikel" in tokens
    assert "3" in tokens or "16" in tokens  # split on '.'
    assert "werkruimte" in tokens


def test_tokenize_empty_string() -> None:
    assert _tokenize("") == []


def test_tokenize_preserves_digits() -> None:
    tokens = _tokenize("ECLI NL HR 2023 1234")
    assert "2023" in tokens
    assert "1234" in tokens


# ---------------------------------------------------------------------------
# BM25Index construction
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str, text: str, roles: list[str]) -> Chunk:
    meta = ChunkMetadata(
        doc_id="TEST",
        wet="Test Wet",
        classification="public",
        allowed_roles=roles,
        source_file="test.html",
    )
    return Chunk(chunk_id=chunk_id, text=text, metadata=meta)


def test_bm25_index_builds_from_chunks() -> None:
    chunks = [
        _make_chunk("c1", "werkruimte aftrekbaarheid belasting", ["public"]),
        _make_chunk("c2", "auto privégebruik bijtelling", ["public"]),
    ]
    idx = BM25Index(chunks)
    assert idx.corpus_size == 2


def test_bm25_search_returns_relevant_chunk_first() -> None:
    # Need ≥3 docs to avoid BM25 IDF = log((N-df+0.5)/(df+0.5)) = 0 when df = N/2.
    # With N=3, df=1: IDF = log(2.5/1.5) ≈ 0.51 → non-zero scores.
    chunks = [
        _make_chunk("werkruimte", "werkruimte thuiswerken aftrekbaarheid belasting", ["public"]),
        _make_chunk("auto", "auto privégebruik bijtelling", ["public"]),
        _make_chunk("box3", "sparen beleggen vermogen rendement", ["public"]),
    ]
    idx = BM25Index(chunks)
    results = idx.search("werkruimte aftrekbaarheid", user_roles=["public"])
    assert len(results) > 0, "BM25 returned no results — check tokenization / IDF"
    assert results[0][0] == "werkruimte"


def test_bm25_search_rbac_excludes_fiod_from_public() -> None:
    chunks = [
        _make_chunk(
            "public_chunk", "eigenwoningforfait berekening", ["public", "helpdesk", "fiod"]
        ),
        _make_chunk("fiod_chunk", "fraudesignalen onverklaard vermogen", ["fiod"]),
    ]
    idx = BM25Index(chunks)
    results = idx.search("vermogen", user_roles=["public"])
    ids = [r[0] for r in results]
    assert "fiod_chunk" not in ids, "FIOD chunk must not be visible to public users"


def test_bm25_search_fiod_user_sees_fiod_chunk() -> None:
    chunks = [
        _make_chunk(
            "public_chunk",
            "eigenwoningforfait berekening belasting",
            ["public", "helpdesk", "fiod"],
        ),
        _make_chunk("fiod_chunk", "fraudesignalen onverklaard vermogen", ["fiod"]),
        _make_chunk(
            "extra_chunk", "auto bijtelling zakelijk gebruik", ["public", "helpdesk", "fiod"]
        ),
    ]
    idx = BM25Index(chunks)
    results = idx.search("vermogen", user_roles=["fiod"])
    ids = [r[0] for r in results]
    assert "fiod_chunk" in ids


def test_bm25_search_empty_query_returns_empty() -> None:
    chunks = [_make_chunk("c1", "some text here", ["public"])]
    idx = BM25Index(chunks)
    results = idx.search("", user_roles=["public"])
    assert results == []


def test_bm25_search_top_k_limits_results() -> None:
    chunks = [_make_chunk(f"c{i}", f"belasting aftrek artikel {i}", ["public"]) for i in range(20)]
    idx = BM25Index(chunks)
    results = idx.search("belasting", user_roles=["public"], top_k=5)
    assert len(results) <= 5


def test_bm25_search_scores_descending() -> None:
    chunks = [
        _make_chunk("high", "werkruimte werkruimte werkruimte aftrek", ["public"]),
        _make_chunk("low", "auto transport zakelijk", ["public"]),
    ]
    idx = BM25Index(chunks)
    results = idx.search("werkruimte", user_roles=["public"])
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Integration with real corpus
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not DATA_RAW.exists(), reason="data/raw not found")
def test_bm25_indexes_full_corpus() -> None:
    chunks = chunk_directory(DATA_RAW)
    idx = BM25Index(chunks)
    assert idx.corpus_size > 0


@pytest.mark.skipif(not DATA_RAW.exists(), reason="data/raw not found")
def test_bm25_finds_werkruimte_chunk() -> None:
    chunks = chunk_directory(DATA_RAW)
    idx = BM25Index(chunks)
    results = idx.search("werkruimte thuiswerken aftrekbaarheid", user_roles=["public"])
    assert len(results) > 0
    # The top result should reference werkruimte article
    top_id, top_score = results[0]
    assert top_score > 0.0


@pytest.mark.skipif(not DATA_RAW.exists(), reason="data/raw not found")
def test_bm25_helpdesk_cannot_see_fiod_chunks() -> None:
    chunks = chunk_directory(DATA_RAW)
    idx = BM25Index(chunks)
    results = idx.search("fraude vermogen constructies", user_roles=["helpdesk"])
    ids = [r[0] for r in results]
    fiod_ids = {c.chunk_id for c in chunks if c.metadata.classification == "fiod"}
    overlap = set(ids) & fiod_ids
    assert not overlap, f"Helpdesk user received FIOD chunks via BM25: {overlap}"
