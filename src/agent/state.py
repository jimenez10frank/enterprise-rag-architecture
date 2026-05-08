"""Pydantic models for CRAG agent state and LLM-structured payloads.

AgentState is the LangGraph state schema: Pydantic is supported by StateGraph
in LangGraph 1.x, so we keep one canonical model instead of duplicating a
TypedDict. Every field that flows to retrieval includes `user_roles` only
there — never pass retrieved text into a role-decision prompt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.ingestion.schema import Chunk

GradeLabel = Literal["relevant", "ambiguous", "irrelevant"]
Confidence = Literal["high", "medium", "low"]


class Citation(BaseModel):
    """Single source-backed anchor for a claim (docs/project/TRAPS.md TRAP 6)."""

    chunk_id: str = Field(description="Must match a retrieved chunk_id exactly")
    artikel: str = Field(description="Article reference from chunk metadata")
    lid: int | None = Field(default=None, description="Paragraph number if applicable")
    quote: str = Field(..., max_length=500, description="Verbatim excerpt from the chunk")


class CitedClaim(BaseModel):
    """One factual statement with at least one citation."""

    claim: str = Field(..., min_length=1)
    citations: list[Citation] = Field(..., min_length=1)


class Answer(BaseModel):
    """Generator output — schema forces citations when the model answers."""

    claims: list[CitedClaim] = Field(default_factory=list)
    confidence: Confidence = Field(default="medium")
    unanswerable: bool = False
    unanswerable_reason: str | None = None

    @model_validator(mode="after")
    def _claims_or_unanswerable(self) -> Answer:
        if self.unanswerable:
            return self
        if not self.claims:
            msg = "Non-unanswerable responses must include at least one cited claim"
            raise ValueError(msg)
        return self


class GradeResult(BaseModel):
    """Three-way retrieval quality grade (docs/project/TRAPS.md TRAP 7)."""

    grade: GradeLabel
    reasoning: str = Field(..., min_length=1)
    missing_info: str | None = Field(
        default=None,
        description="What is unclear or missing when grade is ambiguous",
    )


class DecompositionResult(BaseModel):
    """LLM output: one or more retrieval queries (sub-questions)."""

    questions: list[str] = Field(
        ...,
        min_length=1,
        description="Single question or multiple sub-questions for multi-part queries",
    )

    @field_validator("questions")
    @classmethod
    def _non_empty_strings(cls, qs: list[str]) -> list[str]:
        out = [q.strip() for q in qs if q and q.strip()]
        if not out:
            msg = "At least one non-empty question is required"
            raise ValueError(msg)
        return out


class AgentState(BaseModel):
    """Mutable graph state passed between CRAG nodes."""

    original_question: str = Field(..., min_length=1)
    user_roles: list[str] = Field(..., min_length=1)
    decomposed_questions: list[str] | None = None
    retrieved_chunks: list[Chunk] = Field(default_factory=list)
    grade: GradeLabel | None = None
    grade_reasoning: str | None = None
    missing_info: str | None = None
    retry_count: int = Field(default=0, ge=0)
    final_answer: Answer | None = None
