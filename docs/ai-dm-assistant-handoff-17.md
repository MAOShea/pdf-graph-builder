# AI-DM-Assistant Handoff 17: D3 creature DR overrides (graph parameter)

**From:** pdf-graph-builder  
**Date:** 2026-08-13  
**Context:** [Briefing 19](./pdf-graph-builder-briefing-19.md) / [handoff-16](./ai-dm-assistant-handoff-16.md).

**Verdict:** **D3 green** — creature attack/defence DR overrides materialize with `Circumstance {role: fighting}-[:APPLIES_TO]->(creature instance)` + `Compare.threshold`. Opaque `If.id` (`if:d3-<hash>`). **No creature name / `-vs-` / `goblin` in ids.** D1/D2 intact. **Ball is with ADA** — extend R16 to match `(FOR procedure) + (APPLIES_TO creature in situation)`; never parse creature from `If.id`. Smoke **G1–G4**.

---

## Ingest status (operator DB `morkborg`)

| Field | Value |
|---|---|
| Document | `mork-borg.pdf` (post ADA reset+bootstrap + full `.\ingest-morkborg.ps1`) |
| Scaffold | `Circumstance-[:APPLIES_TO]->Creature` / `Monster` present |
| Contract | `games/mork-borg/operational-spines.json` **v0.3.0** |
| D3 materialize | `.\materialize-operational-spines.ps1` after contract change (`scanned=12`, `emitted=11`, warnings=0) |

Next full scaffold-diff extract (`section_phase >= 2`) will re-emit D3 automatically via `/extract` hook.

---

## What pgb shipped

| Item | Detail |
|---|---|
| Spine contract | D1 (3) + D2 (4) + `creature_dr_overrides` extract rules |
| Materializer | `backend/src/spine_materialization.py` — batch CREATURES passages; opaque ids; `APPLIES_TO` on Circumstance |
| Extract hook | unchanged: scaffold-diff when `section_phase >= 2` |
| Recovery CLI | `.\materialize-operational-spines.ps1` |

### Design choices

1. **Creature is a graph parameter** — shared per-creature `Circumstance` (`role: fighting`) `APPLIES_TO` fiction instance `mork-borg.pdf#entity:creature:<slug>` (DENOTES target).
2. **`If.id`** = `if:d3-` + sha1(procedure \| creature_id \| threshold)[:16]. Same pattern for `bool:` / `circumstance:` / `compare:`.
3. **Outcomes reused** from D1 (`outcome:melee-hit` / miss, etc.).
4. **Conservative extract** (first rule wins):  
   - `attacks and defence are DRN` → Melee + Ranged + Defense  
   - `attacks are DRN` → Melee + Ranged  
   - `DRN to hit them` → Melee + Ranged  
   - `easy|difficult|hard to hit (DRN)` → Melee + Ranged  
   Skips ability-test / infection / piercing-only / paralysis lines (Scum, Zombie, Wyvern, Undead*, Blood-drenched skeleton).

### Creatures that received overrides

| Creature | Threshold | Procedures |
|---|---|---|
| **Goblin** (exemplar) | **14** | MeleeAttack, RangedAttack, DefenseRoll |
| Berserker | 10 | MeleeAttack, RangedAttack |
| Grotesque | 10 | MeleeAttack, RangedAttack |
| Troll | 10 | MeleeAttack, RangedAttack |
| Wraith | 14 | MeleeAttack, RangedAttack |

---

## Acceptance Cypher (pasted post-materialize)

### D3-P0 — Prior spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN [
  'if:melee-hit-default', 'if:crit-attack', 'if:fumble-defence'
]
RETURN i.id ORDER BY i.id
```

| i.id |
|---|
| `if:crit-attack` |
| `if:fumble-defence` |
| `if:melee-hit-default` |

### D3-P1 — Overrides bound by graph parameter

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:`IF`]->(b:BoolExpression {combinator: 'AND'})
MATCH (b)-[:HAS_ATOM]->(circ:Circumstance)-[:APPLIES_TO]->(c)
MATCH (b)-[:HAS_ATOM]->(cmp:Compare)
WHERE cmp.threshold IS NOT NULL
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure,
       coalesce(c.name, c.title, c.id) AS creature,
       cmp.threshold AS threshold,
       i.id AS if_id,
       count(DISTINCT t) AS then_n,
       count(DISTINCT e) AS else_n
ORDER BY creature, procedure
```

