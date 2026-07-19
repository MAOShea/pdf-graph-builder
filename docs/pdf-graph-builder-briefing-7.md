# Briefing 7: Rulebook catalog — p.75 index materialization

**For pdf-graph-builder agents.** Materializes the publisher index from `passage-sections.json` → `index_source` as **`RulebookIndex`** and **`IndexEntry`** nodes in Neo4j.

**Prerequisites:** [Briefing 6](./pdf-graph-builder-briefing-6.md) (section chunking uses the same contract file). [Briefing 4](./pdf-graph-builder-briefing-4.md) for ingest context.

**Follow-on:** [Briefing 8](./pdf-graph-builder-briefing-8.md) — typed fiction instances from `entry_kind` (after bootstrap with Place/Creature seeds).

**Design reference (AI-DM-Assistant):** [DESIGN.md §8.5](../../DESIGN.md#85-rulebook-catalog-layer-p75-index)

**Synced artifacts:**

```powershell
.\scripts\sync-ingest-manifest.ps1
.\scripts\sync-outbox-briefings.ps1
```

| Path | Role |
|---|---|
| `games/mork-borg/passage-sections.json` | `index_source` — `world_index`, `creatures_index`, `rules_index` |
| `games/mork-borg/ingest-manifest.json` | `rulebook_index` block — labels, column map, id pattern |

---

## Problem

The Bare Bones rulebook index (p.75) lists **81 entries** in three columns: THE WORLD, CREATURES, RULES. Operators and runtime need:

| Query | Without catalog | With catalog |
|---|---|---|
| List all RULES index labels | Scrape chunks / guess | One Cypher on `IndexEntry` |
| “Where is Galgenbeck?” | Keyword search | `THE_WORLD` entry + page |
| Link creature name → stat block | Fuzzy match on text | `CREATURES` entry → `MAPS_TO` StatBlock |

Section chunking ([briefing-6](./pdf-graph-builder-briefing-6.md)) answers **content boundaries**; the index answers **exact publisher labels**.

---

## Contract: `index_source`

In `passage-sections.json` v0.2.1+:

```json
"index_source": {
  "page": 75,
  "layout": "three_columns",
  "columns": ["THE WORLD", "CREATURES", "RULES"],
  "world_index": [{"page": 12, "title": "Galgenbeck"}, ...],
  "creatures_index": [...],
  "rules_index": [...]
}
```

Each array item: `{ "page": number, "title": string }`. Optional future fields: `entry_kind`, `also_in_column`.

**Column enum stored on nodes:** normalize to `THE_WORLD`, `CREATURES`, `RULES` (underscores, no spaces).

---

## Graph model

### Nodes

**RulebookIndex** (one per indexed document):

| Property | Example |
|---|---|
| `id` | `mork-borg.pdf#rulebook-index` |
| `index_page` | 75 |
| `layout` | `three_columns` |
| `tier` | 5 |

**IndexEntry** (one per index row):

| Property | Example |
|---|---|
| `id` | `mork-borg.pdf#index:RULES:tests` |
| `title` | `Tests` |
| `page` | 28 |
| `column` | `RULES` |
| `entry_kind` | `rule_topic` (optional — see below) |
| `tier` | 5 |

### Relationships

```cypher
MATCH (d:Document {fileName: $file_name})
MATCH (idx:RulebookIndex {id: $index_id})
MERGE (d)-[:HAS_INDEX]->(idx)

MATCH (idx)-[:HAS_ENTRY]->(e:IndexEntry)
MERGE (e)-[:INDEXED_IN]->(d)   // page hint lives on e.page

// Optional wiring (same ingest pass or follow-up):
MATCH (e:IndexEntry {title: $index_title})-[:MAPS_TO_SECTION]->(c:Chunk)
WHERE c.section_id = $section_id

MATCH (e:IndexEntry {column: 'CREATURES'})-[:MAPS_TO]->(s:StatBlock)
```

**Cross-column duplicates:** e.g. “Calendar of Nechrubel” in RULES (p.17) and “Calendar of Nechrubel, the” in THE_WORLD (p.17). MERGE both entries; add `(e1)-[:ALSO_INDEXED_AS]->(e2)` when titles normalize to the same concept (operator review).

---

## New module: `src/index_materialization.py`

### Entry point

```python
def materialize_rulebook_index(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
) -> dict[str, int]:
    """
    Load index_source from passage-sections.json + rulebook_index from ingest-manifest.
    Returns stats: entries_created, by_column, also_indexed_links, warnings.
    """
```

Load path:

1. `manifest = load_ingest_manifest(game)` → `manifest["rulebook_index"]`
2. Resolve `games/mork-borg/passage-sections.json` → `index_source`
3. For each column in `column_map`, iterate the matching JSON array

### Stable ids

```python
def slug_title(title: str) -> str:
    # lowercase, strip punctuation, collapse whitespace → hyphenated slug
    ...

entry_id = f"{file_name}#index:{column}:{slug_title(title)}"
index_id = f"{file_name}#rulebook-index"
```

Re-run must be **idempotent** (MERGE on `id`).

### Optional `entry_kind`

Manifest lists suggested kinds per column. Initial ingest may leave `entry_kind` null; a small operator CSV or heuristics pass can tag THE_WORLD entries (Galgenbeck → `location`, Josilfa Migol → `person`). Do not block Phase 1 on full tagging.

---

## Wire to `sections[]`

When `sections[].index_title` is present, link matching RULES index entry:

```cypher
MATCH (e:IndexEntry {column: 'RULES', title: $index_title})
MATCH (c:Chunk {section_id: $section_id})
MERGE (e)-[:MAPS_TO_SECTION]->(c)
```

Multiple index rows may map to one section (p.30 Attack/Combat/Defence → `violence-combat`). One index row must not map to multiple sections.

---

## Integration hook

Run **after** document upload (Document node exists), **before or after** section chunking:

```python
from src.index_materialization import materialize_rulebook_index

index_stats = materialize_rulebook_index(graph, file_name, game="mork-borg")
logger.info("rulebook_index: %s", index_stats)
```

Order relative to briefing-6:

| Order | Rationale |
|---|---|
| Index **before** sections | Section linker can query IndexEntry |
| Index **after** sections | Section chunks must exist for MAPS_TO_SECTION |

Either works if linker runs as a second pass after both complete.

---

## Acceptance criteria

Run in Neo4j Browser (`:use morkborg`):

```cypher
// Index shell
MATCH (d:Document)-[:HAS_INDEX]->(idx:RulebookIndex)
RETURN d.fileName, idx.index_page, idx.layout;

// Count by column (expect ~28 / ~12 / ~41 for Bare Bones)
MATCH (idx:RulebookIndex)-[:HAS_ENTRY]->(e:IndexEntry)
RETURN e.column, count(e) AS n ORDER BY e.column;

// RULES catalog query
MATCH (idx:RulebookIndex)-[:HAS_ENTRY]->(e:IndexEntry)
WHERE e.column = 'RULES'
RETURN e.title, e.page ORDER BY e.page, e.title;

// Section links for Phase 1
MATCH (e:IndexEntry {title: 'Tests'})-[:MAPS_TO_SECTION]->(c:Chunk)
RETURN e.title, c.section_id;
```

**Pass:**

- One `RulebookIndex` per ingested Bare Bones document
- Entry counts match contract arrays (±0)
- Phase 1 RULES entries (`Abilities`, `Tests`, `Carrying capacity`, `Hit Points`) link to section chunks when briefing-6 has run
- No duplicate `IndexEntry.id` for same title+column

**Fail → operator:**

- Fix `index_source` in `passage-sections.json`, re-sync, re-run materializer

---

## Out of scope (this briefing)

- Automatic `entry_kind` inference from PDF (operator/heuristic pass OK)
- StatBlock linking for all CREATURES (follow ingest extract)
- Table registry nodes (separate — manifest `lookup_tables[]`)
- Runtime retrieval changes (AI-DM-Assistant `backend/app/retrieval.py`)

---

## Handoff to AI-DM-Assistant runtime

After index nodes exist:

1. Resolve question terms → `IndexEntry` (RULES) → `MAPS_TO_SECTION` → `RulePassage`
2. DM prep: list CREATURES / THE_WORLD from catalog without chunk search
3. Surface index page in citations alongside passage page

Report results to AI-DM-Assistant [inbox](../inbox/) when done.

---

## Checklist for pgb agent

- [ ] Load `rulebook_index` from ingest-manifest + `index_source` from passage-sections.json
- [ ] Implement `index_materialization.py` with MERGE ids
- [ ] Emit `RulebookIndex`, `IndexEntry`, `HAS_INDEX`, `HAS_ENTRY`, `INDEXED_IN`
- [ ] Link `sections[].index_title` → `MAPS_TO_SECTION` when chunks exist
- [ ] Log cross-column title pairs for `ALSO_INDEXED_AS` review
- [ ] Verify acceptance Cypher on `morkborg`
- [ ] Report to AI-DM-Assistant inbox
