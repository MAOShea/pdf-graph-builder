# Briefing 12: Stop scaffold evidence / USES fan-out onto broad seeds

**For pdf-graph-builder agents.** After a full scaffold-diff ingest (post briefings 10–11 / handoff-8 contracts), ADA chat smoke (**2026-08-07**) shows **entity-scoped Goblin prose is clean**, but runtime CONTEXT is polluted because **broad SeedNodes** (`Creature`, `Place`, …) were wired to unrelated page `Chunk`s and lookup tables.

**This is an ingest / edge-routing bug in pdf-graph-builder — not an ADA prompt or synonym-list fix.**

**Prerequisites:** Fresh full ingest on `morkborg` with entity passages + tables materialization. ADA retrieval follows the graph as designed (`USES` + `DOCUMENTED_BY`/`CONFIRMS_SEED` from matched seeds).

---

## Symptoms (ADA smoke)

### Q — “Where is Galgenbeck?”

- **Good:** Catalog `THE_WORLD/place`, typed `Place`, p.12 Galgenbeck prose.
- **Bad:** CONTEXT includes **`OptionalClassesTable`** (6 class rows) under “Lookup tables (linked from seeds via USES)”.

### Q — “What is a Goblin in Mörk Borg?”

- **Good:** `MAPS_TO_PASSAGE` entity-passage for Goblin — curse / Quick / DR14; **no** Head 7s / Bent / Scum (briefings 10–11).
- **Bad:** CONTEXT also pulls:
  - Rule passages via seed evidence: **abilities** (p.27), **carrying-capacity** (p.28), **hit-points-and-broken** (p.29)
  - Lookup tables via USES: **`AgonyEndTable`**, **`TrapsTable`**
- LLM then attributes PC ability lists, encumbrance, and hemorrhage to Goblins.

---

## Neo4j evidence (operator-confirmed)

### 1. Wrong `USES` on fiction type seed

```cypher
MATCH (c:Creature:SeedNode)-[:USES]->(t)
RETURN t.name, labels(t)
```

**Actual:**

| t.name | labels |
|---|---|
| TrapsTable | IngestNode, TrapsTable |
| AgonyEndTable | IngestNode, AgonyEndTable |

**Expected:** `Creature` has **no** `USES` to those tables.  
Manifest `used_by` is `TrapsTable` → `Trap`, `AgonyEndTable` → `Misery` only.

Likely same class: `Place` → `OptionalClassesTable` (Galgenbeck smoke). Verify:

```cypher
MATCH (p:Place:SeedNode)-[:USES]->(t)
RETURN t.name, labels(t)
```

### 2. Book-wide evidence dump onto `Creature`

```cypher
MATCH (c:Creature:SeedNode)<-[r:DOCUMENTED_BY|CONFIRMS_SEED]-(p)
RETURN type(r) AS rel,
       labels(p) AS labels,
       coalesce(p.section_id, '') AS section_id,
       coalesce(p.page, p.page_number, p.page_number_start) AS page,
       substring(coalesce(p.text, ''), 0, 60) AS preview
ORDER BY page
LIMIT 40
```

**Actual (sample):** For many pages, **both** `DOCUMENTED_BY` and `CONFIRMS_SEED` from page `Chunk`s — including unrelated content:

| page | preview (truncated) |
|---|---|
| 1 | Bare Bones title page |
| 3 | Occult Treasures |
| 4 | Traps and Devilry |
| 17–18 | Calendar of Nechrubel |
| 21 | Create a Player Character |
| 27 | Abilities |
| 29 | Hit Points |
| 31+ | Crit / Reaction / Powers / … |

**Expected:** Evidence edges to `Creature` only when the chunk/passage **actually documents or confirms** that scaffold concept (e.g. bestiary / creature-test rules — or none until a real confirm). **Not** every page that happens to exist in the PDF.

---

## Root cause (investigate)

Likely one or more of:

1. **`USES` materialization** — any seed with scaffold `(Seed)-[:USES]->(:LookupTable)` receives **all** concrete tables, instead of only manifest `used_by` targets (`Trap`→`TrapsTable`, `Misery`→`AgonyEndTable`, `AbilityTest`→`DRTable`, `CharacterCreation`→`OptionalClassesTable`, …).
2. **`DOCUMENTED_BY` / `CONFIRMS_SEED` routing** — extract/scaffold-diff attaches page `Chunk`s to overly broad labels (`Creature`, `Place`, `Monster`, …) when the text is not about that concept; or attaches the same chunk to every seed in a candidate set.
3. **Dual edges** — many chunks get **both** `DOCUMENTED_BY` and `CONFIRMS_SEED` to the same seed (noise; prefer one semantics per briefing-1/2 model).

