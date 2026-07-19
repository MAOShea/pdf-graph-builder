# Agent directives (pdf-graph-builder)

## PDF lookup tables — user says “parse table XYZ”

When the user asks for a table to be **parsed from the PDF** (e.g. “get `WeaponTable` in”, “parse the traps table from page 4”), treat that as an **end-to-end delivery request**, not a design discussion.

**Do whatever is required** to make the table materialize in Neo4j (`:IngestNode` + `:HAS_ENTRY` rows). Typical work, in order:

1. **Manifest** — add or fix the entry in `games/<game>/ingest-manifest.json` → `lookup_tables[]` (`name`, `columns`, `instance_of`, `acceptance_rows` when known).
2. **Extraction mode** — prefer PDF: add/tune `pdf_extract` (`header_patterns`, `index`, `pages`, `stop_before`, `status: verified`). If PDF parse is not viable, add `hand_authored.file` under `games/<game>/hand-authored-overrides/` and point the manifest at it.
3. **Probe** — verify parse against the PDF (e.g. `probe_npc_tables.py`, `test_pdf_table_parser.py`) before claiming done.
4. **Materialize** — run the **unified lookup-table pipeline** (PDF on disk → Neo4j). Do **not** read chunk text from Neo4j as table input.
5. **Bundle wiring** — if the table is nested or referenced (`parent_bundle`, `uses_tables`, character creation), update manifest + `optional-classes.json`; the pipeline runs bundle materialization by default.

### Two flavours, one pipeline

| Flavour | Entry | When |
|---|---|---|
| **Online service** | `.\ingest-pdf.ps1` → `POST /extract` with `ingest_mode=scaffold-diff` | Full ingest: lookup tables + LLM scaffold-diff + embeddings |
| **CLI** | `.\ingest-tables.ps1` or `backend\ingest_tables.py` | Tables only (no LLM); same `run_lookup_table_pipeline()` |

Both call `src/table_pipeline.py` → `run_lookup_table_pipeline()`. **Source text is always the PDF file on disk.** Neo4j is the **sink** (tables, optional chunk `table_json` evidence), not the source.

```powershell
# All manifest PDF tables
.\ingest-tables.ps1

# Specific tables
.\ingest-tables.ps1 -Tables WeaponTable,ArmorTable

# Page range filter
.\ingest-tables.ps1 -StartPage 4 -EndPage 5
```

Deprecated wrappers (`enrich_pdf_tables.py`, `materialize_pdf_tables.py`, `materialize_weapon_armor.py`) delegate to `ingest_tables.py`.

Do **not** stop at “add a manifest entry” unless the user asked for explanation only.

**Complementary questions are fine** when they unblock the work (game id, page range, hand-authored vs PDF, bundle links). Do **not** ask permission to edit the manifest or run materialization when the user already asked for the table.

Contract reference: `README.md` (Use Case 2 → Lookup tables), `docs/pdf-graph-builder-briefing-3.md`, `docs/roadmap.md`, `games/mork-borg/hand-authored-overrides/README.md`.

After ingest, run `.\check-coverage.ps1` for a manifest-driven coverage report.

Section chunking (Briefing 6): `games/<game>/passage-sections.json` via manifest `passage_sections.file`; runs automatically on scaffold-diff extract, or `backend\materialize_passage_sections.py --phase 1`.

Rulebook index catalog (Briefings 7+8): `index_source` in `passage-sections.json` + `rulebook_index` in manifest → `RulebookIndex`, `IndexEntry`, typed fiction instances; runs automatically on scaffold-diff extract after section chunking, or `.\materialize-rulebook-index.ps1` (requires `:Document` for `mork-borg.pdf` in Neo4j).
