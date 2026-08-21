# pdf-as-md

**Markdown sink** for the shared ingest extract path. Validates PDF fidelity by eye.

Parsing is **not** owned here. It lives in:

| Module | Role |
|---|---|
| `backend/src/document_extract.py` | Normalized PDF stream, contract sections, `resolve_tables_in_span` (PDF + hand-authored) |
| `backend/src/section_chunking.py` | Section materialization (honors `content_source`) |
| `backend/src/table_pipeline.py` | Lookup-table ingest (uses `resolve_tables_in_span`) |
| `backend/src/spine_materialization.py` | Operational If contract (`operational-spines.json`); pdf-as-md renders THEN/ELSE + evidence needles vs the span |

This tool only renders that model to `.as.md` (no Neo4j).

## Run

```powershell
.\tools\pdf-as-md\pdf-as-md.ps1
# → tools/pdf-as-md/out/mork-borg.as.md  (full book + (unsectioned) gaps)

# Focused review by contract section id (clips to those spans; skips CREATURES appendix)
.\tools\pdf-as-md\pdf-as-md.ps1 -Section equipment
.\tools\pdf-as-md\pdf-as-md.ps1 -Section reaction-morale,crit-fumble-rest
```

| Flag | Meaning |
|---|---|
| `-Section` / `--section ID` | Include only these contract section ids (repeatable; comma-separated OK). **Focused dump:** clip to those spans — `(unsectioned)` only *between* selected ids, not the rest of the book. Skips the CREATURES appendix. Default (no `-Section`): all matched sections. Not an ingest `section_phase` gate. |
| `--pages-only` | Full normalized stream only |
| `--sections-only` | Contract sections only — no `(unsectioned)` gaps (even between two `-Section` ids) |
| `--no-entities` | Skip CREATURES appendix (implied by `-Section`) |
| `-o PATH` | Output path |

## Design

- **Default tables:** `resolve_tables_in_span` (manifest `pdf_extract` sequential, `aligned_columns`, `split_italic`, or `hand_authored`). `split_italic` tables render the italic result column in `*markdown italics*` so the operator can check vs the PDF.
- **Spines:** Ifs whose `evidence.section_id` cites the section — contracted THEN/ELSE plus whether `text_contains_any` hits the span. PDF dagger/BEL bullet runs in that section are replaced in-place with a tagged markdown list (same role as a table grid). Not a parse into Neo4j.
- **Overrides:** `passage-sections.json` `content_source`, optional `contains_lookup_tables` allowlist
- Change parse behavior in `document_extract` / manifest — not by forking logic in this folder
