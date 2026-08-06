# AI-DM-Assistant Handoff 8: AgonyEndTable + linked-table retrieval (Traps / Agony)

**From:** pdf-graph-builder  
**Date:** 2026-08-06  
**Context:** New label→die chooser table on Bare Bones p.17; chat retrieval gap for structured `HAS_ENTRY` rows.

---

## 1. Contract sync (merge pgb → ADA SoT)

ADA `corpus/games/mork-borg/` is source of truth for Tier-5 contracts. pdf-graph-builder is ahead on:

| Artifact | pgb path | Action |
|---|---|---|
| `AgonyEndTable` | `games/mork-borg/ingest-manifest.json` | Merge into ADA `ingest-manifest.json` (do **not** blind-overwrite pgb with the shorter ADA copy) |
| Hand-authored rows | `games/mork-borg/hand-authored-overrides/agony-end.json` | Copy into ADA corpus (e.g. `corpus/games/mork-borg/tables/agony-end.json`) and point `hand_authored.file` at the ADA-relative path used by sync |
| `text_filters` | `games/mork-borg/passage-sections.json` v0.5.4 | Merge top-level `text_filters` (Bare Bones running footer / edge page numbers) into ADA `passage-sections.json` |

After merge, sync scripts ADA → pgb as usual so both repos stay aligned.

---

## 2. Runtime table shape — no new type

`AgonyEndTable` uses the **same** graph shape as dice lookups (`TrapsTable`, `DRTable`, …):

```text
(:AgonyEndTable:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
(:AgonyEndTable)-[:HAS_COLUMN]->(:TableColumn {role:"index"|"result"})
(:AgonyEndTable)-[:HAS_ENTRY]->(:TableEntry {cells: {...}})
```

| | Dice lookup (e.g. Traps) | Agony chooser |
|---|---|---|
| Index column | numeric face (`d12`) | duration label string |
| Result column | outcome text | die to use (`d100` … `d2`) |

Chat does **not** need a new node label or parser for “chooser vs roll table.” Column names / `role` + `cells` carry the flavour. No ADA adapter change is required merely to *store* or *render* these rows once they are in CONTEXT.

---

## 3. Requirement (not optional): linked-table retrieval for Traps and Agony

**Status today:** structured rows enter CONTEXT only via

```cypher
MATCH (n)-[:USES]->(t)-[:HAS_ENTRY]->(r:TableEntry)
```

(`ContextRetriever._add_linked_tables` in ADA `backend/app/retrieval.py`).

`DRTable` works because ingest wires `AbilityTest -[:USES]-> DRTable` from manifest `used_by`.

**`TrapsTable` and `AgonyEndTable` have no `used_by` and therefore no `USES` edges.** Catalog / passage text may mention them; **`HAS_ENTRY` rows do not systematically land in CONTEXT.** That breaks the product path for the prompts below. Fixing this is a **hard requirement**, not a nice-to-have.

### ADA must implement

**R1 — Seed owners (Tier 4 / deltas)**  
Declare which scaffold seeds own each table (create or un-defer labels as needed):

| Table | Proposed `used_by` seed(s) | Rationale |
|---|---|---|
| `TrapsTable` | e.g. `Trap` / dungeon-prep seed (ADA chooses canonical label; add to deltas if missing) | Random trap resolution |
| `AgonyEndTable` | `Misery` (and optionally `WorldLore` if Calendar framing is separate) | Campaign-length → Misery die |

Also add Tier-4 `USES` edges seed→`LookupTable` where that is how other tables are scaffolded (mirror `AbilityTest USES LookupTable` / `CharacterCreation USES LookupTable`).

**R2 — Manifest `used_by` (Tier 5 contract)**  
On ADA SoT `ingest-manifest.json`:

- `TrapsTable.used_by`: seed label(s) from R1  
- `AgonyEndTable.used_by`: seed label(s) from R1  

After sync + `.\ingest-tables.ps1` (or full extract), Neo4j must show:

```cypher
MATCH (s)-[:USES]->(t:TrapsTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN s, count(r)
// expect rows > 0

MATCH (s)-[:USES]->(t:AgonyEndTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN s, count(r)
// expect 5 rows
```

**R3 — Retrieval hints**  
Extend `systems/mork-borg/retrieval_hints.py` so natural language reaches those seeds (and thus linked tables), e.g.:

- traps / trap / d12 traps / devilry → seed(s) that `USES` `TrapsTable`
- agony / calendar / nechrubel / campaign length / when will all this agony / misery die → seed(s) that `USES` `AgonyEndTable`

(Existing `"misery"` → `Misery` is necessary but not sufficient until R1–R2 wire `Misery USES AgonyEndTable`.)

### Acceptance prompts (smoke)

| # | Human prompt | CONTEXT must include | Reply behaviour |
|---|---|---|---|
| A | *“Corridor trap — I rolled a 7 on the d12 traps table. What happens?”* | `TrapsTable` `HAS_ENTRY` for `d12: 7` (structured rows, not only prose) | Index = roll → trap text |
| B | *“Campaign length: we want about a month of play. Which Misery die does ‘When will all this agony end?’ say we use?”* | `AgonyEndTable` row `duration: A cruel month` → `die: d6` | Index = chosen duration → die |

**Pass criteria:** both prompts show the table in the UI context inspector under linked lookup tables (or equivalent), with row cells present; answers cite that table evidence.

### Ownership split

| Work | Owner |
|---|---|
| Seed labels + deltas `USES` | AI-DM-Assistant |
| Manifest `used_by` + hand-authored path sync | AI-DM-Assistant (SoT) → sync to pgb |
| Materialize `USES` on ingest from `used_by` | pdf-graph-builder (already implemented) |
| `retrieval_hints` + chat smoke | AI-DM-Assistant |

---

## pgb already delivered (for sync)

- `AgonyEndTable` + `hand-authored-overrides/agony-end.json` (5 rows)  
- `passage-sections.json` `text_filters` for Bare Bones footer  
- pdf-as-md shows Agony via `resolve_tables_in_span` hand-authored substitute  

Neo4j materialize of `AgonyEndTable` needs a running DB + `.\ingest-tables.ps1 -Tables AgonyEndTable` after contract sync.
