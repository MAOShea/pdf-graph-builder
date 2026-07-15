# Briefing 4: Operational handoff — Phase 1 now, Optional Classes later

**For pdf-graph-builder agents — read this file first.** No extra context from the operator is required.

**Prerequisites:** [Briefing 3](./pdf-graph-builder-briefing-3.md) (flat lookup table materialization). Briefings 1–2 for general ingest conventions.

**Synced artifacts (should already be in this repo):**

| Path | Version / note |
|---|---|
| `games/mork-borg/ingest-manifest.json` | v0.3.1 — `DRTable` `pdf_extract` + Phase 2 table contracts |
| `games/mork-borg/tables/optional-classes.json` | Bundle map (Phase 2 only) |
| `mork-borg-corpse-plunder-d66.json` | Hand-authored (Phase 2 only) |

If missing, ask the operator to run `.\scripts\sync-ingest-manifest.ps1` and `.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant.

---

## Current scaffold state (2026-07-15)

AI-DM-Assistant has **reset and re-bootstrapped** `morkborg`. Do **not** re-bootstrap from pdf-graph-builder.

| Check | Expected |
|---|---|
| Database | `morkborg` |
| `:SeedNode` count | **54** nodes, **68** relationships |
| Tier-5 ingest | **None** — wiped with reset; all prior chunks / `:IngestNode` data is gone |
| Ontology | `lookup-tables.json` v0.3 (`SelectableBundle`, `SELECTS`, `CONTAINS`, `APPLIES_DURING`); `OptionalClass` in Tier 4 seeds |

**Verify before ingest:**

```cypher
:use morkborg
MATCH (n:SeedNode) RETURN count(n) AS seed_nodes  // 54
MATCH (n:IngestNode) RETURN count(n) AS ingest_nodes  // 0
```

---

## Phase 1 — do now (ability test spike)

**Goal:** One cited answer to *"I rolled 12 on Agility — do I pass?"* requires ability-test `RulePassage` nodes **and** a materialized `DRTable`.

### Step 1 — Connect and confirm scaffold

- Neo4j database: `morkborg`
- Confirm 54 `:SeedNode`s (query above)

### Step 2 — Upload and extract (p.27–31)

Upload the Mörk Borg rulebook PDF (or excerpt covering Tests / Abilities / DR).

**Allowed node labels:**

```
AbilityTest, AbilityScore, Agility, Strength, Presence, Toughness, D20Roll, DifficultyRating, Modifier, Test, Randomizer, ResolutionProcedure, Outcome, RulePassage, PlayerCharacter
```

**Allowed relationship types:**

```
SPECIALIZES, USES, APPLIES_TO, PART_OF, MODIFIES, DOCUMENTED_BY, CONFIRMS_SEED, TRIGGERS, RESOLVES, PRODUCES
```

**Additional instructions:**

```
Extract RulePassage nodes with short quoted excerpts and page references.
Link passages to existing schema nodes via DOCUMENTED_BY.
Do not invent new procedure types beyond the allowed labels.
Flag ability tests as AbilityTest linked to the relevant AbilityScore.
```

### Step 3 — Materialize DRTable

After PDF chunks exist for p.28:

```bash
python backend/enrich_pdf_tables.py
```

Contract: `games/mork-borg/ingest-manifest.json` → `lookup_tables[DRTable]`. Uses existing `materialize_lookup_table()` — one flat handler, role-based columns (`DR` index + `label` result). See Briefing 3.

### Step 4 — Verify Phase 1

```cypher
// DR table
MATCH (t:DRTable:IngestNode)-[:HAS_ENTRY]->(r:TableEntry)
RETURN count(r) AS rows  // expect 7

MATCH (t:DRTable)-[:INSTANCE_OF]->(:LookupTable:SeedNode)
RETURN t.name

MATCH (t:DRTable)-[:APPLIES_TO]->(:DR:SeedNode)
RETURN t.name

MATCH (at:AbilityTest)-[:USES]->(t:DRTable)
RETURN at.name, t.name

