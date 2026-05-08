"""Hierarchical HTML chunker for Dutch legal documents.

Splits documents along their structural boundaries (artikel → lid → sub),
NOT by character count. Standard text splitters destroy hierarchical
context and make precise legal citation impossible. See TRAPS.md TRAP 1.

Parsing strategy:
  - Document-level metadata from <meta> tags in <head>.
  - Structure from CSS classes + data-* attributes:
      div.hoofdstuk[data-nummer]  → Chapter
      div.afdeling[data-nummer]   → Section
      div.artikel[data-nummer]    → Article
      div.lid[data-nummer]        → Paragraph (= one chunk boundary)
      div.sub[data-letter]        → Sub-provision (folded into parent lid chunk)
  - One lid = one chunk. Articles without lids produce one chunk each.
  - Sub-provisions are included in their parent lid's chunk text so that
    the full context of a multi-part provision is always retrievable together.

Why not character/token splitters (TRAP 1):
  A 512-token split across artikel 3.16 lid 1 and lid 2 would yield a chunk
  whose citation is ambiguous and whose legal meaning is incomplete. The
  structural boundary IS the correct semantic boundary in legal documents.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import cast

from bs4 import BeautifulSoup, Tag

from src.ingestion.schema import ALL_ROLES, Chunk, ChunkMetadata, Classification

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_meta(soup: BeautifulSoup, name: str) -> str:
    """Return the content attribute of a <meta name="..."> tag, or ''."""
    tag = soup.find("meta", attrs={"name": name})
    if not isinstance(tag, Tag):
        return ""
    content = tag.get("content", "")
    if isinstance(content, list):
        return content[0] if content else ""
    return str(content)


def _get_data_attr(tag: Tag, attr: str) -> str | None:
    """Return a data-* attribute value as a plain string, handling bs4 list returns."""
    val = tag.get(attr)
    if val is None:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return str(val)


def _parse_date(value: str) -> date | None:
    """Parse an ISO 8601 date string; return None if malformed."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _clean_text(raw: str) -> str:
    """Collapse whitespace runs into a single space and strip."""
    return re.sub(r"\s+", " ", raw).strip()


def _resolve_classification(raw: str, source: str) -> Classification:
    """Validate and cast a raw string to the Classification Literal type."""
    if raw not in ("public", "internal", "fiod"):
        raise ValueError(
            f"{source}: invalid classification '{raw}'. Must be one of: public, internal, fiod."
        )
    return cast(Classification, raw)


# ---------------------------------------------------------------------------
# Per-lid chunk builder
# ---------------------------------------------------------------------------


