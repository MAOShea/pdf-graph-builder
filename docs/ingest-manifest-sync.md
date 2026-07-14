# Ingest manifest sync — AI-DM-Assistant → pdf-graph-builder

Tier-5 **materialization contracts** live in `corpus/games/<game>/ingest-manifest.json` (AI-DM-Assistant source of truth). They are separate from Tier-4 seeds (`deltas.json`) and are **not** read by bootstrap.

The runtime assistant discovers what exists by querying Neo4j after ingest — it does not read this file.

---

## What lives where

| File | Repo | Tier | Read by |
|---|---|---|---|
| `deltas.json` | AI-DM-Assistant | 4 — ontology | `bootstrap.py` |
| `ingest-manifest.json` | AI-DM-Assistant (source of truth) | 5 — contract | Operator; copied to pdf-graph-builder |
| `games/<game>/ingest-manifest.json` | pdf-graph-builder (runtime copy) | 5 — contract | Ingest pipeline (`table_materialization.py`, etc.) |

**pdf-graph-builder may extend the synced manifest** with `pdf_extract` blocks (detection signatures). Push verified changes back to AI-DM-Assistant when the contract stabilises.

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

1. **Load** `games/mork-borg/ingest-manifest.json` at ingest startup (replace hardcoded constants in `pdf_table_parser.py` / `table_materialization.py`).
2. **Extract** tables from PDF chunk text using each entry's `pdf_extract` signatures (see below).
3. **Match** parsed `Chunk.table_json` against manifest `columns` and shape heuristics.
4. **Materialize** `:IngestNode` table instances per briefing-3 / manifest `lookup_tables` entries.
5. **Validate** extracted rows against `acceptance_rows` — log mismatch; **PDF extraction wins** when labels differ (e.g. DR "routine but some chance of failure" vs shortened acceptance "routine").

---

## PDF table signatures (`pdf_extract`)

AI-DM-Assistant defines **what to materialize** (`columns`, `acceptance_rows`, scaffold links).

pdf-graph-builder owns **how to find tables in PDF text**. PyMuPDF `find_tables()` returns 0 for most Mörk Borg tables; content appears as inline `(dN)` headings and numbered rows in `:Chunk.text`.

### Per-entry fields

| Field | Purpose |
|---|---|
| `pdf_extract.header_patterns` | Regex list; first match starts table body |
| `pdf_extract.stop_before` | Next heading / section — end of table body |
| `pdf_extract.index.type` | See index types below |
| `pdf_extract.index.values` | For `dr_set`: explicit keys e.g. `[6,8,10,12,14,16,18]` |
| `pdf_extract.min_rows` / `max_rows` | Validation bounds |
| `pdf_extract.multi_table_page` | If true, extract repeatedly per chunk (page 4) |
| `pdf_extract.prefer_page` | When duplicates exist (DR on p.28 and p.76), prefer this page |
| `pdf_extract.status` | `verified`, `partial`, `todo` |

### Index extractor types (generic Python, not per-table)

| `index.type` | Row pattern | Used by |
|---|---|---|
| `dr_set` | Fixed values from `index.values` | DRTable |
| `d12` | Keys 1–12 | Traps, Weather, dungeon d12 tables |
| `d10` | Keys 1–10 | Occult treasures, imminent danger |
| `d6` | Keys 1–6 | Character generation |
| `d8` | Keys 1–8 | Raised in, decoctions |
| `d66` | Two-digit keys 11–66; ranges like `11–16` | Corpse plundering (hard) |
| `d6_x_d8` | Composite row keys | Name table (3 columns) |
| `d20` | Keys 1–20 | Basilisks demand, arcane catastrophes |
| `d100` | Keys 1–100 | Adventure spark |

Reference corpus (hand-authored, for tests): `corpus/mork-borg/tables/*.json`.

---

## Mörk Borg — table inventory (Bare Bones PDF)

Scanned from `mork-borg.pdf` and ingested `:Chunk` nodes (76 pages, 76 chunks). Full contracts: [games/mork-borg/ingest-manifest.json](../games/mork-borg/ingest-manifest.json).

### Phase 1 — verified / materialized

| Instance | Page | Header | Index | Cols | Rows | Status |
|---|---|---|---|---|---|---|
| `DRTable` | 28 | `Difficulty Ratings (DR)` | dr_set | DR, label | 7 | **verified** — materialized in Neo4j |

Duplicate on p.76 (quick reference) — prefer p.28 (`prefer_page: 28`).

### Phase 2 — high priority

