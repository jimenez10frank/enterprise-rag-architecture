"""Data models for document chunks and their metadata.

These models define the canonical shape of a chunk as it flows through
the ingestion pipeline: chunker → embedding → Qdrant payload.
Every claim the LLM makes traces back to a chunk_id defined here.

The classification + allowed_roles pair on every chunk is the foundation
of the RBAC pre-filter. Both fields must be present on every chunk — a
missing classification is a type error at construction time, not a silent
security gap discovered at runtime. See TRAPS.md TRAP 2.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# Sensitivity tiers — must map exactly to the values stored in Qdrant payload.
Classification = Literal["public", "internal", "fiod"]

ROLE_PUBLIC: str = "public"
ROLE_HELPDESK: str = "helpdesk"
ROLE_FIOD: str = "fiod"

ALL_ROLES: list[str] = [ROLE_PUBLIC, ROLE_HELPDESK, ROLE_FIOD]


class ChunkMetadata(BaseModel):
    """Payload stored in Qdrant alongside every vector.

    The RBAC pre-filter queries allowed_roles before HNSW search runs.
    Every other field is used for citation generation and filtering.
    """

    doc_id: str = Field(description="Document identifier, e.g. BWBR0011353")
    wet: str = Field(description="Full act name, e.g. 'Wet inkomstenbelasting 2001'")
    hoofdstuk: str | None = Field(default=None, description="Chapter number, e.g. '3'")
    afdeling: str | None = Field(default=None, description="Section number, e.g. '3.2'")
    artikel: str | None = Field(default=None, description="Article number, e.g. '3.16'")
    lid: int | None = Field(default=None, description="Paragraph number, e.g. 2")
    sub: str | None = Field(default=None, description="Sub-provision letter, e.g. 'a'")
    classification: Classification = Field(description="Data sensitivity level")
    allowed_roles: list[str] = Field(description="Roles permitted to retrieve this chunk")
    source_file: str = Field(description="Original filename for traceability")
    effective_date: date | None = Field(default=None, description="Version valid-from date")

    def citation_label(self) -> str:
        """Human-readable citation for LLM output, e.g. 'Wet IB 2001, art. 3.16 lid 2'."""
        parts = [self.wet]
        if self.artikel:
            parts.append(f"art. {self.artikel}")
        if self.lid is not None:
            parts.append(f"lid {self.lid}")
        if self.sub:
            parts.append(f"onderdeel {self.sub}")
        return ", ".join(parts)


class Chunk(BaseModel):
    """Single retrievable unit: text + metadata + stable ID."""

    chunk_id: str = Field(description="Stable ID derived from doc_id + position in hierarchy")
    text: str = Field(description="Verbatim text of this provision, prefixed with article title")
    metadata: ChunkMetadata

    @classmethod
    def make_id(
        cls,
        doc_id: str,
        artikel: str | None,
        lid: int | None,
        sub: str | None,
    ) -> str:
        """Deterministic chunk ID from its position in the legal hierarchy.

        IDs are stable across re-ingestion so that embedding cache hits work
        correctly and Qdrant upserts are idempotent.
        """
        parts = [doc_id]
        if artikel:
            parts.append(f"art_{artikel.replace('.', '_')}")
        if lid is not None:
            parts.append(f"lid_{lid}")
        if sub:
            parts.append(f"sub_{sub}")
        return "_".join(parts)
