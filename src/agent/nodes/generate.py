"""Generation with citation validation and a single repair attempt.

See docs/project/TRAPS.md (TRAP 6).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.llm_factory import structured_llm
from src.agent.nodes.escalate import run_escalate
from src.agent.state import AgentState, Answer
from src.ingestion.schema import Chunk

_GENERATE_SYSTEM = """You are a Dutch tax and legal assistant using ONLY the provided source chunks.
Rules:
- Every factual statement must be a separate claim with at least one citation.
- Each citation MUST use a chunk_id from the context exactly as written.
- artikel in each citation MUST match the article reference for that chunk in the context.
- quote MUST be a short verbatim excerpt copied from that chunk's body (max 500 chars).
- If the chunks do not support a reliable answer, set unanswerable=true and explain why.
Do not cite chunks you were not given."""


def _normalized_whitespace(text: str) -> str:
    return " ".join(text.lower().split())


def _quote_matches_source(quote: str, chunk_text: str, *, threshold: float = 0.9) -> bool:
    """Verbatim preference; fuzzy longest-run match for minor whitespace drift."""
    q = _normalized_whitespace(quote)
    t = _normalized_whitespace(chunk_text)
    if not q:
        return False
    if q in t:
        return True
    sm = SequenceMatcher(None, q, t, autojunk=False)
    m = sm.find_longest_match(0, len(q), 0, len(t))
    return (m.size / len(q)) >= threshold


def _artikel_consistent(cit_artikel: str, chunk: Chunk) -> bool:
    meta_a = chunk.metadata.artikel
    if meta_a is None:
        return True
    c = cit_artikel.strip().lower()
    c = re.sub(r"^art\.?\s*", "", c).strip()
    m = meta_a.strip().lower()
    return c == m or m in c or c in m


def validate_answer(answer: Answer, chunks: list[Chunk]) -> list[str]:
    """Return human-readable validation errors; empty list means OK."""
    errs: list[str] = []
    if answer.unanswerable:
        return errs
    by_id: dict[str, Chunk] = {c.chunk_id: c for c in chunks}
    for ci, claim in enumerate(answer.claims):
        for cj, cit in enumerate(claim.citations):
            ch = by_id.get(cit.chunk_id)
            if ch is None:
                errs.append(f"claim[{ci}] citation[{cj}]: unknown chunk_id {cit.chunk_id!r}")
                continue
            if not _artikel_consistent(cit.artikel, ch):
                errs.append(
                    f"claim[{ci}] citation[{cj}]: artikel {cit.artikel!r} "
                    f"inconsistent with chunk {ch.chunk_id}",
                )
            if not _quote_matches_source(cit.quote, ch.text):
                errs.append(
                    f"claim[{ci}] citation[{cj}]: quote not found in chunk {ch.chunk_id}",
                )
    return errs


def _chunks_block(chunks: list[Chunk]) -> str:
    parts: list[str] = []
    for ch in chunks:
        meta_line = (
            f"chunk_id={ch.chunk_id} | artikel={ch.metadata.artikel!r} | "
            f"lid={ch.metadata.lid} | {ch.metadata.citation_label()}"
        )
        parts.append(f"### {meta_line}\n{ch.text}\n")
    return "\n".join(parts)


def run_generate(state: AgentState) -> dict[str, Any]:
    """Structured generation plus post-validation; on failure escalate safely."""
    if not state.retrieved_chunks:
        return run_escalate(
            state.model_copy(
                update={
                    "grade": "irrelevant",
                    "grade_reasoning": "No chunks available for generation.",
                    "missing_info": None,
                },
            ),
        )

    llm = structured_llm(Answer, temperature=0.0)
    ctx = _chunks_block(state.retrieved_chunks)
    user = f"Vraag:\n{state.original_question}\n\nBronchunks:\n{ctx}"
    base_messages = [
        SystemMessage(content=_GENERATE_SYSTEM),
        HumanMessage(content=user),
    ]
    answer: Answer = llm.invoke(base_messages)

    errs = validate_answer(answer, state.retrieved_chunks)
    if not errs:
        return {"final_answer": answer}

    repair = HumanMessage(
        content=(
            "Your answer failed validation. Fix it.\n"
            + "\n".join(errs)
            + "\nEnsure every quote appears verbatim in its chunk and chunk_id matches."
        ),
    )
    answer2: Answer = llm.invoke([*base_messages, repair])
    errs2 = validate_answer(answer2, state.retrieved_chunks)
    if errs2:
        return run_escalate(
            state.model_copy(
                update={
                    "grade": "ambiguous",
                    "grade_reasoning": "Citation validation failed after repair: "
                    + "; ".join(errs2),
                    "missing_info": None,
                },
            ),
        )
    return {"final_answer": answer2}
