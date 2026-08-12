# Briefing 19: Altitude D — Goblin DR14 `If` spines (D3 vertical slice)

**For pdf-graph-builder agents.** Third **operational fill** under altitude D ([DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order)). Same closed vocabulary as [briefing-17](./pdf-graph-builder-briefing-17.md) / [briefing-18](./pdf-graph-builder-briefing-18.md).

**Prerequisite:** D1 + D2 spines green ([handoff-15](../inbox/ai-dm-assistant-handoff-15.md), [handoff-16](../inbox/ai-dm-assistant-handoff-16.md)). Goblin **entity-scoped** `RulePassage` already exists (fiction gate / briefing-10–11). Scaffold has `If` / `BoolExpression` / `Circumstance` / `Compare` / `Creature` / `CreatureTest`.

**Do not invent** sheet relationship types (`HAS_STAT`, `HAS_ATTACK`, `HAS_ARMOR`, …) — those labels are **not** in ADA Tier 0–4 seeds yet. This briefing is the **Goblin DR14 adjudication slice** (the paper shape already locked in DESIGN). Full creature-sheet ontology = later ADA seed PR + follow-up briefing.

---

## Framing (unchanged)

| Side | Role |
|---|---|
| **DM prompt** | Situation (e.g. fighting a Goblin) — **not** an IF/THEN/ELSE |
| **Rulebook** | Library of `If` spines |
| **pgb** | Materialize Goblin DR14 spines + cite Goblin entity passage |
| **ADA (later)** | Extend R16 to select these when the situation mentions Goblin |

Closed vocabulary only. `Circumstance` = evaluable situating atom (true/false). Not status `Condition`.

---

## Closed vocabulary

**Nodes:** `If`, `BoolExpression`, `Circumstance`, `Compare`, `Outcome`  
**Rels:** `FOR`, `IF`, `THEN`, `ELSE`, `HAS_ATOM`; `COMPARED_TO` → `DR` / threshold **14**  
**Property:** `BoolExpression.combinator` ∈ {`LEAF`, `AND`, `OR`, `NOT`} — Goblin guards use **`AND`**

**Evidence:** every spine `DOCUMENTED_BY` → Goblin **entity** `RulePassage` (not a neighbor creature, not bounty trail, not `violence-combat` alone).

---

## Book cue (Bare Bones Goblin)

Entity passage Special line (paraphrase — match your extract):

> Quick; **attacks and defence are DR14**.

Meaning for spines: when the situation is fighting a Goblin, PC melee / ranged / defence tests use threshold **14** (not the default 12 Violence spines).

---

## D3 scope — what to materialize (Goblin only)

Extend `operational-spines.json` (v0.2.x → v0.3.0). Deterministic materializer; full `.\ingest-morkborg.ps1 -SectionPhase 2` (or current phase that includes CREATURES entity passages). **Do not** wipe D1/D2 spines.

### 1. Melee vs Goblin (DR 14)

```text
(:If {id: "if:melee-hit-goblin"})-[:FOR]->(:MeleeAttack)
(:If)-[:IF]->(:BoolExpression {combinator: "AND"})
(:BoolExpression)-[:HAS_ATOM]->(:Circumstance {name: "fighting Goblin"})
(:BoolExpression)-[:HAS_ATOM]->(:Compare {op: ">=", threshold: 14})-[:COMPARED_TO]->(:DR)
(:If)-[:THEN]->(:Outcome)   // hit
(:If)-[:ELSE]->(:Outcome)   // miss
```

### 2. Ranged vs Goblin (DR 14)

Same shape: `if:ranged-hit-goblin` `FOR` `RangedAttack`.

### 3. Defence vs Goblin (DR 14)

Same shape: `if:defence-goblin` `FOR` `DefenseRoll`.

### Optional (only if Goblin prose clearly states creature-side tests)

```text
(:If {id: "if:goblin-creature-test"})-[:FOR]->(:CreatureTest)
... AND Circumstance "Goblin acting" + Compare threshold 14 ...
```

Skip if the book only constrains PC attack/defence DR. Document the choice in the handoff.

**Stable ids (required):**  
`if:melee-hit-goblin`, `if:ranged-hit-goblin`, `if:defence-goblin`  
(+ `bool:*`, `circumstance:fighting-goblin`, `compare:*-dr14`, `outcome:*`).

**Circumstance naming:** use exactly `fighting Goblin` (or document a single canonical string). Do not create a parallel “vs Goblin” / “Goblin present” synonym set in the graph.

---

## Out of scope

| Deferred | Why |
|---|---|
| D1/D2 spines | Keep; do not regress |
| Full bestiary sheet (`HAS_HP`, `HAS_ATTACK`, armor tiers as edges) | **ADA seed lock first** — not this briefing |
| Every CREATURES row | Goblin vertical slice only |
| Lore / Galgenbeck | Never |
| Changing ADA `ludemes.json` from pgb | Gap → handoff; ADA fixes seeds |

