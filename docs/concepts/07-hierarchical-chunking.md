# 07 — Hierarchical Chunking

## What it is

Hierarchical chunking means splitting documents along their structural boundaries rather than by character count or token count. Instead of "every 512 tokens, split," we split "at the end of each lid (paragraph) of each artikel." The resulting chunks are bounded by the document's own logical structure, and every chunk carries a full breadcrumb of where it came from as metadata.

## Why it matters for this project

Legal citations require precision. If a user asks about "artikel 3.114 lid 2 Wet IB 2001" and the system's answer doesn't come from exactly that provision, it's wrong regardless of semantic similarity. Standard character splitters shred these structures — a `RecursiveCharacterTextSplitter` at 512 tokens might split an artikel in the middle, merging half of one lid with half of the next into a single chunk. That chunk's citation would be meaningless. (See TRAP 1.)

More critically: every chunk must carry the metadata that drives RBAC. Without `classification` and `allowed_roles` on every chunk, the pre-filter at the vector query stage has nothing to filter on. Hierarchical chunking is how that metadata gets embedded into the corpus.

## The legal hierarchy for Dutch legislation

```
Wet (Act)
  └── Hoofdstuk (Chapter)
        └── Afdeling (Section)
              └── Artikel (Article)
                    └── Lid (Paragraph/Subsection)
                          └── Sub-bepaling (a, b, c...)
```

Typical chunk boundary: one `lid`. Short artikels without lids are one chunk each.

For case law (jurisprudence), the hierarchy is different:
```
ECLI identifier
  └── r.o. (rechtsoverweging) number
```

One rechtsoverweging = one chunk.

## The ChunkMetadata schema

```python
class ChunkMetadata(BaseModel):
    wet: str                            # "Wet inkomstenbelasting 2001"
    hoofdstuk: str                      # "3"
    afdeling: str | None
    artikel: str                        # "3.114"
    lid: int | None                     # 2
    sub: str | None                     # "a", "b", etc.
    classification: Literal["public", "internal", "fiod"]
    allowed_roles: list[str]
    doc_id: str
    source_url: str
    effective_date: date | None
```

This schema is stored as Qdrant payload alongside the vector. The RBAC pre-filter queries `allowed_roles` and `classification` from this payload.

## Fallback for non-standard documents

E-learning materials, policy memos, and other documents that don't fit the Wet/Artikel/Lid hierarchy get semantic chunking: split on headings and paragraphs. Still must carry `doc_id`, `classification`, and `allowed_roles`. Document this fallback explicitly in the design doc and in the chunker code.

## Concrete example

Input: Article 3.16a Wet IB 2001, two lids.

Output chunks:
```
chunk_1:
  text: "Artikel 3.16a, lid 1: De kosten van een werkruimte..."
  metadata: {wet: "Wet inkomstenbelasting 2001", artikel: "3.16a", lid: 1,
             classification: "public", allowed_roles: ["public", "helpdesk", "fiod"]}

chunk_2:
  text: "Artikel 3.16a, lid 2: In afwijking van het eerste lid..."
  metadata: {wet: "Wet inkomstenbelasting 2001", artikel: "3.16a", lid: 2,
             classification: "public", allowed_roles: ["public", "helpdesk", "fiod"]}
```

A `RecursiveCharacterTextSplitter` would probably merge these two lids — and might also grab the first line of artikel 3.17. Then the citation "artikel 3.16a" would be half correct.

## How it appears in our code

TODO — see `src/ingestion/chunker.py` once Phase 2 is implemented.

## Self-check questions

1. Why does using `RecursiveCharacterTextSplitter` make citation enforcement impossible for Dutch legal documents?
2. A chunk has `classification: "internal"` and `allowed_roles: ["helpdesk", "fiod"]`. A public user queries the system. At what stage is this chunk excluded, and why not at the Python application layer?
3. An e-learning PDF has no legal hierarchy. What must the fallback chunker still preserve, and why?
