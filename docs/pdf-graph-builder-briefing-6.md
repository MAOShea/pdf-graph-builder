# Briefing 6: Section-driven chunking (heading anchors)

**For pdf-graph-builder agents.** Implements operator-declared rulebook sections as chunk/passage boundaries — replacing ad hoc **one chunk = one page** for declared phases.

**Prerequisites:** [Briefing 4](./pdf-graph-builder-briefing-4.md) Phase 1 ingest context. [Briefing 3](./pdf-graph-builder-briefing-3.md) for table materialization (orthogonal — run after section chunks exist).

**Design reference (AI-DM-Assistant):** [DESIGN.md §8.4](../../DESIGN.md#84-section-driven-chunking-heading-anchors)

**Synced artifacts (run from AI-DM-Assistant repo root):**

```powershell
.\scripts\sync-ingest-manifest.ps1
.\scripts\sync-outbox-briefings.ps1
```

| Path | Role |
|---|---|
| `games/mork-borg/passage-sections.json` | Section contracts — start/end heading regexes, seed links, phase; **`index_source`** for p.75 catalog |
| `games/mork-borg/ingest-manifest.json` | Points at `passage_sections.file`; table contracts unchanged |

---

## Problem

Today the ingest pipeline typically emits **`Chunk` nodes ~aligned to PDF pages**. That splits procedures mid-paragraph and forces downstream hacks:

| Symptom | Where it hurts |
|---|---|
| Test procedure split across pages | Incomplete CONTEXT for ability-test questions |
| Keyword search on arbitrary page text | Weak Tier B/C answers (see AI-DM-Assistant DESIGN §13.1) |
| Hardcoded page-range fallback (pp. 27–31) | Runtime POC scaffolding in `backend/app/retrieval.py` — not product policy |

**Goal:** Chunks and `RulePassage` nodes bounded by **declared section headings** in the rulebook, linked to **seed labels** from the contract.

---

## Contract: `passage-sections.json`

Source of truth: `corpus/games/mork-borg/passage-sections.json` in AI-DM-Assistant.

### Top-level fields

| Field | Purpose |
|---|---|
| `index_source` | p.75 three-column index — materialized as `RulebookIndex` / `IndexEntry` ([briefing-7](./pdf-graph-builder-briefing-7.md)) |
| `anchor_matching` | Global flags: `case_insensitive`, `normalize_whitespace`, `multiline` |
| `sections[]` | Ordered section definitions |

### Per-section fields

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Stable id stored on graph nodes (`section_id`) |
| `phase` | yes | Ingest phase gate (1 = ability-test spike) |
| `title` | yes | Human label for logs / operator review |
| `start_anchor` | yes | `{ "type": "heading_regex", "pattern": "..." }` — inclusive |
| `end_anchor` | yes | Same shape — **exclusive** (section ends before this heading) |
| `links_to_seed_labels` | yes | Seed node labels for `CONFIRMS_SEED` / `DOCUMENTED_BY` wiring |
| `extract_rule_passages` | no | Default true — emit `RulePassage` nodes inside section |
| `passage_granularity` | no | `paragraph` (default) or `section` (single passage) |
| `operator_page_hint` | no | **Verification only** — not used for boundary detection |
| `index_title` | no | Exact RULES index label — links to `IndexEntry` after briefing-7 |
| `contains_lookup_tables` | no | Names tables materialized inside section (e.g. `DRTable`) |

### Mörk Borg Phase 1 sections (v0.2.1 contract)

| `id` | `index_title` | Start anchor | End anchor | Seed links |
|---|---|---|---|---|
| `abilities` | Abilities | `^\\s*Abilities\\s*$` | `^\\s*Tests\\s*$` | AbilityScore, Agility, … |
| `tests-and-dr` | Tests | `^\\s*Tests\\s*$` | `^\\s*Carrying Capacity\\s*$` | AbilityTest, D20Roll, DR, … |
| `carrying-capacity` | Carrying capacity | `^\\s*Carrying Capacity\\s*$` | `^\\s*Hit Points\\s*$` | Strength, Agility |
| `hit-points-and-broken` | Hit Points | `^\\s*Hit Points\\s*$` | `^\\s*Violence\\s*$` | HitPoints, Toughness |

**Operator action:** Before marking contract `status: verified`, run anchor match against extracted PDF text and adjust regexes if headings differ (font/layout variants).

---

## Design: section chunking pipeline

| Step | Input | Output |
|---|---|---|
| **A. Load contract** | `passage-sections.json` | In-memory section list for active `phase` |
| **B. Build document text stream** | All page texts for `Document`, page order | Single string with page markers OR page-index map |
| **C. Match anchors** | Section start/end regexes | Character offsets / page ranges per section |
| **D. Emit section chunks** | Section text spans | `Chunk` nodes with `section_id`, `section_title`, page range |
| **E. Emit rule passages** | Paragraph splits inside section | `RulePassage` nodes + edges to seed labels |
| **F. Link to document** | Existing patterns | `PART_OF`, `FIRST_CHUNK`, `NEXT_CHUNK` as today |

Run **section chunking after PDF text extraction** and **before or alongside** constrained LLM extract. Table materialization (`enrich_pdf_tables.py`) should prefer chunks tagged with the section that declares `contains_lookup_tables`.

---

## New module: `src/section_chunking.py`

### Entry point

```python
def materialize_passage_sections(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    phase: int = 1,
) -> dict[str, int]:
    """
    Chunk document text by passage-sections.json heading anchors.
    Returns stats: sections_matched, chunks_created, passages_created,
    seed_links_created, warnings.
    """
```

Load:

1. `manifest = load_ingest_manifest(game)` → read `manifest["passage_sections"]["file"]`
2. Resolve `games/mork-borg/passage-sections.json`
3. Filter `sections` where `section["phase"] <= phase` (or `== phase` for strict mode)

### Step A — Document text stream

Concatenate extracted page text in page order. Preserve page boundaries for citation:

```python
# Pseudocode — implement with your existing page text store
pages = fetch_document_pages(graph, file_name)  # [{page_number, text}, ...]
stream, page_map = build_page_indexed_stream(pages)
```

`page_map` maps string offset → `page_number` for citation on passages.

Apply `anchor_matching.normalize_whitespace` before regex search if configured.

### Step B — Anchor resolution

For each section in contract order:

```python
start_m = re.search(start_pattern, stream, flags=re.MULTILINE | re.IGNORECASE)
end_m = re.search(end_pattern, stream[start_m.end():], flags=...) if start_m else None
section_text = stream[start_m.end() : start_m.end() + end_m.start()] if end_m else None
```

**Warnings (non-fatal):**

- Start anchor not found → skip section, log `section_id`
- End anchor not found → optionally extend to EOF with warning
- Overlapping sections → log; prefer contract order

### Step C — Create section `Chunk` nodes

MERGE stable id: `{file_name}#section:{section_id}`

Suggested properties:

| Property | Example |
|---|---|
| `id` | `mork-borg.pdf#section:tests-and-dr` |
| `section_id` | `tests-and-dr` |
| `section_title` | `Tests and Difficulty Ratings` |
| `text` | Full section text (may exceed old page chunk size) |
| `page_number_start` | 28 |
| `page_number_end` | 31 |
| `tier` | 5 |
| `coverage` | `ingest-confirmed` (after operator review) |

Relationships:

```cypher
MATCH (d:Document {fileName: $file_name})
MATCH (c:Chunk {id: $chunk_id})
MERGE (c)-[:PART_OF]->(d)
```

**Policy:** For documents with section chunks, **do not also emit overlapping page-only chunks for the same page range** (or mark page chunks `superseded_by_section: true`). Pick one strategy per ingest run to avoid duplicate retrieval noise.

### Step D — `RulePassage` extraction

When `extract_rule_passages: true`, split `section_text` on blank lines (paragraph granularity):

```python
for i, para in enumerate(paragraphs):
    passage_id = f"{file_name}#section:{section_id}#p{i}"
    # MERGE RulePassage node with text, page from page_map at para offset
```

Link to seed labels from `links_to_seed_labels`:

```cypher
MATCH (p:RulePassage {id: $passage_id})
MATCH (s:SeedNode)
WHERE $label IN labels(s)
MERGE (s)<-[:CONFIRMS_SEED]-(p)
```

Use `DOCUMENTED_BY` instead if your extract pipeline already standardizes on that direction — **pick one and stay consistent** with Briefing 4 extract instructions. AI-DM-Assistant retrieval today checks `(n)<-[:CONFIRMS_SEED]-(c:Chunk)` — extend to `RulePassage` when runtime is updated.

Optional: one `DOCUMENTED_BY` from `(AbilityTest:SeedNode)` to the passage that states the core test procedure (operator review selects canonical passage).

### Step E — Integration hook

Call from ingest completion (after PDF upload + text extraction):

```python
# After document pages exist, before enrich_pdf_tables.py
from src.section_chunking import materialize_passage_sections

section_stats = materialize_passage_sections(graph, file_name, game="mork-borg", phase=1)
logger.info("section_chunking: %s", section_stats)
```

Re-run must be **idempotent** (MERGE on stable ids).

---

## Interaction with existing pipelines

| Pipeline | Order relative to section chunking |
|---|---|
| PDF upload / page text | **Before** — section chunking needs page text |
| Section chunking | **After** page text |
| Constrained LLM extract | **After** section chunks — can use section context in prompts |
| `enrich_pdf_tables.py` / DRTable | **After** section chunks — match `DRTable` inside `tests-and-dr` |
| Briefing 5 bundle materialization | **Unchanged** — Phase 2 only |

---

## Acceptance criteria (Phase 1)

Run in Neo4j Browser (`:use morkborg`) after ingest + section materialization:

```cypher
// Section chunks exist
MATCH (c:Chunk)
WHERE c.section_id IN ['abilities', 'tests-and-dr', 'carrying-capacity', 'hit-points-and-broken']
RETURN c.section_id, c.section_title, c.page_number_start, c.page_number_end, size(c.text) AS chars
ORDER BY c.page_number_start;

// Rule passages linked to AbilityTest
MATCH (at:AbilityTest:SeedNode)<-[:CONFIRMS_SEED|DOCUMENTED_BY]-(p:RulePassage)
RETURN at.name, count(p) AS passages;

// Ability-test section mentions DR / d20 (sanity)
MATCH (c:Chunk {section_id: 'tests-and-dr'})
RETURN c.section_id, c.text CONTAINS 'DR' AS mentions_dr, c.text CONTAINS 'd20' AS mentions_d20;
```

**Pass:**

- Both Phase 1 sections matched (or operator documents anchor fix in contract)
- At least one `RulePassage` linked to `AbilityTest`
- `tests-and-dr` chunk contains DR table region (for `enrich_pdf_tables.py`)
- No duplicate page chunks covering the same text without a deprecation flag

**Fail → operator:**

- Adjust regexes in `passage-sections.json`, re-sync, re-ingest affected document

---

## Handoff to AI-DM-Assistant runtime

After section chunking ships, AI-DM-Assistant will update `backend/app/retrieval.py` to:

1. Prefer `RulePassage` + `section_id` over keyword page search
2. Map question keywords → seed labels → linked passages (using `links_to_seed_labels` graph edges)
3. Remove hardcoded pp. 27–31 fallback when section passages exist

Until then, section chunking still improves **pgb** `/chat_bot` spikes and operator review in Neo4j Browser.

---

## Out of scope (this briefing)

- Vector re-embedding strategy for large section chunks (may need sub-chunk embeddings later)
- Automatic heading discovery from PDF layout (headings are **operator-declared** in contract)
- Runtime adapter/prompt changes (AI-DM-Assistant repo)

---

## Checklist for pgb agent

- [ ] Load `games/mork-borg/passage-sections.json` from synced path
- [ ] Implement `section_chunking.py` with stable MERGE ids
- [ ] Wire into post-upload ingest hook
- [ ] Emit `section_id` on `Chunk`; emit `RulePassage` with seed links
- [ ] Avoid duplicate page + section chunks for same span
- [ ] Log anchor miss warnings with `operator_page_hint`
- [ ] Verify acceptance Cypher above on `morkborg`
- [ ] Report results to AI-DM-Assistant [inbox](../inbox/) when done
