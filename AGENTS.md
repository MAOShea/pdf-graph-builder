# Agent directives (pdf-graph-builder)

## Multi-root workspace (with AI-DM-Assistant)

Operator may open **this repo and AI-DM-Assistant** in one Cursor window. Then **one agent**, two git remotes. Name which root a task is for.

| Root | Touch |
| --- | --- |
| **This repo** | Ingest Python (materializers, extract); SoT `games/<game>/` contracts |
| **AI-DM-Assistant** | Seeds, bootstrap, retrieve, adapters, smokes |

- Commit only in the repo you edited. Do not copy materializers into ADA.
- Same chat can edit both trees. Do **not** wait for an outbox paste from a second agent.
- Briefing / `docs/ai-dm-assistant-handoff-*.md` files are **optional archive** after ingest, not the workflow.
- ADA `corpus/games/<game>/` copies are mirrors. Edit SoT **here**; promote with ADA `sync-*-from-pgb.ps1`. Sync policy: `docs/ingest-manifest-sync.md`.

If this window is **pgb-only**, ADA still uses outbox/inbox as a courier.

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

**Architecture pin:** contracts vs Ollama, scaffold-diff edges, prompt location, and full ingest vs light CLIs — `design.md` → *Product path: contracts first, Ollama second*. After a DB reset, use full `.\ingest-morkborg.ps1` (not only `materialize-*`).

After ingest, run `.\check-section-gates.ps1` (section Chunks, IndexEntry `MAPS_TO_SECTION`, passage splits, spine `DOCUMENTED_BY` — fail closed) then `.\check-coverage.ps1` (tables). Do not treat table coverage as a substitute for the section-shape gate. ADA chat smokes come after both.

Section chunking (Briefing 6): `games/<game>/passage-sections.json` via manifest `passage_sections.file`; **pdf-graph-builder is source of truth** for that file (not ADA). Runs automatically on scaffold-diff extract, or `backend\materialize_passage_sections.py --phase 1`. Sync policy: `docs/ingest-manifest-sync.md`.

**Boundary contract (design):** Chunk/passage spans are operator-maintained JSON, not Python hardcodes — `sections[].start_anchor`/`end_anchor` (RULES), `entity_passage.end_detection.stop_before` (CREATURES prose), and lookup-table `pdf_extract.stop_before`. Amend the JSON after a PDF pass; re-materialize. Optional per `creatures_index` row: `text_end_hint`. Field guide: `games/mork-borg/README.md`.

Rulebook index catalog (Briefings 7+8): `index_source` in `passage-sections.json` + `rulebook_index` in manifest → `RulebookIndex`, `IndexEntry`, typed fiction instances; runs automatically on scaffold-diff extract after section chunking, or `.\materialize-rulebook-index.ps1` (requires `:Document` for `mork-borg.pdf` in Neo4j).

Entity-scoped creature prose (Briefings 10–11): CREATURES index rows → per-creature `:RulePassage` (`MAPS_TO_PASSAGE` / entity `DOCUMENTED_BY`); end cuts from `entity_passage` in the same JSON; runs in the catalog pass, or `backend\materialize_rulebook_index.py --entity-passages-only`.
