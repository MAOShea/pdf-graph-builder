# Agent directives (pdf-graph-builder)

## Multi-root workspace (with AI-DM-Assistant)

Operator may open **this repo and AI-DM-Assistant** in one Cursor window. Then **one agent**, two git remotes. Name which root a task is for.

| Root | Touch |
| --- | --- |
| **This repo** | Ingest Python (materializers, extract); SoT `games/<game>/` contracts |
| **AI-DM-Assistant** | Seeds, bootstrap, retrieve, adapters, smokes |

- Commit only in the repo you edited. Do not copy materializers into ADA.
- Same chat can edit both trees. Edit SoT **here** (`games/<game>/`). Do **not** copy contracts into ADA `corpus/`.
- Do not write briefing/handoff courier files. Historical `*-briefing-*.md` / `*-handoff-*.md` live in git only.
- Seeds (`deltas.json`) stay in ADA. After ADA seed changes: ADA reset+bootstrap, then re-ingest here.
- Coverage/contracts may need new JSON and materializer tweaks. **Stable operator scripts** (`ingest-morkborg.ps1`, `ingest-pdf.ps1`, `check-section-gates.ps1`, `check-coverage.ps1`, `start.ps1`, and similar wrappers) must not be edited unless you ask first.

## Agent sessions

Coverage work in Cursor: **one work unit per chat**. Operator declares **session mode** (`clone` | `design`) at start — agents cannot see the model picker. Full rules: [AI-DM-Assistant AGENTS.md — Agent sessions (coverage work)](../AI-DM-Assistant/AGENTS.md#agent-sessions-coverage-work).

## PDF lookup tables — user says “parse table XYZ”

When the user asks for a table to be **parsed from the PDF** (e.g. “get `WeaponTable` in”, “parse the traps table from page 4”), treat that as an **end-to-end delivery request**, not a design discussion.

**Do whatever is required** to make the table materialize in Neo4j (`:IngestNode` + `:HAS_ENTRY` rows). Typical work, in order:

1. **DESIGN** — name the table in ADA `DESIGN.md` §6.2.3 (coverage bucket + page) if it is not already there. DESIGN leads; this manifest implements.
2. **Manifest** — add or fix the entry in `games/<game>/ingest-manifest.json` → `lookup_tables[]` (`name`, `columns`, `instance_of`, `acceptance_rows` when known).
3. **Extraction mode** — prefer PDF: add/tune `pdf_extract` (`header_patterns`, `index`, `pages`, `stop_before`, `status: verified`). If PDF parse is not viable, add `hand_authored.file` under `games/<game>/hand-authored-overrides/` and point the manifest at it.
4. **Probe** — verify parse against the PDF (e.g. `probe_npc_tables.py`, `test_pdf_table_parser.py`) before claiming done.
5. **Materialize** — run the **unified lookup-table pipeline** (PDF on disk → Neo4j). Do **not** read chunk text from Neo4j as table input.
6. **Bundle wiring** — if the table is nested or referenced (`parent_bundle`, `uses_tables`, character creation), update manifest + `optional-classes.json`; the pipeline runs bundle materialization by default.

### Two flavours, one pipeline

| Flavour | Entry | When |
|---|---|---|
| **Online service** | `.\ingest-pdf.ps1` → `POST /extract` with `ingest_mode=scaffold-diff` | Full ingest: lookup tables; MiniLM embeddings only with `-ScaffoldDiffEmbed`; Ollama Stage 2 only with `-ScaffoldDiffLlm` |
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

Contract reference: `README.md` (Use Case 2 → Lookup tables), `docs/roadmap.md`, `games/mork-borg/hand-authored-overrides/README.md`.

**Architecture pin:** contracts vs Ollama, scaffold-diff edges, prompt location, and full ingest vs light CLIs — `design.md` → *Product path: contracts first, Ollama second*. Stage 2 is **opt-in** (`-ScaffoldDiffLlm`). Chunk embeddings are **opt-in** (`-ScaffoldDiffEmbed`). After a DB reset, use full `.\ingest-morkborg.ps1` (not only `materialize-*`).

After ingest, run `.\check-section-gates.ps1` (section Chunks, IndexEntry `MAPS_TO_SECTION`, passage splits, spine `DOCUMENTED_BY` — fail closed) then `.\check-coverage.ps1` (tables). Do not treat table coverage as a substitute for the section-shape gate. ADA chat smokes come after both.

Section chunking: `games/<game>/passage-sections.json` via manifest `passage_sections.file`; **this repo is source of truth** for that file. Runs automatically on scaffold-diff extract, or `backend\materialize_passage_sections.py --phase 1`. Do not copy it into ADA.

**Boundary contract (design):** Chunk/passage spans are operator-maintained JSON, not Python hardcodes — `sections[].start_anchor`/`end_anchor` (RULES), `entity_passage.end_detection.stop_before` (CREATURES prose), and lookup-table `pdf_extract.stop_before`. Amend the JSON after a PDF pass; re-materialize. **Prompt the human operator** to run `.\tools\pdf-as-md\pdf-as-md.ps1` (with `-Section` when focused) and compare `tools/pdf-as-md/out/<game>.as.md` to the PDF — that is the visual check that passages/other JSON and the PDF parser are correct. Do not skip the prompt; do not treat parser tests or ingest gates as that check. Optional per `creatures_index` row: `text_end_hint`. Field guide: `games/mork-borg/README.md`. Tool: `tools/pdf-as-md/README.md`.

Rulebook index catalog: `index_source` in `passage-sections.json` + `rulebook_index` in manifest → `RulebookIndex`, `IndexEntry`, typed fiction instances; runs automatically on scaffold-diff extract after section chunking, or `.\materialize-rulebook-index.ps1` (requires `:Document` for `mork-borg.pdf` in Neo4j).

Entity-scoped creature prose: CREATURES index rows → per-creature `:RulePassage` (`MAPS_TO_PASSAGE` / entity `DOCUMENTED_BY`); end cuts from `entity_passage` in the same JSON; runs in the catalog pass, or `backend\materialize_rulebook_index.py --entity-passages-only`.
