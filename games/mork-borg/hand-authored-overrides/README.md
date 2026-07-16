# Hand-authored overrides (Mörk Borg)

Content here **overrides the same information from the PDF** when automated extraction is unreliable or impossible.

Referenced from `ingest-manifest.json` via `hand_authored.file` or used by `bundle_materialization.py` (`optional-classes.json`).

| File | Role |
|---|---|
| `corpse-plunder.txt` | Human-editable source; run `sync-corpse-plunder.ps1` to refresh JSON |
| `corpse-plunder-d66.json` | Ingest-ready; `CorpsePlunderTable` |
| `optional-classes.json` | Optional-class selector + bundle map |
| `name-table.json` | `NameTable` — hand-authored (manifest `hand_authored.file`) |
| `traps-and-weather.json` | Reference copy; `TrapsTable` / `WeatherTable` materialize from PDF p.4 |
| `occult-treasures.json` | Reference copy (5/10 rows); graph uses PDF parse (10 rows) |

PDF ingest still runs for chunks and LLM extract; materialization prefers these files where manifest says `hand_authored` / `pdf_extract.status: hand-authored`.
