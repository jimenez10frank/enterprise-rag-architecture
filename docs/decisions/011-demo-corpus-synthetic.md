# 011. Demo corpus: synthetic structured HTML vs full wetten.overheid.nl harvest

**Date:** 2026-05-08
**Status:** Accepted (interim demo scope)
**Phase introduced:** 2.1

## Context

`docs/project/ROADMAP.md` Phase 2.1 describes downloading ~**50 real** articles and rulings from `wetten.overheid.nl` and related sources. `docs/project/ASSESSMENT.md` asks for a **working vertical slice** on ~**50 real** documents while the **design doc** carries production scale.

**Actual progress (PROGRESS.md):** Phase 2 uses **16 synthetic HTML files** (`data/raw/README.md`) that **mimic** Dutch legal structure and RBAC metadata, but are **not** copies of government publications.

## Options considered

### Option A: Block implementation until all real URLs are harvested

- **Pros:** Perfect alignment with ROADMAP 2.1 wording.
- **Cons:** Slows proving ingestion/RBAC/retrieval/CRAG; licensing/traceability work for bulk download.

### Option B: Ship **synthetic** corpus now; treat real harvest as **enhancement** tracked explicitly

- **Pros:** Unblocks Modules 1–3 and agent work; chunker + RBAC still validated structurally.
- **Cons:** “Real Dutch law” nuance and edge cases underrepresented until real docs land.

## Decision

We chose **Option B** for the **current repo state**, documented honestly in `data/raw/README.md` and this ADR.

Reasoning:

- The rubric rewards **architectural judgment** and a **working pipeline**, not only corpus size.
- Remaining gap is **explicitly visible** so Phase 6 can discuss tradeoffs and future work.

## Consequences

**What this makes easy:** CI and local dev without network dependencies to government sites.

**What this makes hard:** Ragas baselines and stakeholder demos must caveat “synthetic sources”; **golden set** (Phase 5.5) should prefer **real** snippets when added.

**Rollback path:** Import real corpus under `data/raw/` per ROADMAP, update README with source URLs and download dates — supersede scope claims in Phase 6 README.

## References

- `docs/project/ROADMAP.md` § Phase 2.1
- `data/raw/README.md`
- `docs/project/PROGRESS.md`
