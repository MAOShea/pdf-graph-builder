# Briefing 18: Altitude D — materialize Crit / fumble / rest / infection `If` spines (D2)

**For pdf-graph-builder agents.** Second **operational fill** under altitude D ([DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order)). Same closed vocabulary as [briefing-17](./pdf-graph-builder-briefing-17.md) / [handoff-15](../inbox/ai-dm-assistant-handoff-15.md).

**Prerequisite:** D1 Violence spines green on the operator DB (handoff-15). Scaffold still has `If` / `BoolExpression` / `Circumstance` / `Compare`. Section `crit-fumble-rest` + catalog `MAPS_TO_SECTION` for Crit / Fumble / Resting / Infection must remain green ([briefing-15](./pdf-graph-builder-briefing-15.md), [briefing-16](./pdf-graph-builder-briefing-16.md)).

**Do not** invent Crit/Fumble/Rest **SeedNode** labels in this briefing. Attach spines with `FOR` to **existing** procedure / play-structure seeds (below). Gap reports only if a FOR target is missing from scaffold.

---

## Framing (unchanged)

| Side | Role |
|---|---|
| **DM prompt** | Situation — **not** an IF/THEN/ELSE |
| **Rulebook** | Library of `If` spines |
| **pgb** | Materialize D2 spines + cite `crit-fumble-rest` passages |
| **ADA (later)** | Extend select hop ([R16](../../DESIGN.md#82116-r16--select-altitude-d-if-spines)) to load these spines |

Closed vocabulary only. No open LLM predicates. Status seed `Condition` ≠ `Circumstance` / `Compare`.

---

## Closed vocabulary (same as D1)

**Nodes:** `If`, `BoolExpression`, `Circumstance`, `Compare`, `Outcome`  
**Rels:** `FOR`, `IF`, `THEN`, `ELSE`, `HAS_ATOM`; reuse `COMPARED_TO` where a DR/threshold applies  
**Property:** `BoolExpression.combinator` ∈ {`LEAF`, `AND`, `OR`, `NOT`}

**Evidence:** every spine `DOCUMENTED_BY` → `RulePassage` with `section_id: "crit-fumble-rest"` (prefer `#p0`… passages from the section split — not a full-page Chunk).

---

## D2 scope — what to materialize

Bare Bones **Crit / fumble / rest** (section `crit-fumble-rest`). **Four spines** aligned to ADA standing smokes R1–R4. Extend `games/mork-borg/operational-spines.json` (or equivalent) — deterministic materializer, same path as D1 (`section_phase >= 2` full extract).

### 1. Crit on attack (natural 20) — smoke R1

```text
(:If {id: "if:crit-attack"})-[:FOR]->(:MeleeAttack)   // also emit twin FOR RangedAttack OR one If with two FOR — pick one pattern and document
(:If)-[:IF]->(:BoolExpression {combinator: "LEAF"})
(:BoolExpression)-[:HAS_ATOM]->(:Compare {op: "=", left: "natural_face", threshold: 20})
  // no COMPARED_TO DR — face equality, not DR12
(:If)-[:THEN]->(:Outcome)   // double damage
(:If)-[:THEN]->(:Outcome)   // armor / protection −1 tier
// ELSE omitted if book silent on "not a crit"
```

Book cue: Crit (natural 20) — double damage; armor reduced one tier. Cite crit intro / `#p0` (or the passage that holds Crit attack prose).

**Also cover defence crit if the same passage states it** — either a second `If` `FOR` `DefenseRoll` with the same Compare(face=20) pattern, or document that Bare Bones only defines attack crit in the cited passage (paste prose excerpt in handoff).

### 2. Fumble on defence (natural 1) — smoke R2

```text
(:If {id: "if:fumble-defence"})-[:FOR]->(:DefenseRoll)
(:If)-[:IF]->(:BoolExpression {combinator: "LEAF"})
(:BoolExpression)-[:HAS_ATOM]->(:Compare {op: "=", left: "natural_face", threshold: 1})
(:If)-[:THEN]->(:Outcome)   // double damage (to defender)
(:If)-[:THEN]->(:Outcome)   // armor −1 tier
```

Cite Fumble passage under `crit-fumble-rest`.

### 3. Rest — catch breath / drink (d4 HP) — smoke R3

No dedicated Rest seed. Use existing Tier-0 **`Downtime`** (or `ResolutionProcedure` if Downtime is awkward — prefer `Downtime`):

```text
(:If {id: "if:rest-catch-breath"})-[:FOR]->(:Downtime)
(:If)-[:IF]->(:BoolExpression {combinator: "LEAF"})
(:BoolExpression)-[:HAS_ATOM]->(:Circumstance {name: "catch breath and drink"})  // situating atom; true/false
(:If)-[:THEN]->(:Outcome)   // restore d4 HP
```

Cite Resting passage. Do **not** invent a `Rest` SeedNode in ADA without a seed PR.

### 4. Infection blocks normal rest benefit — smoke R4

```text
(:If {id: "if:infection-blocks-rest"})-[:FOR]->(:Downtime)
(:If)-[:IF]->(:BoolExpression {combinator: "AND"})
(:BoolExpression)-[:HAS_ATOM]->(:Circumstance {name: "Infected"})
(:BoolExpression)-[:HAS_ATOM]->(:Circumstance {name: "full night rest"})  // or single Circumstance "Infected character rests overnight" as LEAF — document choice
(:If)-[:THEN]->(:Outcome)   // no HP restore from rest / lose d6 HP instead (match Bare Bones wording on Outcomes)
```

Cite Infection / Resting passage that states infected do not benefit from resting. Prefer **`Circumstance`**, not status `Condition` label, for the Infected atom (status `Condition` remains d20-3.5 CharacterState shelf).

**Stable ids (required):**  
`if:crit-attack`, `if:fumble-defence`, `if:rest-catch-breath`, `if:infection-blocks-rest`  
(+ `bool:*`, `compare:natural-20` / `compare:natural-1`, `circumstance:*`, `outcome:*` children).

---

## Out of scope

| Deferred | Why |
|---|---|
| Violence DR12 spines | **D1** — already shipped; do not regress |
| Goblin DR14 / creature sheets | **D3** |
| New Tier-0/4 Crit/Rest SeedNode labels | Optional later ADA seed PR — not required for D2 if `FOR` Downtime / Melee / Defense works |
| Lore edges | Never |
| Changing R16 in ADA | ADA extends select hop **after** your green handoff |

---

## Ops path

1. Confirm D1 spines still present (`if:melee-hit-default` etc.) — do not delete them.
2. Confirm `crit-fumble-rest` Chunk + RulePassages + IndexEntry `MAPS_TO_SECTION` (briefing-16 P5).
3. Extend **operational spine materializer** + `operational-spines.json` for the four D2 spines.
4. Full `.\ingest-morkborg.ps1` with `section_phase >= 2` (product path). Recovery CLI OK for dev; handoff must be on Completed Document after full extract.
5. Handoff with **acceptance Cypher pasted**. No “ball with ADA” until D2-P0–P2 green.

**Contract SoT:** pgb owns `operational-spines.json` / manifest pointer; ADA promotes mirrors if needed.

---

## Acceptance gates (handoff must paste results)

### D2-P0 — D1 still green + section present

```cypher
MATCH (i:If:IngestNode)
WHERE i.id STARTS WITH 'if:melee' OR i.id STARTS WITH 'if:ranged' OR i.id STARTS WITH 'if:defence'
RETURN count(i) AS d1_spines
```

**Expect:** ≥ 3. Plus `crit-fumble-rest` passage-section Chunk exists.

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

**Expect:** 4 `if_id` rows; crit/fumble show `Compare` with threshold **20** / **1**; rest/infection show `Circumstance` atoms; `then_n` ≥ 1 each.

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

**Expect:** ≥ 1 passage per spine.

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

**Expect:** only `FOR`, `IF`, `THEN`, `ELSE`, `DOCUMENTED_BY`, `CONFIRMS_SEED`, `INSTANCE_OF` (as used). Guard chain uses `HAS_ATOM` / `COMPARED_TO` off BoolExpression/Compare — include those nodes in a second check if needed.

---

## Gate checklist (handoff)

| Gate | Required |
|---|---|
| D1 spines intact | **Required** |
| Briefing-15/16 `crit-fumble-rest` + catalog P5 | Keep green |
| **D2-P0** | **Required** |
| **D2-P1** four spines | **Required** |
| **D2-P2** evidence | **Required** |
| **D2-P3** closed rels | **Required** |

---

## What ADA will do after a green handoff

1. Extend **R16** select hop to load D2 spines when the situation matches (crit / fumble / rest / infected) — not cowboy short-circuits.  
2. Graph + CONTEXT smokes for R1–R4 (spine + `crit-fumble-rest` citation).  
3. Open **D3** only after those are green.

---

## Standing smokes (ADA, after handoff)

| Id | Prompt focus | Spine |
|---|---|---|
| **R1** | Crit melee natural 20 — damage + armor | `if:crit-attack` |
| **R2** | Fumbled defence natural 1 | `if:fumble-defence` |
| **R3** | Catch breath and drink — d4 HP | `if:rest-catch-breath` |
| **R4** | Infected — rest / overnight | `if:infection-blocks-rest` |

---

## Sync

`.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root, or paste this file into the pgb Cursor session. Reply with `docs/inbox/ai-dm-assistant-handoff-*.md`.
