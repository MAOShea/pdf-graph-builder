# Mörk Borg ingest contracts

Tier-5 materialization contracts for this game. **This folder is the only copy.** Do not copy these files into AI-DM-Assistant. Policy: [docs/ingest-manifest-sync.md](../../docs/ingest-manifest-sync.md).

| File | Source of truth | Role |
|---|---|---|
| [`passage-sections.json`](./passage-sections.json) | **This repo** | Section anchors, `text_filters`, p.75 index, entity-passage end rules |
| [`ingest-manifest.json`](./ingest-manifest.json) | **This repo** | Lookup tables, `pdf_extract`, bundles, pointers |
| [`operational-spines.json`](./operational-spines.json) | **This repo** | Altitude-D If spines |
| [`hand-authored-overrides/`](./hand-authored-overrides/) | **This repo** | Table JSON when PDF parse is not viable — [README](./hand-authored-overrides/README.md) |

Edit contracts **here**. After ingest, run `.\check-section-gates.ps1` then `.\check-coverage.ps1`. Full ingest: `.\ingest-morkborg.ps1` (Ollama Stage 2 off unless `-ScaffoldDiffLlm`; MiniLM embeddings off unless `-ScaffoldDiffEmbed`).

**Design:** passage/table **boundaries live in JSON**, not hardcoded in Python. Amend the contract after a PDF pass; re-run ingest or the relevant materializer.

---

## `passage-sections.json`

Operator-maintained contract for:

1. **RULES mechanism sections** — heading-anchor chunking → section `Chunk` + `RulePassage`
2. **Publisher index (p.75)** — `RulebookIndex` / `IndexEntry` + fiction `INSTANCE_OF`
3. **CREATURES entity prose** — per-creature `RulePassage` with contract-driven end cuts

Field guide: this README. Historical implementation notes (briefings 6–11) are in git.

### Top-level fields

| Field | Purpose |
|---|---|
| `id`, `game`, `version`, `status` | Contract identity (`draft` → `verified` after operator PDF check) |
| `verified_against`, `verified_date`, `verified_note` | Provenance / operator notes |
| `index_source` | p.75 three-column catalog |
| `anchor_matching` | Global regex flags for section anchors |
| `text_filters` | Strip running PDF headers/footers from the shared extract stream |
| `entity_passage` | CREATURES span end rules (`stop_before`) |
| `sections[]` | Ordered RULES section definitions |

### `text_filters`

Stream hygiene for every page before section/table resolve (not table-specific — do **not** put this in `ingest-manifest.json`).

| Field | Purpose |
|---|---|
| `drop_line_patterns` | Regexes; whole lines that fullmatch are removed |
| `strip_inline_patterns` | Regexes; matching substrings removed within a line |
| `drop_edge_page_number` | Drop a first/last line that is only the page number (keeps mid-page table keys like a lone `1`) |

### `index_source`

| Field | Purpose |
|---|---|
| `page` | Index page in the PDF (Bare Bones: 75) |
| `layout` | e.g. `three_columns` |
| `columns` | Display names: `THE WORLD`, `CREATURES`, `RULES` |
| `world_index` / `creatures_index` / `rules_index` | Arrays of index rows |

**Per index row:**

| Field | Required | Purpose |
|---|---|---|
| `title` | yes | Exact (or near-exact) publisher label |
| `page` | yes | Hint page for that entry (not used as section boundary) |
| `entry_kind` | yes* | Fiction/routing kind → seed via manifest `entry_kind_to_seed` (`creature`, `place`, `faction`, …) |
| `maps_to_seed` | no | RULES → mechanism: `IndexEntry-[:MAPS_TO_SEED]->SeedNode` labels (e.g. Powers + Scrolls → `Power`). Not a SeedNode for the publisher title itself. |
| `uses_tables` | no | RULES → lookup table: `IndexEntry-[:USES]->` ingest table ids (e.g. Weapons → `WeaponTable`; Equipment → shop lists). Materialize tables first. |
| `text_end_hint` | no | Exclusive end for that creature’s entity passage (literal or regex) when shared `stop_before` fails |

\*Required for fiction wiring (Briefing 8); amend if a row maps to the wrong seed type.

Graph column enums use underscores: `THE_WORLD`, `CREATURES`, `RULES`.

### `anchor_matching`

| Field | Purpose |
|---|---|
| `strategy` | Currently `heading_regex` |
| `case_insensitive` | Match ignoring case |
| `normalize_whitespace` | Collapse whitespace before match |
| `multiline` | `^` / `$` apply per line |

### `sections[]` (RULES mechanics)

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Stable id on graph nodes (`section_id`) |
| `phase` | yes | Ingest phase gate (`1` = ability-test spike; higher = later) |
| `title` | yes | Human label |
| `start_anchor` | yes | Boundary start — see anchor types below |
| `end_anchor` | if `heading_regex` | Exclusive end heading (required for `heading_regex`; unused for `page_range`) |
| `links_to_seed_labels` | yes | Seed labels for `CONFIRMS_SEED` / `DOCUMENTED_BY` |
| `index_title` | no | Primary RULES index label → `IndexEntry` `MAPS_TO_SECTION` (kept for tools) |
| `index_titles` | no | All RULES index labels that map to this section Chunk (compound spans). Linker prefers this list over singular `index_title`. |
| `operator_page_hint` | no | Verification only — **not** used for boundary detection |
| `extract_rule_passages` | no | Default true |
| `passage_granularity` | no | `paragraph` (default), `section`, or `subheading_regex` |
| `passage_split` | if `subheading_regex` | `{ "type": "heading_regex", "pattern": "..." }` — each match starts a passage (inclusive); preamble before first match kept |
| `column` | no | Index column hint (`THE_WORLD`, `RULES`, …) for operator/tools |
| `contains_lookup_tables` | no | **Override allowlist** — if set, only try these manifest tables on this span. Default (omit): auto-detect any verified `pdf_extract` table |
| `content_source` | no | **Override** when PDF text cannot represent the span (see below) |
| `notes` | no | Operator comments |

