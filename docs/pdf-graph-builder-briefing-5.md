# Briefing 5: Implement bundle materialization (Phase 2 — Optional Classes)

**For pdf-graph-builder agents.** Implements the graph wiring that [Briefing 4](./pdf-graph-builder-briefing-4.md) defers: selector rows → bundles → nested tables.

**Prerequisites:** [Briefing 3](./pdf-graph-builder-briefing-3.md) flat `materialize_lookup_table()` must already work. Phase 1 (`DRTable`) may be done first; this briefing is independent code you add on top.

**Contract sources (synced from AI-DM-Assistant):**

| File | Role |
|---|---|
| `games/mork-borg/ingest-manifest.json` | `parent_bundle`, `selects_bundle`, `character_creation` block |
| `games/mork-borg/tables/optional-classes.json` | Six bundle definitions (`contains_tables`, `uses_tables`) |

---

## Problem

Today `table_materialization.py` only runs the **flat** pipeline:

```
LookupTable :IngestNode → HAS_COLUMN → HAS_ENTRY
```

Optional Classes (p.46–57) needs **additional edges** after flat tables exist:

```
OptionalClassesTable row ──SELECTS──► FangedDeserter :OptionalClass :IngestNode
FangedDeserter ──APPLIES_DURING──► CharacterCreation :SeedNode
FangedDeserter ──CONTAINS──► EarliestMemoriesTable :IngestNode
GutterbornScum ──USES──► WeaponTable :IngestNode   (when that table exists)
```

Nested tables (`EarliestMemoriesTable`, `EldritchOriginsTable`, …) are **still flat tables** — same `materialize_lookup_table()` handler. Only **placement in the graph** differs (`CONTAINS` from bundle, not sibling-of-selector on the page).

---

## Design: two-pass pipeline

| Pass | Owner | Output |
|---|---|---|
| **1. Flat materialize** | Existing `materialize_lookup_table()` | `:IngestNode` tables + columns + rows |
| **2. Bundle wire** | **New** `bundle_materialization.py` | Bundles + `SELECTS` / `CONTAINS` / `APPLIES_DURING` / `USES` |

Call pass 2 **after** pass 1 in `enrich_pdf_tables.py` (and any full-book ingest completion hook).

```python
# enrich_pdf_tables.py (after existing calls)
from src.bundle_materialization import materialize_character_creation_bundles

flat_stats = materialize_lookup_tables_from_chunks(...)
bundle_stats = materialize_character_creation_bundles(
    graph, file_name, scaffold_map, game="mork-borg"
)
```

Pass 2 must be **idempotent** (MERGE edges, stable bundle node ids).

---

## New module: `src/bundle_materialization.py`

### Entry point

```python
def materialize_character_creation_bundles(
    graph,
    file_name: str,
    scaffold_map: dict,
    *,
    game: str = "mork-borg",
) -> dict[str, int]:
    """
    Wire character-creation bundles per manifest character_creation block.
    Returns stats: bundles_created, selects_linked, contains_linked, uses_linked, warnings.
    """
```

Load:

1. `manifest = load_ingest_manifest(game)`
2. `cc = manifest.get("character_creation")` — skip if absent
3. `bundles_path` → resolve `games/mork-borg/tables/optional-classes.json` (manifest `bundle_schema` path is AI-DM-Assistant-relative; map to local `games/mork-borg/tables/optional-classes.json`)

### Step A — Ensure selector table linked to CharacterCreation

Manifest says `CharacterCreation -[:USES]-> OptionalClassesTable`.

If `materialize_lookup_table` already handles `used_by` on the selector spec, this may exist. **Verify**; if missing, MERGE:

```cypher
MATCH (cc:CharacterCreation:SeedNode)
MATCH (t:OptionalClassesTable:IngestNode {id: 'OptionalClassesTable'})
MERGE (cc)-[:USES]->(t)
```

### Step B — Create bundle nodes (one per `optional-classes.json` → `bundles[]`)

For each bundle `b` with `id` e.g. `FangedDeserter`:

```cypher
MERGE (bundle:IngestNode:OptionalClass:FangedDeserter {id: $bundle_id})
SET bundle.name = $display_name,
    bundle.tier = 5,
    bundle.source = $file_name,
    bundle.pages = $pages
WITH bundle
MATCH (seed:OptionalClass:SeedNode)
MERGE (bundle)-[:INSTANCE_OF]->(seed)
```

- Dynamic label: use bundle `id` as an extra label (same pattern as `DRTable`).
- `bundle_instance_of` from manifest: `OptionalClass`.
- Do **not** emit `SPECIALIZES` from ingest.

### Step C — APPLIES_DURING CharacterCreation

For every bundle:

```cypher
MATCH (bundle:IngestNode {id: $bundle_id})
MATCH (cc:CharacterCreation:SeedNode)
MERGE (bundle)-[:APPLIES_DURING]->(cc)
```

### Step D — SELECTS from selector rows

Manifest `OptionalClassesTable.acceptance_rows[]` has `selects_bundle` per row.

1. Materialize selector table first (pass 1).
2. For each acceptance row with `selects_bundle`:
   - Find row node: `OptionalClassesTable:row:{index_key}` where `cells` matches (e.g. `d6: 1`).
   - MERGE `(row)-[:SELECTS]->(bundle)`.

```cypher
MATCH (t:OptionalClassesTable:IngestNode {id: 'OptionalClassesTable'})
MATCH (row:TableEntry:IngestNode)
WHERE row.id STARTS WITH 'OptionalClassesTable:row:' AND row.cells CONTAINS $d6_json
MATCH (bundle:IngestNode {id: $bundle_id})
MERGE (row)-[:SELECTS]->(bundle)
```

