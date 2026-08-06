# Ingest manifest sync — AI-DM-Assistant → pdf-graph-builder

Tier-5 **materialization contracts** live in `corpus/games/<game>/ingest-manifest.json`. They are separate from Tier-4 seeds (`deltas.json`) and are **not** read by bootstrap.

The runtime assistant discovers what exists by querying Neo4j after ingest — it does not read this file.

---

## What lives where

| File | Repo | Tier | Read by |
|---|---|---|---|
| `deltas.json` | AI-DM-Assistant | 4 — ontology | `bootstrap.py` |
| `ingest-manifest.json` | AI-DM-Assistant (source of truth) | 5 — contract | Operator; copied to pdf-graph-builder |
| `passage-sections.json` | AI-DM-Assistant (source of truth) | 5 — contract | Operator; copied to pdf-graph-builder |
| `games/<game>/ingest-manifest.json` | pdf-graph-builder (runtime copy) | 5 — contract | Ingest pipeline (`table_materialization.py`, etc.) |
| `games/<game>/passage-sections.json` | pdf-graph-builder (runtime copy) | 5 — contract | Section anchors + `index_source` + `entity_passage` end rules |

---

## How to sync to pdf-graph-builder

### Option A — Sync scripts (recommended)

When outbox briefings or ingest manifest change:

```powershell
.\scripts\sync-outbox-briefings.ps1
.\scripts\sync-ingest-manifest.ps1
```

Defaults: target `d:\GitHub\pdf-graph-builder`. Override with `-PdfGraphBuilderRoot` if needed.

**Note:** pdf-graph-builder may carry a **longer** `ingest-manifest.json` than this repo (extra `lookup_tables` / `pdf_extract` blocks added during ingest work). A full copy **overwrites** those extensions. When pgb is ahead, merge new top-level blocks (e.g. `rulebook_index`) by hand or patch-only sync — do not blind-copy the shorter AI-DM-Assistant file over pgb's full manifest.

### Option B — Manual copy (manifest only)

```powershell
Copy-Item `
  "d:\GitHub\AI-DM-Assistant\corpus\games\mork-borg\ingest-manifest.json" `
  "d:\GitHub\pdf-graph-builder\games\mork-borg\ingest-manifest.json"
```

Create `games/mork-borg/` in pdf-graph-builder if it does not exist yet.

### Option C — Agent paste only

Paste [pdf-graph-builder-briefing-3.md](./pdf-graph-builder-briefing-3.md) into a pdf-graph-builder session when implementing ingest code. Use sync scripts when files have changed.

---

## What pdf-graph-builder should do with it

1. **Load** `games/mork-borg/ingest-manifest.json` at ingest startup (replace hardcoded constants in `table_materialization.py`).
2. **Load** `games/mork-borg/passage-sections.json` for heading-anchor chunking **and** entity-passage end rules — field guide [games/mork-borg/README.md](../games/mork-borg/README.md); briefings 6 / 10–11. Boundaries stay in the JSON (`sections[]` anchors, `entity_passage.stop_before`); Python only matches.
3. **Materialize** p.75 index from `index_source` — see [pdf-graph-builder-briefing-7.md](./pdf-graph-builder-briefing-7.md) and manifest `rulebook_index` block.
4. **Match** parsed `Chunk.table_json` against manifest `columns` and shape heuristics.
5. **Materialize** `:IngestNode` table instances per briefing-3 / manifest `lookup_tables` entries.
6. **Validate** extracted rows against `acceptance_rows` (operator-verified reference) — log mismatch, do not trust manifest text over PDF extraction.

### Flat lookup tables — one handler, role-based columns

Do **not** create per-die handlers (`d6_result`, `d8_result`, …). One materializer covers all flat tables:

| Manifest field | Purpose |
|---|---|
| `name` | Stable technical id (e.g. `TrapsTable`) — graph node `id` / `name` |
| `title` | Optional human/PDF title override. If omitted, extract uses the **matched PDF heading** (e.g. `Traps and Devilry (d12)`) so wording stays consistent with the book |
| `columns[].role: index` | Lookup key column (name may be `DR`, `d6`, `d66`, …) |
| `columns[].role: result` | Outcome text column |
| `pdf_extract.index` | How to enumerate index keys for PDF parsing (`dr_set`, `d6`, `d8`, sparse ranges, …) |
| `pdf_extract.header_patterns` | Where the table starts in chunk text |

Graph nodes store `title` (+ `pdf_heading` when from PDF). Do not rename `name` to match book wording — keep ids stable.

Phase 1 only needs `DRTable` `pdf_extract`. Phase 2 optional-class nested tables reuse the same handler; `parent_bundle` is graph wiring after materialize.

---

## Mörk Borg — current contract

Source: [corpus/games/mork-borg/ingest-manifest.json](../corpus/games/mork-borg/ingest-manifest.json)

Phase 1: `DRTable` on p.28 — 2 columns, 7 acceptance rows, links to `LookupTable`, `DR`, `AbilityTest`.

Phase 1 sections: [passage-sections.json](../../corpus/games/mork-borg/passage-sections.json) v0.4.0 — `abilities`, `tests-and-dr`, `carrying-capacity`, `hit-points-and-broken` (heading anchors).

Rulebook catalog: same file → `index_source` (p.75) — `rules_index` (41), `world_index` (28), `creatures_index` (12). Materialize per briefing-7.

Entity passages: same file → `entity_passage.end_detection.stop_before` (bounty/loot line regexes). Operator PDF pass can amend patterns or add per-row `text_end_hint` on `creatures_index`.
