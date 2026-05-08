"""Tests for golden set parsing and dataset building (no paid API calls)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.eval.ragas_runner import GoldenRow, build_eval_dataset, load_golden


def test_load_golden_fixture(tmp_path: Path) -> None:
    p = tmp_path / "g.jsonl"
    p.write_text(
        '{"question": "q1", "expected_answer_summary": "a", '
        '"expected_chunk_ids": [], "user_role": "public", "expected_outcome": "answered"}\n',
        encoding="utf-8",
    )
    rows = load_golden(p)
    assert len(rows) == 1
    assert isinstance(rows[0], GoldenRow)


def test_load_repo_golden_has_eighteen_rows() -> None:
    root = Path(__file__).resolve().parents[2]
    golden = root / "data" / "golden" / "golden_set.jsonl"
    rows = load_golden(golden)
    assert len(rows) == 18


def test_build_eval_dataset_uses_graph(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "g.jsonl"
    p.write_text(
        '{"question": "q", "expected_answer_summary": "ref", '
        '"expected_chunk_ids": [], "user_role": "public", "expected_outcome": "answered"}\n',
        encoding="utf-8",
    )

    mock_graph = MagicMock()

    def _invoke(st: object) -> dict[str, object]:
        from src.agent.state import Answer, Citation, CitedClaim

        return {
            "final_answer": Answer(
                claims=[
                    CitedClaim(
                        claim="hello",
                        citations=[Citation(chunk_id="x", artikel="1", quote="z")],
                    ),
                ],
            ),
            "retrieved_chunks": [],
        }

    mock_graph.invoke.side_effect = _invoke
    monkeypatch.setattr("src.eval.ragas_runner.build_agent_graph", lambda *a, **k: mock_graph)

    ds = build_eval_dataset(p, bm25=MagicMock(), qdrant=MagicMock(), skip_rerank=True)
    assert ds[0]["response"] == "hello"
    assert ds[0]["reference"] == "ref"
