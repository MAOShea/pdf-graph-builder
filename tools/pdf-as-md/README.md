# pdf-as-md

**Markdown sink** for the shared ingest extract path. Validates PDF fidelity by eye.

Parsing is **not** owned here. It lives in:

| Module | Role |
|---|---|
| `backend/src/document_extract.py` | Normalized PDF stream, contract sections, `resolve_tables_in_span` (PDF + hand-authored) |
| `backend/src/section_chunking.py` | Section materialization (honors `content_source`) |
| `backend/src/table_pipeline.py` | Lookup-table ingest (uses `resolve_tables_in_span`) |

This tool only renders that model to `.as.md` (no Neo4j).

## Run

```powershell
.\tools\pdf-as-md\pdf-as-md.ps1
# → tools/pdf-as-md/out/mork-borg.as.md
```

| Flag | Meaning |
|---|---|
| `--phase N` | Sections with `phase <= N` |
| `--pages-only` | Full normalized stream only |
| `--sections-only` | Contract sections only |
| `--no-entities` | Skip CREATURES appendix |
| `-o PATH` | Output path |

## Design

- **Default tables:** `resolve_tables_in_span` (manifest `pdf_extract` / `hand_authored`)
- **Overrides:** `passage-sections.json` `content_source`, optional `contains_lookup_tables` allowlist
- Change parse behavior in `document_extract` / manifest — not by forking logic in this folder
