# Briefing 19: Altitude D — creature DR overrides as graph parameters (D3)

**For pdf-graph-builder agents.** Third **operational fill** under altitude D ([DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order)). Same closed vocabulary as [briefing-17](./pdf-graph-builder-briefing-17.md) / [briefing-18](./pdf-graph-builder-briefing-18.md).

**Prerequisite:** D1 + D2 spines green ([handoff-15](../inbox/ai-dm-assistant-handoff-15.md), [handoff-16](../inbox/ai-dm-assistant-handoff-16.md)). CREATURES entity passages exist. **ADA seed grammar updated** (`ludemes` 0.4.1: `Circumstance-[:APPLIES_TO]->Monster`; MB `deltas` 0.3.3: `→Creature`). Operator must **reset + bootstrap** before this fill so the scaffold allows the parameter edge.

**Design rule (read this):** the creature is a **graph parameter** (edge to an instance node), **not** a substring of `If.id`.  
Do **not** use ids like `if:melee-vs-goblin` / `if:melee-hit-goblin`. Those encode the creature in a string and force ADA into slug parsing.

**Sheet rels:** deferred here — see **[briefing-20](./pdf-graph-builder-briefing-20.md)** (D4). Do not invent `HAS_STAT` / free-form sheet edges in this D3 fill.

---

## Framing

| Side | Role |
|---|---|
| **DM prompt** | Situation — which procedure, which creature instance |
| **Rulebook** | `If` spines |
| **pgb** | Emit override spines; bind creature via **`APPLIES_TO`** (or equivalent closed edge) |
| **ADA** | Select by matching procedure **and** creature instance in the guard — not by parsing id strings |

---

## Identity = subgraph (not a named string)

A creature DR override is uniquely identified by:

```text
(If)-[:FOR]->(Procedure)          // MeleeAttack | RangedAttack | DefenseRoll
(If)-[:IF]->(BoolExpression {combinator: "AND"})
(BoolExpression)-[:HAS_ATOM]->(Circumstance {role: "fighting"})
(Circumstance)-[:APPLIES_TO]->(CreatureInstance)   // the parameter
(BoolExpression)-[:HAS_ATOM]->(Compare {threshold: N})-[:COMPARED_TO]->(DR)
(If)-[:THEN|ELSE]->(Outcome)
(If)-[:DOCUMENTED_BY]->(entity RulePassage for that creature)
```

**`If.id`:** opaque stable merge key only — e.g. ingest element id, or hash of `(procedure, creature_instance_id, threshold)`.  
Human-readable creature names belong on the **creature node** / catalog title, not inside `If.id`.

**MERGE / upsert:** match existing override by **graph shape** (same `FOR` procedure + same `Circumstance-[:APPLIES_TO]->` instance), not by decoding a slug from `id`.

---

## Template (batch every qualifying CREATURES row)

For each creature instance `C` whose entity prose states an attack/defence DR (or clear equivalent):

```text
(:If:IngestNode {id: <opaque>})-[:FOR]->(:MeleeAttack)
(:If)-[:IF]->(:BoolExpression {combinator: "AND"})
(:BoolExpression)-[:HAS_ATOM]->(:Circumstance {role: "fighting"})
(:Circumstance)-[:APPLIES_TO]->(C)
(:BoolExpression)-[:HAS_ATOM]->(:Compare {op: ">=", threshold: <N>})-[:COMPARED_TO]->(:DR)
(:If)-[:THEN]->(:Outcome)   // hit
(:If)-[:ELSE]->(:Outcome)   // miss
```

Emit the same shape for `RangedAttack` and `DefenseRoll` when the prose applies to attacks and defence (Goblin: DR14 for both).

**Skip** creatures with no extractable DR override (leave D1 defaults).

**Batch source:** full `creatures_index` — one materializer pass.

---

## Goblin = acceptance exemplar only

Prose: attacks and defence **DR14**.  
Expect three override `If` nodes whose `Circumstance-[:APPLIES_TO]->` Goblin instance and `Compare.threshold = 14`, `FOR` Melee / Ranged / Defence.  
**Ids must not contain `goblin`.**

---

## Out of scope

| Deferred | Why |
|---|---|
| D1/D2 spines | Keep |
| `HAS_*` sheet ontology | ADA seeds first |
| Creature name inside `If.id` | **Forbidden** |
| Inventing DR when prose silent | Skip |
| Per-creature briefings | Forbidden |

---

## Ops path

**Split of work** (ingest is **only** in pgb — ADA never runs Tier-5):

| Where | What |
|---|---|
| **ADA** | Seed grammar + **reset + bootstrap** only (scaffold). Then paste this briefing into a pgb session. |
| **pgb** | All Tier-5: fiction + D1/D2 spines + **this D3 fill** on the fresh DB (reset wiped prior ingest). |

