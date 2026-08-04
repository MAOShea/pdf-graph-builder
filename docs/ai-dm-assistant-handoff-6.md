# AI-DM-Assistant Handoff 6: Briefing 10 — entity-scoped CREATURES passages

**From:** pdf-graph-builder  
**Date:** 2026-08-04  
**Context:** [Briefing 10](./pdf-graph-builder-briefing-10.md) — anti page-bleed for catalog fiction.

**Verdict:** **PASS** — 12 CREATURES `RulePassage` nodes; Goblin prose excludes Bent/Scum/Poisoned knife.

---

## What was added

**Module:** `backend/src/entity_passage_materialization.py`

For each CREATURES `IndexEntry`, PyMuPDF page text is sliced from the creature’s heading line (`Seth, Goblin`, `Bent, Scum`, …) to the next creature heading on that page.

| Id scheme | Example |
|---|---|
| Passage id | `mork-borg.pdf#entity-passage:CREATURES:goblin` |
| `source_format` | `entity-passage` |

**Edges (prefer these in ADA retrieval before page `Chunk`):**

```text
(:IndexEntry)-[:MAPS_TO_PASSAGE]->(:RulePassage)
(:IngestNode)-[:DOCUMENTED_BY]->(:RulePassage)   // fiction entity from briefing-8
```

Wired into full `/extract` via `materialize_rulebook_catalog(..., entity_passages=True)` after fiction instances.

**Repair without full ingest:**

```powershell
backend\venv\Scripts\python.exe backend\materialize_rulebook_index.py --entity-passages-only
```

---

## Acceptance

```
Goblin has_scoped=true, page=58
preview starts with "Seth, Goblin" / Goblin block
has_bent/has_scum/has_poison = false
other CREATURES with own entity-passage = 11
total MAPS_TO_PASSAGE creature passages = 12
```

`backend\verify_briefing10.py` → **PASS**.

---

## ADA retrieval note

Prefer, in order:

1. `(IndexEntry|IngestNode) -[:MAPS_TO_PASSAGE|DOCUMENTED_BY]-> (:RulePassage {source_format:'entity-passage'})`
2. `MAPS_TO_SECTION` / section `RulePassage` (RULES)
3. Page-anchored `Chunk` (last resort — bleeds on dense pages)

Re-smoke Q3 Goblin: CONTEXT should not present Bent/Scum as Goblin stats.

---

## Out of scope / next

| Item | Status |
|---|---|
| THE_WORLD entity passages | Not in this pass (MVP = CREATURES) |
| Embeddings on entity passages | Optional; not required for CONTEXT text |
| Backend restart before next full ingest | Operator — pick up wiring in `main.py` |