Find the code path (table materializer `used_by` wiring; extract confirm/document edges) and fix at source. Surgical DELETE of bad edges is OK for the current DB **if** re-ingest with the fix is also guaranteed.

---

## Required fix

1. **`USES`:** Create `(seed)-[:USES]->(concreteTable)` **only** for seeds listed in that table’s `used_by` (and equivalent character_creation / DRTable rules). Never fan out “all LookupTable instances” to every seed that `USES` the abstract `LookupTable` scaffold node.
2. **Evidence:** Attach `DOCUMENTED_BY` / `CONFIRMS_SEED` only with a **positive match** (section `links_to_seed_labels`, constrained extract hit, operator confirm). Do **not** link arbitrary page chunks to type seeds (`Creature`, `Place`, `Monster`, `Setting`, …).
3. **Idempotent cleanup:** On re-materialize / re-extract, strip prior bad fan-out edges before rewriting (same spirit as briefing-9 `INSTANCE_OF` repair).
4. **Regression queries** (below) must stay green after full ingest.

**Do not** “fix” this by asking ADA to ignore `USES` / seed evidence for fiction questions. That hides the graph bug.

---

## Acceptance criteria

```cypher
// A — Creature must not USES trap/agony/optional-class tables
MATCH (c:Creature:SeedNode)-[:USES]->(t)
WHERE t:TrapsTable OR t:AgonyEndTable OR t:OptionalClassesTable OR t:DRTable
RETURN count(*) AS bad;
// expect 0

// B — Place must not USES character-creation / trap tables
MATCH (p:Place:SeedNode)-[:USES]->(t)
WHERE t:OptionalClassesTable OR t:TrapsTable OR t:AgonyEndTable
RETURN count(*) AS bad;
// expect 0

// C — used_by owners still linked
MATCH (:Trap:SeedNode)-[:USES]->(:TrapsTable)
RETURN count(*) AS traps_ok;   // expect >= 1

MATCH (:Misery:SeedNode)-[:USES]->(:AgonyEndTable)
RETURN count(*) AS agony_ok;   // expect >= 1

// D — Creature evidence is not book-wide
MATCH (c:Creature:SeedNode)<-[:DOCUMENTED_BY|CONFIRMS_SEED]-(p)
WITH count(*) AS n
RETURN n;
// expect small (ideally passages that truly concern Creature / bestiary);
// FAIL if n is dozens of unrelated page Chunks (pre-fix: >> 20 across many pages)

// E — Spot: no abilities page chunk on Creature
MATCH (c:Creature:SeedNode)<-[:DOCUMENTED_BY|CONFIRMS_SEED]-(p)
WHERE coalesce(p.page, p.page_number, p.page_number_start) = 27
   OR coalesce(p.section_id, '') = 'abilities'
RETURN count(*) AS abilities_on_creature;
// expect 0
```

**ADA smoke (after fix + ingest):**

| Prompt | CONTEXT must include | CONTEXT must NOT include |
|---|---|---|
| Where is Galgenbeck? | place / p.12 (section or page) | OptionalClassesTable |
| What is a Goblin…? | entity-passage Goblin | AgonyEndTable, TrapsTable, abilities/carrying/broken PC rules |

---

## Out of scope

- ADA retrieval_hints synonym lists  
- Re-doing entity-passage boundary work (briefings 10–11) unless regressions appear  
- WORLD section materialization — **required**, not optional; see [briefing-13](./pdf-graph-builder-briefing-13.md) (ADA prefers sections; graph must have them)  
- Coverage phase 2 combat deepening  

---

## Operator checklist (AI-DM-Assistant)

- [ ] Sync: `.\scripts\sync-outbox-briefings.ps1`
- [ ] Paste this briefing into pgb session
- [ ] After handoff: re-smoke Galgenbeck + Goblin; confirm CONTEXT clean
- [ ] Then optionally smoke handoff-8 trap / agony table prompts

---

## Checklist for pgb agent

- [ ] Locate USES fan-out (concrete tables → wrong seeds)
- [ ] Locate DOCUMENTED_BY / CONFIRMS_SEED fan-out onto `Creature` / `Place` (and audit other broad seeds)
- [ ] Fix routing; clean existing `morkborg` edges or full re-ingest
- [ ] Acceptance Cypher A–E green
- [ ] Handoff: root-cause file + before/after counts (`Creature` USES degree; evidence degree)
