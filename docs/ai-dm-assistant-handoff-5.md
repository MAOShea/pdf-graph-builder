# AI-DM-Assistant Handoff 5: Briefing 9 — fiction INSTANCE_OF fan-out fixed

**From:** pdf-graph-builder  
**Date:** 2026-08-04  
**Context:** [Briefing 9](./pdf-graph-builder-briefing-9.md) hot-fix after handoff-4 / Briefing 8.

**Verdict:** **PASS** — acceptance Cypher 1–4 green; Galgenbeck → `Place` only.

---

## Root cause

**File:** `backend/src/index_materialization.py` → `materialize_fiction_instances()`

**Bad pattern:** After resolving a seed via label, the MERGE matched seeds with:

```cypher
MATCH (seed:SeedNode)
WHERE toLower(coalesce(seed.seed_id, seed.id, '')) = toLower($seed_id)
MERGE (entity)-[:INSTANCE_OF]->(seed)
```

`_find_seed_node` returned `coalesce(seed_id, id, name)`. When that value was empty or non-unique relative to `seed_id`/`id` on other seeds, the WHERE matched **many/all** SeedNodes. Each fiction entity got ~35 `INSTANCE_OF` edges (WORLD) or ~11 (CREATURES) instead of one.

Handoff-4 only checked “has a Place link,” so Briefing 8 false-greened.

---

## Fix

1. Resolve seed **only** by label from `entry_kind_to_seed` (`$seed_label IN labels(seed)` + `LIMIT 1`).
2. Abort if that label is missing or matches more than one SeedNode.
3. Strip existing fiction `INSTANCE_OF` before re-MERGE (idempotent repair).
4. Same label-scoped pattern for Setting `INSTANCE_OF` / `OCCURS_IN`.

**Repair run (no full re-ingest):**

```powershell
backend\venv\Scripts\python.exe backend\materialize_rulebook_index.py --fiction-only
```

Stripped **1112** bad edges; recreated **40** correct `INSTANCE_OF` links.

---

## Before / after

| Metric | Before | After |
|---|---|---|
| Fiction `INSTANCE_OF` total | 1112 | **40** |
| Galgenbeck → SeedNode count | 35 | **1** (`Place`) |
| Entities with ≠1 seed | 40 | **0** |
| Place cross-type `INSTANCE_OF` | 442 | **0** |
| Creature cross-type `INSTANCE_OF` | 120 | **0** |
| Places / creatures counts | 13 / 12 | **13 / 12** |

Acceptance: `backend\verify_briefing9.py` → **PASS**.

---

## ADA smoke test

Re-ask “Galgenbeck” in chat. Sources should cite **one** fiction instance typed as Place (not Player/GameMaster/…).

---

## Open

| Item | Owner |
|---|---|
| Restart pgb backend so next full ingest uses the fixed materializer | operator |
| Runtime Sources already fixed once graph is clean | AI-DM-Assistant |
