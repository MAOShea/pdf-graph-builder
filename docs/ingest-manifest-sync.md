# Ingest contract sync — AI-DM-Assistant ↔ pdf-graph-builder

Tier-5 **materialization contracts** are separate from Tier-4 seeds (`deltas.json`) and are **not** read by bootstrap. The runtime assistant discovers what exists by querying Neo4j after ingest — it does not read these files at chat time.

---

## Authorship = source of truth

**Rule:** The project where a file is **authored** owns the SoT. The other project may keep a **copy** (mirror). Do not call the mirror “SoT” just because it lives under `corpus/`.

| File | Authored in (SoT) | Other repo | Sync after authoring |
|---|---|---|---|
| `deltas.json` / seed stack | **ADA** | pgb may read/copy if needed | Stay in ADA; bootstrap here |
| `passage-sections.json` | **pgb** | ADA `corpus/…` **mirror** | `sync-passage-sections-from-pgb.ps1` (pgb → ADA only) |
| `ingest-manifest.json` | **pgb** | ADA `corpus/…` **mirror** | `sync-ingest-contracts-from-pgb.ps1` (pgb → ADA only) |
| `hand-authored-overrides/*.json` | **pgb** | ADA mirror | Same as ingest-manifest (pgb → ADA) |
| Outbox briefings | **ADA** | pgb `docs/` copy | `sync-outbox-briefings.ps1` |
| Inbox handoffs | **pgb** | ADA `docs/inbox/` copy | Manual copy into inbox |

**There is no script that pushes `ingest-manifest.json` (or hand-authored overrides) from ADA → pgb.** Edit the SoT in pdf-graph-builder; promote the mirror here. If an ADA agent notes a needed manifest change, put it in an **outbox briefing** for pgb — do not edit the ADA mirror as if it were SoT (or expect a reverse sync).

**Tables in chat CONTEXT:** declare `used_by` on SoT manifest rows + Tier-4 `(Seed)-[:USES]->(:LookupTable)`. Runtime matches table names/pages in the KG — avoid synonym lists in `retrieval_hints.py`.

---

## What lives where

| File | SoT repo | Mirror | Read by |
|---|---|---|---|
| `deltas.json` | ADA | — | `bootstrap.py` |
| `passage-sections.json` | pgb `games/<game>/` | ADA `corpus/games/<game>/` | pgb section / entity materializers |
| `ingest-manifest.json` | pgb `games/<game>/` | ADA `corpus/games/<game>/` | pgb ingest; ADA agents/docs (mirror) |
| `hand-authored-overrides/*` | pgb | ADA | pgb table materialization |

---

## How to sync

### After a pgb session that edited `passage-sections.json`

```powershell
# From AI-DM-Assistant repo root
.\scripts\sync-passage-sections-from-pgb.ps1
# Preview only:
.\scripts\sync-passage-sections-from-pgb.ps1 -WhatIf
```

### After a pgb session that edited `ingest-manifest.json` / hand-authored overrides

```powershell
.\scripts\sync-ingest-contracts-from-pgb.ps1
# or: .\scripts\sync-ingest-manifest.ps1   # delegates to the same from-pgb script
```

### Briefings (ADA → pgb docs only — not contracts)

```powershell
.\scripts\sync-outbox-briefings.ps1
```

### Agent paste

Paste outbox briefings into a pdf-graph-builder session when implementing ingest code. Use the **from-pgb** scripts when pgb files have changed.

---

## What pdf-graph-builder should do with the contracts

1. **Load** `games/mork-borg/ingest-manifest.json` at ingest startup.
2. **Load** `games/mork-borg/passage-sections.json` for heading-anchor chunking **and** entity-passage end rules — see [pdf-graph-builder-briefing-6.md](./pdf-graph-builder-briefing-6.md) / Briefings 10–11. Boundaries stay in the JSON; Python only matches.
3. **Materialize** p.75 index from `index_source` — see [pdf-graph-builder-briefing-7.md](./pdf-graph-builder-briefing-7.md).
4. **Match** parsed `Chunk.table_json` against manifest `columns` and shape heuristics.
5. **Materialize** `:IngestNode` table instances per briefing-3 / manifest `lookup_tables`.
6. **Validate** extracted rows against `acceptance_rows` — log mismatch, do not trust manifest text over PDF extraction.

### Flat lookup tables — one handler, role-based columns

Do **not** create per-die handlers (`d6_result`, `d8_result`, …). One materializer covers all flat tables:

| Manifest field | Purpose |
|---|---|
| `columns[].role: index` | Lookup key column (name may be `DR`, `d6`, `d66`, …) |
| `columns[].role: result` | Outcome text column |
| `pdf_extract.index` | How to enumerate index keys for PDF parsing |
| `pdf_extract.header_patterns` | Where the table starts in chunk text |

---

## Mörk Borg — current contract pointers

- Manifest (mirror): [corpus/games/mork-borg/ingest-manifest.json](../../corpus/games/mork-borg/ingest-manifest.json) — SoT in pgb `games/mork-borg/`
- Passage sections (mirror): [corpus/games/mork-borg/passage-sections.json](../../corpus/games/mork-borg/passage-sections.json) — promote from pgb with `sync-passage-sections-from-pgb.ps1`
