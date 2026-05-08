"""Ragas evaluation harness over ``data/golden/golden_set.jsonl`` (Phase 5.4).

Loads curated rows, runs the compiled LangGraph once per question with the
caller's RBAC role, builds a HuggingFace ``Dataset`` in the shape Ragas expects,
and reports Faithfulness, Context Precision, Context Recall, and Answer
Relevancy.

Faithfulness is computed only on rows with ``expected_outcome == "answered"`` —
escalations would distort entailment scores. The CI gate (Faithfulness ≥ 0.95)
uses that subset mean.

See docs/concepts/11-rag-evaluation.md for metric definitions.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Literal, cast

from datasets import Dataset
from openai import OpenAI
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from ragas.evaluation import EvaluationResult

from src.agent.graph import build_agent_graph
from src.agent.state import AgentState, Answer
from src.config import settings
from src.ingestion.chunker import chunk_directory
from src.ingestion.schema import Chunk
from src.retrieval.bm25 import BM25Index

logger = logging.getLogger(__name__)

Outcome = Literal["answered", "escalated"]


class GoldenRow(BaseModel):
    """One line of ``golden_set.jsonl`` — hand-curated eval expectations."""

    question: str = Field(..., min_length=1)
    expected_answer_summary: str = Field(..., min_length=1)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    user_role: str = Field(..., min_length=1)
    expected_outcome: Outcome


def load_golden(path: Path) -> list[GoldenRow]:
    """Parse JSONL; skips empty lines."""
    rows: list[GoldenRow] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(GoldenRow.model_validate(json.loads(line)))
    return rows


def answer_to_text(answer: Answer | None) -> str:
    """Flatten structured output for Ragas ``response`` column."""
    if answer is None:
        return ""
    if answer.unanswerable:
        return answer.unanswerable_reason or "Ik kan dit niet beantwoorden."
    return " ".join(c.claim for c in answer.claims)


def iter_eval_samples(
    rows: Sequence[GoldenRow],
    *,
    bm25: BM25Index,
    qdrant: QdrantClient,
    skip_rerank: bool = False,
) -> Iterator[dict[str, Any]]:
    """Run the agent on each golden question; yield dicts for Dataset.from_list."""
    graph = build_agent_graph(bm25, qdrant, skip_rerank=skip_rerank)
    for row in rows:
        st = AgentState(original_question=row.question, user_roles=[row.user_role])
        out = graph.invoke(st)
        final: Answer | None = out.get("final_answer")
        raw_chunks = out.get("retrieved_chunks") or []
        chunks = cast(list[Chunk], raw_chunks)
        contexts = [c.text for c in chunks]
        yield {
            "user_input": row.question,
            "response": answer_to_text(final),
            "contexts": contexts,
            "reference": row.expected_answer_summary,
            "expected_outcome": row.expected_outcome,
        }


def build_eval_dataset(
    golden_path: Path,
    *,
    bm25: BM25Index,
    qdrant: QdrantClient,
    skip_rerank: bool = False,
) -> Dataset:
    rows = load_golden(golden_path)
    records = list(iter_eval_samples(rows, bm25=bm25, qdrant=qdrant, skip_rerank=skip_rerank))
    return Dataset.from_list(records)


def run_ragas(
    dataset: Dataset,
    *,
    answered_only: bool = True,
) -> EvaluationResult:
    """Run Ragas metrics; requires OpenAI credentials."""
    from ragas import evaluate
    from ragas.embeddings import OpenAIEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    if answered_only:
        subset = dataset.filter(lambda x: x["expected_outcome"] == "answered")
    else:
        subset = dataset

    if len(subset) == 0:
        msg = "No rows left after filtering — check golden set"
        raise ValueError(msg)

    client = OpenAI(api_key=settings.openai_api_key)
    llm = llm_factory(settings.llm_model, client=client)
    embeddings = OpenAIEmbeddings(client=client, model=settings.embedding_model)

    metrics = [
        Faithfulness(),
        ContextPrecision(),
        ContextRecall(),
        AnswerRelevancy(),
    ]

    # Ragas does not need expected_outcome inside evaluate()
    eval_set = subset.remove_columns(["expected_outcome"])

    scorecard = evaluate(
        eval_set,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )
    return cast(EvaluationResult, scorecard)


def format_results_table(result: EvaluationResult) -> str:
    df = result.to_pandas()
    return str(df.to_string(index=False))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Run Ragas on the golden legal-RAG set.")
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path("data/golden/golden_set.jsonl"),
        help="Path to golden_set.jsonl",
    )
    parser.add_argument(
        "--faithfulness-min",
        type=float,
        default=0.95,
        help="Exit 1 if mean Faithfulness on 'answered' rows is below this.",
    )
    parser.add_argument(
        "--skip-rerank",
        action="store_true",
        help="Faster local eval without Cohere (matches integration tests).",
    )
    args = parser.parse_args(argv)

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY unset — skipping Ragas (exit 0).")
        return 0

    raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    chunks = chunk_directory(raw_dir)
    bm25 = BM25Index(chunks)
    qdrant = QdrantClient(url=settings.qdrant_url)

    try:
        ds = build_eval_dataset(
            args.golden,
            bm25=bm25,
            qdrant=qdrant,
            skip_rerank=args.skip_rerank,
        )
        result = run_ragas(ds, answered_only=True)
        table = format_results_table(result)
        print(table)

        df = result.to_pandas()
        mean_faith = float(df["faithfulness"].mean())
        logger.info("Mean Faithfulness (answered subset, n=%d): %.4f", len(df), mean_faith)
        if mean_faith < args.faithfulness_min:
            logger.error(
                "Faithfulness %.4f is below required minimum %.4f",
                mean_faith,
                args.faithfulness_min,
            )
            return 1
    finally:
        qdrant.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
