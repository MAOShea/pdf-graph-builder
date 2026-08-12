# AI-DM-Assistant Handoff 14: Briefing 17 — Violence If spines (D1)

**From:** pdf-graph-builder  
**Date:** 2026-08-11  
**Context:** [Briefing 17](./pdf-graph-builder-briefing-17.md) — altitude D operational fill (D1).

**Verdict:** **D1-P0–P3 green.** Three Violence DR12 `If` spines materialized as `:IngestNode`s with evidence into `violence-combat` RulePassages. **Ball is with ADA** for retrieval hop + C1–C3 smokes (no papering missing spines).

---

## What landed

| Item | Detail |
|---|---|
| Contract | `games/mork-borg/operational-spines.json` v0.1.0 (+ manifest `operational_spines` pointer) |
| Materializer | `backend/src/spine_materialization.py` — deterministic MERGE; closed vocab only |
| Hook | `POST /extract` scaffold-diff when `section_phase >= 2` |
| Recovery CLI | `.\materialize-operational-spines.ps1` (`-EnsureSections` after DB reset) |

**Stable ids:** `if:melee-hit-default`, `if:ranged-hit-default`, `if:defence-default` (+ Compare / BoolExpression / Outcome children).

**Property:** `Compare.threshold = 12` (int); `COMPARED_TO` → SeedNode `DR`.

**Ops note:** Operator reset+bootstrap for D0.4 cleared Tier-5. This handoff used `materialize-operational-spines.ps1 -EnsureSections` (Document stub + section phase 2 + spines) + catalog re-link — **not** a full LLM `/extract`. Product path remains `.\ingest-morkborg.ps1` (`section_phase` default 2) once backend is up.

---

## Gate results (pasted)

### D1-P0 — Scaffold

```cypher
MATCH (n:SeedNode)
WHERE n.name IN ['If', 'BoolExpression', 'Compare', 'Circumstance']
RETURN n.name ORDER BY n.name
```

| name |
|---|
| BoolExpression |
| Circumstance |
| Compare |
| If |

**4 / 4**

### D1-P1 — Three procedure spines (IngestNode instances only)

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:`IF`]->(b:BoolExpression)-[:HAS_ATOM]->(c:Compare)
OPTIONAL MATCH (c)-[:COMPARED_TO]->(dr)
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure,
       b.combinator AS combinator,
       c.threshold AS threshold,
       dr.name AS compared_to,
       count(DISTINCT t) AS then_count,
       count(DISTINCT e) AS else_count,
       i.id AS if_id
ORDER BY procedure
```

| procedure | combinator | threshold | compared_to | then | else | if_id |
|---|---|---|---|---|---|---|
| DefenseRoll | LEAF | **12** | DR | 1 | 1 | `if:defence-default` |
| MeleeAttack | LEAF | **12** | DR | 1 | 1 | `if:melee-hit-default` |
| RangedAttack | LEAF | **12** | DR | 1 | 1 | `if:ranged-hit-default` |

**Note:** Bootstrap also has abstract `SeedNode:If`–`FOR`–procedure shape edges. Acceptance must filter **`i:IngestNode`** (or require `IF`→`BoolExpression` with `threshold`). Threshold property is `Compare.threshold`.

### D1-P2 — Evidence

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:DOCUMENTED_BY]->(p:RulePassage)
WHERE p.section_id = 'violence-combat'
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure, collect(p.id) AS ids
ORDER BY procedure
```

| procedure | passages |
|---|---|
| DefenseRoll | `…#violence-combat#p3` (Test Agility) |
| MeleeAttack | `…#violence-combat#p1` (Test Strength) |
| RangedAttack | `…#violence-combat#p2` (Test Presence) |

### D1-P3 — Closed rel set on ingest Ifs

```cypher
MATCH (i:If:IngestNode)-[r]->()
WHERE NOT type(r) IN ['FOR','IF','THEN','ELSE','DOCUMENTED_BY','CONFIRMS_SEED','INSTANCE_OF']
RETURN DISTINCT type(r) AS unexpected_rel
```

**Result:** empty (no unexpected spine rels).

---

## Checklist

| Gate | Status |
|---|---|
| Briefing-14 Violence section/passages | ✅ rematerialized |
| Catalog→violence-combat | ✅ re-linked (`materialize-rulebook-index -Phase 2`) |
| D1-P0 | ✅ |
| D1-P1 | ✅ |
| D1-P2 | ✅ |
| D1-P3 | ✅ |

---

## ADA next

1. Promote `operational-spines.json` + updated `ingest-manifest.json` from pgb if mirrors lag.  
2. Retrieval: situation → candidate `If` (`FOR` procedure) → `IF`/`THEN`/`ELSE` + citing passage.  
3. Smoke **C1–C3** (Sources + CONTEXT must show spine + `violence-combat` citation).  
4. Open **D2** only after C1–C3 green on real edges — do not paper missing spines.
