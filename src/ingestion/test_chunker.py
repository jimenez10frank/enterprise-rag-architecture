"""Tests for the hierarchical HTML chunker.

All tests are offline — no API keys, no infrastructure required.
They test the core invariants of TRAP 1 (no character splitter) and
TRAP 2 (classification and allowed_roles on every chunk).
"""

from __future__ import annotations

from pathlib import Path

from src.ingestion.chunker import chunk_directory, chunk_document
from src.ingestion.schema import Chunk

# Navigate from src/ingestion/ up two levels to the project root → data/raw/
DATA_RAW = Path(__file__).parents[2] / "data" / "raw"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_file(name: str) -> Path:
    p = DATA_RAW / name
    assert p.exists(), f"Test fixture not found: {p}"
    return p


# ---------------------------------------------------------------------------
# TRAP 1 guard: no character-based splitter ever imported in chunker.py
# ---------------------------------------------------------------------------


def test_no_character_text_splitter_in_chunker() -> None:
    """Regression guard: chunker.py must never import character splitters."""
    chunker_src = (Path(__file__).parent / "chunker.py").read_text(encoding="utf-8")
    forbidden = [
        "RecursiveCharacterTextSplitter",
        "CharacterTextSplitter",
        "TokenTextSplitter",
        "SentenceTransformersTokenTextSplitter",
    ]
    for name in forbidden:
        assert name not in chunker_src, (
            f"TRAP 1 VIOLATED: '{name}' found in chunker.py. "
            "Character-based splitters destroy legal document hierarchy."
        )


# ---------------------------------------------------------------------------
# Public document: art. 3.16 (4 lids)
# ---------------------------------------------------------------------------


def test_art_3_16_chunk_count() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    # 4 lids → 4 chunks
    assert len(chunks) == 4, f"Expected 4 chunks, got {len(chunks)}"


def test_art_3_16_classification_is_public() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    for chunk in chunks:
        assert chunk.metadata.classification == "public"


def test_art_3_16_allowed_roles_includes_all() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    for chunk in chunks:
        assert "public" in chunk.metadata.allowed_roles
        assert "helpdesk" in chunk.metadata.allowed_roles
        assert "fiod" in chunk.metadata.allowed_roles


def test_art_3_16_metadata_fields() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    c = chunks[0]
    assert c.metadata.wet == "Wet inkomstenbelasting 2001"
    assert c.metadata.artikel == "3.16"
    assert c.metadata.lid == 1
    assert c.metadata.doc_id == "BWBR0011353"
    assert c.metadata.hoofdstuk == "3"
    assert c.metadata.afdeling == "3.2"
    assert c.metadata.source_file == "wet_ib_2001_art_3_16.html"


def test_art_3_16_text_includes_artikel_title() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    for chunk in chunks:
        assert "3.16" in chunk.text or "Werkruimte" in chunk.text, (
            f"Chunk text does not reference the artikel: {chunk.text[:80]}"
        )


def test_art_3_16_lid_numbers_are_sequential() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    lids = [c.metadata.lid for c in chunks]
    assert lids == [1, 2, 3, 4]


def test_art_3_16_chunk_ids_are_stable() -> None:
    """Same file chunked twice must produce identical chunk_ids."""
    chunks_a = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    chunks_b = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    assert [c.chunk_id for c in chunks_a] == [c.chunk_id for c in chunks_b]


def test_art_3_16_chunk_ids_are_unique() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk IDs detected"


def test_art_3_16_text_is_non_empty() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    for chunk in chunks:
        assert chunk.text.strip(), f"Empty text on chunk {chunk.chunk_id}"


# ---------------------------------------------------------------------------
# Document with sub-provisions: art. 3.14 (3 lids, lids 1+2 have subs)
# ---------------------------------------------------------------------------


