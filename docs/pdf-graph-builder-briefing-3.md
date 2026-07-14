# Briefing 3: Lookup Tables — Columns, Rows, and Tier-5 Ingest

**Context:** This follows [Briefing 1](./pdf-graph-builder-briefing.md) and [Briefing 2](./pdf-graph-builder-briefing-2.md). AI-DM-Assistant has re-bootstrapped `morkborg` with an extended lookup-table ontology. The scaffold now has abstract table concepts; **concrete table content is Tier-5 ingest work in pdf-graph-builder**.

**Scaffold state:** ~52 `:SeedNode` nodes, ~63 relationships. No `DRTable`, no `DR6`–`DR18` rows in the bootstrap.

---

## Three different "table" concepts — do not conflate

| Layer | What | Owner | Purpose |
|---|---|---|---|
| **A. Mechanism ontology** | `LookupTable`, `TableColumn`, `TableEntry` | Bootstrap (Tier 1 seeds) | Vocabulary — "tables exist as a resolution mechanism" |
| **B. Concrete table instances** | `DRTable` + columns + rows | **Tier-5 ingest** (`:IngestNode`) | Queryable mechanism facts the runtime assistant uses |
| **C. Parsed table on chunk** | `Chunk.table_json` | pdf-graph-builder chunking | Source evidence / LLM context — **not** a substitute for B |

pdf-graph-builder already does **C** (`table_json` with `columns` + `rows` on `:Chunk`). This briefing is about adding **B** — materialising mechanism nodes from parsed tables during ingest.

---

## What the scaffold already has (do not re-create)

From bootstrap:

```
(:LookupTable:SeedNode)           // abstract mechanism family
(:TableColumn:SeedNode)           // abstract column concept
(:TableEntry:SeedNode)            // abstract row concept
(:AbilityTest:SeedNode)-[:USES]->(:LookupTable:SeedNode)   // Tier 4 delta
(:DR:SeedNode)-[:SPECIALIZES]->(:DifficultyRating:SeedNode)
```

**Missing from scaffold (ingest must create):**

- Concrete `DRTable` instance
- Column definitions for that table
- Row entries with cell values
- Links: `DRTable INSTANCE_OF LookupTable`, `AbilityTest USES DRTable`, `DRTable APPLIES_TO DR`

Reference contract: `corpus/games/mork-borg/deltas.json` → `ingest_expectations.lookup_tables[0]`

Ontology source: `corpus/seeds/families/lookup-tables.json` (v0.2 — `TableColumn`, `HAS_COLUMN`, `cells` on rows)

---

## Target graph shape for Mörk Borg DR table (p.28)

When ingest finds the DR reference table, create:

```cypher
// 1. Table instance
(:DRTable:IngestNode {
  name: "DRTable",
  tier: 5,
  source: "<doc/chunk ref>",
  page: 28
})-[:INSTANCE_OF]->(:LookupTable:SeedNode)

// 2. Column definitions (one node per column)
(:DRTable)-[:HAS_COLUMN]->(:DRTable:DR:TableColumn:IngestNode {
  name: "DRTable:DR",
  column_name: "DR",
  role: "index",      // lookup key
  position: 0,
  tier: 5
})

(:DRTable)-[:HAS_COLUMN]->(:DRTable:label:TableColumn:IngestNode {
  name: "DRTable:label",
  column_name: "label",
  role: "result",     // outcome text
  position: 1,
  tier: 5
})

// 3. Rows — values in a cells map, NOT flat index/result props only
(:DRTable)-[:HAS_ENTRY]->(:DRTable:row:12:TableEntry:IngestNode {
  name: "DRTable:row:12",
  cells: {DR: 12, label: "normal"},
  tier: 5
})
// ... repeat for DR 6, 8, 10, 14, 16, 18

// 4. Semantic links
(:DRTable)-[:APPLIES_TO]->(:DR:SeedNode)
(:AbilityTest:SeedNode)-[:USES]->(:DRTable:IngestNode)
// and/or CONFIRMS_SEED on the existing AbilityTest-[:USES]->LookupTable edge
```

**Expected rows** (from `ingest_expectations`):

