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
| `games/<game>/passage-sections.json` | pdf-graph-builder (runtime copy) | 5 — contract | Section chunking (`section_chunking.py`, etc.) |

---

## How to sync to pdf-graph-builder

### Option A — Sync scripts (recommended)

When outbox briefings or ingest manifest change:

```powershell
.\scripts\sync-outbox-briefings.ps1
.\scripts\sync-ingest-manifest.ps1
```

Defaults: target `d:\GitHub\pdf-graph-builder`. Override with `-PdfGraphBuilderRoot` if needed.

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
2. **Load** `games/mork-borg/passage-sections.json` for heading-anchor chunking — see [pdf-graph-builder-briefing-6.md](./pdf-graph-builder-briefing-6.md).
3. **Match** parsed `Chunk.table_json` against manifest `columns` and shape heuristics.
4. **Materialize** `:IngestNode` table instances per briefing-3 / manifest `lookup_tables` entries.
5. **Validate** extracted rows against `acceptance_rows` (operator-verified reference) — log mismatch, do not trust manifest text over PDF extraction.

### Flat lookup tables — one handler, role-based columns

Do **not** create per-die handlers (`d6_result`, `d8_result`, …). One materializer covers all flat tables:

| Manifest field | Purpose |
|---|---|
| `columns[].role: index` | Lookup key column (name may be `DR`, `d6`, `d66`, …) |
| `columns[].role: result` | Outcome text column |
| `pdf_extract.index` | How to enumerate index keys for PDF parsing (`dr_set`, `d6`, `d8`, sparse ranges, …) |
| `pdf_extract.header_patterns` | Where the table starts in chunk text |

Phase 1 only needs `DRTable` `pdf_extract`. Phase 2 optional-class nested tables reuse the same handler; `parent_bundle` is graph wiring after materialize.

---

## Mörk Borg — current contract

Source: [corpus/games/mork-borg/ingest-manifest.json](../corpus/games/mork-borg/ingest-manifest.json)

Phase 1: `DRTable` on p.28 — 2 columns, 7 acceptance rows, links to `LookupTable`, `DR`, `AbilityTest`.

Phase 1 sections: [passage-sections.json](../../corpus/games/mork-borg/passage-sections.json) — `abilities`, `ability-tests-and-dr` (heading anchors).
