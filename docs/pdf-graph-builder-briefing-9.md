# Briefing 9: Fix fiction `INSTANCE_OF` fan-out

**For pdf-graph-builder agents.** Hotfix after [briefing-8](./pdf-graph-builder-briefing-8.md). Typed fiction materialization created **too many** `INSTANCE_OF` edges: each fiction `IngestNode` was linked to **nearly every** `:SeedNode`, not to the single seed required by `entry_kind_to_seed`.

**Prerequisites:**

1. Briefings 7–8 already implemented (catalog + fiction materializer exist).
2. Synced contracts unchanged: `ingest-manifest.json` ≥ **0.3.5** (`entry_kind_to_seed`), `passage-sections.json` ≥ **0.3.0**.
3. Scaffold still has one SeedNode per type (`Place`, `Faction`, …) — do **not** bootstrap-change for this fix.

**Design / contract reference:** [briefing-8 § Contract](./pdf-graph-builder-briefing-8.md#contract-entry_kind--seed-label) · `games/mork-borg/ingest-manifest.json` → `rulebook_index.materialization.entry_kind_to_seed`

---

## Observed failure (runtime symptom)

AI-DM-Assistant chat for “Galgenbeck” returned correct prose (catalog + chunk) but **Sources** listed Galgenbeck once per ludeme seed (`Player`, `GameMaster`, `Session`, `Place`, `Monster`, …).

Neo4j confirmation (`:use morkborg`):

```cypher
MATCH (e:IndexEntry {title:'Galgenbeck'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
RETURN x.name, labels(s), count(*)
ORDER BY labels(s);
```

**Actual:** dozens of rows (one per SeedNode).  
**Expected:** exactly one row — `["SeedNode", "Place"]` (order of labels irrelevant).

Handoff-4 acceptance only checked “has a Place link,” not “has **only** the mapped seed.” That false-greened briefing-8.

---

## Root cause (likely)

Fiction materializer resolves the target seed incorrectly, e.g.:

- `MATCH (s:SeedNode)` then `MERGE (entity)-[:INSTANCE_OF]->(s)` for **all** seeds, or
- label filter omitted when looking up seed by `entry_kind_to_seed`, or
- MERGE pattern that attaches to every node matching a broad predicate.

**Correct pattern** (one seed per entity):

```cypher
// seedLabel = entry_kind_to_seed[e.entry_kind]  e.g. "Place"
MATCH (seed:SeedNode)
WHERE seedLabel IN labels(seed)
WITH seed LIMIT 1   // abort if 0 or >1 distinct seeds for that label
MATCH (e:IndexEntry)-[:DENOTES]->(entity)
WHERE e.id = $entryId   // or MERGE entity first
MERGE (entity)-[:INSTANCE_OF]->(seed)
```

Or equivalent in Python: look up **one** seed node by label string from the map, then a single MERGE.

| `entry_kind` | Sole allowed `INSTANCE_OF` target |
|---|---|
| `place` | `:Place:SeedNode` |
| `supporting_character` | `:SupportingCharacter:SeedNode` |
| `faction` | `:Faction:SeedNode` |
| `world_lore` | `:WorldLore:SeedNode` |
| `creature` | `:Creature:SeedNode` |

RULES kinds stay catalog-only (no fiction instance) — unchanged from briefing-8.

---

## Required fix

1. **Locate** fiction materializer (`fiction_instance_materialization.py`, `index_materialization.py`, or whatever briefing-8 added).
2. **Stop** linking to all SeedNodes. Resolve seed **only** via `entry_kind_to_seed[entry_kind]`.
3. **Abort with error** if that seed label is missing or ambiguous after bootstrap (do not silently skip or fan-out).
4. **Repair existing graph** (pick one):

   **A. Re-materialize (preferred if idempotent):**  
   Delete bad fiction `INSTANCE_OF` edges (or delete fiction IngestNodes + re-run materializer), then re-run with the fixed code. Keep `IndexEntry` / `RulebookIndex` unless your pipeline rebuilds them too.

   **B. Surgical Cypher repair** (if you must not re-ingest chunks):

   ```cypher
   // Example for places — generalize per entry_kind
   MATCH (e:IndexEntry {entry_kind:'place'})-[:DENOTES]->(x:IngestNode)
   MATCH (x)-[r:INSTANCE_OF]->(s:SeedNode)
   WHERE NOT s:Place
   DELETE r;

   // Ensure the correct edge exists
   MATCH (e:IndexEntry {entry_kind:'place'})-[:DENOTES]->(x:IngestNode)
   MATCH (place:Place:SeedNode)
   MERGE (x)-[:INSTANCE_OF]->(place);
   ```

   Repeat for `supporting_character` → SupportingCharacter, `faction` → Faction, `world_lore` → WorldLore, `creature` → Creature.

5. **Do not** add `:SeedNode` or type labels onto the fiction instance as a substitute for a correct single `INSTANCE_OF`.

---

## Acceptance criteria (strict — all must pass)

```cypher
// 1) No fiction entity may INSTANCE_OF more than one SeedNode
MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
WHERE e.entry_kind IN ['place','supporting_character','faction','world_lore','creature']
WITH x, e.entry_kind AS kind, count(s) AS n
WHERE n <> 1
RETURN x.name, kind, n
ORDER BY n DESC;
// expect 0 rows

// 2) Spot check Galgenbeck
MATCH (e:IndexEntry {title:'Galgenbeck'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
RETURN labels(s);
// expect exactly one row containing Place (+ SeedNode)

// 3) Kind matches mapped seed (counts)
MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
WHERE e.entry_kind = 'place' AND s:Place
RETURN count(DISTINCT x) AS places;
// expect same count as place IndexEntries that were materialized (≈13)

MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
WHERE e.entry_kind = 'creature' AND s:Creature
RETURN count(DISTINCT x) AS creatures;
// expect ≈12

// 4) No cross-type INSTANCE_OF for fiction
MATCH (e:IndexEntry {entry_kind:'place'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
WHERE NOT s:Place
RETURN count(*);  // expect 0

MATCH (e:IndexEntry {entry_kind:'creature'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(s:SeedNode)
WHERE NOT s:Creature
RETURN count(*);  // expect 0
```

**Pass:** queries 1 and 4 return empty / zero; Galgenbeck → Place only; place/creature counts stable vs handoff-4.

**Fail:** do not mark briefing-8/9 done; fix materializer and repair again.

---

## Out of scope

- AI-DM-Assistant retrieval workarounds (optional mask only; not a substitute for this fix)
- New ontology / seed labels
- RULES → mechanism `MAPS_TO_SEED`
- Section chunking expansion (`section_phase`)

---

## Operator checklist (AI-DM-Assistant side)

- [ ] Sync this briefing: `.\scripts\sync-outbox-briefings.ps1`
- [ ] Paste into pgb session
- [ ] After pgb green: re-smoke Galgenbeck Sources in ADA chat (expect one fiction citation: Place)
- [ ] Copy pgb handoff into `docs/inbox/`

---

## Checklist for pgb agent

- [ ] Find fan-out in fiction `INSTANCE_OF` creation
- [ ] Resolve seed solely from `entry_kind_to_seed`
- [ ] Repair existing `morkborg` edges (re-materialize or surgical DELETE + MERGE)
- [ ] Acceptance Cypher **1–4** all green
- [ ] Report root cause (file + bad pattern) + before/after counts to AI-DM-Assistant inbox
