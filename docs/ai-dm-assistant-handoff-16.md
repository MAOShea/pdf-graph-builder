# AI-DM-Assistant Handoff 16: D2 Crit / fumble / rest / infection spines

**From:** pdf-graph-builder  
**Date:** 2026-08-11  
**Context:** [Briefing 18](./pdf-graph-builder-briefing-18.md) / [handoff-15](./ai-dm-assistant-handoff-15.md).

**Verdict:** **D2 green** — four Crit/fumble/rest/infection `If` spines materialize with closed vocabulary + `crit-fumble-rest` evidence. D1 Violence spines intact. **Ball is with ADA** — extend R16 select hop and smoke **R1–R4**. Do not invent Crit/Rest SeedNode labels.

---

## Ingest status (operator DB `morkborg`)

| Field | Value |
|---|---|
| Document | `mork-borg.pdf` **Completed** |
| Chunks | 71 / 71 processed |
| Tokens | ~239 667 |
| `section_phase` | **2** (sections + operational spines in `/extract`) |
| Contract | `games/mork-borg/operational-spines.json` **v0.2.0** |

Full `.\ingest-morkborg.ps1 -SectionPhase 2` after contract+materializer change. Spines survived cleanup+extract.

---

## What pgb shipped

| Item | Detail |
|---|---|
| Spine contract | D1 (3) + D2 (4) = **7** spines |
| Materializer | `backend/src/spine_materialization.py` — `compare_dr` / `compare_face` / `circumstance`; multi-`FOR`; multi-`THEN`; optional `ELSE` |
| Extract hook | scaffold-diff when `section_phase >= 2` |
| Recovery CLI | `.\materialize-operational-spines.ps1` |

**Stable D2 ids:** `if:crit-attack`, `if:fumble-defence`, `if:rest-catch-breath`, `if:infection-blocks-rest`  
(+ `bool:*`, `compare:natural-20` / `compare:natural-1`, `circumstance:*`, `outcome:*` children).

### Design choices (document for retrieval)

1. **`if:crit-attack`** — one `If` with **two** `FOR` → `MeleeAttack` + `RangedAttack`. Face Compare `natural_face = 20` (**no** `COMPARED_TO` DR). Two `THEN` Outcomes (double damage; armor −1 tier). `ELSE` omitted.
2. **Defence crit** — Bare Bones `#p0` says defence crit is **“PC gains a free attack”**, not double damage / armor tier. **Not** emitted as a twin of attack crit.
3. **`if:fumble-defence`** — `FOR` `DefenseRoll`; face `= 1`; two `THEN` (double damage; armor −1). Attack fumble (weapon breaks) deferred.
4. **`if:rest-catch-breath`** — `FOR` **`Downtime`** (no Rest seed); LEAF `Circumstance` “catch breath and drink” → restore d4 HP.
5. **`if:infection-blocks-rest`** — `FOR` `Downtime`; **AND** of Circumstance `Infected` + `resting` (not status `Condition`); THEN no rest benefit / lose d6 HP daily.

---

## Acceptance Cypher (pasted post-ingest)

### D2-P0 — D1 still green + section present

```cypher
MATCH (i:If:IngestNode)
WHERE i.id STARTS WITH 'if:melee' OR i.id STARTS WITH 'if:ranged' OR i.id STARTS WITH 'if:defence'
RETURN count(i) AS d1_spines
```

| d1_spines | crit-fumble-rest Chunk |
|---|---|
| **3** | **1** |

### D2-P1 — Four D2 spines

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
WHERE i.id IN [
  'if:crit-attack',
  'if:fumble-defence',
  'if:rest-catch-breath',
  'if:infection-blocks-rest'
]
MATCH (i)-[:`IF`]->(b:BoolExpression)-[:HAS_ATOM]->(atom)
OPTIONAL MATCH (i)-[:THEN]->(t)
RETURN i.id AS if_id,
       coalesce(proc.name, labels(proc)[0]) AS procedure,
       b.combinator AS combinator,
       labels(atom) AS atom_labels,
       coalesce(atom.threshold, atom.name) AS atom_key,
       count(DISTINCT t) AS then_n
ORDER BY if_id
```

| if_id | procedure | combinator | atom | key | then_n |
|---|---|---|---|---|---|
| `if:crit-attack` | MeleeAttack | LEAF | Compare | **20** | 2 |
| `if:crit-attack` | RangedAttack | LEAF | Compare | **20** | 2 |
| `if:fumble-defence` | DefenseRoll | LEAF | Compare | **1** | 2 |
| `if:infection-blocks-rest` | Downtime | AND | Circumstance | Infected | 1 |
| `if:infection-blocks-rest` | Downtime | AND | Circumstance | resting | 1 |
| `if:rest-catch-breath` | Downtime | LEAF | Circumstance | catch breath and drink | 1 |

### D2-P2 — Evidence → crit-fumble-rest

```cypher
MATCH (i:If:IngestNode)-[:DOCUMENTED_BY]->(p:RulePassage)
WHERE i.id IN [
  'if:crit-attack',
  'if:fumble-defence',
  'if:rest-catch-breath',
  'if:infection-blocks-rest'
]
  AND (p.section_id = 'crit-fumble-rest' OR p.id CONTAINS 'crit-fumble-rest')
RETURN i.id AS if_id, collect(DISTINCT p.id) AS passages
ORDER BY if_id
```

| if_id | passage |
|---|---|
| `if:crit-attack` | `…#crit-fumble-rest#p0` |
| `if:fumble-defence` | `…#crit-fumble-rest#p1` |
| `if:rest-catch-breath` | `…#crit-fumble-rest#p3` |
| `if:infection-blocks-rest` | `…#crit-fumble-rest#p3` |

### D2-P3 — No vocabulary leakage

```cypher
MATCH (i:If:IngestNode)-[r]->()
WHERE i.id STARTS WITH 'if:crit'
   OR i.id STARTS WITH 'if:fumble'
   OR i.id STARTS WITH 'if:rest'
   OR i.id STARTS WITH 'if:infection'
RETURN DISTINCT type(r) AS rel
ORDER BY rel
```

| rel |
|---|
| DOCUMENTED_BY |
| FOR |
| IF |
| INSTANCE_OF |
| THEN |

(Guard atoms use `HAS_ATOM` off BoolExpression; face Compare has no `COMPARED_TO`.)

### Defence-crit prose (why no second face-20 spine)

From `#p0` Crit passage:

> Attack: Double damage, armor/protection is also reduced one tier.  
> Defence: PC gains a free attack.

---

## Gate checklist

| Gate | Status |
|---|---|
| D1 spines intact | ✅ |
| `crit-fumble-rest` + catalog P5 | ✅ (kept) |
| **D2-P0** | ✅ |
| **D2-P1** four spines | ✅ |
| **D2-P2** evidence | ✅ |
| **D2-P3** closed rels | ✅ |

---

## ADA next (required)

1. Extend **R16** select hop for crit / fumble / rest / infected situations (not cowboy short-circuits).  
2. Graph + CONTEXT smokes **R1–R4** (spine + `crit-fumble-rest` citation).  
3. Open **D3** only after those are green.

Promote from pgb if mirrors lag: `operational-spines.json` v0.2.0, this handoff.
