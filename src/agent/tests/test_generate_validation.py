"""Offline tests for citation validation (TRAPS.md TRAP 6)."""

from __future__ import annotations

from src.agent.nodes.generate import validate_answer
from src.agent.state import Answer, Citation, CitedClaim
from src.ingestion.schema import ROLE_PUBLIC, Chunk, ChunkMetadata


def _chunk() -> Chunk:
    meta = ChunkMetadata(
        doc_id="D1",
        wet="Wet",
        artikel="3.2",
        lid=1,
        classification="public",
        allowed_roles=[ROLE_PUBLIC],
        source_file="x.html",
    )
    return Chunk(
        chunk_id="cid1",
        text="De belasting bedraagt vijftien procent volgens artikel 3.2.",
        metadata=meta,
    )


def test_validate_answer_accepts_exact_quote() -> None:
    ch = _chunk()
    ans = Answer(
        claims=[
            CitedClaim(
                claim="Tarief is vastgelegd.",
                citations=[
                    Citation(
                        chunk_id="cid1",
                        artikel="3.2",
                        lid=1,
                        quote="De belasting bedraagt vijftien procent",
                    ),
                ],
            ),
        ],
        confidence="high",
    )
    assert validate_answer(ans, [ch]) == []


def test_validate_answer_rejects_bad_chunk_id() -> None:
    ch = _chunk()
    ans = Answer(
        claims=[
            CitedClaim(
                claim="x",
                citations=[Citation(chunk_id="nope", artikel="3.2", lid=1, quote="De belasting")],
            ),
        ],
        confidence="high",
    )
    errs = validate_answer(ans, [ch])
    assert len(errs) == 1
    assert "unknown chunk_id" in errs[0]


def test_validate_answer_skips_checks_when_unanswerable() -> None:
    ch = _chunk()
    ans = Answer(unanswerable=True, unanswerable_reason="none", confidence="low")
    assert validate_answer(ans, [ch]) == []