| Instance | Page(s) | Header | Index | Cols | Rows | Notes |
|---|---|---|---|---|---|---|
| `TrapsTable` | 4 | `Traps and Devilry (d12)` | d12 | d12, Trap | 12 | Same chunk as weather + corpse; `multi_table_page` |
| `WeatherTable` | 4 | `weather (d12)` | d12 | d12, Weather | 12 | Stop before `Corpse plundering` |
| `OccultTreasuresTable` | 3 | `Occult Treasures` / `d10` | d10 | d10, Treasure | 10 | Verified from PDF p.3 |
| `CorpsePlunderTable` | 4–5 | `Corpse plundering (d66)` | d66 | d66, result | ~36 | **hand-authored** — see below |

---

## Hand-authored exceptions (`hand_authored`)

When PDF extraction is not viable (e.g. d66 Corpse plundering), use a JSON file **beside `mork-borg.pdf`** and point the manifest at it.

### Manifest fields (per `lookup_tables[]` entry)

```json
"hand_authored": {
  "file": "mork-borg-corpse-plunder-d66.json",
  "skip_pdf_extract": true
},
"pdf_extract": { "status": "hand-authored" }
```

- **`skip_pdf_extract`** — PDF parser will not attempt this table; avoids duplicate/broken rows from chunk text.
- **`file`** — path relative to workspace root (same folder as `mork-borg.pdf`).

### JSON file fields (beside PDF)

| Field | Purpose |
|---|---|
| `manifest_table` | Links file to manifest entry e.g. `CorpsePlunderTable` |
| `override_pdf` | `true` — documents that PDF content is superseded for this table |
| `blocks[].rows` | `[[d66, result], ...]` — d66 may be `"11-16"` or `21` |

**Source txt format** ([corpus/mork-borg/tables/corpse-plunder.txt](../corpus/mork-borg/tables/corpse-plunder.txt)): each row is `roll  result` where **two or more spaces** divide the d66 column from the explanation. Only the first such run is a divider; double spaces inside the result text are preserved.

```powershell
.\sync-corpse-plunder.ps1    # txt -> mork-borg-corpse-plunder-d66.json
.\ingest-hand-table.ps1      # load into Neo4j
```

Example: [mork-borg-corpse-plunder-d66.json](../mork-borg-corpse-plunder-d66.json)

### CLI ingest (no curl)

```powershell
.\ingest-hand-table.ps1
# or
cd backend
.\venv\Scripts\python.exe ingest_hand_table.py ..\mork-borg-corpse-plunder-d66.json
```

Requires prior `mork-borg.pdf` ingest (Document node in Neo4j). Full PDF re-ingest also loads hand-authored tables automatically after PDF extraction.

**Note:** `override_pdf` skips PDF **parsing** for this table. The corpse-plunder prose may still appear in page-4 chunk text for the LLM; stripping that from chunks is a separate optional step.

---
| Instance | Page | Header (approx) | Index | Status |
|---|---|---|---|---|
| `OptionalClassesTable` | 46 | `Optional Classes (d6)` | d6 | todo |
| `EarliestMemoriesTable` | 46 | `EARLIEST MEMORIES (d6)` | d6 | todo |
| `BadBirthTable` | 48 | `Bad Birth (d6)` | d6 | todo |
| `EldritchOriginsTable` | 50 | `Eldritch Origins (d6)` | d6 | todo |
| `ThingsGoingWrongTable` | 52 | `Things were going so well… (d6)` | d6 | todo |
| `RaisedInTable` | 56 | `Probably raised in (d8)` | d8 | todo |
| `HerbmasterDecoctionsTable` | 57 | `Occult Herbmaster decoctions (d8)` | d8 | todo |
| `NameTable` | TBD | Name table | d6_x_d8 | todo — 3 columns (d6, d8, Name) |

### Phase 3 — encounter / dungeon tables

| Instance | Page | Header (approx) | Index | Status |
|---|---|---|---|---|
| `WanderTable` | 68 | `Where do you wander? (d12)` | d12 | todo |
| `DwellsHereTable` | 72 | `Who or what dwells here now? (d12)` | d12 | todo |
| `DistinctiveFeatureTable` | 73 | `Distinctive feature (d12)` | d12 | todo |
| `ImminentDangerTable` | 72 | `Imminent danger (d10)` | d10 | todo |
| `AdventureSparkTable` | 69 | `Adventure spark (d100)` | d100 | todo |
| `BasilisksDemandTable` | 36 | `The Basilisks Demand (d20)` | d20 | todo |
| `ArcaneCatastrophesTable` | 43 | `Arcane catastrophes (d20)` | d20 | todo |

### Page 76 — quick reference (avoid as primary source)

p.76 concatenates DR, Initiative, Armor tiers, Broken rules, etc. Signatures overlap Phase 1–3 tables. **Prefer earlier canonical page** when duplicate headers match.

---

## Sync back to AI-DM-Assistant

When pdf-graph-builder verifies a signature against live chunks:

1. Update `acceptance_rows` from extracted PDF text (not the other way around).
2. Push manifest changes to AI-DM-Assistant source of truth, then re-sync here.
3. Do **not** add table rows to `deltas.json`.