| procedure | creature | threshold | if_id | then_n | else_n |
|---|---|---|---|---|---|
| MeleeAttack | Berserker | 10 | `if:d3-af773122f84bc4cc` | 1 | 1 |
| RangedAttack | Berserker | 10 | `if:d3-892cd4b40c97c754` | 1 | 1 |
| DefenseRoll | Goblin | **14** | `if:d3-2393b8d674143b52` | 1 | 1 |
| MeleeAttack | Goblin | **14** | `if:d3-0724f59052a53acd` | 1 | 1 |
| RangedAttack | Goblin | **14** | `if:d3-795bad78deaf9b85` | 1 | 1 |
| MeleeAttack | Grotesque | 10 | `if:d3-56a6964679394d84` | 1 | 1 |
| RangedAttack | Grotesque | 10 | `if:d3-7005d0be2074987d` | 1 | 1 |
| MeleeAttack | Troll | 10 | `if:d3-8d32372beaf9ba3c` | 1 | 1 |
| RangedAttack | Troll | 10 | `if:d3-ffbddf386d0e367c` | 1 | 1 |
| MeleeAttack | Wraith | 14 | `if:d3-2b16717607f8fb16` | 1 | 1 |
| RangedAttack | Wraith | 14 | `if:d3-5c111e99fce520c4` | 1 | 1 |

### D3-P1b — Id hygiene

```cypher
MATCH (i:If:IngestNode)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(i.id) CONTAINS toLower(coalesce(c.name, c.title, ''))
   OR toLower(i.id) CONTAINS 'goblin'
   OR toLower(i.id) CONTAINS '-vs-'
RETURN i.id, coalesce(c.name, c.title) AS creature
```

**Expect / got:** **zero rows**.

### D3-P2 — Evidence → entity passage

```cypher
MATCH (i:If:IngestNode)-[:DOCUMENTED_BY]->(p:RulePassage)
MATCH (i)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
RETURN coalesce(c.name, c.title, c.id) AS creature,
       collect(DISTINCT p.id) AS passages
ORDER BY creature
```

| creature | passages |
|---|---|
| Berserker | `…#entity-passage:CREATURES:berserker` |
| Goblin | `…#entity-passage:CREATURES:goblin` |
| Grotesque | `…#entity-passage:CREATURES:grotesque` |
| Troll | `…#entity-passage:CREATURES:troll` |
| Wraith | `…#entity-passage:CREATURES:wraith` |

### D3-P3 — Closed rels on If

```cypher
MATCH (i:If:IngestNode)-[r]->()
WHERE exists {
  (i)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->()
}
RETURN DISTINCT type(r) AS rel ORDER BY rel
```

| rel |
|---|
| DOCUMENTED_BY |
| ELSE |
| FOR |
| IF |
| INSTANCE_OF |
| THEN |

(`APPLIES_TO` / `HAS_ATOM` / `COMPARED_TO` hang off Circumstance / BoolExpression / Compare — not off `If`. No `HAS_ATTACK`.)

---

## Gate checklist

| Gate | Status |
|---|---|
| Creature via `APPLIES_TO` instance | ✅ |
| Opaque `If.id` (D3-P1b zero rows) | ✅ |
| Batch CREATURES with extractable DR | ✅ (5 creatures / 11 spines) |
| Goblin exemplar threshold 14 × 3 procedures | ✅ |
| D3-P0…P3 | ✅ |

---

## ADA next (required)

1. Extend **R16** to prefer override spines when situation creature matches `Circumstance-[:APPLIES_TO]->` instance — **never** parse creature from `If.id`.  
2. Prefer those over default DR12 when parameter matches.  
3. Smokes **G1–G3** (Goblin DR14) + **G4** (e.g. Troll/Wraith).  
4. Sheet ontology later.

Promote from pgb if mirrors lag: `operational-spines.json` v0.3.0, this handoff → ADA `docs/inbox/`.