// Evidence
MATCH (at:AbilityTest)-[:DOCUMENTED_BY|*1..2]-(rp:RulePassage)
RETURN at.name, rp LIMIT 5
```

### Phase 1 success criteria

- [ ] `AbilityTest` has `DOCUMENTED_BY` → `RulePassage`
- [ ] `DRTable`: 2 columns, 7 rows, `INSTANCE_OF LookupTable`
- [ ] `AbilityTest -[:USES]-> DRTable`, `DRTable -[:APPLIES_TO]-> DR`
- [ ] `chat_bot` spike with citation for Agility test / DR 12

### Phase 1 — do not

- Do **not** implement bundle materialization (`SELECTS`, `CONTAINS`, `parent_bundle`) yet
- Do **not** materialize Optional Classes or other Phase 2 tables unless operator explicitly expands scope
- Do **not** re-bootstrap `morkborg` from this repo — scaffold owner is AI-DM-Assistant

---

## Phase 2 — deferred (Optional Classes, p.46–57)

Implement **after** Phase 1 spike passes. **Implementation spec:** [Briefing 5](./pdf-graph-builder-briefing-5.md) — add `bundle_materialization.py` in pdf-graph-builder.

Ontology and manifest are ready; ingest code for bundles is not required for Phase 1.

### Problem

Optional Classes is **not** a flat lookup table:

```
CharacterCreation (setup phase, not turn play)
  └── OptionalClassesTable (d6 selector)
        └── row N SELECTS OptionalClass bundle
              ├── prose + mechanics (RulePassage)
              ├── CONTAINS nested LookupTable(s)
              └── USES external LookupTable(s) (weapon, armor, …)
```

### Scaffold already in Neo4j (from bootstrap)

| Concept | Source |
|---|---|
| `SelectableBundle`, `SELECTS`, `CONTAINS`, `APPLIES_DURING` | Tier 1 `lookup-tables.json` v0.3 |
| `OptionalClass SPECIALIZES SelectableBundle` | Tier 4 `deltas.json` |
| `CharacterCreation USES LookupTable` | Tier 4 `deltas.json` |

### Target graph shape (Phase 2)

```cypher
(:OptionalClassesTable:IngestNode)-[:INSTANCE_OF]->(:LookupTable:SeedNode)
(:CharacterCreation:SeedNode)-[:USES]->(:OptionalClassesTable:IngestNode)
(:OptionalClassesTable)-[:HAS_ENTRY]->(:row:1:TableEntry)-[:SELECTS]->(:FangedDeserter:IngestNode:OptionalClass)
(:FangedDeserter)-[:APPLIES_DURING]->(:CharacterCreation:SeedNode)
(:FangedDeserter)-[:CONTAINS]->(:EarliestMemoriesTable:IngestNode)
```

### Manifest contract (Phase 2)

`ingest-manifest.json`:

| Block | Purpose |
|---|---|
| `lookup_tables[]` with `parent_bundle` | Nested tables belong to a class, not the page |
| `acceptance_rows[].selects_bundle` | Selector row → bundle id |
| `character_creation` | Materialization rules |
| `games/mork-borg/tables/optional-classes.json` | Six bundles |

### Six classes (d6)

| d6 | Bundle id | Nested tables |
|---|---|---|
| 1 | `FangedDeserter` | EarliestMemories, FangedDeserterEquipment |
| 2 | `GutterbornScum` | BadBirth; USES Weapon, Armor |
| 3 | `EsotericHermit` | EldritchOrigins |
| 4 | `WretchedRoyalty` | ThingsGoingWrong, WretchedRoyaltyEquipment |
| 5 | `HereticalPriest` | HereticalPriestOrigins |
| 6 | `OccultHerbmaster` | RaisedIn, HerbmasterDecoctions; USES Weapon, Armor |

### Phase 2 implementation notes

1. Nested tables: use `parent_bundle` from manifest — not page siblings of the selector.
2. Bundle nodes: `:IngestNode` + `OptionalClass`; link `SELECTS` from row entry.
3. `CONTAINS` from bundle to nested tables; `APPLIES_DURING CharacterCreation` on every bundle.
4. Flat nested tables (e.g. EldritchOrigins) use the **same** `materialize_lookup_table()` handler — only graph wiring differs.
5. **No** `SPECIALIZES` from ingest.

### Phase 2 verification

```cypher
MATCH (b:OptionalClass:IngestNode)-[:CONTAINS]->(t:LookupTable)
RETURN b.name, collect(t.name) AS nested ORDER BY b.name
```

---

## Flat tables — one handler (all phases)

Do **not** create per-die handlers (`d6_result`, `d8_result`, …). One materializer; column **roles** (`index`, `result`) and per-table `pdf_extract.index` key enumeration. See [ingest-manifest-sync.md](./ingest-manifest-sync.md).

---

## One-line summary

> **Phase 1:** Ingest p.27–31, materialize `DRTable`, verify ability-test citations. **Phase 2:** Optional-class bundles (`SELECTS` / `CONTAINS`) — deferred until Phase 1 passes.