def test_art_3_14_sub_provisions_folded_into_lid_chunk() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_14.html"))
    # Lid 1 has sub-bepalingen a, b, c — all should appear in the lid's chunk text
    lid1 = next(c for c in chunks if c.metadata.lid == 1 and c.metadata.artikel == "3.14")
    assert "a." in lid1.text
    assert "b." in lid1.text


def test_art_3_14_chunk_count() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_14.html"))
    # 3 lids → 3 chunks (subs folded in, not separate)
    art_3_14_chunks = [c for c in chunks if c.metadata.artikel == "3.14"]
    assert len(art_3_14_chunks) == 3


# ---------------------------------------------------------------------------
# FIOD classified documents
# ---------------------------------------------------------------------------


def test_fiod_001_classification_is_fiod() -> None:
    chunks = chunk_document(_get_file("fiod_intern_001_signalen_vermogensfraude.html"))
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.metadata.classification == "fiod", (
            f"FIOD document produced chunk with wrong classification: "
            f"{chunk.metadata.classification}"
        )


def test_fiod_001_allowed_roles_fiod_only() -> None:
    chunks = chunk_document(_get_file("fiod_intern_001_signalen_vermogensfraude.html"))
    for chunk in chunks:
        assert chunk.metadata.allowed_roles == ["fiod"], (
            f"FIOD chunk must be restricted to ['fiod'], got: {chunk.metadata.allowed_roles}"
        )


def test_fiod_001_public_role_not_in_allowed_roles() -> None:
    chunks = chunk_document(_get_file("fiod_intern_001_signalen_vermogensfraude.html"))
    for chunk in chunks:
        assert "public" not in chunk.metadata.allowed_roles
        assert "helpdesk" not in chunk.metadata.allowed_roles


def test_all_three_fiod_files_are_classified() -> None:
    fiod_files = [
        "fiod_intern_001_signalen_vermogensfraude.html",
        "fiod_intern_002_constructies_offshore.html",
        "fiod_intern_003_invordering_bestuurders.html",
    ]
    for fname in fiod_files:
        chunks = chunk_document(_get_file(fname))
        assert all(c.metadata.classification == "fiod" for c in chunks), (
            f"{fname}: not all chunks have classification='fiod'"
        )


# ---------------------------------------------------------------------------
# citation_label helper
# ---------------------------------------------------------------------------


def test_citation_label_format() -> None:
    chunks = chunk_document(_get_file("wet_ib_2001_art_3_16.html"))
    lid2 = next(c for c in chunks if c.metadata.lid == 2)
    label = lid2.metadata.citation_label()
    assert "3.16" in label
    assert "lid 2" in label
    assert "Wet inkomstenbelasting 2001" in label


# ---------------------------------------------------------------------------
# chunk_directory
# ---------------------------------------------------------------------------


def test_chunk_directory_returns_chunks_for_all_html_files() -> None:
    all_chunks = chunk_directory(DATA_RAW)
    assert len(all_chunks) > 0


def test_chunk_directory_includes_fiod_chunks() -> None:
    all_chunks = chunk_directory(DATA_RAW)
    fiod_chunks = [c for c in all_chunks if c.metadata.classification == "fiod"]
    assert len(fiod_chunks) > 0, "No FIOD chunks found in corpus"


def test_chunk_directory_has_public_and_fiod_separate() -> None:
    all_chunks = chunk_directory(DATA_RAW)
    public_ids = {c.chunk_id for c in all_chunks if c.metadata.classification == "public"}
    fiod_ids = {c.chunk_id for c in all_chunks if c.metadata.classification == "fiod"}
    assert not public_ids.intersection(fiod_ids), "Public and FIOD chunk IDs overlap"


def test_chunk_make_id_deterministic() -> None:
    id1 = Chunk.make_id("BWBR0011353", "3.16", 2, None)
    id2 = Chunk.make_id("BWBR0011353", "3.16", 2, None)
    assert id1 == id2
    assert "3_16" in id1
    assert "lid_2" in id1