def _build_lid_chunk(
    lid_tag: Tag,
    artikel_title: str,
    doc_id: str,
    wet: str,
    hoofdstuk: str | None,
    afdeling: str | None,
    artikel_num: str | None,
    classification: Classification,
    allowed_roles: list[str],
    source_file: str,
    effective_date: date | None,
) -> Chunk | None:
    """Build a single Chunk from a div.lid element."""
    lid_num_raw = _get_data_attr(lid_tag, "data-nummer")
    lid_num: int | None = int(lid_num_raw) if lid_num_raw and lid_num_raw.isdigit() else None

    # Extract main lid text from p.lid-tekst
    lid_tekst_tag = lid_tag.find("p", class_="lid-tekst")
    main_text = ""
    if isinstance(lid_tekst_tag, Tag):
        main_text = _clean_text(lid_tekst_tag.get_text(separator=" "))

    # Fold sub-provisions into the same chunk so the full provision is searchable
    sub_parts: list[str] = []
    for sub_tag in lid_tag.find_all("div", class_="sub"):
        if not isinstance(sub_tag, Tag):
            continue
        sub_letter = _get_data_attr(sub_tag, "data-letter") or ""
        sub_tekst_tag = sub_tag.find("p", class_="sub-tekst")
        sub_text = ""
        if isinstance(sub_tekst_tag, Tag):
            sub_text = _clean_text(sub_tekst_tag.get_text(separator=" "))
        if sub_text:
            prefix_str = f"{sub_letter}. " if sub_letter else ""
            sub_parts.append(f"{prefix_str}{sub_text}")

    # Compose final chunk text: artikel title + lid text + sub-provisions
    parts: list[str] = []
    if artikel_title:
        parts.append(f"{artikel_title} —")
    if main_text:
        parts.append(main_text)
    if sub_parts:
        parts.extend(sub_parts)

    full_text = _clean_text(" ".join(parts))
    if not full_text:
        return None

    chunk_id = Chunk.make_id(doc_id, artikel_num, lid_num, None)
    metadata = ChunkMetadata(
        doc_id=doc_id,
        wet=wet,
        hoofdstuk=hoofdstuk,
        afdeling=afdeling,
        artikel=artikel_num,
        lid=lid_num,
        sub=None,
        classification=classification,
        allowed_roles=allowed_roles,
        source_file=source_file,
        effective_date=effective_date,
    )
    return Chunk(chunk_id=chunk_id, text=full_text, metadata=metadata)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_document(html_path: Path) -> list[Chunk]:
    """Parse a single HTML legal document into an ordered list of Chunks.

    Each chunk corresponds to one lid (paragraph) of one artikel. Articles
    that contain no lid elements produce a single chunk for the whole article.

    Args:
        html_path: Path to an HTML file structured per data/raw/README.md.

    Returns:
        Ordered list of Chunk objects ready for embedding and Qdrant upsert.

    Raises:
        ValueError: If required document metadata (wet-naam, classification)
                    is missing or invalid.
    """
    html_text = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_text, "html.parser")

    # --- Document-level metadata from <meta> tags ---
    doc_id = _get_meta(soup, "bwb-id") or html_path.stem
    wet = _get_meta(soup, "wet-naam")
    if not wet:
        raise ValueError(f"{html_path.name}: missing <meta name='wet-naam'>")

    raw_classification = _get_meta(soup, "classification") or "public"
    classification = _resolve_classification(raw_classification, html_path.name)

    raw_roles = _get_meta(soup, "allowed-roles")
    allowed_roles: list[str] = (
        [r.strip() for r in raw_roles.split(",") if r.strip()] if raw_roles else list(ALL_ROLES)
    )

    effective_date = _parse_date(_get_meta(soup, "effective-date"))

    chunks: list[Chunk] = []

    # --- Walk every artikel in document order ---
    for artikel_tag in soup.find_all("div", class_="artikel"):
        if not isinstance(artikel_tag, Tag):
            continue

        artikel_num = _get_data_attr(artikel_tag, "data-nummer")

        # Resolve ancestor hoofdstuk / afdeling from the DOM tree
        hoofdstuk: str | None = None
        hfd_tag = artikel_tag.find_parent("div", class_="hoofdstuk")
        if isinstance(hfd_tag, Tag):
            hoofdstuk = _get_data_attr(hfd_tag, "data-nummer")

        afdeling: str | None = None
        afd_tag = artikel_tag.find_parent("div", class_="afdeling")
        if isinstance(afd_tag, Tag):
            afdeling = _get_data_attr(afd_tag, "data-nummer")

        # Article title for inclusion in chunk text (helps LLM form citations)
        artikel_title = ""
        titel_tag = artikel_tag.find("h4", class_="artikel-opschrift")
        if isinstance(titel_tag, Tag):
            artikel_title = _clean_text(titel_tag.get_text())

        lid_tags = artikel_tag.find_all("div", class_="lid", recursive=False)

        if not lid_tags:
            # Article without explicit lids → one chunk for the whole article.
            # Collect all text inside the artikel except the title tag.
            text_parts: list[str] = []
            for p in artikel_tag.find_all("p"):
                if isinstance(p, Tag) and not p.find_parent("h4"):
                    text_parts.append(_clean_text(p.get_text()))
            body_text = " ".join(text_parts)
            full_text = _clean_text(
                f"{artikel_title} — {body_text}" if body_text else artikel_title
            )
            if not full_text:
                continue
            chunk_id = Chunk.make_id(doc_id, artikel_num, None, None)
            metadata = ChunkMetadata(
                doc_id=doc_id,
                wet=wet,
                hoofdstuk=hoofdstuk,
                afdeling=afdeling,
                artikel=artikel_num,
                lid=None,
                sub=None,
                classification=classification,
                allowed_roles=allowed_roles,
                source_file=html_path.name,
                effective_date=effective_date,
            )
            chunks.append(Chunk(chunk_id=chunk_id, text=full_text, metadata=metadata))
            continue

        # One chunk per lid
        for lid_tag in lid_tags:
            if not isinstance(lid_tag, Tag):
                continue
            chunk = _build_lid_chunk(
                lid_tag=lid_tag,
                artikel_title=artikel_title,
                doc_id=doc_id,
                wet=wet,
                hoofdstuk=hoofdstuk,
                afdeling=afdeling,
                artikel_num=artikel_num,
                classification=classification,
                allowed_roles=allowed_roles,
                source_file=source_file_name(html_path),
                effective_date=effective_date,
            )
            if chunk is not None:
                chunks.append(chunk)

    return chunks


def source_file_name(path: Path) -> str:
    """Return just the filename, not the full path."""
    return path.name


def chunk_directory(raw_dir: Path) -> list[Chunk]:
    """Chunk all HTML files in a directory, sorted by filename for determinism."""
    all_chunks: list[Chunk] = []
    for path in sorted(raw_dir.glob("*.html")):
        all_chunks.extend(chunk_document(path))
    return all_chunks