| DR | label |
|---|---|
| 6 | so simple people laugh at you for failing |
| 8 | routine |
| 10 | pretty simple |
| 12 | normal |
| 14 | difficult |
| 16 | really hard |
| 18 | should not be possible |

Use exact rulebook text for labels; the table above is the acceptance test.

---

## Column roles (from Tier 1 seed)

| Role | Meaning | Example |
|---|---|---|
| `index` | Roll / lookup key | DR value, d10 result |
| `result` | Outcome text | "normal", treasure description |
| `weight` | Probability | % or weight column |
| `data` | Other structured value | modifier, damage die |

**Node naming convention** (match bootstrap):

- Column: `{tableName}:{columnName}` → `DRTable:DR`
- Row: `{tableName}:row:{index}` → `DRTable:row:12` (use index-column value)

---

## Implementation path in pdf-graph-builder

**Suggested flow:**

1. Chunking already produces `Chunk.table_json` like:
   ```json
   {"title": "...", "columns": ["DR", "label"], "rows": [[6, "so simple..."], ...]}
   ```
2. **New ingest step** (table extraction): when a chunk has `block_type: table` and content matches a known scaffold expectation (or heuristic: two columns, first is numeric DR), materialise mechanism nodes (layer B above).
3. Link table instance to source chunk via `DOCUMENTED_BY` or similar evidence edge.
4. Emit `CONFIRMS_SEED` for `AbilityTest USES LookupTable` once `DRTable` is linked.

**Do not:**

- Create flat `DR6`, `DR8`, … as `:DifficultyRating` nodes (old workaround — removed)
- Put `DRTable` or rows in `deltas.json` / bootstrap
- Write `SPECIALIZES` relationships during ingest
- Treat `Chunk.table_json` alone as sufficient for runtime table lookup — the assistant queries mechanism nodes

---

## Relationship ownership reminder

| Rel | Who creates it for tables |
|---|---|
| `INSTANCE_OF` | Ingest — `DRTable` → `LookupTable` |
| `HAS_COLUMN` | Ingest — table → column defs |
| `HAS_ENTRY` | Ingest — table → rows |
| `APPLIES_TO` | Ingest — `DRTable` → `DR` |
| `USES` | Ingest — `AbilityTest` → `DRTable` (concrete link) |
| `CONFIRMS_SEED` | Ingest — evidence agrees with scaffold claim |
| `DOCUMENTED_BY` | Ingest — passage/chunk supports a node |

---

## Verification queries after ingest

```cypher
// DR table structure
MATCH (t:DRTable:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(col:TableColumn)
OPTIONAL MATCH (t)-[:HAS_ENTRY]->(row:TableEntry)
RETURN t.name, collect(col.column_name) AS columns, count(row) AS rows

// Row content
MATCH (:DRTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN r.name, r.cells ORDER BY r.cells.DR

// Procedure link
MATCH (at:AbilityTest)-[:USES]->(t)
RETURN at.name, labels(t), t.name
```

Expected: 1 table, 2 columns, 7 rows, `AbilityTest USES DRTable`.

---

## Priority for Mörk Borg POC

**Phase 1:** DR reference table only (p.28) — proves the column+row+cells model.

**Phase 2:** Random tables (character gen, encounters) — same pattern, different column roles (`index` from die roll, `result` from outcome column).

---

## Files to read in AI-DM-Assistant repo

| File | What |
|---|---|
| `corpus/seeds/families/lookup-tables.json` | Tier 1 ontology (`TableColumn`, `HAS_COLUMN`, `cells`) |
| `corpus/games/mork-borg/deltas.json` | `ingest_expectations` contract for `DRTable` |
| `DESIGN.md` §6.2.2 | Full model and Cypher examples |
| `docs/pdf-graph-builder-briefing-2.md` | Prior ingest bugs (case norm, instance routing, SeedNode leakage) still apply |

---

## One-line summary

> When you parse a rulebook table, don't stop at `Chunk.table_json` — also create `:IngestNode` `LookupTable` instances with `:HAS_COLUMN` column defs and `:HAS_ENTRY` rows using a `cells` map keyed by column name; for Mörk Borg start with `DRTable` on p.28 per `deltas.json` `ingest_expectations`.