**THE WORLD place blocks (v0.5.5):** gothic titles are ordinary `heading_regex` sections on the concatenated stream (so “The Western Kingdom” may start on p.15 and end on p.16). Two-line titles use `\\n` in the pattern (`What Was Written` / `Must Be Known`, `Valley of the` / `Unfortunate Undead`). Nested smaller heads use `passage_granularity: subheading_regex` (Roman I–IV under What Was Written; `Anthelia’s Ambivalence` under Kergüs).

Match against **PDF text on disk**, not Neo4j chunk text.

#### Anchor types (`start_anchor.type`)

| `type` | Fields | Behavior |
|---|---|---|
| `heading_regex` | `pattern` | Inclusive match; body starts after the heading. Pair with `end_anchor` (`heading_regex`) exclusive end. |
| `page_range` | `start_page`, `end_page` | Whole pages **inclusive** (e.g. 6–7 = Colophon/credits). No heading match; `end_anchor` unused. |

**Default vs override (tables):** `pdf-as-md` / table ingest treat a span as a table when ingest-manifest `pdf_extract.header_patterns` match.

- **Sequential (default):** `extract_table_from_text` on the flattened `get_text()` stream — index token + remainder. That is enough for die/DR lists.
- **`aligned_columns`:** when the book is a 2- or 3-column list and `get_text()` stacks each cell on its own line. Parser reads PDF word x-coordinates; `column_x_cuts` in the manifest are the left edges of columns 1..n-1 (operator-maintained, like `stop_before`). Wrapped notes (only the last column filled) join the previous row.
- **`split_italic`:** sequential index keys, then two result columns from PDF span italic (roman → column 1 `immediate`, italic → column 2 `unrealized`). Flattened `get_text()` cannot do this. Regular glyph islands (`d4`, `HP`) between italic neighbors inherit italic — that is PDF subset encoding, not a second roman outcome. Continuation headers (`… (d20) cont.`) are dropped. Requires the PDF file.
- **`content_source` / hand-authored:** `passage-sections.json` override when PDF text still cannot represent the span (e.g. two-column name grid).

`passage-sections.json` `contains_lookup_tables` is an optional allowlist when auto-detect would pick the wrong table.

#### `content_source` (optional override)

Use when the PDF span matches but `get_text()` cannot represent the content (e.g. two-column name grid). Anchors still locate the span; the body comes from a file.

| Field | Purpose |
|---|---|
| `type` | Currently `hand_authored_file` |
| `file` | Path relative to `games/<game>/` (e.g. `hand-authored-overrides/name-table.json`) |
| `skip_pdf_text` | Default true — omit shredded PDF text for this span |
| `render` | Hint for tools (`blocks` = `name-table.json` shape with `blocks[].type: table`) |
| `notes` | Operator comments |

Example: section `character-names` → `hand-authored-overrides/name-table.json` (same file as ingest-manifest `NameTable`). `tools/pdf-as-md` renders it as a Markdown table and skips the PDF stream for that span.

### `entity_passage` (CREATURES prose)

| Field | Purpose |
|---|---|
| `enabled` | If `false`, skip entity-passage materialization |
| `columns` | Which index columns to slice (MVP: `["CREATURES"]`) |
| `end_detection.order` | Cut priority, e.g. `next_index_title_on_page` then `stop_before` |
| `end_detection.stop_before` | List of `{ "type": "line_regex", "pattern": "...", "notes": "..." }` — **exclusive** whole-line cuts (bounty/loot tallies) |
| `end_detection.stop_before_flags` | Regex flags string, typically `"im"` |

**End of a creature span** = earliest of: next creature heading on the page, first `stop_before` hit, optional row `text_end_hint`.

After editing: re-run full ingest, or recovery  
`backend\materialize_rulebook_index.py --entity-passages-only`.

### Operator checklist

1. Open the Bare Bones PDF at the relevant pages.
2. Confirm section headings match `start_anchor` / `end_anchor` patterns (font/OCR variants).
3. Confirm creature blocks stop before bounty lines; amend `stop_before` or add `text_end_hint` if a label is missing.
4. Confirm `entry_kind` on index rows (wrong kind → wrong `INSTANCE_OF` seed).
5. Bump `version` / `verified_note` when you change boundaries; set `status: verified` when happy.
6. After full ingest, from the pgb repo root run `.\check-section-gates.ps1` (fail-closed section/index/spine shape) then `.\check-coverage.ps1` (tables). ADA smokes are the consumer check, not this gate.

**Validate extract vs PDF:** run [`tools/pdf-as-md`](../../tools/pdf-as-md) — Markdown **sink** over `backend/src/document_extract.py` (shared with ingest). Optional `-Section <id>` for a focused dump (clips to that span; skips CREATURES appendix). Tables in the span render as markdown rows. Spines that cite the section render as a **THEN/ELSE contract panel**; PDF dagger/BEL lists in that span are replaced with a tagged markdown list (same metadata line as a table). Do not add parse logic in the tool.

---

## `ingest-manifest.json` (pointer)

Lookup-table delivery and table `pdf_extract.stop_before` are documented in the root [README](../../README.md) (Use Case 2) and [hand-authored-overrides/README.md](./hand-authored-overrides/README.md). Manifest fields `passage_sections.file` and `rulebook_index` point at this folder’s passage contract.
