# AI-DM-Assistant Handoff 9: Briefing 12 — seed_id fan-out fixed

**From:** pdf-graph-builder  
**Date:** 2026-08-07  
**Context:** [Briefing 12](./pdf-graph-builder-briefing-12.md) — USES / evidence pollution on broad seeds after ADA smoke.

**Verdict:** **FIXED** (code + surgical repair on `morkborg`). Full re-ingest still recommended so legitimate `CONFIRMS_SEED` / `DOCUMENTED_BY` from LLM extract are rewritten under the new matcher.

---

## Root cause

Bootstrap stores a **file-level** `seed_id` on every seed from that file (e.g. all Mörk Borg deltas → `mork-borg-deltas`; all universal ludemes → `ttrpg-universal`).

Table materialization and scaffold-diff then matched:

```cypher
WHERE toLower(coalesce(n.seed_id, n.id, '')) = toLower($seed_id)
```

So `used_by: ["Trap"]` resolved to seed_id `mork-borg-deltas` and **MERGE USES from every delta seed** onto `TrapsTable` (Creature, Misery, Agility, …). Same for `CharacterCreation` → `ttrpg-universal` → Place and dozens of others got `USES OptionalClassesTable`.

Evidence fan-out: CONFIRMS_SEED / DOCUMENTED_BY used the same seed_id match → book-wide Chunk→Creature edges (smoke: 82).

---

## Fix

| Area | Change |
|---|---|
| `table_materialization.py` | Match seeds by **concept label** (`$label IN labels(seed)`); never by file `seed_id` alone |
| `bundle_materialization.py` | Same for OptionalClass `INSTANCE_OF` |
| `graphDB_dataAccess.fetch_scaffold_node_map` | Key map by concept labels / name; do not key solely by shared `seed_id` |
| `common_fn.save_scaffold_diff_in_neo4j` | CONFIRMS_SEED / DOCUMENTED_BY and scaffold rels resolve by label / name / id — not shared seed_id |

**Repair (already run on operator DB):**

```powershell
backend\venv\Scripts\python.exe backend\repair_briefing12_fanout.py
```

- Deleted fan-out `SeedNode-[:USES]->table` (64 edges); rewired from manifest `used_by`  
- Deleted polluted `Chunk→SeedNode` DOCUMENTED_BY|CONFIRMS_SEED (4158) — next full ingest restores legitimate confirms  

---

## Acceptance (post-repair counts)

| Check | Before | After |
|---|---|---|
| A Creature USES trap/agony/… | 2 | **0** |
| B Place USES optional/trap/agony | 1 | **0** |
| C Trap→TrapsTable / Misery→AgonyEnd | 1 / 1 | **1 / 1** |
| D Creature evidence degree | 82 | **0** (cleared; expect small after re-ingest) |
| E abilities page on Creature | 4 | **0** |

---

## ADA follow-up

1. **Full re-ingest** (or at least scaffold-diff extract) so Chunk→Seed confirms use label matching.  
2. Re-smoke Galgenbeck / Goblin (CONTEXT must not include OptionalClasses / Agony / Traps / abilities).  
3. Re-smoke handoff-8 trap / agony prompts (USES owners still wired).

No ADA retrieval change required — graph was wrong; graph is fixed.
