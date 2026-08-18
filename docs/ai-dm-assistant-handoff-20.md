# AI-DM-Assistant Handoff 20: D4 creature sheets

**From:** pdf-graph-builder  
**Date:** 2026-08-15  
**Context:** [Briefing 23](./pdf-graph-builder-briefing-23.md) (execute) / lock [briefing-20](./pdf-graph-builder-briefing-20.md) / [handoff-19](./ai-dm-assistant-handoff-19.md).

**Verdict:** **D4 green** — CREATURES entity passages parse into closed sheet slots (`HAS_HIT_POINTS` / `HAS_MORALE` / `HAS_ARMOR` / `HAS_ATTACK`). Goblin exemplar HP **6** / Morale **7** / Ropy skin **-d2** / Knife/shortbow **d4**. D1–D3 + `SUPERSEDES` intact. **Ball is with ADA** — retrieval hop for sheet slots; smokes **S1–S4**.

---

## Ops (what we did)

| Action | Done? |
|---|---|
| ADA reset + bootstrap (sheet scaffold) | **Yes** (operator — before this session) |
| Full product-path `.\ingest-morkborg.ps1` | **Yes** — `Document` **Completed**; nodes=147 / rels=244 / chunks=147; ~47 min |
| D4 sheets in extract path | **Yes** — `creature_sheets: 12/12` with 54 slots during extract |

```powershell
.\ingest-morkborg.ps1
# recovery / sheets-only:
backend\venv\Scripts\python.exe backend\materialize_creature_sheets.py
```

**Fill mode:** full scaffold-diff ingest after reset (`section_phase=2`). Spines + `SUPERSEDES` + sheets re-emitted in `/extract` before LLM chunk pass; tables via lookup pipeline.

**Stats (extract):** spines created 18 (7 + 11 D3), SUPERSEDES 11, sheets 12 creatures / 54 slots.

---

## What pgb shipped

| Item | Detail |
|---|---|
| Parser + materializer | `backend/src/creature_sheet_materialization.py` |
| Extract hook | `main.py` after operational spines (`section_phase >= 2`) |
| CLI | `backend/materialize_creature_sheets.py` |
| Constants | `HAS_HIT_POINTS` / `HAS_MORALE` / `HAS_ARMOR` / `HAS_ATTACK` in `INGEST_REL_TYPES` |
| Tests | `backend/test_creature_sheets.py` (Goblin + No armor / morale-none / 2d6 / or-attacks) |

Opaque sheet ids: `sheet:hp:<hash>`, `sheet:morale:…`, `sheet:armor:…`, `sheet:atk:…` — no creature display names in ids.

---

## Acceptance Cypher (pasted)

### D4-P0 — Prior spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN ['if:melee-hit-default', 'if:crit-attack']
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS n
```

| n |
|---|
| **13** |

### D4-P1 — Goblin sheet slots

```cypher
MATCH (c)-[:INSTANCE_OF]->(:Creature)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
OPTIONAL MATCH (c)-[:HAS_HIT_POINTS]->(hp:HitPoints)
OPTIONAL MATCH (c)-[:HAS_MORALE]->(m:Morale)
OPTIONAL MATCH (c)-[:HAS_ARMOR]->(a:Armor)
OPTIONAL MATCH (c)-[:HAS_ATTACK]->(atk:AttackProfile)
RETURN coalesce(c.name, c.title) AS creature,
       hp.value AS hp,
       m.value AS morale,
       coalesce(a.name, a.title) AS armor,
       a.reduce AS armor_reduce,
       collect(DISTINCT {name: coalesce(atk.name, atk.title), damage: atk.damage}) AS attacks
```

| creature | hp | morale | armor | armor_reduce | attacks |
|---|---|---|---|---|---|
| Goblin | **6** | **7** | Ropy skin | **-d2** | Knife/shortbow **d4** |

### D4-P2 — Batch HP

```cypher
MATCH (c)-[:HAS_HIT_POINTS]->(:HitPoints)
WHERE (c)-[:INSTANCE_OF]->(:Creature) OR c:Creature OR 'Creature' IN labels(c)
RETURN count(DISTINCT c) AS creatures_with_hp
```

| creatures_with_hp |
|---|
| **12** instances with `INSTANCE_OF` Creature (≥5). Gate query with `OR c:Creature` may also count the scaffold seed → report **13** in that form. |

### D4-P3 — Closed rels

```cypher
MATCH (c)-[r]->()
WHERE ((c)-[:INSTANCE_OF]->(:Creature) OR 'Creature' IN labels(c))
  AND type(r) STARTS WITH 'HAS_'
RETURN DISTINCT type(r) AS rel ORDER BY rel
```

| rel |
|---|
| HAS_ARMOR |
| HAS_ATTACK |
| HAS_HIT_POINTS |
| HAS_MORALE |

(No `HAS_STAT`.)

### D4-P4 — SUPERSEDES still present

```cypher
MATCH ()-[r:SUPERSEDES]->()
RETURN count(r) AS n
```

| n |
|---|
| **11** (post full-ingest re-check; ≥3) |

Goblin trio → matching defaults: Defense / Melee / Ranged — **3 rows** (opaque override ids unchanged).

---

## Gate checklist

| Gate | Status |
|---|---|
| Typed sheet edges only | ✅ |
| Goblin HP 6 / Morale 7 / armor / attack | ✅ (re-checked after full ingest) |
| Batch CREATURES | ✅ |
| D1–D3 spines intact | ✅ (13) |
| SUPERSEDES (D4-P4) | ✅ |
| No ArmorClass / HAS_STAT | ✅ |
| Full product-path Document Completed | ✅ |

---

## ADA next

1. Retrieval hop: creature in situation → sheet slots into CONTEXT.  
2. Smokes **S1–S4** (Goblin HP / armor / attack / morale).  

```powershell
# From pdf-graph-builder root — promote this handoff into ADA inbox:
Copy-Item -Force .\docs\ai-dm-assistant-handoff-20.md D:\GitHub\AI-DM-Assistant\docs\inbox\
```