1. **ADA operator:** after seed pull —  
   `python schema/reset_db.py --game mork-borg --confirm`  
   then `python schema/bootstrap.py --game mork-borg`  
   Confirm scaffold has `Circumstance-[:APPLIES_TO]->Creature` (and/or `Monster`).  
2. **Hand this briefing to pgb** (sync/paste).  
3. **pgb:** extend spine materializer (template + loop CREATURES; opaque ids; `APPLIES_TO` → creature **instance**); run full product-path ingest (fiction + D1 + D2 + D3).  
4. **pgb → ADA inbox:** handoff with Cypher pasted — prove parameter edge, not id substrings.

**This is not Tier-5-only on the ADA side.** New seed grammar → ADA reset + bootstrap first; then pgb re-dresses the empty scaffold.

---

## Acceptance gates (handoff must paste results)

### D3-P0 — Prior spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN [
  'if:melee-hit-default', 'if:crit-attack', 'if:fumble-defence'
]
RETURN i.id ORDER BY i.id
```

**Expect:** 3 rows.

### D3-P1 — Overrides bound by graph parameter (not id slug)

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:`IF`]->(b:BoolExpression {combinator: 'AND'})
MATCH (b)-[:HAS_ATOM]->(circ:Circumstance)-[:APPLIES_TO]->(c)
WHERE (c:IngestNode OR c:Creature OR c.name IS NOT NULL)
  AND (c)-[:INSTANCE_OF]->(:Creature) OR 'Creature' IN labels(c)
      OR exists { (c)-[:INSTANCE_OF]->(:SeedNode) }
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

**Expect:**

- Multiple creatures when prose supports it (batch).  
- Goblin (by **creature** column / node), threshold **14**, three procedures.  
- **`if_id` does not contain creature names** (handoff: assert with a check — e.g. no `goblin` / `scum` substring in `i.id` for these rows).  
- `then_n` / `else_n` ≥ 1.

Simplify the `WHERE` on `c` to match how your instances are actually labelled; the invariant is: **Circumstance APPLIES_TO the creature instance**.

### D3-P1b — Id hygiene (required)

```cypher
MATCH (i:If:IngestNode)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(i.id) CONTAINS toLower(coalesce(c.name, c.title, ''))
   OR toLower(i.id) CONTAINS 'goblin'
   OR toLower(i.id) CONTAINS '-vs-'
RETURN i.id, coalesce(c.name, c.title) AS creature
```

**Expect:** **zero rows**. Creature must not appear in `If.id`; `-vs-` slug pattern retired.

### D3-P2 — Evidence from that creature’s entity passage

```cypher
MATCH (i:If:IngestNode)-[:DOCUMENTED_BY]->(p:RulePassage)
MATCH (i)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
RETURN coalesce(c.name, c.title, c.id) AS creature,
       collect(DISTINCT p.id) AS passages
ORDER BY creature
```

**Expect:** passages are that creature’s entity scope.

### D3-P3 — Closed rels on If

```cypher
MATCH (i:If:IngestNode)-[r]->()
WHERE exists {
  (i)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->()
}
RETURN DISTINCT type(r) AS rel ORDER BY rel
```

**Expect:** `FOR`, `IF`, `THEN`, `ELSE`, `DOCUMENTED_BY`, … — no `HAS_ATTACK`.

---

## Gate checklist

| Gate | Required |
|---|---|
| Creature via `APPLIES_TO` instance | **Required** |
| Opaque `If.id` (no creature name / no `-vs-` slug) | **Required** |
| Batch CREATURES with extractable DR | **Required** |
| Goblin exemplar threshold 14 in **creature** column | **Required** |
| D3-P0…P3 | **Required** |

---

## What ADA will do after a green handoff

1. Extend **R16** to match `(FOR procedure) + (Circumstance APPLIES_TO creature mentioned in situation)` — **never** parse creature from `If.id`.  
2. Prefer those overrides over default DR12 when the creature parameter matches.  
3. Smokes use Goblin + one other override creature (if any).  
4. Sheet ontology later.

---

## Standing smokes (ADA)

| Id | Prompt | Expect in CONTEXT |
|---|---|---|
| **G1** | *I melee a Goblin — what's the DR?* | Override `If` FOR MeleeAttack, Circumstance APPLIES_TO Goblin, threshold **14** |
| **G2** | *I shoot a Goblin — DR?* | same, RangedAttack |
| **G3** | *I defend against a Goblin — DR?* | same, DefenseRoll |
| **G4** | Same for another creature that received an override | bound via APPLIES_TO, not id string |

---

## Sync

`.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root, or paste into the pgb Cursor session.