**Prefer** matching by parsed `cells` map equality, not display text. Fallback: join `optional-classes.json` `selector_cells` to row `cells`.

### Step E — CONTAINS nested tables (`parent_bundle`)

For each manifest `lookup_tables[]` entry with `parent_bundle`:

```cypher
MATCH (bundle:IngestNode {id: $parent_bundle})
MATCH (table:IngestNode {id: $table_name})   // e.g. EarliestMemoriesTable
MERGE (bundle)-[:CONTAINS]->(table)
```

Run after the nested table is materialized in pass 1. If table not found, log warning and continue (partial ingest).

**Also** wire from `optional-classes.json` `contains_tables` — should agree with manifest `parent_bundle`. Prefer manifest as source of truth; use JSON as validation / display names.

### Step F — USES external tables (`uses_tables`)

From manifest per-table `uses_tables` or bundle JSON `uses_tables` (e.g. `WeaponTable`, `ArmorTable`):

```cypher
MATCH (bundle:IngestNode {id: $bundle_id})
MATCH (ext:IngestNode {id: $external_table_name})
MERGE (bundle)-[:USES]->(ext)
```

If external table not materialized yet, **log warning, do not fail**. Weapon/armor tables may come from a later ingest pass.

### Step G — DOCUMENTED_BY (optional in v1)

Manifest lists `bundle -[:DOCUMENTED_BY]-> RulePassage`. Defer to LLM extract pass or a follow-up that links class prose chunks on bundle pages. **Not blocking** for table wiring tests.

---

## Allowed ingest relationship types (add to allowlist)

Ensure extract / materialization allowlists include:

```
SELECTS, CONTAINS, APPLIES_DURING
```

Still **no** `SPECIALIZES` from ingest.

---

## Integration checklist

| Task | File |
|---|---|
| Add `bundle_materialization.py` | `backend/src/` |
| Call after flat materialize | `backend/enrich_pdf_tables.py` |
| Unit tests: bundle node merge, SELECTS by cells, CONTAINS by parent_bundle | `backend/test_bundle_materialization.py` |
| Optional: CLI probe | `backend/materialize_bundles.py` one-off |

### Suggested tests

1. **Mock graph** or test DB: flat `OptionalClassesTable` with 1 row + `FangedDeserter` bundle → `SELECTS` exists.
2. Flat `EarliestMemoriesTable` + `parent_bundle: FangedDeserter` → after pass 2, `CONTAINS` exists.
3. Idempotent re-run does not duplicate edges.
4. Missing nested table → warning, no exception.

---

## Verification (after full p.46–57 ingest + both passes)

```cypher
// Selector
MATCH (cc:CharacterCreation:SeedNode)-[:USES]->(sel:OptionalClassesTable)
RETURN cc.name, sel.name

// Six bundles
MATCH (b:OptionalClass:IngestNode)
RETURN b.id, b.name ORDER BY b.id

// SELECTS
MATCH (row:TableEntry)-[:SELECTS]->(b:OptionalClass:IngestNode)
RETURN row.id, b.id ORDER BY row.id

// CONTAINS per bundle
MATCH (b:OptionalClass:IngestNode)-[:CONTAINS]->(t:IngestNode)
RETURN b.id, collect(t.name) AS nested ORDER BY b.id

// Setup-phase tag
MATCH (b:IngestNode)-[:APPLIES_DURING]->(:CharacterCreation)
RETURN b.id
```

**Expected bundle ids:** `FangedDeserter`, `GutterbornScum`, `EsotericHermit`, `WretchedRoyalty`, `HereticalPriest`, `OccultHerbmaster`.

**Expected CONTAINS counts:**

| Bundle | Nested tables |
|---|---|
| FangedDeserter | EarliestMemoriesTable, FangedDeserterEquipmentTable |
| GutterbornScum | BadBirthTable |
| EsotericHermit | EldritchOriginsTable |
| WretchedRoyalty | ThingsGoingWrongTable, WretchedRoyaltyEquipmentTable |
| HereticalPriest | HereticalPriestOriginsTable |
| OccultHerbmaster | RaisedInTable, HerbmasterDecoctionsTable |

---

## Flat tables — do not duplicate handlers

`EldritchOriginsTable`, `EarliestMemoriesTable`, etc. use the **same** `materialize_lookup_table()` as `DRTable`. Column roles (`index`, `result`) + per-table `pdf_extract.index` only. No `d6_result` / `d8_result` template types.

---

## Phase gating

| When | Action |
|---|---|
| Phase 1 spike in progress | Implement this module; do not block Phase 1 on it |
| Phase 1 done | Run full-book or p.46–57 ingest + both passes to validate |
| `OptionalClassesTable` `pdf_extract.status` is `todo` | Flip to `verified` once header parse works (see manifest) |

---

## What AI-DM-Assistant already did (do not redo)

- Tier 0–4 ontology in Neo4j (`SelectableBundle`, `OptionalClass`, …) — bootstrap owner is AI-DM-Assistant
- `ingest-manifest.json` contracts and `optional-classes.json`
- Flat table `pdf_extract` signatures for nested tables

This briefing is **pdf-graph-builder code only**.

---

## One-line summary

> Add `bundle_materialization.py`: after flat tables materialize, create `OptionalClass` bundle nodes and wire `SELECTS` (selector rows), `CONTAINS` (`parent_bundle`), `APPLIES_DURING` (`CharacterCreation`), and optional `USES` (external tables).