---

## Ops path

1. Confirm Goblin entity `RulePassage` exists and stops before neighbor/bounty bleed.  
2. Confirm D1/D2 `If:IngestNode` counts unchanged after your run.  
3. Extend spine contract + materializer (`circumstance` + `compare_dr` with threshold 14, `combinator: AND`).  
4. Full product-path ingest (not recovery-only for the handoff claim).  
5. Handoff with acceptance Cypher pasted. No “ball with ADA” until D3-P0–P2 green.

**No ADA reset/bootstrap** unless scaffold labels are missing (they should not be). Tier-5 only → full ingest is enough ([same rule as D2](../inbox/ai-dm-assistant-handoff-16.md)).

---

## Acceptance gates (handoff must paste results)

### D3-P0 — Prior spines intact + Goblin passage

```cypher
MATCH (i:If:IngestNode)
WHERE i.id STARTS WITH 'if:melee-hit-default'
   OR i.id STARTS WITH 'if:crit'
   OR i.id STARTS WITH 'if:fumble'
RETURN count(i) AS prior_sample
```

```cypher
MATCH (p:RulePassage)
WHERE toLower(coalesce(p.id,'')) CONTAINS 'goblin'
   OR toLower(coalesce(p.text,'')) CONTAINS 'goblin'
RETURN count(p) AS goblin_passages
```

**Expect:** prior_sample ≥ 1 (smoke that D1/D2 still there); goblin_passages ≥ 1 entity-scoped preferred.

### D3-P1 — Three Goblin DR14 spines

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
WHERE i.id IN [
  'if:melee-hit-goblin',
  'if:ranged-hit-goblin',
  'if:defence-goblin'
]
MATCH (i)-[:`IF`]->(b:BoolExpression)-[:HAS_ATOM]->(atom)
OPTIONAL MATCH (atom)-[:COMPARED_TO]->(dr)
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
RETURN i.id AS if_id,
       coalesce(proc.name, labels(proc)[0]) AS procedure,
       b.combinator AS combinator,
       labels(atom) AS atom_labels,
       coalesce(atom.threshold, atom.name) AS atom_key,
       coalesce(dr.name, '') AS compared_to,
       count(DISTINCT t) AS then_n,
       count(DISTINCT e) AS else_n
ORDER BY if_id, atom_key
```

**Expect:** three `if_id`s; combinator **AND**; Circumstance key fighting Goblin; Compare threshold **14**; THEN≥1 and ELSE≥1 each.

### D3-P2 — Evidence → Goblin entity passage

```cypher
MATCH (i:If:IngestNode)-[:DOCUMENTED_BY]->(p:RulePassage)
WHERE i.id IN [
  'if:melee-hit-goblin',
  'if:ranged-hit-goblin',
  'if:defence-goblin'
]
RETURN i.id AS if_id, collect(DISTINCT p.id) AS passages
ORDER BY if_id
```

**Expect:** ≥ 1 passage per spine; passage ids/text clearly Goblin entity (not Bent/Scum neighbor).

### D3-P3 — No new rel vocabulary

```cypher
MATCH (i:If:IngestNode)-[r]->()
WHERE i.id CONTAINS 'goblin'
RETURN DISTINCT type(r) AS rel
ORDER BY rel
```

**Expect:** `FOR`, `IF`, `THEN`, `ELSE`, `DOCUMENTED_BY`, `CONFIRMS_SEED`, `INSTANCE_OF` only on the `If`. No `HAS_ATTACK` / `HAS_STAT`.

---

## Gate checklist

| Gate | Required |
|---|---|
| D1/D2 spines intact | **Required** |
| Goblin entity passage clean | **Required** |
| **D3-P0** | **Required** |
| **D3-P1** three AND spines DR14 | **Required** |
| **D3-P2** Goblin evidence | **Required** |
| **D3-P3** closed rels | **Required** |

---

## What ADA will do after a green handoff

1. Extend **R16** to prefer Goblin DR14 spines when the situation mentions Goblin (over default DR12).  
2. Graph + API/CONTEXT smokes (e.g. *I melee a Goblin — what's the DR?*).  
3. Definitional *What is a Goblin?* may still use entity-passage short-circuit; adjudication asks must use spines.  
4. Full sheet ontology only after ADA locks seed labels.

---

## Standing smokes (ADA, after handoff)

| Id | Prompt focus | Spine |
|---|---|---|
| **G1** | Melee a Goblin — DR? | `if:melee-hit-goblin` (14, not 12) |
| **G2** | Shoot a Goblin / bow — DR? | `if:ranged-hit-goblin` |
| **G3** | Defend against a Goblin — DR? | `if:defence-goblin` |

---

## Sync

`.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root, or paste into the pgb Cursor session. Reply with `docs/inbox/ai-dm-assistant-handoff-*.md`.
